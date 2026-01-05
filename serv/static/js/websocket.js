/**
 * WebSocket Client para atualizações em tempo real
 * Print Monitor - Dashboard em Tempo Real
 */

// Configuração
const WS_RECONNECT_INTERVAL = 5000;  // 5 segundos
const WS_PING_INTERVAL = 30000;      // 30 segundos

// Estado
let socket = null;
let isConnected = false;
let reconnectTimer = null;
let pingTimer = null;

/**
 * Inicializa a conexão WebSocket
 */
function initWebSocket() {
    // Verifica se Socket.IO está disponível
    if (typeof io === 'undefined') {
        console.warn('Socket.IO não disponível. Atualizações em tempo real desabilitadas.');
        updateConnectionStatus(false, 'Socket.IO não carregado');
        return;
    }

    try {
        // Conecta ao servidor
        socket = io({
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity
        });

        // Eventos de conexão
        socket.on('connect', onConnect);
        socket.on('disconnect', onDisconnect);
        socket.on('connect_error', onConnectError);
        
        // Eventos de dados
        socket.on('connected', onServerConnected);
        socket.on('subscribed', onSubscribed);
        socket.on('new_print_event', onNewPrintEvent);
        socket.on('stats_update', onStatsUpdate);
        socket.on('pong', onPong);

    } catch (error) {
        console.error('Erro ao inicializar WebSocket:', error);
        updateConnectionStatus(false, 'Erro de conexão');
    }
}

/**
 * Handlers de eventos de conexão
 */
function onConnect() {
    console.log('🔌 WebSocket conectado');
    isConnected = true;
    updateConnectionStatus(true);
    
    // Inscreve-se no dashboard
    socket.emit('subscribe_dashboard');
    
    // Inicia ping periódico
    startPing();
}

function onDisconnect(reason) {
    console.log('🔌 WebSocket desconectado:', reason);
    isConnected = false;
    updateConnectionStatus(false, reason);
    stopPing();
}

function onConnectError(error) {
    console.error('❌ Erro de conexão WebSocket:', error);
    updateConnectionStatus(false, 'Erro de conexão');
}

function onServerConnected(data) {
    console.log('✅ Servidor confirmou conexão:', data);
    showNotification('Conectado em tempo real', 'success');
}

function onSubscribed(data) {
    console.log('📺 Inscrito no room:', data.room);
}

/**
 * Handler para novo evento de impressão
 */
function onNewPrintEvent(data) {
    console.log('🖨️ Novo evento de impressão:', data);
    
    const event = data.event;
    
    // Atualiza a tabela de eventos recentes (se existir)
    const tableBody = document.querySelector('#eventos-recentes tbody, #recent-events tbody');
    if (tableBody) {
        const newRow = document.createElement('tr');
        newRow.classList.add('new-event');
        newRow.innerHTML = `
            <td>${event.user || '-'}</td>
            <td>${event.printer_name || '-'}</td>
            <td>${event.pages || 1}</td>
            <td>${event.date || '-'}</td>
            <td>${event.document || '-'}</td>
        `;
        
        // Insere no topo
        tableBody.insertBefore(newRow, tableBody.firstChild);
        
        // Remove animação após 3 segundos
        setTimeout(() => newRow.classList.remove('new-event'), 3000);
        
        // Limita a 10 linhas
        while (tableBody.children.length > 10) {
            tableBody.removeChild(tableBody.lastChild);
        }
    }
    
    // Mostra notificação toast
    showNotification(
        `Nova impressão: ${event.user} - ${event.pages} páginas`,
        'info'
    );
}

/**
 * Handler para atualização de estatísticas
 */
function onStatsUpdate(data) {
    console.log('📊 Estatísticas atualizadas:', data);
    
    // Atualiza contadores no dashboard
    updateElement('#total-hoje, .stat-total-hoje', data.total_hoje);
    updateElement('#paginas-hoje, .stat-paginas-hoje', data.paginas_hoje);
    updateElement('#folhas-hoje, .stat-folhas-hoje', data.folhas_hoje);
    updateElement('#usuarios-ativos, .stat-usuarios-ativos', data.usuarios_ativos);
    
    // Dispara evento customizado
    document.dispatchEvent(new CustomEvent('statsUpdated', { detail: data }));
}

function onPong(data) {
    console.debug('🏓 Pong recebido:', data.time);
}

/**
 * Funções auxiliares
 */
function updateConnectionStatus(connected, message = '') {
    const indicator = document.querySelector('#ws-status, .ws-indicator');
    if (indicator) {
        indicator.classList.toggle('connected', connected);
        indicator.classList.toggle('disconnected', !connected);
        indicator.title = connected ? 'Tempo real ativo' : `Desconectado: ${message}`;
        
        // Atualiza ícone
        const icon = indicator.querySelector('i, .icon');
        if (icon) {
            icon.className = connected ? 'fas fa-wifi' : 'fas fa-wifi-slash';
        }
    }
    
    // Atualiza badge
    const badge = document.querySelector('#ws-badge, .ws-badge');
    if (badge) {
        badge.textContent = connected ? 'AO VIVO' : 'OFFLINE';
        badge.className = `ws-badge ${connected ? 'live' : 'offline'}`;
    }
}

function updateElement(selector, value) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
        if (el) {
            // Anima a mudança
            el.classList.add('value-changed');
            el.textContent = typeof value === 'number' ? value.toLocaleString('pt-BR') : value;
            setTimeout(() => el.classList.remove('value-changed'), 1000);
        }
    });
}

function showNotification(message, type = 'info') {
    // Verifica se existe sistema de toast
    if (typeof Toastify !== 'undefined') {
        Toastify({
            text: message,
            duration: 3000,
            gravity: 'top',
            position: 'right',
            backgroundColor: type === 'success' ? '#28a745' : 
                            type === 'error' ? '#dc3545' : '#17a2b8'
        }).showToast();
    } else {
        // Fallback: cria toast simples
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 8px;
            background: ${type === 'success' ? '#28a745' : 
                        type === 'error' ? '#dc3545' : '#17a2b8'};
            color: white;
            font-weight: 500;
            z-index: 9999;
            animation: slideIn 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

function startPing() {
    stopPing();
    pingTimer = setInterval(() => {
        if (socket && isConnected) {
            socket.emit('ping');
        }
    }, WS_PING_INTERVAL);
}

function stopPing() {
    if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
    }
}

/**
 * CSS para animações
 */
function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .new-event {
            animation: highlight 3s ease;
        }
        @keyframes highlight {
            0% { background-color: rgba(40, 167, 69, 0.3); }
            100% { background-color: transparent; }
        }
        .value-changed {
            animation: pulse 0.5s ease;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); color: #28a745; }
        }
        .ws-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
        }
        .ws-indicator.connected {
            color: #28a745;
        }
        .ws-indicator.disconnected {
            color: #dc3545;
        }
        .ws-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .ws-badge.live {
            background: #28a745;
            color: white;
            animation: blink 2s infinite;
        }
        .ws-badge.offline {
            background: #6c757d;
            color: white;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
    `;
    document.head.appendChild(style);
}

// Inicializa quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    injectStyles();
    initWebSocket();
});

// Exporta para uso global
window.PrintMonitorWS = {
    init: initWebSocket,
    isConnected: () => isConnected,
    socket: () => socket
};

