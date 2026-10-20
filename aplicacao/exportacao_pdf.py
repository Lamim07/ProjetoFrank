"""PDF local em memória, com conteúdo escapado e fontes incorporadas."""

from dataclasses import dataclass, field
from io import BytesIO
import os
from pathlib import Path
from xml.sax.saxutils import escape

from .fluxo_controle import FunctionFlow


@dataclass
class ReportSection:
    title: str
    paragraphs: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    graph: FunctionFlow | None = None
    break_before: bool = False


def analysis_sections(result) -> list[ReportSection]:
    sections = [ReportSection("Visão geral", [result.summary, f"Assunto: {result.subject}",
                f"Linguagem: {result.language} | Confiança: {result.language_confidence}",
                f"Tipo: {result.content_type}"])]
    for title, findings in (("Estruturas", result.structures), ("Funções", result.functions),
                            ("Regras de negócio", result.business_rules), ("Operações", result.operations),
                            ("Transações e erros", result.transactions)):
        sections.append(ReportSection(title, columns=["Achado", "Evidência no TXT"],
                                      rows=[[f.description, f.evidence] for f in findings]))
    sections.append(ReportSection("Pontos a confirmar", result.uncertainties or ["Nenhum ponto registrado."]))
    return sections


def explanation_sections(result) -> list[ReportSection]:
    sections = [ReportSection("Visão geral", [result.overview])]
    for title, findings in (("Fluxo passo a passo", result.execution_flow), ("Entradas e saídas", result.inputs_outputs),
                            ("Cálculos e regras", result.calculations_rules), ("Operações com dados", result.data_operations)):
        sections.append(ReportSection(title, columns=["Explicação", "Evidência no TXT"],
                                      rows=[[f.description, f.evidence] for f in findings]))
    sections.append(ReportSection("O que o TXT não mostra", result.unknowns or ["Nenhuma lacuna registrada."]))
    return sections


def functional_sections(suite) -> list[ReportSection]:
    domains = [[d.name, display_interval(d), str(d.scale), format(d.epsilon, "f"), d.null_policy] for d in suite.domains]
    partitions = [[r[k] for k in ("entrada", "particao", "representante", "classe")] for r in suite.partitions]
    boundaries = [[r[k] for k in ("entrada", "fronteira", "posicao", "valor", "classe")] for r in suite.boundaries]
    cases = [[r["id"] + " / " + r["tecnica"], r["objetivo"],
              "; ".join(f"{k}={'NULL' if v is None else v}" for k, v in r["valores"].items()), r["esperado"]]
             for r in suite.cases]
    return [
        ReportSection("Critérios confirmados", suite.notes + (["Fórmula: " + suite.formula] if suite.formula else []),
                      ["Entrada", "Intervalo", "Casas", "ε", "Nulo"], domains),
        ReportSection("Classes de equivalência (PCE)", columns=["Entrada", "Partição", "Representante", "Classe"], rows=partitions),
        ReportSection("Análise de valores limite (AVL)", columns=["Entrada", "Fronteira", "Posição", "Valor", "Classe"], rows=boundaries),
        ReportSection("Casos de teste", columns=["Caso", "Objetivo", "Entradas", "Resultado esperado"], rows=cases),
    ]


def display_interval(domain) -> str:
    return ("[" if domain.lower_inclusive else "]") + format(domain.lower, "f") + "; " + format(domain.upper, "f") + ("]" if domain.upper_inclusive else "[")


def flow_sections(report) -> list[ReportSection]:
    sections = []
    for index, flow in enumerate(report.functions):
        sections.append(ReportSection(flow.name,
                        [f"N = {len(flow.nodes)} nós; E = {len(flow.edges)} arestas; P = 1; V(G) = E - N + 2P = {flow.complexity}."] + flow.notes,
                        graph=flow, break_before=index > 0))
        sections.append(ReportSection("Blocos de " + flow.name, columns=["Nó", "Linha", "Conteúdo"],
                                      rows=[[n.id, str(n.line or "-"), n.text] for n in flow.nodes]))
        sections.append(ReportSection("Arestas de " + flow.name, columns=["Origem", "Destino", "Condição"],
                                      rows=[[a, b, label or "sequência"] for a, b, label in flow.edges]))
    if report.unsupported:
        sections.append(ReportSection("Funções sem métrica", report.unsupported))
    return sections


def _diagram(flow: FunctionFlow, width: float):
    from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
    from reportlab.lib import colors
    if len(flow.nodes) > 22:
        return None
    # Ignore DFS back edges only for layout; all edges remain in the drawing.
    adjacency = {n.id: [] for n in flow.nodes}
    for a, b, _ in flow.edges:
        adjacency[a].append(b)
    visited, active, order, back = set(), set(), [], set()

    def visit(n):
        visited.add(n)
        active.add(n)
        for b in adjacency[n]:
            if b in active:
                back.add((n, b))
            elif b not in visited:
                visit(b)
        active.remove(n)
        order.append(n)

    visit(flow.nodes[0].id)
    ranks = {n.id: 0 for n in flow.nodes}
    for n in reversed(order):
        for b in adjacency[n]:
            if (n, b) not in back:
                ranks[b] = max(ranks[b], ranks[n] + 1)
    levels = {}
    for n in flow.nodes:
        levels.setdefault(ranks[n.id], []).append(n)
    if max(levels) > 10 or max(map(len, levels.values())) > 3:
        return None
    height = (max(levels) + 1) * 56 + 12
    drawing = Drawing(width, height)
    positions = {}
    box_w = min(155, width / max(map(len, levels.values())) - 12)
    for rank, group in levels.items():
        for index, n in enumerate(group):
            positions[n.id] = ((index + 1) * width / (len(group) + 1), height - rank * 56 - 24)
    for a, b, label in flow.edges:
        x1, y1 = positions[a]
        x2, y2 = positions[b]
        if (a, b) in back:
            bend = width - 5
            x1 += box_w / 2
            x2 += box_w / 2
            if a == b:
                y1 -= 8
                y2 += 8
            drawing.add(Line(x1, y1, bend, y1, strokeColor=colors.HexColor("#84978f")))
            drawing.add(Line(bend, y1, bend, y2, strokeColor=colors.HexColor("#84978f")))
            drawing.add(Line(bend, y2, x2, y2, strokeColor=colors.HexColor("#84978f")))
            drawing.add(Polygon([x2, y2, x2+6, y2-3, x2+6, y2+3], fillColor=colors.HexColor("#84978f"), strokeColor=None))
            if label:
                drawing.add(String(bend-20, (y1+y2)/2, label, fontName="TSBody", fontSize=7))
        elif ranks[b] - ranks[a] > 1:
            side = 1 if label == "não" else -1
            start = x1 + side * box_w / 2
            end = x2 + side * box_w / 2
            rail = min(width-5, max(start, end)+20) if side == 1 else max(5, min(start, end)-20)
            for xa, ya, xb, yb in ((start, y1, rail, y1), (rail, y1, rail, y2), (rail, y2, end, y2)):
                drawing.add(Line(xa, ya, xb, yb, strokeColor=colors.HexColor("#84978f")))
            drawing.add(Polygon([end, y2, end+side*6, y2-3, end+side*6, y2+3], fillColor=colors.HexColor("#84978f"), strokeColor=None))
            if label:
                drawing.add(String(rail+3, (y1+y2)/2, label, fontName="TSBody", fontSize=7))
        else:
            y1 -= 15
            y2 += 15
            drawing.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#84978f")))
            drawing.add(Polygon([x2, y2, x2-3, y2+6, x2+3, y2+6], fillColor=colors.HexColor("#84978f"), strokeColor=None))
            if label:
                drawing.add(String((x1+x2)/2+3, (y1+y2)/2, label, fontName="TSBody", fontSize=7))
    for n in flow.nodes:
        x, y = positions[n.id]
        drawing.add(Rect(x-box_w/2, y-15, box_w, 30, rx=4,
                         fillColor=colors.HexColor("#e9f3ee" if n.kind not in ("if", "loop") else "#fff0ce"),
                         strokeColor=colors.HexColor("#8ba497")))
        drawing.add(String(x, y+3, n.id + (f" · L{n.line}" if n.line else ""), textAnchor="middle", fontName="TSBold", fontSize=8))
        label = " ".join(n.text.split())
        drawing.add(String(x, y-8, label[:28] + ("..." if len(label)>28 else ""), textAnchor="middle", fontName="TSBody", fontSize=6.5))
    return drawing


def render_pdf(title: str, filename: str, sections: list[ReportSection]) -> bytes:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    font_dir = Path(reportlab.__file__).parent / "fonts"
    if "TSBody" not in pdfmetrics.getRegisteredFontNames():
        candidates = [
            (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
             Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbd.ttf"),
            (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
             Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
            (font_dir / "Vera.ttf", font_dir / "VeraBd.ttf"),
        ]
        regular, bold = next(pair for pair in candidates if all(p.is_file() for p in pair))
        pdfmetrics.registerFont(TTFont("TSBody", str(regular)))
        pdfmetrics.registerFont(TTFont("TSBold", str(bold)))
    normal = ParagraphStyle("normal", fontName="TSBody", fontSize=9, leading=13, spaceAfter=7, splitLongWords=True)
    heading = ParagraphStyle("section", parent=normal, fontName="TSBold", fontSize=13, leading=17, spaceBefore=14, spaceAfter=8, keepWithNext=True)
    main_title = ParagraphStyle("title", parent=heading, fontSize=21, leading=26)
    cell = ParagraphStyle("cell", parent=normal, fontSize=7.5, leading=10, spaceAfter=0, alignment=TA_LEFT)

    def paragraph(text, style=normal):
        # Model/file content is always text, never ReportLab XML or remote media.
        value = str(text)
        if ord("ε") not in pdfmetrics.getFont("TSBody").face.charWidths:
            value = value.replace("ε", "epsilon")
        return Paragraph(escape(value).replace("\n", "<br/>"), style)

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=38, rightMargin=38,
                                 topMargin=44, bottomMargin=42, title=title, author="TestingStudio Web")
    story = [paragraph(title, main_title), paragraph("Arquivo: " + filename),
             paragraph("Relatório de análise estática. O código recebido não foi executado."), Spacer(1, 10)]
    for section in sections:
        if section.break_before:
            story.append(PageBreak())
        story.append(paragraph(section.title, heading))
        story.extend(paragraph(p) for p in section.paragraphs)
        if section.graph:
            graph = _diagram(section.graph, document.width)
            if graph:
                story.extend([graph, Spacer(1, 12)])
            else:
                story.append(paragraph("O grafo completo está representado nas tabelas de nós e arestas a seguir."))
        if section.columns and section.rows:
            data = [[paragraph(c, cell) for c in section.columns]]
            data.extend([[paragraph(v, cell) for v in row] for row in section.rows])
            table = LongTable(data, colWidths=[document.width/len(section.columns)]*len(section.columns),
                              repeatRows=1, splitInRow=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3eee8")),
                ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#cfdad3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
        elif section.columns:
            story.append(paragraph("Nenhum achado confirmado."))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("TSBody", 8)
        canvas.setFillColor(colors.HexColor("#63766b"))
        canvas.drawString(38, 24, "TestingStudio Web")
        canvas.drawRightString(A4[0]-38, 24, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
