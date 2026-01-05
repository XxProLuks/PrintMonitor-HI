"""
Módulo Centralizado de Validação
=================================

Fornece funções de validação reutilizáveis para todo o sistema.
Centraliza a lógica de validação para manter consistência.

Autor: Print Monitor Team
Versão: 1.0.0
"""

import re
from typing import Optional, Union, List, Dict, Any
from datetime import datetime


# =============================================================================
# VALIDAÇÃO DE STRINGS
# =============================================================================

def validar_string(
    valor: Any,
    nome_campo: str = "campo",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    permitir_vazio: bool = False,
    padrao: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Valida uma string.
    
    Args:
        valor: Valor a validar
        nome_campo: Nome do campo (para mensagens de erro)
        min_length: Comprimento mínimo
        max_length: Comprimento máximo
        permitir_vazio: Se permite string vazia
        padrao: Valor padrão se None ou vazio
        
    Returns:
        Tuple (valido, mensagem_erro)
    """
    # Aplica valor padrão
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        if padrao is not None:
            valor = padrao
        elif not permitir_vazio:
            return False, f"{nome_campo} é obrigatório"
        else:
            return True, None
    
    # Converte para string
    if not isinstance(valor, str):
        valor = str(valor)
    
    valor = valor.strip()
    
    # Valida comprimento
    if min_length is not None and len(valor) < min_length:
        return False, f"{nome_campo} deve ter pelo menos {min_length} caracteres"
    
    if max_length is not None and len(valor) > max_length:
        return False, f"{nome_campo} deve ter no máximo {max_length} caracteres"
    
    return True, None


def validar_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Valida um endereço de email.
    
    Args:
        email: Email a validar
        
    Returns:
        Tuple (valido, mensagem_erro)
    """
    if not email or not isinstance(email, str):
        return False, "Email inválido"
    
    email = email.strip().lower()
    
    # Regex básico para email
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(padrao, email):
        return False, "Formato de email inválido"
    
    return True, None


def validar_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Valida um nome de usuário.
    
    Args:
        username: Nome de usuário a validar
        
    Returns:
        Tuple (valido, mensagem_erro)
    """
    if not username or not isinstance(username, str):
        return False, "Nome de usuário inválido"
    
    username = username.strip()
    
    # Valida comprimento
    if len(username) < 3:
        return False, "Nome de usuário deve ter pelo menos 3 caracteres"
    
    if len(username) > 50:
        return False, "Nome de usuário deve ter no máximo 50 caracteres"
    
    # Valida caracteres permitidos (letras, números, underscore, hífen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Nome de usuário pode conter apenas letras, números, underscore e hífen"
    
    return True, None


# =============================================================================
# VALIDAÇÃO DE NÚMEROS
# =============================================================================

def validar_numero(
    valor: Any,
    nome_campo: str = "campo",
    tipo: type = int,
    min_valor: Optional[Union[int, float]] = None,
    max_valor: Optional[Union[int, float]] = None,
    permitir_zero: bool = True,
    permitir_negativo: bool = True
) -> tuple[bool, Optional[str], Optional[Union[int, float]]]:
    """
    Valida um número.
    
    Args:
        valor: Valor a validar
        nome_campo: Nome do campo
        tipo: Tipo esperado (int ou float)
        min_valor: Valor mínimo
        max_valor: Valor máximo
        permitir_zero: Se permite zero
        permitir_negativo: Se permite valores negativos
        
    Returns:
        Tuple (valido, mensagem_erro, valor_convertido)
    """
    # Tenta converter
    try:
        if tipo == int:
            num = int(valor)
        elif tipo == float:
            num = float(valor)
        else:
            return False, f"Tipo {tipo} não suportado", None
    except (ValueError, TypeError):
        return False, f"{nome_campo} deve ser um número válido", None
    
    # Valida zero
    if not permitir_zero and num == 0:
        return False, f"{nome_campo} não pode ser zero", None
    
    # Valida negativo
    if not permitir_negativo and num < 0:
        return False, f"{nome_campo} não pode ser negativo", None
    
    # Valida mínimo
    if min_valor is not None and num < min_valor:
        return False, f"{nome_campo} deve ser pelo menos {min_valor}", None
    
    # Valida máximo
    if max_valor is not None and num > max_valor:
        return False, f"{nome_campo} deve ser no máximo {max_valor}", None
    
    return True, None, num


# =============================================================================
# VALIDAÇÃO DE DATAS
# =============================================================================

def validar_data(
    valor: Any,
    nome_campo: str = "data",
    formato: str = "%Y-%m-%d",
    permitir_futuro: bool = True,
    permitir_passado: bool = True
) -> tuple[bool, Optional[str], Optional[datetime]]:
    """
    Valida uma data.
    
    Args:
        valor: Valor a validar (string ou datetime)
        nome_campo: Nome do campo
        formato: Formato esperado (se string)
        permitir_futuro: Se permite datas futuras
        permitir_passado: Se permite datas passadas
        
    Returns:
        Tuple (valido, mensagem_erro, datetime_objeto)
    """
    # Se já é datetime
    if isinstance(valor, datetime):
        dt = valor
    else:
        # Tenta converter string
        try:
            if isinstance(valor, str):
                dt = datetime.strptime(valor.strip(), formato)
            else:
                return False, f"{nome_campo} deve ser uma data válida", None
        except (ValueError, TypeError):
            return False, f"{nome_campo} deve estar no formato {formato}", None
    
    # Valida futuro
    if not permitir_futuro and dt > datetime.now():
        return False, f"{nome_campo} não pode ser uma data futura", None
    
    # Valida passado
    if not permitir_passado and dt < datetime.now():
        return False, f"{nome_campo} não pode ser uma data passada", None
    
    return True, None, dt


# =============================================================================
# VALIDAÇÃO DE LISTAS E DICIONÁRIOS
# =============================================================================

def validar_lista(
    valor: Any,
    nome_campo: str = "lista",
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    tipo_item: Optional[type] = None
) -> tuple[bool, Optional[str]]:
    """
    Valida uma lista.
    
    Args:
        valor: Valor a validar
        nome_campo: Nome do campo
        min_items: Número mínimo de itens
        max_items: Número máximo de itens
        tipo_item: Tipo esperado dos itens
        
    Returns:
        Tuple (valido, mensagem_erro)
    """
    if not isinstance(valor, list):
        return False, f"{nome_campo} deve ser uma lista"
    
    # Valida quantidade
    if min_items is not None and len(valor) < min_items:
        return False, f"{nome_campo} deve ter pelo menos {min_items} item(ns)"
    
    if max_items is not None and len(valor) > max_items:
        return False, f"{nome_campo} deve ter no máximo {max_items} item(ns)"
    
    # Valida tipo dos itens
    if tipo_item is not None:
        for i, item in enumerate(valor):
            if not isinstance(item, tipo_item):
                return False, f"{nome_campo}[{i}] deve ser do tipo {tipo_item.__name__}"
    
    return True, None


def validar_dict(
    valor: Any,
    nome_campo: str = "objeto",
    campos_obrigatorios: Optional[List[str]] = None,
    campos_permitidos: Optional[List[str]] = None
) -> tuple[bool, Optional[str]]:
    """
    Valida um dicionário.
    
    Args:
        valor: Valor a validar
        nome_campo: Nome do campo
        campos_obrigatorios: Lista de campos obrigatórios
        campos_permitidos: Lista de campos permitidos (whitelist)
        
    Returns:
        Tuple (valido, mensagem_erro)
    """
    if not isinstance(valor, dict):
        return False, f"{nome_campo} deve ser um objeto/dicionário"
    
    # Valida campos obrigatórios
    if campos_obrigatorios:
        for campo in campos_obrigatorios:
            if campo not in valor:
                return False, f"{nome_campo} deve conter o campo '{campo}'"
    
    # Valida campos permitidos (whitelist)
    if campos_permitidos:
        campos_invalidos = [k for k in valor.keys() if k not in campos_permitidos]
        if campos_invalidos:
            return False, f"{nome_campo} contém campos não permitidos: {', '.join(campos_invalidos)}"
    
    return True, None


# =============================================================================
# VALIDAÇÃO DE REQUISIÇÕES
# =============================================================================

def validar_request_json(
    data: Dict,
    campos_obrigatorios: List[str],
    tipos_esperados: Optional[Dict[str, type]] = None
) -> tuple[bool, Optional[str], Optional[Dict]]:
    """
    Valida dados de uma requisição JSON.
    
    Args:
        data: Dados da requisição
        campos_obrigatorios: Lista de campos obrigatórios
        tipos_esperados: Dict {campo: tipo} para validação de tipos
        
    Returns:
        Tuple (valido, mensagem_erro, dados_validados)
    """
    # Valida que é um dict
    valido, erro = validar_dict(data, "dados")
    if not valido:
        return False, erro, None
    
    # Valida campos obrigatórios
    for campo in campos_obrigatorios:
        if campo not in data:
            return False, f"Campo obrigatório ausente: {campo}", None
    
    # Valida tipos
    if tipos_esperados:
        for campo, tipo_esperado in tipos_esperados.items():
            if campo in data and not isinstance(data[campo], tipo_esperado):
                return False, f"Campo '{campo}' deve ser do tipo {tipo_esperado.__name__}", None
    
    return True, None, data


# =============================================================================
# SANITIZAÇÃO
# =============================================================================

def sanitizar_string(valor: str, max_length: Optional[int] = None) -> str:
    """
    Sanitiza uma string removendo caracteres perigosos.
    
    Args:
        valor: String a sanitizar
        max_length: Comprimento máximo (trunca se necessário)
        
    Returns:
        String sanitizada
    """
    if not isinstance(valor, str):
        valor = str(valor)
    
    # Remove caracteres de controle
    valor = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', valor)
    
    # Remove espaços extras
    valor = ' '.join(valor.split())
    
    # Trunca se necessário
    if max_length and len(valor) > max_length:
        valor = valor[:max_length]
    
    return valor.strip()


def sanitizar_sql_identifier(identificador: str) -> str:
    """
    Sanitiza um identificador SQL (nome de tabela, coluna, etc).
    
    Args:
        identificador: Identificador a sanitizar
        
    Returns:
        Identificador sanitizado
    """
    if not isinstance(identificador, str):
        return ""
    
    # Remove caracteres não permitidos em identificadores SQL
    # Permite apenas: letras, números, underscore
    identificador = re.sub(r'[^a-zA-Z0-9_]', '', identificador)
    
    return identificador

