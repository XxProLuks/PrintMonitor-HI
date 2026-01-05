"""
Módulo de Detecção de Anomalias usando Machine Learning
Identifica padrões suspeitos de impressão que podem indicar uso indevido ou desperdício
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas não disponível. Funcionalidades de detecção limitadas.")

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn não disponível. Usando detecção estatística simples.")


def obter_dados_para_analise(conn: sqlite3.Connection, dias: int = 30) -> List[Dict]:
    """
    Obtém dados de impressão para análise de anomalias
    
    Args:
        conn: Conexão com banco de dados
        dias: Número de dias de histórico
        
    Returns:
        Lista de eventos com features para análise
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.id,
                e.date,
                e.user,
                e.machine,
                e.printer_name,
                e.pages_printed,
                e.duplex,
                e.color_mode,
                e.sector,
                e.document_name,
                e.job_id
            FROM events e
            WHERE e.date >= ?
            ORDER BY e.date DESC
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        eventos = []
        for row in rows:
            data_evento = datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]
            hora = data_evento.hour
            dia_semana = data_evento.weekday()  # 0=segunda, 6=domingo
            
            folhas_fisicas = calcular_folhas_fisicas(row[5] or 0, row[6])
            
            eventos.append({
                'id': row[0],
                'data': data_evento,
                'user': row[2] or 'Desconhecido',
                'machine': row[3] or 'Desconhecido',
                'printer_name': row[4] or 'Desconhecido',
                'pages_printed': row[5] or 0,
                'folhas_fisicas': folhas_fisicas,
                'duplex': row[6] or 0,
                'color_mode': row[7] or 'Black & White',
                'sector': row[8] or 'Desconhecido',
                'document_name': row[9] or '',
                'job_id': row[10],
                'hora': hora,
                'dia_semana': dia_semana,
                'is_weekend': dia_semana >= 5,
                'is_night': hora < 6 or hora > 22,
                'is_color': 1 if row[7] == 'Color' else 0
            })
        
        return eventos
        
    except Exception as e:
        logger.error(f"Erro ao obter dados para análise: {e}")
        return []


def calcular_estatisticas_usuario(conn: sqlite3.Connection, usuario: str, dias: int = 30) -> Dict:
    """
    Calcula estatísticas normais de um usuário
    
    Args:
        conn: Conexão com banco de dados
        usuario: Nome do usuário
        dias: Período de análise
        
    Returns:
        Dicionário com estatísticas (média, desvio padrão, etc.)
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.pages_printed,
                e.duplex,
                e.date
            FROM events e
            WHERE e.user = ? AND e.date >= ?
        """
        
        rows = conn.execute(query, (usuario, data_inicio.isoformat())).fetchall()
        
        if not rows:
            return {
                'media_paginas': 0,
                'desvio_paginas': 0,
                'max_paginas': 0,
                'total_eventos': 0,
                'horarios_medios': []
            }
        
        paginas = []
        horas = []
        
        for row in rows:
            folhas = calcular_folhas_fisicas(row[0] or 0, row[1])
            paginas.append(folhas)
            
            data_evento = datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2]
            horas.append(data_evento.hour)
        
        if PANDAS_AVAILABLE:
            import numpy as np
            media = np.mean(paginas)
            desvio = np.std(paginas)
        else:
            media = sum(paginas) / len(paginas)
            variancia = sum((x - media) ** 2 for x in paginas) / len(paginas)
            desvio = math.sqrt(variancia)
        
        return {
            'media_paginas': media,
            'desvio_paginas': desvio,
            'max_paginas': max(paginas),
            'total_eventos': len(rows),
            'horarios_medios': horas
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas do usuário: {e}")
        return {}


def detectar_anomalias_isolation_forest(eventos: List[Dict]) -> List[Dict]:
    """
    Detecta anomalias usando Isolation Forest
    
    Args:
        eventos: Lista de eventos para análise
        
    Returns:
        Lista de eventos classificados como anômalos
    """
    if not SKLEARN_AVAILABLE or not PANDAS_AVAILABLE or len(eventos) < 10:
        return detectar_anomalias_estatisticas(eventos)
    
    try:
        # Prepara features
        features = []
        for evento in eventos:
            features.append([
                evento['folhas_fisicas'],
                evento['hora'],
                evento['dia_semana'],
                evento['is_weekend'],
                evento['is_night'],
                evento['is_color']
            ])
        
        X = np.array(features)
        
        # Normaliza features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Treina Isolation Forest
        isolation_forest = IsolationForest(
            contamination=0.1,  # Espera ~10% de anomalias
            random_state=42,
            n_estimators=100
        )
        isolation_forest.fit(X_scaled)
        
        # Prediz anomalias
        predicoes = isolation_forest.predict(X_scaled)
        scores = isolation_forest.score_samples(X_scaled)
        
        # Identifica anomalias (predição = -1)
        anomalias = []
        for i, evento in enumerate(eventos):
            if predicoes[i] == -1:
                evento['anomalia_score'] = float(scores[i])
                evento['tipo_anomalia'] = 'isolation_forest'
                evento['severidade'] = 'alta' if scores[i] < -0.5 else 'media'
                anomalias.append(evento)
        
        return anomalias
        
    except Exception as e:
        logger.error(f"Erro na detecção com Isolation Forest: {e}")
        return detectar_anomalias_estatisticas(eventos)


def detectar_anomalias_estatisticas(eventos: List[Dict]) -> List[Dict]:
    """
    Detecta anomalias usando métodos estatísticos simples
    
    Args:
        eventos: Lista de eventos para análise
        
    Returns:
        Lista de eventos classificados como anômalos
    """
    try:
        if not eventos:
            return []
        
        # Calcula estatísticas gerais
        folhas = [e['folhas_fisicas'] for e in eventos]
        
        if PANDAS_AVAILABLE:
            import numpy as np
            media = np.mean(folhas)
            desvio = np.std(folhas)
        else:
            media = sum(folhas) / len(folhas)
            variancia = sum((x - media) ** 2 for x in folhas) / len(folhas)
            desvio = math.sqrt(variancia)
        
        # Identifica outliers (Z-score > 3)
        anomalias = []
        for evento in eventos:
            z_score = abs((evento['folhas_fisicas'] - media) / desvio) if desvio > 0 else 0
            
            # Critérios de anomalia
            is_anomalia = False
            tipo_anomalia = []
            severidade = 'baixa'
            
            # Volume anormal
            if z_score > 3:
                is_anomalia = True
                tipo_anomalia.append('volume_anormal')
                severidade = 'alta'
            elif z_score > 2:
                is_anomalia = True
                tipo_anomalia.append('volume_atipico')
                severidade = 'media'
            
            # Horário incomum
            if evento['is_night']:
                is_anomalia = True
                tipo_anomalia.append('horario_incomum')
            
            # Fim de semana
            if evento['is_weekend']:
                is_anomalia = True
                tipo_anomalia.append('fim_semana')
            
            # Volume muito alto em uma única impressão
            if evento['folhas_fisicas'] > media * 5:
                is_anomalia = True
                tipo_anomalia.append('volume_excessivo')
                severidade = 'alta'
            
            if is_anomalia:
                evento['anomalia_score'] = z_score
                evento['tipo_anomalia'] = ', '.join(tipo_anomalia)
                evento['severidade'] = severidade
                anomalias.append(evento)
        
        return anomalias
        
    except Exception as e:
        logger.error(f"Erro na detecção estatística: {e}")
        return []


def detectar_padroes_suspeitos(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """
    Detecta padrões suspeitos de impressão
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Dicionário com anomalias detectadas e estatísticas
    """
    try:
        # Obtém dados
        eventos = obter_dados_para_analise(conn, dias)
        
        if not eventos:
            return {
                'anomalias': [],
                'total_eventos': 0,
                'total_anomalias': 0,
                'percentual_anomalias': 0,
                'metodo': 'sem_dados'
            }
        
        # Detecta anomalias
        if SKLEARN_AVAILABLE and len(eventos) >= 10:
            anomalias = detectar_anomalias_isolation_forest(eventos)
            metodo = 'Isolation Forest'
        else:
            anomalias = detectar_anomalias_estatisticas(eventos)
            metodo = 'Estatístico'
        
        # Agrupa por usuário
        anomalias_por_usuario = {}
        for anomalia in anomalias:
            usuario = anomalia['user']
            if usuario not in anomalias_por_usuario:
                anomalias_por_usuario[usuario] = []
            anomalias_por_usuario[usuario].append(anomalia)
        
        # Agrupa por tipo
        anomalias_por_tipo = {}
        for anomalia in anomalias:
            tipo = anomalia.get('tipo_anomalia', 'desconhecido')
            if tipo not in anomalias_por_tipo:
                anomalias_por_tipo[tipo] = []
            anomalias_por_tipo[tipo].append(anomalia)
        
        resultado = {
            'anomalias': anomalias[:100],  # Limita a 100 mais recentes
            'total_eventos': len(eventos),
            'total_anomalias': len(anomalias),
            'percentual_anomalias': (len(anomalias) / len(eventos) * 100) if eventos else 0,
            'metodo': metodo,
            'anomalias_por_usuario': {
                usuario: len(anoms) 
                for usuario, anoms in anomalias_por_usuario.items()
            },
            'anomalias_por_tipo': {
                tipo: len(anoms)
                for tipo, anoms in anomalias_por_tipo.items()
            },
            'top_usuarios_suspeitos': sorted(
                anomalias_por_usuario.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:10]
        }
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao detectar padrões suspeitos: {e}")
        return {
            'anomalias': [],
            'total_eventos': 0,
            'total_anomalias': 0,
            'percentual_anomalias': 0,
            'metodo': 'erro',
            'erro': str(e)
        }


def verificar_fraude_potencial(conn: sqlite3.Connection, usuario: str, dias: int = 7) -> Dict:
    """
    Verifica se um usuário específico apresenta padrões suspeitos
    
    Args:
        conn: Conexão com banco de dados
        usuario: Nome do usuário
        dias: Período de análise
        
    Returns:
        Dicionário com análise de fraude potencial
    """
    try:
        # Obtém eventos do usuário
        eventos = obter_dados_para_analise(conn, dias)
        eventos_usuario = [e for e in eventos if e['user'] == usuario]
        
        if not eventos_usuario:
            return {
                'usuario': usuario,
                'suspeito': False,
                'score_risco': 0,
                'motivos': []
            }
        
        # Calcula estatísticas do usuário
        stats = calcular_estatisticas_usuario(conn, usuario, dias=30)
        
        # Análise de padrões
        motivos = []
        score_risco = 0
        
        # Volume muito alto
        total_paginas = sum(e['folhas_fisicas'] for e in eventos_usuario)
        media_esperada = stats.get('media_paginas', 0) * len(eventos_usuario)
        
        if total_paginas > media_esperada * 2:
            motivos.append(f"Volume 2x maior que o normal ({total_paginas:.0f} vs {media_esperada:.0f})")
            score_risco += 30
        
        # Horários incomuns
        eventos_noite = sum(1 for e in eventos_usuario if e['is_night'])
        if eventos_noite > len(eventos_usuario) * 0.3:
            motivos.append(f"Muitas impressões em horário incomum ({eventos_noite}/{len(eventos_usuario)})")
            score_risco += 20
        
        # Fim de semana
        eventos_fds = sum(1 for e in eventos_usuario if e['is_weekend'])
        if eventos_fds > 0:
            motivos.append(f"Impressões em fim de semana ({eventos_fds})")
            score_risco += 15
        
        # Muitas impressões coloridas
        eventos_color = sum(1 for e in eventos_usuario if e['is_color'])
        if eventos_color > len(eventos_usuario) * 0.5:
            motivos.append(f"Alto uso de impressão colorida ({eventos_color}/{len(eventos_usuario)})")
            score_risco += 10
        
        # Impressões muito grandes
        max_paginas = max(e['folhas_fisicas'] for e in eventos_usuario)
        if max_paginas > 500:
            motivos.append(f"Impressão muito grande detectada ({max_paginas} páginas)")
            score_risco += 25
        
        suspeito = score_risco >= 30
        
        return {
            'usuario': usuario,
            'suspeito': suspeito,
            'score_risco': min(100, score_risco),
            'motivos': motivos,
            'total_eventos': len(eventos_usuario),
            'total_paginas': total_paginas,
            'recomendacao': 'investigar' if suspeito else 'normal'
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar fraude potencial: {e}")
        return {
            'usuario': usuario,
            'suspeito': False,
            'score_risco': 0,
            'motivos': [],
            'erro': str(e)
        }

