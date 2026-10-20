"""Revisão acessível da proposta e visualização da RTM nos dois sentidos."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .analyzer import AnalysisError
from .gemini_client import GeminiClient, GeminiError
from .interface_relatorios import pdf_actions
from .relatorio_requisitos import requirement_sections
from .requisitos import RequirementPlan, build_rtm, derive_requirements, parse_requirements, rtm_csv


ORIGINS = {"especificacao": "Especificação", "observado_no_codigo": "Observado no código"}
FLOWS = {"principal": "Principal", "alternativo": "Alternativo", "excecao": "Exceção"}


def _text(value) -> str:
    return "" if value is None or pd.isna(value) else str(value).strip()


def _items(value, separator=" | ") -> list[str]:
    return [v.strip() for v in _text(value).split(separator) if v.strip()]


def _rows(frame):
    return [{k: _text(v) for k, v in row.items()} for row in frame.to_dict("records")
            if any(_text(v) for v in row.values())]


def review_tables(plan: RequirementPlan, prefix: str):
    st.caption("Use vírgulas entre IDs e ' | ' entre passos ou pré-condições. Os IDs devem ser únicos e corresponder aos vínculos usados.")
    req_columns = ["ID", "Requisito", "Origem", "Evidência"]
    uc_columns = ["ID", "Nome", "Ator", "Requisitos", "Pré-condições", "Principal", "Alternativos", "Exceções"]
    ct_columns = ["ID", "Cenário", "Fluxo", "Requisitos", "Casos de uso", "Pré-condições", "Passos", "Esperado", "Pendências"]
    reqs = [{"ID": r.id, "Requisito": r.description, "Origem": ORIGINS[r.origin], "Evidência": r.evidence} for r in plan.requirements]
    ucs = [{"ID": u.id, "Nome": u.title, "Ator": u.actor, "Requisitos": ", ".join(u.requirement_ids),
            "Pré-condições": " | ".join(u.preconditions), "Principal": " | ".join(u.main_flow),
            "Alternativos": " | ".join(u.alternative_flows), "Exceções": " | ".join(u.exception_flows)} for u in plan.use_cases]
    cts = [{"ID": c.id, "Cenário": c.title, "Fluxo": FLOWS[c.flow_type], "Requisitos": ", ".join(c.requirement_ids),
            "Casos de uso": ", ".join(c.use_case_ids), "Pré-condições": " | ".join(c.preconditions),
            "Passos": " | ".join(c.steps), "Esperado": c.expected_result, "Pendências": " | ".join(c.pending)} for c in plan.test_cases]
    st.markdown("**Requisitos**")
    req = st.data_editor(pd.DataFrame(reqs, columns=req_columns), num_rows="dynamic", hide_index=True, width="stretch",
                         key=prefix+"_req", column_config={"Origem": st.column_config.SelectboxColumn(options=list(ORIGINS.values()), required=True)})
    st.markdown("**Casos de uso e fluxos**")
    uc = st.data_editor(pd.DataFrame(ucs, columns=uc_columns), num_rows="dynamic", hide_index=True,
                        width="stretch", key=prefix+"_uc")
    st.markdown("**Casos de teste**")
    ct = st.data_editor(pd.DataFrame(cts, columns=ct_columns), num_rows="dynamic", hide_index=True, width="stretch",
                        key=prefix+"_ct", column_config={"Fluxo": st.column_config.SelectboxColumn(options=list(FLOWS.values()), required=True)})
    gaps = st.text_area("Pontos que precisam de confirmação (um por linha)", value="\n".join(plan.gaps), key=prefix+"_gaps")
    return req, uc, ct, gaps


def edited_plan(req_frame, uc_frame, ct_frame, gaps: str, content: str) -> RequirementPlan:
    origins = {v: k for k, v in ORIGINS.items()}
    flows = {v: k for k, v in FLOWS.items()}
    payload = {
        "requirements": [{"id": r["ID"], "description": r["Requisito"], "origin": origins.get(r["Origem"], ""),
                          "evidence": r["Evidência"]} for r in _rows(req_frame)],
        "use_cases": [{"id": r["ID"], "title": r["Nome"], "actor": r["Ator"],
                       "requirement_ids": _items(r["Requisitos"], ","), "preconditions": _items(r["Pré-condições"]),
                       "main_flow": _items(r["Principal"]), "alternative_flows": _items(r["Alternativos"]),
                       "exception_flows": _items(r["Exceções"])} for r in _rows(uc_frame)],
        "test_cases": [{"id": r["ID"], "title": r["Cenário"], "flow_type": flows.get(r["Fluxo"], ""),
                        "requirement_ids": _items(r["Requisitos"], ","), "use_case_ids": _items(r["Casos de uso"], ","),
                        "preconditions": _items(r["Pré-condições"]), "steps": _items(r["Passos"]),
                        "expected_result": r["Esperado"], "pending": _items(r["Pendências"])} for r in _rows(ct_frame)],
        "gaps": [line.strip() for line in gaps.splitlines() if line.strip()],
    }
    return parse_requirements(json.dumps(payload, ensure_ascii=False), content)


def requirements_view(content: str, filename: str, digest: str):
    st.subheader("Requisitos, casos de uso e rastreabilidade")
    st.write("Derive casos de teste para o caminho principal, desvios aceitáveis e situações de exceção. Depois, revise a proposta e confira a RTM.")
    if st.button("Derivar requisitos e casos de teste", type="primary", width="stretch"):
        try:
            with st.spinner("Lendo requisitos e propondo casos de teste…"):
                plan = derive_requirements(content, GeminiClient())
            st.session_state["requirements_result"] = plan
            st.session_state["requirements_reviewed"] = False
            st.session_state["requirements_revision"] = st.session_state.get("requirements_revision", 0) + 1
            st.session_state.pop("pdf_requisitos", None)
        except (AnalysisError, GeminiError) as exc:
            st.error(str(exc))
    plan: RequirementPlan | None = st.session_state.get("requirements_result")
    if plan is None:
        st.caption("Use um TXT com requisitos ou descrição de casos de uso. Código também pode ser analisado; os comportamentos encontrados serão identificados como observações.")
        return
    if any(r.origin == "observado_no_codigo" for r in plan.requirements):
        st.warning("Há comportamentos observados no código. Confirme-os com a especificação antes de tratá-los como requisitos do produto.")
    revision = st.session_state.get("requirements_revision", 0)
    prefix = digest + "_rtm_" + str(revision)
    with st.expander("Revisar requisitos, casos de uso e testes", expanded=True):
        with st.form(prefix + "_form"):
            req, uc, ct, gaps = review_tables(plan, prefix)
            reviewed = st.checkbox("Revisei os requisitos, os fluxos, os resultados esperados e os vínculos apresentados.",
                                   value=st.session_state.get("requirements_reviewed", False), key=prefix+"_reviewed")
            applied = st.form_submit_button("Aplicar revisão e atualizar RTM", type="primary")
        if applied:
            try:
                plan = edited_plan(req, uc, ct, gaps, content)
                st.session_state["requirements_result"] = plan
                st.session_state["requirements_reviewed"] = reviewed
                st.session_state.pop("pdf_requisitos", None)
            except AnalysisError as exc:
                st.error(str(exc))
    reviewed = st.session_state.get("requirements_reviewed", False)
    if reviewed:
        st.success("Revisão registrada. Os casos de teste aguardam execução.")
    else:
        st.info("Proposta aguardando revisão. Nenhum caso de teste foi executado.")
    st.caption("A RTM e os downloads usam a última revisão aplicada. Após editar as tabelas, clique em Aplicar revisão.")
    matrix = build_rtm(plan)
    st.header("Matriz de rastreabilidade (RTM)")
    one, two, three = st.columns(3)
    percentage = matrix.linked_percentage
    one.metric("Requisitos com teste vinculado", "—" if percentage is None else f"{percentage:.1f}%")
    two.metric("Requisitos sem teste", len(matrix.uncovered_requirements))
    three.metric("Testes sem requisito", len(matrix.orphan_tests))
    st.caption("O percentual mede vínculos entre requisitos e casos; não representa testes executados ou aprovados.")
    if matrix.uncovered_requirements:
        st.warning("Requisitos sem caso de teste: " + ", ".join(matrix.uncovered_requirements))
    if matrix.orphan_tests:
        st.warning("Casos sem requisito de origem: " + ", ".join(matrix.orphan_tests))
    if matrix.pending_tests:
        st.warning("Casos com pendências: " + ", ".join(matrix.pending_tests))
    for warning in matrix.warnings:
        st.warning(warning)
    st.subheader("Requisitos → testes")
    st.dataframe(matrix.forward, hide_index=True, width="stretch")
    st.subheader("Testes → requisitos")
    st.dataframe(matrix.reverse, hide_index=True, width="stretch")
    if plan.gaps:
        st.subheader("Pontos a confirmar")
        for gap in plan.gaps:
            st.write("• " + gap)
    payload = {"proposta": plan.model_dump(), "revisao_registrada": reviewed,
               "execucao": "Não executado", "rtm_requisitos_testes": matrix.forward,
               "rtm_testes_requisitos": matrix.reverse}
    st.download_button("Baixar proposta e RTM (.json)", json.dumps(payload, ensure_ascii=False, indent=2),
                        file_name=f"requisitos_{Path(filename).stem}.json", mime="application/json")
    st.download_button("Baixar matriz RTM (.csv)", rtm_csv(matrix),
                        file_name=f"rtm_{Path(filename).stem}.csv", mime="text/csv")
    pdf_actions("Requisitos, casos de uso, testes e RTM", filename,
                requirement_sections(plan, matrix, reviewed), "requisitos")
