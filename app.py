"""TestingStudio Web: documentação e análise de testes sobre arquivos TXT."""

import hashlib
from pathlib import Path

import streamlit as st

from aplicacao.analyzer import AnalysisError, analyze_text, explain_code
from aplicacao.documentation import build_documentation
from aplicacao.file_reader import read_text
from aplicacao.gemini_client import GeminiClient, GeminiError
from aplicacao.models import CodeExplanation, Finding
from aplicacao.exportacao_pdf import analysis_sections, explanation_sections
from aplicacao.interface_relatorios import pdf_actions
from aplicacao.interface_testes import flow_view, functional_view
from aplicacao.interface_requisitos import requirements_view
from aplicacao.validators import MAX_FILE_BYTES, UploadValidationError, validate_upload


PREVIEW_CHARS = 12_000


def clear_results() -> None:
    for key in ("documentation_result", "explanation_result", "functional_result", "flow_result",
                "requirements_result", "requirements_reviewed", "requirements_revision"):
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if key.startswith("pdf_"):
            st.session_state.pop(key, None)


def show_findings(title: str, findings: list[Finding]) -> None:
    st.subheader(title)
    if not findings:
        st.caption("Nenhum achado confirmado nessa categoria.")
        return
    for finding in findings:
        st.write(finding.description)
        st.code(finding.evidence, language=None, wrap_lines=True)


def show_documentation(filename: str) -> None:
    result = st.session_state.get("documentation_result")
    if result is None:
        return

    st.divider()
    st.header("Documentação do arquivo")
    st.write(result.summary)
    first, second, third = st.columns(3)
    first.metric("Tipo de conteúdo", result.content_type)
    second.metric("Linguagem aparente", result.language)
    third.metric("Confiança", result.language_confidence.capitalize())
    st.subheader("Do que trata")
    st.write(result.subject)

    show_findings("Estruturas", result.structures)
    show_findings("Funções", result.functions)
    show_findings("Regras de negócio", result.business_rules)
    show_findings("Operações", result.operations)
    show_findings("Transações e erros", result.transactions)

    if result.uncertainties:
        st.subheader("Pontos que precisam de confirmação")
        for item in result.uncertainties:
            st.write(f"• {item}")

    st.download_button(
        "Baixar documentação (.md)",
        data=build_documentation(result, filename),
        file_name=f"documentacao_{Path(filename).stem}.md",
        mime="text/markdown",
    )
    pdf_actions("Documentação do arquivo", filename, analysis_sections(result), "documentacao")


def show_explanation(filename: str) -> None:
    result: CodeExplanation | None = st.session_state.get("explanation_result")
    if result is None:
        return

    st.divider()
    st.header("Como o código funciona")
    st.write(result.overview)
    show_findings("Fluxo passo a passo", result.execution_flow)
    show_findings("Entradas e saídas", result.inputs_outputs)
    show_findings("Cálculos e regras", result.calculations_rules)
    show_findings("Operações com dados", result.data_operations)
    if result.unknowns:
        st.subheader("O que o TXT não mostra")
        for item in result.unknowns:
            st.write(f"• {item}")
    pdf_actions("Como o código funciona", filename, explanation_sections(result), "explicacao")


def main() -> None:
    st.set_page_config(
        page_title="TestingStudio Web",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
          .block-container {max-width: 1080px; padding-top: 2.25rem;}
          h1, h2, h3 {color: #20344a;}
          h1 {letter-spacing: -0.035em;}
          div[data-testid="stMetric"] {
            border: 1px solid #dfe7e3; border-radius: 10px;
            padding: 0.8rem 1rem; background: #fff;
          }
          div[data-testid="stCode"] {border: 1px solid #dfe7e3;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.caption("TESTINGSTUDIO WEB  /  SPRINTS 1, 2 E 3")
    st.title("Entenda o que há no seu TXT")
    st.write("Documente o código, entenda seu funcionamento e prepare testes a partir de um TXT.")
    st.info(
        "O código do TXT não será executado. Documentação, explicação e derivação de requisitos usam a API Gemini. "
        "PCE/AVL e fluxo de controle são calculados localmente."
    )

    uploaded = st.file_uploader(
        "Arquivo TXT",
        type=["txt"],
        help="UTF-8, até 1 MB. O arquivo permanece apenas nesta sessão.",
    )
    if uploaded is None:
        clear_results()
        st.session_state.pop("analysis_digest", None)
        st.caption("Selecione um .txt para começar.")
        return

    try:
        data = uploaded.getvalue()
        validate_upload(uploaded.name, data)
        content = read_text(data)
    except (UploadValidationError, OSError) as exc:
        clear_results()
        if isinstance(exc, UploadValidationError):
            st.error(str(exc))
        else:
            st.error("Não foi possível ler o arquivo. Envie-o novamente.")
        return

    digest = hashlib.sha256(data).hexdigest()
    if st.session_state.get("analysis_digest") != digest:
        clear_results()
    st.session_state["analysis_digest"] = digest

    st.caption(f"{uploaded.name} · {len(data):,} bytes · limite {MAX_FILE_BYTES:,} bytes")
    with st.expander("Prévia do conteúdo", expanded=False):
        st.code(content[:PREVIEW_CHARS], language=None, wrap_lines=False)
        if len(content) > PREVIEW_CHARS:
            st.caption("Prévia limitada a 12.000 caracteres; a análise usa o arquivo completo.")

    mode = st.radio(
        "O que deseja fazer?",
        ("Documentação", "Explicar o código", "PCE / AVL", "Fluxo de controle", "Requisitos e RTM"),
        horizontal=True,
        help="Cada opção gera um resultado próprio para o mesmo arquivo.",
    )
    if mode == "PCE / AVL":
        functional_view(content, uploaded.name, digest[:12])
        return
    if mode == "Fluxo de controle":
        flow_view(content, uploaded.name)
        return
    if mode == "Requisitos e RTM":
        requirements_view(content, uploaded.name, digest[:12])
        return
    result_key = "documentation_result" if mode == "Documentação" else "explanation_result"
    action = "Gerar documentação" if mode == "Documentação" else "Explicar código"
    if st.button(action, type="primary", width="stretch"):
        st.session_state.pop(result_key, None)
        with st.spinner("Lendo e interpretando o TXT…"):
            try:
                client = GeminiClient()
                st.session_state[result_key] = (
                    analyze_text(content, client)
                    if mode == "Documentação"
                    else explain_code(content, client)
                )
            except (AnalysisError, GeminiError) as exc:
                st.error(str(exc))
    if mode == "Documentação":
        show_documentation(uploaded.name)
    else:
        show_explanation(uploaded.name)


if __name__ == "__main__":
    main()
