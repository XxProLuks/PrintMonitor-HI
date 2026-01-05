"""
Módulo de Alertas Inteligentes e Proativos
Sistema de alertas que aprende padrões e só alerta quando realmente necessário
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
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn não disponível. Usando regras simples.")


def obter_historico_alertas(conn: sqlite3.Connection, dias: int = 90) -> List[Dict]:
    """
    Obtém histórico de alertas e feedback do usuário
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de histórico
        
    Returns:
        Lista de alertas com feedback
    """
    try:
        # Verifica se existe tabela de feedback de alertas
        try:
            conn.execute("SELECT 1 FROM alerta_feedback LIMIT 1")
            tabela_existe = True
        except:
            tabela_existe = False
            # Cria tabela se não existir
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerta_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_alerta TEXT,
                    contexto TEXT,
                    relevante INTEGER,
                    data_feedback DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
        if tabela_existe:
            data_inicio = datetime.now() - timedelta(days=dias)
            rows = conn.execute(
                "SELECT tipo_alerta, contexto, relevante FROM alerta_feedback WHERE data_feedback >= ?",
                (data_inicio.isoformat(),)
            ).fetchall()
            
            return [
                {
                    'tipo': row[0],
                    'contexto': row[1],
                    'relevante': bool(row[2])
                }
                for row in rows
            ]
        
        return []
        
    except Exception as e:
        logger.error(f"Erro ao obter histórico de alertas: {e}")
        return []


def registrar_feedback_alerta(conn: sqlite3.Connection, tipo_alerta: str, 
                             contexto: str, relevante: bool):
    """
    Registra feedback do usuário sobre relevância de um alerta
    
    Args:
        conn: Conexão com banco de dados
        tipo_alerta: Tipo do alerta
        contexto: Contexto do alerta
        relevante: Se o alerta foi relevante
    """
    try:
        conn.execute("""
            INSERT INTO alerta_feedback (tipo_alerta, contexto, relevante)
            VALUES (?, ?, ?)
        """, (tipo_alerta, contexto, int(relevante)))
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar feedback: {e}")


def calcular_relevancia_alerta(conn: sqlite3.Connection, tipo_alerta: str, 
                               contexto: Dict) -> float:
    """
    Calcula relevância de um alerta baseado em histórico
    
    Args:
        conn: Conexão com banco de dados
        tipo_alerta: Tipo do alerta
        contexto: Contexto do alerta
        
    Returns:
        Score de relevância (0-1)
    """
    try:
        historico = obter_historico_alertas(conn)
        
        if not historico:
            # Sem histórico, retorna relevância padrão
            return 0.7
        
        # Filtra alertas similares
        alertas_similares = [
            a for a in historico
            if a['tipo'] == tipo_alerta
        ]
        
        if not alertas_similares:
            return 0.7
        
        # Calcula taxa de relevância
        relevantes = sum(1 for a in alertas_similares if a['relevante'])
        taxa_relevancia = relevantes / len(alertas_similares)
        
        return taxa_relevancia
        
    except Exception as e:
        logger.error(f"Erro ao calcular relevância: {e}")
        return 0.7


def gerar_alertas_inteligentes(conn: sqlite3.Connection, dias: int = 7) -> List[Dict]:
    """
    Gera alertas inteligentes baseados em padrões
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Lista de alertas priorizados
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        # Busca eventos recentes
        query = """
            SELECT 
                e.user,
                e.printer_name,
                e.pages_printed,
                e.duplex,
                e.color_mode,
                e.date,
                e.sector
            FROM events e
            WHERE e.date >= ?
            ORDER BY e.date DESC
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        if not rows:
            return []
        
        # Agrupa por usuário
        eventos_por_usuario = {}
        for row in rows:
            usuario = row[0] or 'Desconhecido'
            if usuario not in eventos_por_usuario:
                eventos_por_usuario[usuario] = []
            
            folhas = calcular_folhas_fisicas(row[2] or 0, row[3])
            eventos_por_usuario[usuario].append({
                'folhas': folhas,
                'data': row[5],
                'color': row[4] == 'Color'
            })
        
        alertas = []
        
        # Alerta: Aumento súbito de uso
        for usuario, eventos in eventos_por_usuario.items():
            if len(eventos) < 2:
                continue
            
            # Compara últimos 3 dias vs anteriores 3 dias
            agora = datetime.now()
            ultimos_3_dias = [e for e in eventos if (agora - e['data']).days <= 3]
            anteriores_3_dias = [e for e in eventos if 3 < (agora - e['data']).days <= 6]
            
            if ultimos_3_dias and anteriores_3_dias:
                total_recente = sum(e['folhas'] for e in ultimos_3_dias)
                total_anterior = sum(e['folhas'] for e in anteriores_3_dias)
                
                if total_anterior > 0:
                    aumento = (total_recente - total_anterior) / total_anterior
                    
                    if aumento > 0.5:  # Aumento de 50%+
                        relevancia = calcular_relevancia_alerta(
                            conn, 'aumento_uso', {'usuario': usuario, 'aumento': aumento}
                        )
                        
                        if relevancia > 0.3:  # Threshold de relevância
                            alertas.append({
                                'tipo': 'aumento_uso',
                                'titulo': f'Aumento de uso detectado',
                                'mensagem': f'{usuario} está imprimindo {aumento*100:.0f}% mais que o normal',
                                'usuario': usuario,
                                'severidade': 'media',
                                'relevancia': relevancia,
                                'data': agora,
                                'contexto': {'aumento': aumento, 'total_recente': total_recente}
                            })
        
        # Alerta: Uso excessivo de cor
        total_color = sum(1 for row in rows if row[4] == 'Color')
        total_geral = len(rows)
        
        if total_geral > 0:
            percentual_color = total_color / total_geral
            
            if percentual_color > 0.4:  # Mais de 40% em cor
                relevancia = calcular_relevancia_alerta(
                    conn, 'uso_excessivo_cor', {'percentual': percentual_color}
                )
                
                if relevancia > 0.3:
                    alertas.append({
                        'tipo': 'uso_excessivo_cor',
                        'titulo': 'Uso excessivo de impressão colorida',
                        'mensagem': f'{percentual_color*100:.0f}% das impressões são coloridas',
                        'severidade': 'media',
                        'relevancia': relevancia,
                        'data': datetime.now(),
                        'contexto': {'percentual': percentual_color}
                    })
        
        # Alerta: Baixo uso de duplex
        total_duplex = sum(1 for row in rows if row[3] == 1)
        total_simplex = sum(1 for row in rows if row[3] == 0)
        total_com_duplex = total_duplex + total_simplex
        
        if total_com_duplex > 10:
            percentual_duplex = total_duplex / total_com_duplex
            
            if percentual_duplex < 0.2:  # Menos de 20% em duplex
                relevancia = calcular_relevancia_alerta(
                    conn, 'baixo_uso_duplex', {'percentual': percentual_duplex}
                )
                
                if relevancia > 0.3:
                    alertas.append({
                        'tipo': 'baixo_uso_duplex',
                        'titulo': 'Baixo uso de impressão duplex',
                        'mensagem': f'Apenas {percentual_duplex*100:.0f}% das impressões usam duplex',
                        'severidade': 'baixa',
                        'relevancia': relevancia,
                        'data': datetime.now(),
                        'contexto': {'percentual': percentual_duplex}
                    })
        
        # Ordena por relevância
        alertas.sort(key=lambda x: x['relevancia'], reverse=True)
        
        return alertas
        
    except Exception as e:
        logger.error(f"Erro ao gerar alertas inteligentes: {e}")
        return []


def filtrar_alertas_por_relevancia(alertas: List[Dict], threshold: float = 0.4) -> List[Dict]:
    """
    Filtra alertas por relevância mínima
    
    Args:
        alertas: Lista de alertas
        threshold: Threshold de relevância mínima
        
    Returns:
        Lista de alertas filtrados
    """
    return [a for a in alertas if a.get('relevancia', 0) >= threshold]


def priorizar_alertas(alertas: List[Dict]) -> List[Dict]:
    """
    Prioriza alertas por severidade e relevância
    
    Args:
        alertas: Lista de alertas
        
    Returns:
        Lista de alertas priorizados
    """
    severidade_peso = {
        'alta': 3,
        'media': 2,
        'baixa': 1
    }
    
    for alerta in alertas:
        severidade = alerta.get('severidade', 'baixa')
        relevancia = alerta.get('relevancia', 0.5)
        
        # Score de prioridade
        alerta['prioridade_score'] = severidade_peso.get(severidade, 1) * relevancia
    
    # Ordena por prioridade
    alertas.sort(key=lambda x: x.get('prioridade_score', 0), reverse=True)
    
    return alertas

