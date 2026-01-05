"""
Módulo de Eventos WebSocket
============================

Gerencia emissão de eventos em tempo real via WebSocket (Socket.IO).

Eventos disponíveis:
- print_event: Novo evento de impressão recebido
- stats_update: Estatísticas atualizadas
- alert: Notificação de alerta
- printer_status: Status de impressora alterado
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Referência global ao socketio (será setada pelo servidor)
_socketio = None
_socketio_available = False


def init_websocket(socketio_instance):
    """
    Inicializa o módulo com a instância do SocketIO.
    
    Args:
        socketio_instance: Instância do Flask-SocketIO
    """
    global _socketio, _socketio_available
    _socketio = socketio_instance
    _socketio_available = socketio_instance is not None
    
    if _socketio_available:
        logger.info("✅ Módulo WebSocket inicializado")
    else:
        logger.warning("⚠️ WebSocket não disponível - eventos não serão emitidos")


def is_websocket_available() -> bool:
    """Verifica se WebSocket está disponível."""
    return _socketio_available and _socketio is not None


def emit_print_event(event_data: Dict[str, Any], room: Optional[str] = None):
    """
    Emite evento de nova impressão para clientes conectados.
    
    Args:
        event_data: Dados do evento de impressão
        room: Sala específica (opcional, None = broadcast)
    """
    if not is_websocket_available():
        return
    
    try:
        payload = {
            'type': 'print_event',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'user': event_data.get('user', 'Desconhecido'),
                'printer': event_data.get('printer_name', 'N/A'),
                'pages': event_data.get('pages_printed', 0),
                'document': event_data.get('document', 'N/A'),
                'color': event_data.get('color_mode', 'N/A'),
                'duplex': event_data.get('duplex', False),
            }
        }
        
        if room:
            _socketio.emit('print_event', payload, room=room)
        else:
            _socketio.emit('print_event', payload, broadcast=True)
        
        logger.debug(f"WebSocket: Evento de impressão emitido - {payload['data']['user']}")
    except Exception as e:
        logger.error(f"Erro ao emitir evento de impressão via WebSocket: {e}")


def emit_stats_update(stats: Dict[str, Any], room: Optional[str] = None):
    """
    Emite atualização de estatísticas do dashboard.
    
    Args:
        stats: Estatísticas atualizadas
        room: Sala específica (opcional)
    """
    if not is_websocket_available():
        return
    
    try:
        payload = {
            'type': 'stats_update',
            'timestamp': datetime.now().isoformat(),
            'data': stats
        }
        
        if room:
            _socketio.emit('stats_update', payload, room=room)
        else:
            _socketio.emit('stats_update', payload, broadcast=True)
        
        logger.debug("WebSocket: Estatísticas atualizadas emitidas")
    except Exception as e:
        logger.error(f"Erro ao emitir atualização de estatísticas via WebSocket: {e}")


def emit_alert(alert_type: str, message: str, level: str = 'info', 
               data: Optional[Dict] = None, room: Optional[str] = None):
    """
    Emite alerta/notificação para clientes.
    
    Args:
        alert_type: Tipo do alerta (quota, limit, warning, info)
        message: Mensagem do alerta
        level: Nível (info, warning, error, success)
        data: Dados adicionais
        room: Sala específica
    """
    if not is_websocket_available():
        return
    
    try:
        payload = {
            'type': 'alert',
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'level': level,
            'message': message,
            'data': data or {}
        }
        
        if room:
            _socketio.emit('alert', payload, room=room)
        else:
            _socketio.emit('alert', payload, broadcast=True)
        
        logger.debug(f"WebSocket: Alerta emitido - {alert_type}: {message}")
    except Exception as e:
        logger.error(f"Erro ao emitir alerta via WebSocket: {e}")


def emit_printer_status(printer_name: str, status: str, details: Optional[Dict] = None):
    """
    Emite mudança de status de impressora.
    
    Args:
        printer_name: Nome da impressora
        status: Novo status (online, offline, error, busy)
        details: Detalhes adicionais
    """
    if not is_websocket_available():
        return
    
    try:
        payload = {
            'type': 'printer_status',
            'timestamp': datetime.now().isoformat(),
            'printer': printer_name,
            'status': status,
            'details': details or {}
        }
        
        _socketio.emit('printer_status', payload, broadcast=True)
        logger.debug(f"WebSocket: Status de impressora emitido - {printer_name}: {status}")
    except Exception as e:
        logger.error(f"Erro ao emitir status de impressora via WebSocket: {e}")


def get_connected_clients() -> int:
    """
    Retorna número de clientes WebSocket conectados.
    
    Returns:
        Número de clientes conectados (0 se WebSocket não disponível)
    """
    if not is_websocket_available():
        return 0
    
    try:
        # Flask-SocketIO não expõe diretamente o número de clientes
        # Retornamos -1 para indicar que está disponível mas não sabemos
        return -1
    except Exception:
        return 0


# Handlers de eventos (serão registrados pelo servidor)
def register_handlers(socketio_instance):
    """
    Registra handlers de eventos WebSocket.
    
    Args:
        socketio_instance: Instância do Flask-SocketIO
    """
    if socketio_instance is None:
        return
    
    @socketio_instance.on('connect')
    def handle_connect():
        logger.info("WebSocket: Cliente conectado")
    
    @socketio_instance.on('disconnect')
    def handle_disconnect():
        logger.info("WebSocket: Cliente desconectado")
    
    @socketio_instance.on('join_dashboard')
    def handle_join_dashboard(data):
        """Cliente entra na sala do dashboard para receber atualizações."""
        from flask_socketio import join_room
        join_room('dashboard')
        logger.debug("WebSocket: Cliente entrou na sala 'dashboard'")
    
    @socketio_instance.on('leave_dashboard')
    def handle_leave_dashboard(data):
        """Cliente sai da sala do dashboard."""
        from flask_socketio import leave_room
        leave_room('dashboard')
        logger.debug("WebSocket: Cliente saiu da sala 'dashboard'")
    
    logger.info("✅ Handlers WebSocket registrados")
