"""Render the validated analysis as a portable Markdown document."""

from .models import AnalysisResult, Finding


def _section(title: str, findings: list[Finding]) -> list[str]:
    lines = [f"## {title}", ""]
    if not findings:
        return lines + ["Nenhum achado confirmado.", ""]
    for finding in findings:
        lines.extend([f"- {finding.description}", f"  - Evidência: `{finding.evidence}`", ""])
    return lines


def build_documentation(result: AnalysisResult, filename: str) -> str:
    lines = [
        f"# Documentação de {filename}",
        "",
        "> Gerada por análise estática do TXT. Confirme os pontos incertos no sistema original.",
        "",
        "## Visão geral",
        "",
        result.summary,
        "",
        f"- **Tipo:** {result.content_type}",
        f"- **Assunto:** {result.subject}",
        f"- **Linguagem aparente:** {result.language}",
        f"- **Confiança:** {result.language_confidence}",
        "",
    ]
    for title, findings in (
        ("Estruturas", result.structures),
        ("Funções", result.functions),
        ("Regras de negócio", result.business_rules),
        ("Operações", result.operations),
        ("Transações e erros", result.transactions),
    ):
        lines.extend(_section(title, findings))
    lines.extend(["## Pontos a confirmar", ""])
    lines.extend(f"- {item}" for item in result.uncertainties)
    if not result.uncertainties:
        lines.append("Nenhum ponto incerto registrado.")
    return "\n".join(lines).rstrip() + "\n"
