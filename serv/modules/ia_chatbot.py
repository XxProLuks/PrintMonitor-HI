"""
Módulo de Chatbot Inteligente
Assistente virtual que responde perguntas sobre impressões, custos e relatórios
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai não disponível. Usando processamento de linguagem natural simples.")

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers não disponível. Usando processamento simples.")


def extrair_intencao(pergunta: str) -> Dict:
    """
    Extrai intenção da pergunta usando processamento de linguagem natural simples
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        Dicionário com intenção e parâmetros
    """
    pergunta_lower = pergunta.lower()
    
    # Padrões de intenção
    intencoes = {
        'custo_total': ['quanto', 'custo', 'gasto', 'valor total', 'total gasto'],
        'custo_usuario': ['quanto', 'usuário', 'user', 'pessoa'],
        'custo_setor': ['quanto', 'setor', 'departamento'],
        'custo_periodo': ['quanto', 'mês', 'semana', 'dia', 'período'],
        'top_usuarios': ['top', 'mais', 'usuários', 'users', 'quem mais'],
        'top_setores': ['top', 'mais', 'setores', 'departamentos'],
        'estatisticas': ['estatísticas', 'estatisticas', 'dados', 'números', 'métricas'],
        'relatorio': ['relatório', 'relatorio', 'report', 'exportar'],
        'previsao': ['previsão', 'previsao', 'futuro', 'próximo', 'proximo'],
        'anomalias': ['anomalia', 'problema', 'erro', 'suspeito', 'estranho']
    }
    
    intencao_detectada = None
    confianca = 0.0
    
    for intencao, palavras_chave in intencoes.items():
        matches = sum(1 for palavra in palavras_chave if palavra in pergunta_lower)
        if matches > 0:
            confianca_atual = matches / len(palavras_chave)
            if confianca_atual > confianca:
                confianca = confianca_atual
                intencao_detectada = intencao
    
    # Extrai parâmetros
    parametros = {}
    
    # Período
    if 'hoje' in pergunta_lower:
        parametros['periodo'] = 'hoje'
    elif 'semana' in pergunta_lower:
        parametros['periodo'] = 'semana'
    elif 'mês' in pergunta_lower or 'mes' in pergunta_lower:
        parametros['periodo'] = 'mes'
    elif 'ano' in pergunta_lower:
        parametros['periodo'] = 'ano'
    
    # Usuário
    match = re.search(r'usu[áa]rio\s+(\w+)', pergunta_lower)
    if match:
        parametros['usuario'] = match.group(1)
    
    # Setor
    match = re.search(r'setor\s+(\w+)', pergunta_lower)
    if match:
        parametros['setor'] = match.group(1)
    
    return {
        'intencao': intencao_detectada or 'geral',
        'confianca': confianca,
        'parametros': parametros
    }


def processar_pergunta_simples(conn: sqlite3.Connection, pergunta: str) -> Dict:
    """
    Processa pergunta usando processamento simples
    
    Args:
        conn: Conexão com banco de dados
        pergunta: Pergunta do usuário
        
    Returns:
        Dicionário com resposta
    """
    try:
        intencao = extrair_intencao(pergunta)
        
        if intencao['intencao'] == 'custo_total':
            periodo = intencao['parametros'].get('periodo', 'mes')
            
            if periodo == 'hoje':
                data_inicio = datetime.now().replace(hour=0, minute=0, second=0)
            elif periodo == 'semana':
                data_inicio = datetime.now() - timedelta(days=7)
            elif periodo == 'mes':
                data_inicio = datetime.now() - timedelta(days=30)
            else:
                data_inicio = datetime.now() - timedelta(days=365)
            
            query = """
                SELECT pages_printed, duplex, color_mode
                FROM events
                WHERE date >= ?
            """
            rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
            
            total = 0
            for row in rows:
                folhas = calcular_folhas_fisicas(row[0] or 0, row[1])
                custo = folhas * (0.10 if row[2] == 'Color' else 0.05)
                total += custo
            
            return {
                'resposta': f'O custo total no período {periodo} foi de R$ {total:.2f}',
                'dados': {'custo_total': total, 'periodo': periodo}
            }
        
        elif intencao['intencao'] == 'top_usuarios':
            query = """
                SELECT user, SUM(pages_printed) as total
                FROM events
                WHERE date >= date('now', '-30 days')
                GROUP BY user
                ORDER BY total DESC
                LIMIT 5
            """
            rows = conn.execute(query).fetchall()
            
            usuarios = [{'usuario': row[0], 'paginas': row[1]} for row in rows]
            
            resposta = "Top 5 usuários:\n"
            for i, u in enumerate(usuarios, 1):
                resposta += f"{i}. {u['usuario']}: {u['paginas']} páginas\n"
            
            return {
                'resposta': resposta,
                'dados': {'usuarios': usuarios}
            }
        
        elif intencao['intencao'] == 'estatisticas':
            query = """
                SELECT 
                    COUNT(*) as total_impressoes,
                    SUM(pages_printed) as total_paginas
                FROM events
                WHERE date >= date('now', '-30 days')
            """
            row = conn.execute(query).fetchone()
            
            return {
                'resposta': f'Estatísticas dos últimos 30 dias:\n'
                           f'Total de impressões: {row[0]}\n'
                           f'Total de páginas: {row[1]}',
                'dados': {'impressoes': row[0], 'paginas': row[1]}
            }
        
        else:
            return {
                'resposta': 'Desculpe, não entendi sua pergunta. Tente perguntar sobre custos, usuários ou estatísticas.',
                'dados': {}
            }
        
    except Exception as e:
        logger.error(f"Erro ao processar pergunta: {e}")
        return {
            'resposta': f'Erro ao processar pergunta: {str(e)}',
            'dados': {},
            'erro': str(e)
        }


def processar_pergunta_openai(conn: sqlite3.Connection, pergunta: str, 
                              api_key: Optional[str] = None) -> Dict:
    """
    Processa pergunta usando OpenAI GPT
    
    Args:
        conn: Conexão com banco de dados
        pergunta: Pergunta do usuário
        api_key: Chave da API OpenAI (opcional)
        
    Returns:
        Dicionário com resposta
    """
    if not OPENAI_AVAILABLE or not api_key:
        return processar_pergunta_simples(conn, pergunta)
    
    try:
        # Obtém dados do banco para contexto
        query = """
            SELECT 
                COUNT(*) as total_impressoes,
                SUM(pages_printed) as total_paginas
            FROM events
            WHERE date >= date('now', '-30 days')
        """
        row = conn.execute(query).fetchone()
        
        contexto = f"""
        Sistema de monitoramento de impressões hospitalar.
        Últimos 30 dias: {row[0]} impressões, {row[1]} páginas.
        """
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Você é um assistente especializado em análise de impressões hospitalares. {contexto}"},
                {"role": "user", "content": pergunta}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        resposta = response.choices[0].message.content
        
        return {
            'resposta': resposta,
            'dados': {'metodo': 'openai'},
            'modelo': 'gpt-3.5-turbo'
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar com OpenAI: {e}")
        return processar_pergunta_simples(conn, pergunta)


def processar_pergunta(conn: sqlite3.Connection, pergunta: str, 
                       api_key: Optional[str] = None) -> Dict:
    """
    Função principal para processar perguntas
    
    Args:
        conn: Conexão com banco de dados
        pergunta: Pergunta do usuário
        api_key: Chave da API OpenAI (opcional)
        
    Returns:
        Dicionário com resposta
    """
    if OPENAI_AVAILABLE and api_key:
        return processar_pergunta_openai(conn, pergunta, api_key)
    else:
        return processar_pergunta_simples(conn, pergunta)

