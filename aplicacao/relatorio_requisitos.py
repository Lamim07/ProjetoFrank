"""Relatório de requisitos, fluxos, casos e RTM para o exportador PDF."""

from .exportacao_pdf import ReportSection
from .requisitos import RequirementPlan, Traceability


def requirement_sections(plan: RequirementPlan, matrix: Traceability, reviewed: bool) -> list[ReportSection]:
    percentage = "Não se aplica" if matrix.linked_percentage is None else f"{matrix.linked_percentage:.1f}%"
    status = "Revisão registrada pelo usuário" if reviewed else "Proposta aguardando revisão"
    sections = [ReportSection("Situação da proposta", [
        status + ". Todos os casos estão não executados.",
        "Requisitos com teste vinculado: " + percentage + ". Esse indicador mede vínculos, não execução ou aprovação.",
        "Requisitos sem teste: " + (", ".join(matrix.uncovered_requirements) or "nenhum"),
        "Testes sem requisito: " + (", ".join(matrix.orphan_tests) or "nenhum"),
        "Testes com pendências: " + (", ".join(matrix.pending_tests) or "nenhum"),
    ]), ReportSection("Requisitos e evidências", columns=["ID", "Descrição", "Origem", "Evidência no TXT"],
        rows=[[r.id, r.description, "Especificação" if r.origin == "especificacao" else "Observado no código", r.evidence]
              for r in plan.requirements])]
    for use_case in plan.use_cases:
        sections.append(ReportSection(f"{use_case.id} — {use_case.title}", [
            "Ator: " + use_case.actor,
            "Requisitos: " + (", ".join(use_case.requirement_ids) or "sem vínculo"),
            "Pré-condições: " + ("; ".join(use_case.preconditions) or "não informadas"),
        ]))
        for title, steps in (("Fluxo principal", use_case.main_flow),
                             ("Fluxos alternativos", use_case.alternative_flows),
                             ("Fluxos de exceção", use_case.exception_flows)):
            sections.append(ReportSection(title, [f"{i}. {step}" for i, step in enumerate(steps, 1)]
                                          or ["Não informado no TXT."]))
    for case in plan.test_cases:
        sections.append(ReportSection(f"{case.id} — {case.title}", [
            "Fluxo: " + {"principal": "Principal", "alternativo": "Alternativo", "excecao": "Exceção"}[case.flow_type],
            "Requisitos: " + (", ".join(case.requirement_ids) or "sem vínculo"),
            "Casos de uso: " + (", ".join(case.use_case_ids) or "sem vínculo"),
            "Pré-condições: " + ("; ".join(case.preconditions) or "não informadas"),
            *[f"Passo {i}: {step}" for i, step in enumerate(case.steps, 1)],
            "Resultado esperado: " + case.expected_result,
            "Pendências: " + ("; ".join(case.pending) or "nenhuma registrada"),
            "Execução: não executado.",
        ]))
    sections.extend([
        ReportSection("RTM — Requisitos para testes", columns=["Requisito", "Casos de uso", "Testes", "Vinculação"],
                      rows=[[r[k] for k in ("requisito", "casos de uso", "testes", "vinculação")] for r in matrix.forward]),
        ReportSection("RTM — Testes para requisitos", columns=["Teste", "Fluxo", "Requisitos", "Casos de uso", "Execução"],
                      rows=[[r[k] for k in ("teste", "fluxo", "requisitos", "casos de uso", "execução")] for r in matrix.reverse]),
        ReportSection("Pontos a confirmar", plan.gaps or ["Nenhuma lacuna registrada."]),
    ])
    if matrix.warnings:
        sections.append(ReportSection("Alertas de coerência", matrix.warnings))
    return sections
