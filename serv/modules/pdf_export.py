"""
Módulo para exportação de relatórios em PDF - Versão Profissional Hospitalar
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    Image, KeepTogether, PageTemplate, Frame, NextPageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
import sqlite3

logger = logging.getLogger(__name__)

# Cores profissionais hospitalares
COR_PRIMARIA = colors.HexColor('#0066CC')  # Azul hospitalar
COR_SECUNDARIA = colors.HexColor('#004499')
COR_DESTAQUE = colors.HexColor('#00A86B')  # Verde saúde
COR_ALERTA = colors.HexColor('#FF6B35')
COR_TEXTO = colors.HexColor('#1a1f2e')
COR_CINZA = colors.HexColor('#F5F5F5')
COR_CINZA_ESCURO = colors.HexColor('#666666')


class NumberedCanvas(canvas.Canvas):
    """Canvas com numeração de páginas"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(COR_CINZA_ESCURO)
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(A4[0] - 1*cm, 1*cm, page_text)
        self.restoreState()


def criar_cabecalho_hospitalar(canvas_obj, doc, hospital_nome: str = "Hospital"):
    """Cria cabeçalho profissional para relatório hospitalar"""
    canvas_obj.saveState()
    
    # Linha superior azul
    canvas_obj.setFillColor(COR_PRIMARIA)
    canvas_obj.rect(0, A4[1] - 2*cm, A4[0], 2*cm, fill=1, stroke=0)
    
    # Logo/Texto do hospital (centro)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.drawCentredString(A4[0]/2, A4[1] - 1.2*cm, hospital_nome.upper())
    
    # Subtítulo
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawCentredString(A4[0]/2, A4[1] - 1.6*cm, "Relatório de Monitoramento de Impressões")
    
    # Data e hora (canto direito)
    canvas_obj.setFont("Helvetica", 9)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    canvas_obj.drawRightString(A4[0] - 1*cm, A4[1] - 1.2*cm, data_hora)
    
    # Linha divisória
    canvas_obj.setFillColor(COR_SECUNDARIA)
    canvas_obj.rect(0, A4[1] - 2.2*cm, A4[0], 0.1*cm, fill=1, stroke=0)
    
    canvas_obj.restoreState()


def criar_rodape_hospitalar(canvas_obj, doc):
    """Cria rodapé profissional"""
    canvas_obj.saveState()
    
    # Linha divisória
    canvas_obj.setFillColor(COR_CINZA_ESCURO)
    canvas_obj.rect(1*cm, 1.5*cm, A4[0] - 2*cm, 0.05*cm, fill=1, stroke=0)
    
    # Texto do rodapé
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(COR_CINZA_ESCURO)
    texto_rodape = "Documento confidencial - Uso interno | Sistema de Monitoramento de Impressões"
    canvas_obj.drawCentredString(A4[0]/2, 1.2*cm, texto_rodape)
    
    canvas_obj.restoreState()


def criar_tabela_profissional(dados: List[List], 
                              cabecalhos: List[str],
                              larguras_colunas: Optional[List[float]] = None,
                              estilo_alternado: bool = True) -> Table:
    """Cria tabela com estilo profissional"""
    if not dados:
        dados = [["Nenhum dado disponível"]]
        cabecalhos = ["Informação"]
    
    # Prepara dados da tabela
    table_data = [cabecalhos] + dados
    
    # Cria tabela
    table = Table(table_data, colWidths=larguras_colunas)
    
    # Estilo profissional
    estilo = [
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Linhas alternadas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), 
         [colors.white, COR_CINZA] if estilo_alternado else [colors.white]),
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, COR_SECUNDARIA),
        
        # Formatação de células
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]
    
    table.setStyle(TableStyle(estilo))
    return table


def gerar_relatorio_hospitalar_completo(
    conn: sqlite3.Connection,
    hospital_nome: str = "Hospital",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    incluir_graficos: bool = False
) -> BytesIO:
    """
    Gera relatório PDF completo e profissional para ambiente hospitalar
    
    Args:
        conn: Conexão com banco de dados
        hospital_nome: Nome do hospital
        start_date: Data inicial (formato YYYY-MM-DD)
        end_date: Data final (formato YYYY-MM-DD)
        incluir_graficos: Se deve incluir gráficos (requer matplotlib)
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    buffer = BytesIO()
    
    # Cria documento com numeração de páginas
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=3*cm,
        bottomMargin=2.5*cm
    )
    
    # Template com cabeçalho e rodapé será aplicado durante o build
    
    # Container para elementos
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    titulo_principal = ParagraphStyle(
        'TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=COR_PRIMARIA,
        spaceAfter=20,
        spaceBefore=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=COR_SECUNDARIA,
        spaceAfter=12,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    texto_normal = ParagraphStyle(
        'TextoNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COR_TEXTO,
        spaceAfter=8,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    # ========================================================================
    # CAPA
    # ========================================================================
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(
        f"<b>{hospital_nome.upper()}</b>",
        ParagraphStyle(
            'CapaTitulo',
            fontSize=28,
            textColor=COR_PRIMARIA,
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        )
    ))
    elements.append(Paragraph(
        "RELATÓRIO DE MONITORAMENTO DE IMPRESSÕES",
        ParagraphStyle(
            'CapaSubtitulo',
            fontSize=18,
            textColor=COR_SECUNDARIA,
            alignment=TA_CENTER,
            spaceAfter=40,
            fontName='Helvetica'
        )
    ))
    
    # Período
    periodo_texto = "Período completo"
    if start_date and end_date:
        periodo_texto = f"De {start_date} a {end_date}"
    elif start_date:
        periodo_texto = f"A partir de {start_date}"
    elif end_date:
        periodo_texto = f"Até {end_date}"
    
    elements.append(Paragraph(
        periodo_texto,
        ParagraphStyle(
            'CapaPeriodo',
            fontSize=14,
            textColor=COR_CINZA_ESCURO,
            alignment=TA_CENTER,
            spaceAfter=60,
            fontName='Helvetica'
        )
    ))
    
    elements.append(Paragraph(
        f"Gerado em: {datetime.now().strftime('%d de %B de %Y, às %H:%M')}",
        ParagraphStyle(
            'CapaData',
            fontSize=11,
            textColor=COR_CINZA_ESCURO,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
    ))
    
    elements.append(PageBreak())
    
    # ========================================================================
    # SUMÁRIO EXECUTIVO
    # ========================================================================
    elements.append(Paragraph("SUMÁRIO EXECUTIVO", titulo_principal))
    elements.append(Spacer(1, 0.3*inch))
    
    # Busca estatísticas gerais
    where_clause = "WHERE 1=1"
    params = []
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    cursor = conn.cursor()
    
    # Usa módulo centralizado de cálculos
    from modules.calculo_impressao import calcular_folhas_fisicas
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in cursor.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Função auxiliar para obter cláusula GROUP BY de job
    def get_job_group_by():
        if has_job_id:
            return """CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END"""
        else:
            return """user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date"""
    
    # Total de impressões (jobs únicos, não eventos)
    if has_job_id:
        total_impressoes = cursor.execute(
            f"""SELECT COUNT(DISTINCT CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END) FROM events {where_clause}""",
            params
        ).fetchone()[0]
    else:
        total_impressoes = cursor.execute(
            f"""SELECT COUNT(DISTINCT user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date) 
            FROM events {where_clause}""",
            params
        ).fetchone()[0]
    
    # Total de páginas (folhas físicas) - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        rows = cursor.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END""",
            params
        ).fetchall()
    else:
        rows = cursor.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date""",
            params
        ).fetchall()
    
    total_paginas = 0
    for row in rows:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        total_paginas += calcular_folhas_fisicas(pages, duplex)
    
    # Outras estatísticas
    total_usuarios = cursor.execute(
        f"SELECT COUNT(DISTINCT user) FROM events {where_clause}",
        params
    ).fetchone()[0]
    
    total_impressoras = cursor.execute(
        f"SELECT COUNT(DISTINCT printer_name) FROM events {where_clause} AND printer_name IS NOT NULL AND printer_name != ''",
        params
    ).fetchone()[0]
    
    # Custo total (soma de todos os eventos, não agrupado por job)
    custo_total = cursor.execute(
        f"SELECT SUM(CASE WHEN cost IS NOT NULL THEN cost ELSE 0 END) FROM events {where_clause}",
        params
    ).fetchone()[0] or 0
    
    # Tabela de resumo executivo
    resumo_data = [
        ["Métrica", "Valor"],
        ["Total de Impressões", f"{total_impressoes:,}"],
        ["Total de Páginas Impressas", f"{total_paginas:,}"],
        ["Usuários Únicos", f"{total_usuarios:,}"],
        ["Impressoras Monitoradas", f"{total_impressoras:,}"],
        ["Custo Total Estimado", f"R$ {custo_total:,.2f}"],
        ["Média de Páginas por Impressão", f"{total_paginas/total_impressoes:.2f}" if total_impressoes > 0 else "0.00"],
        ["Custo Médio por Página", f"R$ {custo_total/total_paginas:.4f}" if total_paginas > 0 else "R$ 0.00"]
    ]
    
    elements.append(criar_tabela_profissional(
        resumo_data[1:],
        resumo_data[0],
        larguras_colunas=[6*cm, 6*cm]
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Análise de modo de cor - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        color_rows = cursor.execute(
            f"""SELECT 
                MAX(color_mode) as color_mode,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events
            {where_clause} AND color_mode IS NOT NULL
            GROUP BY {get_job_group_by()}
            """, params
        ).fetchall()
    else:
        color_rows = cursor.execute(
            f"""SELECT 
                MAX(color_mode) as color_mode,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events
            {where_clause} AND color_mode IS NOT NULL
            GROUP BY {get_job_group_by()}
            """, params
        ).fetchall()
    
    # Agrupa por color_mode e calcula totais
    color_dict = {}
    for row in color_rows:
        color_mode = row[0]
        if not color_mode:
            continue
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        folhas = calcular_folhas_fisicas(pages, duplex)
        
        if color_mode not in color_dict:
            color_dict[color_mode] = {"impressoes": 0, "paginas": 0}
        color_dict[color_mode]["impressoes"] += 1
        color_dict[color_mode]["paginas"] += folhas
    
    color_stats = [(k, v["impressoes"], v["paginas"]) for k, v in sorted(color_dict.items(), key=lambda x: x[1]["paginas"], reverse=True)]
    
    if color_stats:
        elements.append(Paragraph("Distribuição por Modo de Cor", subtitulo))
        color_data = [["Modo de Cor", "Impressões", "Páginas", "% do Total"]]
        total_paginas_color = sum(row[2] for row in color_stats)
        for row in color_stats:
            pct = (row[2] / total_paginas_color * 100) if total_paginas_color > 0 else 0
            color_data.append([
                row[0] or "Não especificado",
                f"{row[1]:,}",
                f"{row[2]:,}",
                f"{pct:.1f}%"
            ])
        
        elements.append(criar_tabela_profissional(
            color_data[1:],
            color_data[0],
            larguras_colunas=[4*cm, 3*cm, 3*cm, 2*cm]
        ))
        elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ========================================================================
    # ANÁLISE POR SETOR (Relevante para hospitais)
    # ========================================================================
    elements.append(Paragraph("ANÁLISE POR SETOR/DEPARTAMENTO", titulo_principal))
    elements.append(Spacer(1, 0.2*inch))
    
    # Busca setores - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        setor_rows = cursor.execute(
            f"""SELECT 
                MAX(COALESCE(account, 'Não especificado')) as setor,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(user) as user
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}
            """, params
        ).fetchall()
    else:
        setor_rows = cursor.execute(
            f"""SELECT 
                MAX(COALESCE(account, 'Não especificado')) as setor,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(user) as user
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}
            """, params
        ).fetchall()
    
    # Agrupa por setor e calcula totais
    setores_dict = {}
    for row in setor_rows:
        setor = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        user = row[3] if len(row) > 3 else None
        folhas = calcular_folhas_fisicas(pages, duplex)
        
        if setor not in setores_dict:
            setores_dict[setor] = {"impressoes": 0, "paginas": 0, "usuarios": set()}
        setores_dict[setor]["impressoes"] += 1
        setores_dict[setor]["paginas"] += folhas
        if user:
            setores_dict[setor]["usuarios"].add(user)
    
    # Calcula custo (soma de todos os eventos, não agrupado por job)
    custo_por_setor = {}
    custo_rows = cursor.execute(
        f"""SELECT 
            COALESCE(account, 'Não especificado') as setor,
            SUM(CASE WHEN cost IS NOT NULL THEN cost ELSE 0 END) as custo
        FROM events
        {where_clause}
        GROUP BY account
        """, params
    ).fetchall()
    for row in custo_rows:
        custo_por_setor[row[0]] = row[1] or 0
    
    setores_data = [
        (setor, data["impressoes"], data["paginas"], custo_por_setor.get(setor, 0), len(data["usuarios"]))
        for setor, data in sorted(setores_dict.items(), key=lambda x: x[1]["paginas"], reverse=True)[:15]
    ]
    if setores_data:
        setores_table = [["Setor/Departamento", "Impressões", "Páginas", "Usuários", "Custo (R$)"]]
        for row in setores_data:
            setores_table.append([
                row[0],
                f"{row[1]:,}",
                f"{row[2]:,}",
                f"{row[4]:,}",
                f"R$ {row[3]:,.2f}"
            ])
        
        elements.append(criar_tabela_profissional(
            setores_table[1:],
            setores_table[0],
            larguras_colunas=[5*cm, 2.5*cm, 2.5*cm, 2*cm, 3*cm]
        ))
    else:
        elements.append(Paragraph(
            "Nenhum dado de setor disponível. Configure o campo 'account' nos eventos.",
            texto_normal
        ))
    
    elements.append(PageBreak())
    
    # ========================================================================
    # TOP USUÁRIOS
    # ========================================================================
    elements.append(Paragraph("TOP 15 USUÁRIOS", titulo_principal))
    elements.append(Spacer(1, 0.2*inch))
    
    # Top usuários - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        usuario_rows = cursor.execute(
            f"""SELECT 
                MAX(user) as user,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}, user
            """, params
        ).fetchall()
    else:
        usuario_rows = cursor.execute(
            f"""SELECT 
                MAX(user) as user,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}, user
            """, params
        ).fetchall()
    
    # Agrupa por usuário e calcula totais
    usuarios_dict = {}
    for row in usuario_rows:
        user = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        folhas = calcular_folhas_fisicas(pages, duplex)
        
        if user not in usuarios_dict:
            usuarios_dict[user] = {"impressoes": 0, "paginas": 0, "total_pages": 0}
        usuarios_dict[user]["impressoes"] += 1
        usuarios_dict[user]["paginas"] += folhas
        usuarios_dict[user]["total_pages"] += pages
    
    # Calcula custo (soma de todos os eventos, não agrupado por job)
    custo_por_usuario = {}
    custo_rows = cursor.execute(
        f"""SELECT 
            user,
            SUM(CASE WHEN cost IS NOT NULL THEN cost ELSE 0 END) as custo
        FROM events
        {where_clause}
        GROUP BY user
        """, params
    ).fetchall()
    for row in custo_rows:
        custo_por_usuario[row[0]] = row[1] or 0
    
    usuarios_data = [
        (user, data["impressoes"], data["paginas"], custo_por_usuario.get(user, 0), data["total_pages"] / data["impressoes"] if data["impressoes"] > 0 else 0)
        for user, data in sorted(usuarios_dict.items(), key=lambda x: x[1]["paginas"], reverse=True)[:15]
    ]
    if usuarios_data:
        usuarios_table = [["Usuário", "Impressões", "Páginas", "Média/Job", "Custo (R$)"]]
        for row in usuarios_data:
            usuarios_table.append([
                row[0],
                f"{row[1]:,}",
                f"{row[2]:,}",
                f"{row[4]:.1f}",
                f"R$ {row[3]:,.2f}"
            ])
        
        elements.append(criar_tabela_profissional(
            usuarios_table[1:],
            usuarios_table[0],
            larguras_colunas=[5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
        ))
    
    elements.append(PageBreak())
    
    # ========================================================================
    # ANÁLISE DE IMPRESSORAS
    # ========================================================================
    elements.append(Paragraph("ANÁLISE DE IMPRESSORAS", titulo_principal))
    elements.append(Spacer(1, 0.2*inch))
    
    # Análise de impressoras - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        impressora_rows = cursor.execute(
            f"""SELECT 
                MAX(COALESCE(printer_name, 'Não especificado')) as impressora,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events
            {where_clause} AND printer_name IS NOT NULL
            GROUP BY {get_job_group_by()}, printer_name
            """, params
        ).fetchall()
    else:
        impressora_rows = cursor.execute(
            f"""SELECT 
                MAX(COALESCE(printer_name, 'Não especificado')) as impressora,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex
            FROM events
            {where_clause} AND printer_name IS NOT NULL
            GROUP BY {get_job_group_by()}, printer_name
            """, params
        ).fetchall()
    
    # Agrupa por impressora e calcula totais
    impressoras_dict = {}
    for row in impressora_rows:
        impressora = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        folhas = calcular_folhas_fisicas(pages, duplex)
        
        if impressora not in impressoras_dict:
            impressoras_dict[impressora] = {"impressoes": 0, "paginas": 0, "total_pages": 0}
        impressoras_dict[impressora]["impressoes"] += 1
        impressoras_dict[impressora]["paginas"] += folhas
        impressoras_dict[impressora]["total_pages"] += pages
    
    # Calcula custo (soma de todos os eventos, não agrupado por job)
    custo_por_impressora = {}
    custo_rows = cursor.execute(
        f"""SELECT 
            printer_name,
            SUM(CASE WHEN cost IS NOT NULL THEN cost ELSE 0 END) as custo
        FROM events
        {where_clause} AND printer_name IS NOT NULL
        GROUP BY printer_name
        """, params
    ).fetchall()
    for row in custo_rows:
        custo_por_impressora[row[0]] = row[1] or 0
    
    impressoras_data = [
        (impressora, data["impressoes"], data["paginas"], data["total_pages"] / data["impressoes"] if data["impressoes"] > 0 else 0, custo_por_impressora.get(impressora, 0))
        for impressora, data in sorted(impressoras_dict.items(), key=lambda x: x[1]["paginas"], reverse=True)[:15]
    ]
    if impressoras_data:
        impressoras_table = [["Impressora", "Impressões", "Páginas", "Média/Job", "Custo (R$)"]]
        for row in impressoras_data:
            impressoras_table.append([
                row[0],
                f"{row[1]:,}",
                f"{row[2]:,}",
                f"{row[3]:.1f}",
                f"R$ {row[4]:,.2f}"
            ])
        
        elements.append(criar_tabela_profissional(
            impressoras_table[1:],
            impressoras_table[0],
            larguras_colunas=[5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
        ))
    
    elements.append(PageBreak())
    
    # ========================================================================
    # ANÁLISE DE EFICIÊNCIA
    # ========================================================================
    elements.append(Paragraph("ANÁLISE DE EFICIÊNCIA", titulo_principal))
    elements.append(Spacer(1, 0.2*inch))
    
    # Uso de duplex
    # Análise duplex - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        duplex_rows = cursor.execute(
            f"""SELECT 
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(pages_printed) as pages
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}
            """, params
        ).fetchall()
    else:
        duplex_rows = cursor.execute(
            f"""SELECT 
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(pages_printed) as pages
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}
            """, params
        ).fetchall()
    
    # Agrupa por tipo duplex e calcula totais
    duplex_dict = {"Duplex (Economia)": {"impressoes": 0, "paginas": 0}, "Simples": {"impressoes": 0, "paginas": 0}, "Não especificado": {"impressoes": 0, "paginas": 0}}
    for row in duplex_rows:
        duplex_val = row[0]
        pages = row[1] or 0
        folhas = calcular_folhas_fisicas(pages, duplex_val)
        
        if duplex_val == 1:
            tipo = "Duplex (Economia)"
        elif duplex_val == 0:
            tipo = "Simples"
        else:
            tipo = "Não especificado"
        
        duplex_dict[tipo]["impressoes"] += 1
        duplex_dict[tipo]["paginas"] += folhas
    
    duplex_data = [(tipo, data["impressoes"], data["paginas"]) for tipo, data in duplex_dict.items() if data["impressoes"] > 0]
    if duplex_data:
        elements.append(Paragraph("Uso de Modo Duplex", subtitulo))
        duplex_table = [["Tipo", "Impressões", "Páginas", "% do Total"]]
        total_duplex = sum(row[2] for row in duplex_data)
        for row in duplex_data:
            pct = (row[2] / total_duplex * 100) if total_duplex > 0 else 0
            duplex_table.append([
                row[0],
                f"{row[1]:,}",
                f"{row[2]:,}",
                f"{pct:.1f}%"
            ])
        
        elements.append(criar_tabela_profissional(
            duplex_table[1:],
            duplex_table[0],
            larguras_colunas=[5*cm, 3*cm, 3*cm, 3*cm]
        ))
        elements.append(Spacer(1, 0.2*inch))
    
    # Análise temporal (por dia da semana) - AGRUPA POR JOB PRIMEIRO
    if has_job_id:
        dias_rows = cursor.execute(
            f"""SELECT 
                CASE CAST(strftime('%w', date) AS INTEGER)
                    WHEN 0 THEN 'Domingo'
                    WHEN 1 THEN 'Segunda-feira'
                    WHEN 2 THEN 'Terça-feira'
                    WHEN 3 THEN 'Quarta-feira'
                    WHEN 4 THEN 'Quinta-feira'
                    WHEN 5 THEN 'Sexta-feira'
                    WHEN 6 THEN 'Sábado'
                END as dia_semana,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                strftime('%w', date) as order_val
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}, strftime('%w', date)
            """, params
        ).fetchall()
    else:
        dias_rows = cursor.execute(
            f"""SELECT 
                CASE CAST(strftime('%w', date) AS INTEGER)
                    WHEN 0 THEN 'Domingo'
                    WHEN 1 THEN 'Segunda-feira'
                    WHEN 2 THEN 'Terça-feira'
                    WHEN 3 THEN 'Quarta-feira'
                    WHEN 4 THEN 'Quinta-feira'
                    WHEN 5 THEN 'Sexta-feira'
                    WHEN 6 THEN 'Sábado'
                END as dia_semana,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                strftime('%w', date) as order_val
            FROM events
            {where_clause}
            GROUP BY {get_job_group_by()}, strftime('%w', date)
            """, params
        ).fetchall()
    
    # Agrupa por dia da semana e calcula totais
    dias_dict = {}
    for row in dias_rows:
        dia = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        order_val = int(row[3]) if len(row) > 3 and row[3] else 0
        folhas = calcular_folhas_fisicas(pages, duplex)
        
        if dia not in dias_dict:
            dias_dict[dia] = {"impressoes": 0, "paginas": 0, "order": order_val}
        dias_dict[dia]["impressoes"] += 1
        dias_dict[dia]["paginas"] += folhas
    
    # Ordena por dia da semana
    dias_data = [(dia, data["impressoes"], data["paginas"]) for dia, data in sorted(dias_dict.items(), key=lambda x: x[1]["order"])]
    if dias_data:
        elements.append(Paragraph("Distribuição por Dia da Semana", subtitulo))
        dias_table = [["Dia da Semana", "Impressões", "Páginas", "% do Total"]]
        total_dias = sum(row[2] for row in dias_data)
        for row in dias_data:
            pct = (row[2] / total_dias * 100) if total_dias > 0 else 0
            dias_table.append([
                row[0],
                f"{row[1]:,}",
                f"{row[2]:,}",
                f"{pct:.1f}%"
            ])
        
        elements.append(criar_tabela_profissional(
            dias_table[1:],
            dias_table[0],
            larguras_colunas=[4*cm, 3*cm, 3*cm, 3*cm]
        ))
    
    elements.append(PageBreak())
    
    # ========================================================================
    # RECOMENDAÇÕES E CONCLUSÕES
    # ========================================================================
    elements.append(Paragraph("RECOMENDAÇÕES E CONCLUSÕES", titulo_principal))
    elements.append(Spacer(1, 0.2*inch))
    
    # Calcula recomendações baseadas nos dados
    recomendacoes = []
    
    # Verifica uso de duplex
    if duplex_data:
        duplex_simples = next((row[2] for row in duplex_data if 'Simples' in row[0]), 0)
        duplex_total = sum(row[2] for row in duplex_data)
        if duplex_total > 0:
            pct_simples = (duplex_simples / duplex_total) * 100
            if pct_simples > 50:
                recomendacoes.append(
                    f"• <b>Economia Potencial:</b> {pct_simples:.1f}% das impressões são em modo simples. "
                    f"Considere incentivar o uso de duplex para reduzir custos em até 50%."
                )
    
    # Verifica uso de cor
    if color_stats:
        color_colorido = next((row[2] for row in color_stats if 'Color' in str(row[0]) or 'color' in str(row[0]).lower()), 0)
        color_total = sum(row[2] for row in color_stats)
        if color_total > 0:
            pct_color = (color_colorido / color_total) * 100
            if pct_color > 30:
                recomendacoes.append(
                    f"• <b>Otimização de Cor:</b> {pct_color:.1f}% das páginas são impressas em cor. "
                    f"Avalie se todas essas impressões realmente necessitam de cor para reduzir custos."
                )
    
    # Verifica concentração de uso
    if usuarios_data and len(usuarios_data) > 0:
        top3_paginas = sum(row[2] for row in usuarios_data[:3])
        if total_paginas > 0:
            pct_top3 = (top3_paginas / total_paginas) * 100
            if pct_top3 > 40:
                recomendacoes.append(
                    f"• <b>Concentração de Uso:</b> Os 3 principais usuários concentram {pct_top3:.1f}% do volume. "
                    f"Considere treinamento específico para otimização de impressões."
                )
    
    if recomendacoes:
        for rec in recomendacoes:
            elements.append(Paragraph(rec, texto_normal))
            elements.append(Spacer(1, 0.1*inch))
    else:
        elements.append(Paragraph(
            "Nenhuma recomendação específica no momento. Continue monitorando o uso.",
            texto_normal
        ))
    
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        "<b>Conclusão:</b> Este relatório apresenta uma visão abrangente do uso de impressões "
        "no ambiente hospitalar. Utilize essas informações para otimizar recursos, reduzir custos "
        "e melhorar a eficiência operacional.",
        texto_normal
    ))
    
    # ========================================================================
    # GERA PDF
    # ========================================================================
    def on_first_page(canvas_obj, doc):
        criar_cabecalho_hospitalar(canvas_obj, doc, hospital_nome)
        criar_rodape_hospitalar(canvas_obj, doc)
    
    def on_later_pages(canvas_obj, doc):
        criar_cabecalho_hospitalar(canvas_obj, doc, hospital_nome)
        criar_rodape_hospitalar(canvas_obj, doc)
    
    doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_later_pages, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    
    return buffer


# Função removida: sistema de comodatos removido
def _removido_gerar_relatorio_comodatos_pdf(conn: sqlite3.Connection, mes: Optional[str] = None) -> BytesIO:
    """
    Gera relatório comparativo de comodatos em PDF.
    
    Args:
        conn: Conexão com banco de dados
        mes: Mês no formato YYYY-MM (None para mês atual)
    
    Returns:
        BytesIO com PDF gerado
    """
    try:
        from modules.analise_comodatos import (
            obter_resumo_comodatos,
            verificar_excedente_comodatos,
            obter_dados_comodato,
            calcular_roi_comodato
        )
        
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        story = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=COR_PRIMARIA,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Relatório Comparativo de Comodatos", title_style))
        story.append(Paragraph(f"Mês: {mes}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        
        # Resumo Geral
        resumo = obter_resumo_comodatos(conn, mes)
        
        resumo_data = [
            ['Métrica', 'Valor'],
            ['Total de Comodatos', str(resumo['total_comodatos'])],
            ['Custo Fixo Total', f"R$ {resumo['total_custo_fixo']:.2f}"],
            ['Custo Excedente Total', f"R$ {resumo['total_custo_excedente']:.2f}"],
            ['Custo Total', f"R$ {resumo['total_custo']:.2f}"],
            ['Uso Total', f"{resumo['total_uso']:,} páginas"],
            ['Limite Total', f"{resumo['total_limite']:,} páginas"],
            ['% de Uso', f"{resumo['percentual_uso_geral']:.1f}%"],
            ['Com Excedente', str(resumo['comodatos_com_excedente'])],
            ['Próximo do Limite', str(resumo['comodatos_proximo_limite'])]
        ]
        
        resumo_table = Table(resumo_data, colWidths=[4*cm, 4*cm])
        resumo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), COR_CINZA),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("Resumo Geral", styles['Heading2']))
        story.append(resumo_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Análise de ROI por Comodato
        story.append(Paragraph("Análise de ROI por Comodato", styles['Heading2']))
        
        comodatos_raw = conn.execute(
            """SELECT printer_name FROM comodatos WHERE ativo = 1"""
        ).fetchall()
        
        roi_data = [['Impressora', 'Custo Comodato', 'Custo Própria', 'Economia', 'ROI']]
        
        for row in comodatos_raw:
            printer_name = row[0]
            roi = calcular_roi_comodato(conn, printer_name, mes)
            
            if roi:
                economia_text = f"R$ {roi['economia']:.2f}"
                roi_text = f"{roi['percentual_economia']:.1f}%"
                cor_linha = COR_DESTAQUE if roi['roi_positivo'] else COR_ALERTA
                
                roi_data.append([
                    printer_name,
                    f"R$ {roi['custo_comodato']:.2f}",
                    f"R$ {roi['custo_propria']:.2f}",
                    economia_text,
                    roi_text
                ])
        
        if len(roi_data) > 1:
            roi_table = Table(roi_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm])
            roi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), COR_CINZA),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(roi_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Alertas de Excedente
        excedentes = verificar_excedente_comodatos(conn, mes)
        
        if excedentes:
            story.append(Paragraph("Alertas de Excedente", styles['Heading2']))
            
            excedente_data = [['Impressora', 'Uso', 'Limite', 'Excedente', 'Custo Excedente']]
            
            for exc in excedentes:
                excedente_data.append([
                    exc['printer_name'],
                    f"{exc['uso_mensal']:,}",
                    f"{exc['limite']:,}",
                    f"{exc['excedente']:,}",
                    f"R$ {exc['custo_excedente_total']:.2f}"
                ])
            
            excedente_table = Table(excedente_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])
            excedente_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COR_ALERTA),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), COR_CINZA),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(excedente_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Rodapé
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            styles['Normal']
        ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de comodatos: {e}")
        raise


def gerar_dashboard_pdf(stats: Dict, setores: List, usuarios: List, 
                       impressoras: List, hospital_nome: str = "Hospital") -> BytesIO:
    """
    Gera PDF do dashboard completo (versão melhorada)
    
    Args:
        stats: Estatísticas gerais
        setores: Lista de setores
        usuarios: Lista de usuários
        impressoras: Lista de impressoras
        hospital_nome: Nome do hospital
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    # Usa a função completa se tiver conexão
    # Por enquanto, mantém compatibilidade
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph(
        f"{hospital_nome} - Dashboard de Impressões",
        ParagraphStyle(
            'Title',
            fontSize=20,
            textColor=COR_PRIMARIA,
            alignment=TA_CENTER,
            spaceAfter=30
        )
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Estatísticas gerais
    elements.append(Paragraph("Estatísticas Gerais", styles['Heading2']))
    stats_data = [
        ['Métrica', 'Valor'],
        ['Total Impressões', f"{stats.get('total_impressos', 0):,}"],
        ['Total Páginas', f"{stats.get('total_paginas', 0):,}"],
        ['Total Usuários', f"{stats.get('total_usuarios', 0):,}"],
        ['Total Setores', f"{stats.get('total_setores', 0):,}"]
    ]
    
    table = criar_tabela_profissional(stats_data[1:], stats_data[0])
    elements.append(table)
    elements.append(PageBreak())
    
    # Setores
    if setores:
        elements.append(Paragraph("Top Setores", styles['Heading2']))
        setores_data = [['Setor', 'Impressões', 'Páginas']]
        for s in setores[:10]:
            setores_data.append([
                str(s.get('setor', '')),
                f"{s.get('total_impressos', 0):,}",
                f"{s.get('total_paginas', 0):,}"
            ])
        
        table = criar_tabela_profissional(setores_data[1:], setores_data[0])
        elements.append(table)
        elements.append(PageBreak())
    
    # Usuários
    if usuarios:
        elements.append(Paragraph("Top Usuários", styles['Heading2']))
        usuarios_data = [['Usuário', 'Impressões', 'Páginas']]
        for u in usuarios[:10]:
            usuarios_data.append([
                str(u.get('user', '')),
                f"{u.get('total_impressos', 0):,}",
                f"{u.get('total_paginas', 0):,}"
            ])
        
        table = criar_tabela_profissional(usuarios_data[1:], usuarios_data[0])
        elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return buffer
