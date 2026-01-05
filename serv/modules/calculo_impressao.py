"""
Módulo Centralizado de Cálculos de Impressão
=============================================

Este módulo é a ÚNICA FONTE DA VERDADE para todos os cálculos relacionados
a impressões no sistema Print Monitor.

IMPORTANTE: Não duplique estas funções em outros módulos!
           Sempre importe deste módulo.

Terminologia Padronizada:
-------------------------
- PÁGINAS (pages): Faces impressas / páginas lógicas (o que o Event 307 retorna)
- FOLHAS (sheets): Folhas físicas de papel consumidas
- CÓPIAS (copies): Número de cópias do documento
- DUPLEX: Se o job foi impresso em frente e verso (True/False)

Fórmulas:
---------
- Simplex: folhas = páginas × cópias
- Duplex:  folhas = ceil((páginas × cópias) / 2)

Exemplos:
---------
| Páginas | Cópias | Duplex | Folhas | Explicação                    |
|---------|--------|--------|--------|-------------------------------|
| 5       | 1      | False  | 5      | 5 faces = 5 folhas            |
| 5       | 1      | True   | 3      | 5 faces ÷ 2 = 2.5 → 3 folhas  |
| 2       | 1      | True   | 1      | 2 faces ÷ 2 = 1 folha         |
| 10      | 1      | True   | 5      | 10 faces ÷ 2 = 5 folhas       |
| 2       | 3      | True   | 3      | 6 faces ÷ 2 = 3 folhas        |
| 1       | 1      | True   | 1      | 1 face ÷ 2 = 0.5 → 1 folha    |

Autor: Print Monitor Team
Versão: 1.0.0
"""

import math
from typing import Optional, Union, Dict
from decimal import Decimal, ROUND_HALF_UP

# =============================================================================
# CONSTANTES
# =============================================================================

# Limites de validação
MAX_PAGINAS = 10000  # Máximo de páginas por job (proteção contra erros)
MAX_COPIAS = 100  # Máximo de cópias por job

# =============================================================================
# FUNÇÕES DE CÁLCULO DE FOLHAS
# =============================================================================


def calcular_folhas(
    paginas: Optional[int],
    duplex: Optional[Union[bool, int]] = False,
    copias: int = 1
) -> int:
    """
    Calcula o número de folhas físicas consumidas.
    
    Esta é a FUNÇÃO PRINCIPAL de cálculo. Use esta função em vez de
    implementar a lógica manualmente.
    
    Args:
        paginas: Número de páginas lógicas (faces impressas por cópia).
                 Valor do Param8 do Event 307.
        duplex: Se o job foi impresso em duplex (frente e verso).
                Aceita: True/False, 1/0, "duplex"/"simplex", ou None.
        copias: Número de cópias do documento (default: 1).
    
    Returns:
        Número de folhas físicas consumidas (sempre >= 0).
    
    Examples:
        >>> calcular_folhas(5, duplex=False)
        5
        >>> calcular_folhas(5, duplex=True)
        3
        >>> calcular_folhas(2, duplex=True, copias=3)
        3
        >>> calcular_folhas(1, duplex=True)
        1
        >>> calcular_folhas(0)
        0
        >>> calcular_folhas(None)
        0
    """
    # Validação de entrada
    if paginas is None or paginas <= 0:
        return 0
    
    # Limita valores extremos
    paginas = min(paginas, MAX_PAGINAS)
    copias = max(1, min(copias, MAX_COPIAS))
    
    # Normaliza o valor de duplex
    is_duplex = normalizar_duplex(duplex)
    
    # Calcula faces totais impressas
    faces_totais = paginas * copias
    
    # Calcula folhas físicas
    if is_duplex:
        # Duplex: 2 faces por folha, arredonda para cima
        return math.ceil(faces_totais / 2)
    else:
        # Simplex: 1 face por folha
        return faces_totais


def calcular_folhas_fisicas(
    pages_printed: Optional[int],
    duplex: Optional[Union[bool, int]] = None,
    copies: int = 1
) -> int:
    """
    Alias para calcular_folhas() - mantido para compatibilidade.
    
    DEPRECATED: Use calcular_folhas() para novos códigos.
    
    Args:
        pages_printed: Número de páginas (alias para 'paginas')
        duplex: Se é duplex (alias para 'duplex')
        copies: Número de cópias (alias para 'copias')
    
    Returns:
        Número de folhas físicas consumidas.
    """
    return calcular_folhas(pages_printed, duplex, copies)


# =============================================================================
# FUNÇÕES DE NORMALIZAÇÃO
# =============================================================================


def normalizar_duplex(valor: Optional[Union[bool, int, str]]) -> bool:
    """
    Normaliza diferentes representações de duplex para booleano.
    
    Aceita múltiplos formatos de entrada e retorna True/False.
    
    Args:
        valor: Valor a ser normalizado. Pode ser:
               - bool: True/False
               - int: 1 (duplex) / 0 (simplex)
               - str: "duplex", "true", "1" / "simplex", "false", "0"
               - None: tratado como False (simplex)
    
    Returns:
        True se duplex, False se simplex.
    
    Examples:
        >>> normalizar_duplex(True)
        True
        >>> normalizar_duplex(1)
        True
        >>> normalizar_duplex("duplex")
        True
        >>> normalizar_duplex(False)
        False
        >>> normalizar_duplex(0)
        False
        >>> normalizar_duplex("simplex")
        False
        >>> normalizar_duplex(None)
        False
    """
    if valor is None:
        return False
    
    if isinstance(valor, bool):
        return valor
    
    if isinstance(valor, int):
        return valor == 1
    
    if isinstance(valor, str):
        valor_lower = valor.lower().strip()
        return valor_lower in ('duplex', 'true', '1', 'yes', 'sim')
    
    return False


def normalizar_paginas(valor: Optional[Union[int, str]]) -> int:
    """
    Normaliza o valor de páginas para inteiro válido.
    
    Args:
        valor: Valor a ser normalizado (int ou string numérica).
    
    Returns:
        Número de páginas (mínimo 0, máximo MAX_PAGINAS).
    """
    if valor is None:
        return 0
    
    try:
        paginas = int(valor)
        return max(0, min(paginas, MAX_PAGINAS))
    except (ValueError, TypeError):
        return 0


def normalizar_copias(valor: Optional[Union[int, str]]) -> int:
    """
    Normaliza o valor de cópias para inteiro válido.
    
    Args:
        valor: Valor a ser normalizado (int ou string numérica).
    
    Returns:
        Número de cópias (mínimo 1, máximo MAX_COPIAS).
    """
    if valor is None:
        return 1
    
    try:
        copias = int(valor)
        return max(1, min(copias, MAX_COPIAS))
    except (ValueError, TypeError):
        return 1


# =============================================================================
# FUNÇÕES DE CÁLCULO DE CUSTO
# =============================================================================


# Funções de custo removidas: sistema de preços removido
# def calcular_custo(...)
# def calcular_custo_completo(...)
# def calcular_custo_comodato(...)


# =============================================================================
# FUNÇÕES DE ECONOMIA
# =============================================================================


def calcular_economia_duplex(paginas: int, copias: int = 1) -> int:
    """
    Calcula quantas folhas são economizadas ao usar duplex.
    
    Args:
        paginas: Número de páginas lógicas.
        copias: Número de cópias.
    
    Returns:
        Número de folhas economizadas.
    
    Examples:
        >>> calcular_economia_duplex(10)
        5
        >>> calcular_economia_duplex(5)
        2
        >>> calcular_economia_duplex(1)
        0
    """
    folhas_simplex = calcular_folhas(paginas, duplex=False, copias=copias)
    folhas_duplex = calcular_folhas(paginas, duplex=True, copias=copias)
    return folhas_simplex - folhas_duplex


# Função removida: sistema de preços removido
# def calcular_economia_pb(...)


# =============================================================================
# FUNÇÕES DE VALIDAÇÃO
# =============================================================================


def validar_evento(evento: Dict) -> Dict[str, Union[bool, str, list]]:
    """
    Valida os campos de um evento de impressão.
    
    Args:
        evento: Dicionário com dados do evento.
    
    Returns:
        Dict com: valido (bool), erros (list), avisos (list)
    """
    erros = []
    avisos = []
    
    # Campos obrigatórios
    if 'date' not in evento:
        erros.append("Campo 'date' é obrigatório")
    if 'user' not in evento:
        erros.append("Campo 'user' é obrigatório")
    if 'machine' not in evento:
        erros.append("Campo 'machine' é obrigatório")
    
    # Validação de páginas
    pages = evento.get('pages', evento.get('pages_printed', 0))
    if pages is not None:
        try:
            pages_int = int(pages)
            if pages_int < 0:
                erros.append("Páginas não pode ser negativo")
            elif pages_int > MAX_PAGINAS:
                avisos.append(f"Páginas ({pages_int}) excede limite ({MAX_PAGINAS})")
        except (ValueError, TypeError):
            erros.append(f"Páginas inválido: {pages}")
    
    # Validação de cópias
    copies = evento.get('copies', 1)
    if copies is not None:
        try:
            copies_int = int(copies)
            if copies_int < 1:
                avisos.append("Cópias menor que 1, será ajustado para 1")
            elif copies_int > MAX_COPIAS:
                avisos.append(f"Cópias ({copies_int}) excede limite ({MAX_COPIAS})")
        except (ValueError, TypeError):
            erros.append(f"Cópias inválido: {copies}")
    
    return {
        'valido': len(erros) == 0,
        'erros': erros,
        'avisos': avisos
    }


# =============================================================================
# FUNÇÕES AUXILIARES PARA SQL
# =============================================================================


def get_sql_folhas_expression(duplex_column: str = 'duplex', 
                               pages_column: str = 'pages_printed',
                               copies_column: str = 'copies') -> str:
    """
    Retorna expressão SQL para calcular folhas físicas.
    
    Útil para queries que precisam calcular folhas diretamente no SQL.
    
    Args:
        duplex_column: Nome da coluna de duplex.
        pages_column: Nome da coluna de páginas.
        copies_column: Nome da coluna de cópias.
    
    Returns:
        String com expressão SQL.
    
    Example:
        >>> get_sql_folhas_expression()
        "CASE WHEN duplex = 1 THEN (pages_printed * COALESCE(copies, 1) + 1) / 2 
         ELSE pages_printed * COALESCE(copies, 1) END"
    """
    return f"""CASE 
        WHEN {duplex_column} = 1 THEN 
            ({pages_column} * COALESCE({copies_column}, 1) + 1) / 2 
        ELSE 
            {pages_column} * COALESCE({copies_column}, 1) 
    END"""


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Funções principais
    'calcular_folhas',
    'calcular_folhas_fisicas',  # Alias para compatibilidade
    # 'calcular_custo',  # Removida - sistema de preços removido
    # 'calcular_custo_completo',  # Removida - sistema de preços removido
    
    # Funções de economia
    'calcular_economia_duplex',
    # 'calcular_economia_pb',  # Removida - sistema de preços removido
    
    # Funções de normalização
    'normalizar_duplex',
    'normalizar_paginas',
    'normalizar_copias',
    
    # Funções de validação
    'validar_evento',
    
    # Auxiliares SQL
    'get_sql_folhas_expression',
    
    # Constantes
    'MAX_PAGINAS',
    'MAX_COPIAS',
]


# =============================================================================
# TESTES (executar com: python -m serv.modules.calculo_impressao)
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("TESTES DO MÓDULO calculo_impressao.py")
    print("=" * 60)
    
    # Teste 1: Cálculo básico de folhas
    print("\n1. Testes de calcular_folhas():")
    testes = [
        (5, False, 1, 5),   # 5 páginas simplex = 5 folhas
        (5, True, 1, 3),    # 5 páginas duplex = 3 folhas
        (2, True, 1, 1),    # 2 páginas duplex = 1 folha
        (10, True, 1, 5),   # 10 páginas duplex = 5 folhas
        (2, True, 3, 3),    # 2 páginas duplex, 3 cópias = 3 folhas
        (1, True, 1, 1),    # 1 página duplex = 1 folha (arredonda)
        (0, False, 1, 0),   # 0 páginas = 0 folhas
        (None, False, 1, 0), # None páginas = 0 folhas
    ]
    
    for paginas, duplex, copias, esperado in testes:
        resultado = calcular_folhas(paginas, duplex, copias)
        status = "✅" if resultado == esperado else "❌"
        print(f"   {status} calcular_folhas({paginas}, duplex={duplex}, copias={copias}) = {resultado} (esperado: {esperado})")
    
    # Teste 2: Normalização de duplex
    print("\n2. Testes de normalizar_duplex():")
    testes_duplex = [
        (True, True),
        (1, True),
        ("duplex", True),
        ("DUPLEX", True),
        (False, False),
        (0, False),
        ("simplex", False),
        (None, False),
    ]
    
    for valor, esperado in testes_duplex:
        resultado = normalizar_duplex(valor)
        status = "✅" if resultado == esperado else "❌"
        print(f"   {status} normalizar_duplex({repr(valor)}) = {resultado} (esperado: {esperado})")
    
    # Teste 3: Cálculo de custo (removido - sistema de preços removido)
    # print("\n3. Testes de calcular_custo():")
    # testes_custo = [
    #     (10, False, 0.10, 0.50, 1.0),   # 10 folhas P&B = R$ 1.00
    #     (10, True, 0.10, 0.50, 5.0),    # 10 folhas color = R$ 5.00
    #     (0, False, 0.10, 0.50, 0.0),    # 0 folhas = R$ 0.00
    # ]
    # 
    # for folhas, colorido, preco_pb, preco_color, esperado in testes_custo:
    #     resultado = calcular_custo(folhas, colorido, preco_pb, preco_color)
    #     status = "✅" if resultado == esperado else "❌"
    #     print(f"   {status} calcular_custo({folhas}, colorido={colorido}) = R$ {resultado} (esperado: R$ {esperado})")
    
    # Teste 4: Economia duplex
    print("\n4. Testes de calcular_economia_duplex():")
    testes_economia = [
        (10, 1, 5),  # 10 páginas = economia de 5 folhas
        (5, 1, 2),   # 5 páginas = economia de 2 folhas
        (1, 1, 0),   # 1 página = economia de 0 folhas
    ]
    
    for paginas, copias, esperado in testes_economia:
        resultado = calcular_economia_duplex(paginas, copias)
        status = "✅" if resultado == esperado else "❌"
        print(f"   {status} calcular_economia_duplex({paginas}, {copias}) = {resultado} folhas (esperado: {esperado})")
    
    # Teste 5: Cálculo completo (removido - sistema de preços removido)
    # print("\n5. Teste de calcular_custo_completo():")
    # resultado = calcular_custo_completo(10, duplex=True, copias=2, colorido=False)
    # print(f"   calcular_custo_completo(10, duplex=True, copias=2, colorido=False):")
    # print(f"   {resultado}")
    
    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS!")
    print("=" * 60)

