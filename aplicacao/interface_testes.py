"""Interface das sprints de testes funcionais e análise estrutural."""

import json

import streamlit as st

from .exportacao_pdf import display_interval, flow_sections, functional_sections
from .fluxo_controle import FlowError, analyze_flow
from .interface_relatorios import pdf_actions
from .testes_funcionais import DomainError, NumericDomain, discover_inputs, generate_suite, number


def functional_view(content: str, filename: str, digest: str):
    st.subheader("Classes de equivalência e valores limite")
    st.write("Defina os domínios que a regra de negócio permite. O cálculo usa esses critérios para gerar uma suíte de teste.")
    suggestions = discover_inputs(content)
    by_name = {item["nome"]: item for item in suggestions}
    if suggestions:
        st.caption("Declarações numéricas encontradas no TXT; os limites de negócio precisam ser informados abaixo.")
        st.dataframe(suggestions, hide_index=True, width="stretch")
    defaults = [name for name in by_name if name.startswith("p_")][:6] or list(by_name)[:3]
    chosen = st.multiselect("Entradas que deseja testar", list(by_name), default=defaults,
                            key=digest + "_chosen")
    manual = st.text_input("Outras entradas (nomes separados por vírgula)", key=digest+"_manual",
                           help="Use nomes sem espaços, como quantidade, preco e desconto.")
    names = list(dict.fromkeys(chosen + [n.strip() for n in manual.split(",") if n.strip()]))
    if not names:
        st.info("Escolha uma entrada ou informe os nomes para configurar os domínios.")
        return
    if len(names) > 12:
        st.error("Selecione até 12 entradas por suíte.")
        return
    with st.form("functional_" + digest):
        values = []
        for name in names:
            st.markdown(f"**Entrada: {name}**")
            prefix = digest + "_domain_" + name
            left, right = st.columns(2)
            lower = left.text_input("Limite mínimo", key=prefix+"_lower", placeholder="Ex.: 0,00")
            upper = right.text_input("Limite máximo", key=prefix+"_upper", placeholder="Ex.: 100,00")
            lower_in = left.checkbox("Incluir o mínimo", value=True, key=prefix+"_lower_in")
            upper_in = right.checkbox("Incluir o máximo", value=True, key=prefix+"_upper_in")
            scale = left.number_input("Casas decimais (0 para inteiros)", min_value=0, max_value=12,
                                       value=by_name.get(name, {}).get("casas", 0), step=1, key=prefix+"_scale")
            policy = right.selectbox("Tratamento de NULL", ("Rejeitar", "Aceitar sem converter", "Converter em zero"), key=prefix+"_null")
            values.append((name, lower, upper, scale, lower_in, upper_in, policy))
        formula = st.text_input("Fórmula do resultado esperado (opcional)", key=digest+"_formula",
                                placeholder="Ex.: (p_val1 * p_val2) + p_val3",
                                help="Somente +, -, *, / e parênteses. A fórmula é um modelo de resultado, não executa o TXT.")
        confirmed = st.checkbox("Confirmo que os limites, a precisão, o tratamento de NULL e a fórmula correspondem aos critérios que quero testar.", key=digest+"_confirmed")
        submitted = st.form_submit_button("Gerar PCE, AVL e casos de teste", type="primary", width="stretch")
    if submitted:
        st.session_state.pop("functional_result", None)
        try:
            if not confirmed:
                raise DomainError("Confirme os critérios antes de gerar os casos.")
            domains = [NumericDomain(name, number(lower), number(upper), int(scale), lower_in, upper_in,
                                      {"Rejeitar": "rejeitar", "Aceitar sem converter": "aceitar", "Converter em zero": "zero"}[policy])
                       for name, lower, upper, scale, lower_in, upper_in, policy in values]
            st.session_state["functional_result"] = generate_suite(domains, formula.strip())
        except DomainError as exc:
            st.error(str(exc))
    suite = st.session_state.get("functional_result")
    if suite is None:
        return
    st.divider()
    st.header("Plano de testes funcionais")
    st.caption("Este resultado usa a última configuração gerada. Após editar os critérios, gere novamente.")
    st.dataframe([{"entrada": d.name, "intervalo": display_interval(d), "epsilon": format(d.epsilon, "f"),
                   "primeiro válido": format(d.first, "f"), "último válido": format(d.last, "f"),
                   "NULL": d.null_policy} for d in suite.domains], hide_index=True, width="stretch")
    st.subheader("Classes de equivalência (PCE)")
    st.dataframe(suite.partitions, hide_index=True, width="stretch")
    st.subheader("Valores limite (AVL)")
    st.dataframe(suite.boundaries, hide_index=True, width="stretch")
    st.subheader("Casos de teste")
    rows = [{**r, "valores": json.dumps(r["valores"], ensure_ascii=False)} for r in suite.cases]
    st.dataframe(rows, hide_index=True, width="stretch")
    for note in suite.notes:
        st.caption(note)
    st.download_button("Baixar casos de teste (.json)", json.dumps({"formula": suite.formula,
                        "criterios": [{"nome": d.name, "minimo": str(d.lower), "maximo": str(d.upper),
                        "inclui_minimo": d.lower_inclusive, "inclui_maximo": d.upper_inclusive,
                        "casas": d.scale, "NULL": d.null_policy} for d in suite.domains],
                        "particoes": suite.partitions, "limites": suite.boundaries, "casos": suite.cases,
                        "observacoes": suite.notes}, ensure_ascii=False, indent=2),
                        file_name="casos_de_teste.json", mime="application/json")
    pdf_actions("PCE, AVL e casos de teste", filename, functional_sections(suite), "testes")


def flow_view(content: str, filename: str):
    st.subheader("Grafo de fluxo e complexidade ciclomática")
    st.write("Analise as funções Informix-4GL do TXT para visualizar decisões e caminhos de controle.")
    st.caption("Suporte: FUNCTION, IF/ELSE, WHILE, FOR e RETURN. Chamadas e SQL são blocos; exceções implícitas não são expandidas.")
    if st.button("Gerar grafo e métricas", type="primary", width="stretch"):
        st.session_state.pop("flow_result", None)
        try:
            st.session_state["flow_result"] = analyze_flow(content)
        except FlowError as exc:
            st.error(str(exc))
    report = st.session_state.get("flow_result")
    if report is None:
        return
    for warning in report.unsupported:
        st.warning(warning)
    if not report.functions:
        st.info("Nenhuma função compatível pôde ser analisada. Veja as construções indicadas acima.")
        return
    st.dataframe([{"função": f.name, "nós (N)": len(f.nodes), "arestas (E)": len(f.edges),
                   "V(G)": f.complexity} for f in report.functions], hide_index=True, width="stretch")
    index = st.selectbox("Função para visualizar", range(len(report.functions)),
                        format_func=lambda i: report.functions[i].name)
    flow = report.functions[index]
    st.metric("Complexidade ciclomática V(G)", flow.complexity)
    st.caption(f"E - N + 2P = {len(flow.edges)} - {len(flow.nodes)} + 2 × 1 = {flow.complexity}")
    st.graphviz_chart(flow.dot(), width="content")
    with st.expander("Ver blocos e arestas completos"):
        st.dataframe([{"nó": n.id, "linha": str(n.line or "-"), "conteúdo": n.text} for n in flow.nodes],
                     hide_index=True, width="stretch")
        st.dataframe([{"origem": a, "destino": b, "condição": label or "sequência"} for a, b, label in flow.edges],
                     hide_index=True, width="stretch")
    for note in flow.notes:
        st.caption(note)
    st.download_button("Baixar grafo (.dot)", flow.dot(), file_name=flow.name+".dot", mime="text/plain")
    pdf_actions("Fluxo de controle e complexidade ciclomática", filename, flow_sections(report), "fluxo")
