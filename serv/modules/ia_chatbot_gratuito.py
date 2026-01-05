"""
Módulo de Chatbot usando APIs Gratuitas
Alternativas gratuitas ao OpenAI que não precisam de créditos
"""

import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests não instalado. APIs gratuitas não funcionarão.")

logger = logging.getLogger(__name__)

# APIs Gratuitas Disponíveis
APIS_GRATUITAS = {
    'huggingface': {
        'nome': 'Hugging Face Inference API',
        'url': 'https://api-inference.huggingface.co/models',
        'modelos': [
            'microsoft/DialoGPT-medium',
            'facebook/blenderbot-400M-distill',
            'google/flan-t5-base'
        ],
        'requer_token': False,  # Alguns modelos não precisam
        'limite': 'Sem limite oficial, mas pode ter rate limiting'
    },
    'ollama': {
        'nome': 'Ollama (Local)',
        'url': 'http://localhost:11434/api/generate',
        'modelos': ['llama2', 'mistral', 'codellama'],
        'requer_token': False,
        'limite': 'Ilimitado (local)'
    },
    'groq': {
        'nome': 'Groq API',
        'url': 'https://api.groq.com/openai/v1/chat/completions',
        'modelos': ['llama-3.1-8b', 'mixtral-8x7b'],
        'requer_token': True,
        'limite': '14,400 requests/dia (gratuito)'
    },
    'together': {
        'nome': 'Together AI',
        'url': 'https://api.together.xyz/v1/chat/completions',
        'modelos': ['meta-llama/Llama-2-7b-chat-hf'],
        'requer_token': True,
        'limite': '$25 créditos iniciais'
    },
    'deepseek': {
        'nome': 'DeepSeek API',
        'url': 'https://api.deepseek.com/v1/chat/completions',
        'modelos': ['deepseek-chat'],
        'requer_token': True,
        'limite': 'Créditos gratuitos disponíveis'
    }
}


def processar_pergunta_huggingface(pergunta: str, contexto: str = "") -> Dict:
    """
    Processa pergunta usando Hugging Face Inference API (gratuito)
    
    Args:
        pergunta: Pergunta do usuário
        contexto: Contexto adicional
        
    Returns:
        Dicionário com resposta
    """
    if not REQUESTS_AVAILABLE:
        return processar_pergunta_simples_local(pergunta, contexto)
    
    try:
        # Usa modelo DialoGPT (conversacional)
        url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        
        headers = {}
        # Opcional: adicionar token se tiver
        # headers["Authorization"] = f"Bearer {os.getenv('HUGGINGFACE_TOKEN')}"
        
        payload = {
            "inputs": f"{contexto}\nUsuário: {pergunta}\nAssistente:",
            "parameters": {
                "max_length": 150,
                "temperature": 0.7,
                "do_sample": True
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            resultado = response.json()
            if isinstance(resultado, list) and len(resultado) > 0:
                resposta = resultado[0].get('generated_text', '')
                # Limpa a resposta
                resposta = resposta.replace(f"{contexto}\nUsuário: {pergunta}\nAssistente:", "").strip()
                return {
                    'resposta': resposta or "Desculpe, não consegui processar sua pergunta.",
                    'metodo': 'Hugging Face',
                    'modelo': 'DialoGPT-medium'
                }
        
        # Fallback para modelo mais simples
        return processar_pergunta_simples_local(pergunta, contexto)
        
    except Exception as e:
        logger.error(f"Erro ao processar com Hugging Face: {e}")
        return processar_pergunta_simples_local(pergunta, contexto)


def processar_pergunta_ollama(pergunta: str, contexto: str = "", 
                              modelo: str = "llama2") -> Dict:
    """
    Processa pergunta usando Ollama (local, gratuito)
    
    Args:
        pergunta: Pergunta do usuário
        contexto: Contexto adicional
        modelo: Modelo a usar (llama2, mistral, etc.)
        
    Returns:
        Dicionário com resposta
    """
    if not REQUESTS_AVAILABLE:
        return {
            'resposta': "Biblioteca 'requests' não instalada. Execute: pip install requests",
            'metodo': 'Erro',
            'erro': 'requests não disponível'
        }
    
    try:
        url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": modelo,
            "prompt": f"{contexto}\n\nPergunta: {pergunta}\nResposta:",
            "stream": False
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            resultado = response.json()
            resposta = resultado.get('response', '').strip()
            
            return {
                'resposta': resposta or "Desculpe, não consegui processar sua pergunta.",
                'metodo': 'Ollama (Local)',
                'modelo': modelo
            }
        
        return processar_pergunta_simples_local(pergunta, contexto)
        
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama não está rodando localmente")
        return {
            'resposta': "Ollama não está disponível. Instale e inicie o Ollama para usar esta funcionalidade.",
            'metodo': 'Ollama (Não disponível)',
            'erro': 'Ollama não está rodando'
        }
    except Exception as e:
        logger.error(f"Erro ao processar com Ollama: {e}")
        return processar_pergunta_simples_local(pergunta, contexto)


def processar_pergunta_groq(pergunta: str, contexto: str = "", 
                           api_key: Optional[str] = None) -> Dict:
    """
    Processa pergunta usando Groq API (gratuito, 14k requests/dia)
    
    Args:
        pergunta: Pergunta do usuário
        contexto: Contexto adicional
        api_key: Chave da API Groq (opcional)
        
    Returns:
        Dicionário com resposta
    """
    if not REQUESTS_AVAILABLE:
        return processar_pergunta_simples_local(pergunta, contexto)
    
    try:
        if not api_key:
            api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            return processar_pergunta_simples_local(pergunta, contexto)
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": f"Você é um assistente especializado em análise de impressões hospitalares. {contexto}"},
                {"role": "user", "content": pergunta}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            resultado = response.json()
            resposta = resultado['choices'][0]['message']['content']
            
            return {
                'resposta': resposta,
                'metodo': 'Groq API',
                'modelo': 'llama-3.1-8b-instant'
            }
        
        return processar_pergunta_simples_local(pergunta, contexto)
        
    except Exception as e:
        logger.error(f"Erro ao processar com Groq: {e}")
        return processar_pergunta_simples_local(pergunta, contexto)


def processar_pergunta_simples_local(pergunta: str, contexto: str = "") -> Dict:
    """
    Processa pergunta usando processamento local simples (sempre disponível)
    
    Args:
        pergunta: Pergunta do usuário
        contexto: Contexto adicional
        
    Returns:
        Dicionário com resposta
    """
    pergunta_lower = pergunta.lower()
    
    # Respostas pré-definidas para perguntas comuns
    respostas = {
        'custo': 'Para verificar custos, acesse o dashboard ou use o endpoint /dashboard.',
        'usuário': 'Para ver estatísticas de usuários, acesse /usuarios.',
        'setor': 'Para ver estatísticas por setor, acesse /setores.',
        'impressora': 'Para ver estatísticas de impressoras, acesse /impressoras.',
        'relatório': 'Para gerar relatórios, acesse /dashboard e use a opção de exportar.',
        'ajuda': 'Posso ajudar com informações sobre custos, usuários, setores e impressoras. Faça uma pergunta específica!'
    }
    
    # Procura palavras-chave
    for palavra, resposta in respostas.items():
        if palavra in pergunta_lower:
            return {
                'resposta': resposta,
                'metodo': 'Processamento Local',
                'modelo': 'Regras Simples'
            }
    
    # Resposta genérica
    return {
        'resposta': 'Desculpe, não entendi sua pergunta. Tente perguntar sobre custos, usuários, setores ou impressoras.',
        'metodo': 'Processamento Local',
        'modelo': 'Regras Simples'
    }


def processar_pergunta_gratuita(conn: sqlite3.Connection, pergunta: str, 
                                 metodo: str = 'auto') -> Dict:
    """
    Função principal para processar perguntas usando APIs gratuitas
    
    Args:
        conn: Conexão com banco de dados
        pergunta: Pergunta do usuário
        metodo: 'auto', 'huggingface', 'ollama', 'groq', 'local'
        
    Returns:
        Dicionário com resposta
    """
    try:
        
        # Obtém contexto do banco
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
        Últimos 30 dias: {row[0] or 0} impressões, {row[1] or 0} páginas.
        """
        
        # Escolhe método
        if metodo == 'auto':
            # Tenta na ordem: Groq > Ollama > Hugging Face > Local
            groq_key = os.getenv('GROQ_API_KEY')
            if groq_key:
                metodo = 'groq'
            elif _ollama_disponivel():
                metodo = 'ollama'
            else:
                metodo = 'huggingface'
        
        # Processa com método escolhido
        if metodo == 'groq':
            return processar_pergunta_groq(pergunta, contexto)
        elif metodo == 'ollama':
            return processar_pergunta_ollama(pergunta, contexto)
        elif metodo == 'huggingface':
            return processar_pergunta_huggingface(pergunta, contexto)
        else:
            return processar_pergunta_simples_local(pergunta, contexto)
        
    except Exception as e:
        logger.error(f"Erro ao processar pergunta: {e}")
        return {
            'resposta': f'Erro ao processar pergunta: {str(e)}',
            'metodo': 'Erro',
            'erro': str(e)
        }


def _ollama_disponivel() -> bool:
    """Verifica se Ollama está disponível localmente"""
    if not REQUESTS_AVAILABLE:
        return False
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def listar_apis_disponiveis() -> List[Dict]:
    """
    Lista APIs gratuitas disponíveis e seu status
    
    Returns:
        Lista de APIs com status
    """
    import os
    
    apis = []
    
    for key, info in APIS_GRATUITAS.items():
        status = 'disponivel'
        motivo = ''
        
        if key == 'groq':
            if not os.getenv('GROQ_API_KEY'):
                status = 'nao_configurado'
                motivo = 'GROQ_API_KEY não configurada'
        elif key == 'ollama':
            if not _ollama_disponivel():
                status = 'nao_disponivel'
                motivo = 'Ollama não está rodando localmente'
        
        apis.append({
            'id': key,
            'nome': info['nome'],
            'status': status,
            'motivo': motivo,
            'limite': info['limite'],
            'requer_token': info['requer_token']
        })
    
    return apis

