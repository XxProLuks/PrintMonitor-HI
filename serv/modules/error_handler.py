"""
Módulo de Tratamento de Erros
==============================

Fornece funções e decorators para tratamento consistente de erros
em toda a aplicação.

Autor: Print Monitor Team
Versão: 1.0.0
"""

import logging
import traceback
from functools import wraps
from typing import Callable, Any
from flask import jsonify, request

logger = logging.getLogger(__name__)


class PrintMonitorError(Exception):
    """Exceção base para erros do sistema"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(PrintMonitorError):
    """Erro de validação"""
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, status_code=400, details=details)
        self.field = field


class DatabaseError(PrintMonitorError):
    """Erro de banco de dados"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=500, details=details)


class AuthenticationError(PrintMonitorError):
    """Erro de autenticação"""
    def __init__(self, message: str = "Não autenticado", details: dict = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(PrintMonitorError):
    """Erro de autorização"""
    def __init__(self, message: str = "Acesso negado", details: dict = None):
        super().__init__(message, status_code=403, details=details)


def handle_errors(f: Callable) -> Callable:
    """
    Decorator para tratamento automático de erros.
    
    Captura exceções e retorna respostas JSON apropriadas.
    
    Usage:
        @app.route("/api/endpoint")
        @handle_errors
        def my_endpoint():
            # código que pode lançar exceções
            return jsonify({"status": "ok"})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except PrintMonitorError as e:
            # Erro conhecido do sistema
            logger.warning(f"⚠️ {e.__class__.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "status_code": e.status_code,
                "details": e.details
            }), e.status_code
        except ValueError as e:
            # Erro de validação genérico
            logger.warning(f"⚠️ Erro de validação: {e}")
            return jsonify({
                "error": str(e),
                "status_code": 400
            }), 400
        except KeyError as e:
            # Campo obrigatório ausente
            logger.warning(f"⚠️ Campo obrigatório ausente: {e}")
            return jsonify({
                "error": f"Campo obrigatório ausente: {e}",
                "status_code": 400
            }), 400
        except Exception as e:
            # Erro inesperado
            logger.error(
                f"❌ Erro inesperado em {f.__name__}: {e}",
                exc_info=True  # Inclui traceback completo
            )
            return jsonify({
                "error": "Erro interno do servidor",
                "status_code": 500,
                "message": str(e) if logger.level <= logging.DEBUG else None
            }), 500
    
    return wrapper


def handle_database_errors(f: Callable) -> Callable:
    """
    Decorator específico para tratamento de erros de banco de dados.
    
    Usage:
        @app.route("/api/endpoint")
        @handle_database_errors
        def my_endpoint():
            with get_db_connection() as conn:
                # operações de banco
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            import sqlite3
            
            if isinstance(e, sqlite3.OperationalError):
                logger.error(f"❌ Erro operacional do banco: {e}", exc_info=True)
                return jsonify({
                    "error": "Erro ao executar operação no banco de dados",
                    "status_code": 500
                }), 500
            elif isinstance(e, sqlite3.DatabaseError):
                logger.error(f"❌ Erro de banco de dados: {e}", exc_info=True)
                return jsonify({
                    "error": "Erro de integridade do banco de dados",
                    "status_code": 500
                }), 500
            elif isinstance(e, sqlite3.IntegrityError):
                logger.warning(f"⚠️ Erro de integridade: {e}")
                return jsonify({
                    "error": "Violação de integridade de dados",
                    "status_code": 409
                }), 409
            else:
                # Re-raise para ser tratado por handle_errors
                raise
    
    return wrapper


def log_error_with_context(error: Exception, context: dict = None):
    """
    Registra um erro com contexto adicional.
    
    Args:
        error: Exceção ocorrida
        context: Dicionário com contexto adicional
    """
    context = context or {}
    
    # Adiciona informações da requisição se disponível
    try:
        if request:
            context.update({
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get("User-Agent")
            })
    except:
        pass
    
    logger.error(
        f"❌ {error.__class__.__name__}: {str(error)}",
        extra={"context": context},
        exc_info=True
    )


def format_error_response(error: Exception, include_details: bool = False) -> dict:
    """
    Formata uma resposta de erro padronizada.
    
    Args:
        error: Exceção ocorrida
        include_details: Se deve incluir detalhes técnicos
        
    Returns:
        Dict com resposta formatada
    """
    response = {
        "error": str(error),
        "status_code": 500
    }
    
    if isinstance(error, PrintMonitorError):
        response.update({
            "error": error.message,
            "status_code": error.status_code,
            "details": error.details
        })
    
    if include_details and logger.level <= logging.DEBUG:
        response["traceback"] = traceback.format_exc()
    
    return response

