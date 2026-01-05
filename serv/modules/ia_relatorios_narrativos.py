"""
Módulo de Geração Automática de Relatórios Narrativos
IA que gera relatórios em linguagem natural a partir dos dados
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai não disponível. Usando geração simples de texto.")


def obter_estatisticas_periodo(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """
    Obtém estatísticas do período
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Dicionário com estatísticas
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                COUNT(*) as total_impressoes,
                SUM(pages_printed) as total_paginas_logicas,
                SUM(CASE WHEN duplex = 1 THEN 1 ELSE 0 END) as total_duplex,
                SUM(CASE WHEN color_mode = 'Color' THEN 1 ELSE 0 END) as total_color,
                COUNT(DISTINCT user) as usuarios_unicos,
                COUNT(DISTINCT printer_name) as impressoras_unicas
            FROM events
            WHERE date >= ?
        """
        
        row = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        if not row:
            return {}
        
        row = row[0]
        
        # Calcula folhas físicas
        query_detalhes = """
            SELECT pages_printed, duplex
            FROM events
            WHERE date >= ?
        """
        detalhes = conn.execute(query_detalhes, (data_inicio.isoformat(),)).fetchall()
        
        total_folhas_fisicas = sum(calcular_folhas_fisicas(d[0] or 0, d[1]) for d in detalhes)
        
        return {
            'total_impressoes': row[0] or 0,
            'total_paginas_logicas': row[1] or 0,
            'total_folhas_fisicas': total_folhas_fisicas,
            'total_duplex': row[2] or 0,
            'total_color': row[3] or 0,
            'usuarios_unicos': row[4] or 0,
            'impressoras_unicas': row[5] or 0,
            'periodo_dias': dias
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {}


def gerar_relatorio_narrativo_simples(conn: sqlite3.Connection, dias: int = 30) -> str:
    """
    Gera relatório narrativo simples
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Texto do relatório
    """
    try:
        stats = obter_estatisticas_periodo(conn, dias)
        
        if not stats:
            return "Não há dados disponíveis para o período solicitado."
        
        # Calcula percentuais
        percentual_duplex = (stats['total_duplex'] / stats['total_impressoes'] * 100) if stats['total_impressoes'] > 0 else 0
        percentual_color = (stats['total_color'] / stats['total_impressoes'] * 100) if stats['total_impressoes'] > 0 else 0
        
        # Gera texto
        relatorio = f"""
RELATÓRIO DE IMPRESSÕES - ÚLTIMOS {dias} DIAS

RESUMO EXECUTIVO
----------------
No período analisado, foram realizadas {stats['total_impressoes']:,} impressões, totalizando {stats['total_folhas_fisicas']:,} folhas físicas de papel.

ANÁLISE DE USO
--------------
- Usuários únicos: {stats['usuarios_unicos']}
- Impressoras utilizadas: {stats['impressoras_unicas']}
- Média diária: {stats['total_impressoes'] / dias:.1f} impressões por dia

EFICIÊNCIA
----------
- Impressões duplex: {stats['total_duplex']} ({percentual_duplex:.1f}% do total)
- Impressões coloridas: {stats['total_color']} ({percentual_color:.1f}% do total)

"""
        
        # Adiciona recomendações
        if percentual_duplex < 30:
            relatorio += "RECOMENDAÇÃO: Considere aumentar o uso de impressão duplex para reduzir custos.\n\n"
        
        if percentual_color > 40:
            relatorio += "RECOMENDAÇÃO: Avalie se todas as impressões coloridas são necessárias.\n\n"
        
        relatorio += f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        
        return relatorio.strip()
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        return f"Erro ao gerar relatório: {str(e)}"


def gerar_relatorio_narrativo_openai(conn: sqlite3.Connection, dias: int = 30, 
                                    api_key: Optional[str] = None) -> str:
    """
    Gera relatório narrativo usando OpenAI GPT
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        api_key: Chave da API OpenAI
        
    Returns:
        Texto do relatório
    """
    if not OPENAI_AVAILABLE or not api_key:
        return gerar_relatorio_narrativo_simples(conn, dias)
    
    try:
        stats = obter_estatisticas_periodo(conn, dias)
        
        if not stats:
            return "Não há dados disponíveis para o período solicitado."
        
        # Prepara dados para o GPT
        dados_texto = f"""
Estatísticas dos últimos {dias} dias:
- Total de impressões: {stats['total_impressoes']}
- Total de folhas físicas: {stats['total_folhas_fisicas']}
- Usuários únicos: {stats['usuarios_unicos']}
- Impressoras utilizadas: {stats['impressoras_unicas']}
- Impressões duplex: {stats['total_duplex']}
- Impressões coloridas: {stats['total_color']}
"""
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um analista especializado em relatórios de impressões hospitalares. Gere relatórios claros, objetivos e com insights acionáveis."},
                {"role": "user", "content": f"Gere um relatório narrativo sobre impressões hospitalares com base nestes dados:\n{dados_texto}\n\nInclua resumo executivo, análise de uso, eficiência e recomendações."}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório com OpenAI: {e}")
        return gerar_relatorio_narrativo_simples(conn, dias)


def gerar_relatorio_narrativo(conn: sqlite3.Connection, dias: int = 30, 
                             api_key: Optional[str] = None) -> Dict:
    """
    Função principal para gerar relatório narrativo
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        api_key: Chave da API OpenAI (opcional)
        
    Returns:
        Dicionário com relatório e metadados
    """
    try:
        if OPENAI_AVAILABLE and api_key:
            texto = gerar_relatorio_narrativo_openai(conn, dias, api_key)
            metodo = 'OpenAI GPT'
        else:
            texto = gerar_relatorio_narrativo_simples(conn, dias)
            metodo = 'Simples'
        
        return {
            'texto': texto,
            'metodo': metodo,
            'periodo_dias': dias,
            'data_geracao': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        return {
            'texto': f'Erro ao gerar relatório: {str(e)}',
            'metodo': 'Erro',
            'erro': str(e)
        }

