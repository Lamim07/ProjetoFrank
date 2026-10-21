"""Módulo avançado: Def-Uso, catálogo de mutantes e experimento aritmético."""

import json
import re
from dataclasses import asdict

import pandas as pd
import streamlit as st

from .def_uso import analyze_data_flow
from .exportacao_pdf import ReportSection
from .fluxo_controle import FlowError
from .interface_relatorios import pdf_actions
from .mutacao import (MutationError, STATUSES, catalog_payload, evaluate_formula_mutation,
                      formula_inputs, generate_mutants, mutant_source, score_registry)
from .modelo_funcao import available_models, evaluate_source_mutation, parse_cases_csv


DATA_NOTES = [
    "Análise estática intraprocedural de definições alcançantes. Parâmetros são definidos na entrada.",
    "c-use é uso em cálculo/saída; p-use é uso em condição, associado a cada aresta de saída.",
    "O caminho candidato não contém redefinição intermediária da variável; sua viabilidade lógica não foi provada.",
    "A análise não executa testes e não mede cobertura. Chamadas, SQL, aliases, arrays e FOR não têm modelo de efeitos neste módulo.",
]


def data_sections(report):
    sections = [ReportSection("Critérios e limites", DATA_NOTES)]
    for function in report.functions:
        sections.append(ReportSection(function.name, function.warnings or ["Nenhum alerta local."]))
        sections.append(ReportSection("Definições e usos", columns=["Nó", "Linha", "Instrução", "Define", "Usa"],
                                      rows=[[str(e[k]) for k in ("nó", "linha", "instrução", "define", "usa")] for e in function.events]))
        sections.append(ReportSection("Pares Def-Uso", columns=["Variável", "Definição", "Uso", "Tipo / aresta", "Caminho candidato"],
                                      rows=[[p["variável"], f'{p["definição"]} / L{p["linha definição"]}',
                                             f'{p["uso"]} / L{p["linha uso"]}', p["tipo"]+" "+p["aresta"], p["caminho candidato"]]
                                            for p in function.pairs]))
    if report.unsupported:
        sections.append(ReportSection("Funções não analisadas", report.unsupported))
    return sections


def data_flow_view(content, filename):
    st.subheader("Pares Def-Uso")
    st.write("Rastreie quais definições podem alcançar cada uso de uma variável, sem uma redefinição no caminho.")
    st.caption("Análise local de funções Informix-4GL. Os caminhos indicam possibilidades estruturais e precisam de revisão.")
    if st.button("Analisar definições e usos", type="primary", width="stretch"):
        st.session_state.pop("data_flow_result", None)
        try:
            st.session_state["data_flow_result"] = analyze_data_flow(content)
        except FlowError as exc:
            st.error(str(exc))
    report = st.session_state.get("data_flow_result")
    if report is None:
        return
    for warning in report.unsupported:
        st.warning(warning)
    if report.functions:
        st.dataframe([{"função": f.name, "pares candidatos": len(f.pairs), "alertas": len(f.warnings)}
                      for f in report.functions], hide_index=True, width="stretch")
        index = st.selectbox("Função para rastrear", range(len(report.functions)),
                             format_func=lambda i: report.functions[i].name)
        function = report.functions[index]
        st.graphviz_chart(function.graph.dot(), width="content")
        st.subheader("Definições e usos por instrução")
        st.dataframe(function.events, hide_index=True, width="stretch")
        st.subheader("Pares e caminhos candidatos")
        st.dataframe(function.pairs, hide_index=True, width="stretch")
        if not function.pairs:
            st.info("Nenhum par Def-Uso local encontrado nesta função.")
        for warning in function.warnings:
            st.warning(warning)
    else:
        st.info("Nenhuma função pôde ser analisada neste subconjunto. Consulte as limitações acima.")
    for note in DATA_NOTES:
        st.caption(note)
    st.download_button("Baixar Def-Uso (.json)", json.dumps(asdict(report), ensure_ascii=False, indent=2),
                       file_name="def_uso.json", mime="application/json")
    pdf_actions("Definições, usos e caminhos candidatos", filename, data_sections(report), "def_uso")


def mutation_sections(mutants, notes, rows, score):
    sections = [ReportSection("Situação da campanha", [
        "Catálogo estático: o TXT e os mutantes não são executados pelo aplicativo.",
        score["origem"], "MS = mortos / (mortos + sobreviventes) x 100.",
        "Equivalentes e inválidos justificados são excluídos. Pendências e erros de execução impedem o escore final.",
        f'Escore final: {score["escore_final"] if score["escore_final"] is not None else "não disponível"}.',
        f'Escore apenas dos avaliados: {score["escore_avaliados"] if score["escore_avaliados"] is not None else "não disponível"}.',
    ] + notes)]
    by_id = {r["ID"]: r for r in rows}
    for m in mutants:
        row = by_id[m.id]
        sections.append(ReportSection(f"{m.id} - {m.function} / L{m.line}", [
            "Operador: " + m.operator, "Original: " + m.before, "Mutante: " + m.after,
            "Situação: " + row["Situação"], "Evidência: " + (row["Evidência"] or "não informada"),
        ]))
    return sections


def arithmetic_sections(result):
    sections = [ReportSection("Experimento no modelo", [result["escopo"],
                "Fórmula original: " + result["formula_original"],
                f'Mutantes mortos: {result["mortos"]} de {result["total"]}; escore: {result["escore"] if result["escore"] is not None else "não se aplica"}.',
                "A fórmula original passou em todos os resultados esperados informados. Comparação numérica exata, sem arredondamento implícito."])]
    sections.append(ReportSection("Casos confirmados", columns=["Caso", "Entradas", "Esperado"],
                                  rows=[[c["id"], json.dumps(c["entradas"], ensure_ascii=False), c["esperado"]] for c in result["casos"]]))
    for mutant in result["mutantes"]:
        sections.append(ReportSection(mutant["id"]+" - "+mutant["situacao"], ["Fórmula: "+mutant["formula"]],
                         ["Caso", "Esperado", "Obtido", "Detectou"],
                         [[o["teste"], o["esperado"], o["obtido"], "Sim" if o["detectou"] else "Não"] for o in mutant["resultados"]]))
    return sections


def mutation_view(content, filename, digest):
    st.subheader("Mutação e eficácia dos testes")
    st.write("Gere variantes com uma alteração por vez e registre quais testes detectam cada falha.")
    source_tab, model_tab, function_tab = st.tabs(["Mutantes do TXT", "Experimento aritmético", "Mutação da função"])
    with source_tab:
        st.caption("Geração estática de operadores aritméticos, relacionais e lógicos em LET, IF, WHILE e RETURN. Cada variante precisa de validação no ambiente de destino.")
        limit = st.number_input("Máximo de mutantes", min_value=1, max_value=300, value=100, step=1)
        if st.button("Gerar catálogo de mutantes", type="primary", width="stretch"):
            try:
                mutants, notes = generate_mutants(content, int(limit))
                st.session_state["mutation_catalog"] = (mutants, notes)
                st.session_state["mutation_registry"] = [{"ID": m.id, "Situação": "Pendente", "Evidência": ""} for m in mutants]
                st.session_state["mutation_revision"] = st.session_state.get("mutation_revision", 0) + 1
            except MutationError as exc:
                st.error(str(exc))
        catalog = st.session_state.get("mutation_catalog")
        if catalog is not None:
            mutants, notes = catalog
            for note in notes:
                st.caption(note)
            if not mutants:
                st.info("Nenhum operador mutável encontrado no subconjunto suportado.")
            else:
                st.dataframe([{"ID": m.id, "função": m.function, "linha": m.line, "alteração": m.operator,
                               "original": m.before, "mutante": m.after} for m in mutants], hide_index=True, width="stretch")
                selected = st.selectbox("Mutante para baixar", range(len(mutants)), format_func=lambda i: mutants[i].id)
                st.download_button("Baixar variante TXT", mutant_source(content, mutants[selected]),
                                   file_name=mutants[selected].id+".txt", mime="text/plain")
                st.subheader("Resultados e evidências externas")
                st.caption("Morto: um teste passou no original e falhou no mutante. Sobrevivente: todos passaram. Equivalente exige justificativa; sobrevivência não prova equivalência.")
                revision = st.session_state.get("mutation_revision", 0)
                with st.form(digest+f"_mutation_{revision}"):
                    frame = st.data_editor(pd.DataFrame(st.session_state["mutation_registry"]), hide_index=True,
                                           disabled=["ID"], width="stretch", key=digest+f"_registry_{revision}",
                                           column_config={"Situação": st.column_config.SelectboxColumn(options=list(STATUSES), required=True)})
                    submit = st.form_submit_button("Aplicar resultados e calcular escore")
                if submit:
                    try:
                        rows = frame.fillna("").to_dict("records")
                        score_registry(mutants, rows)
                        st.session_state["mutation_registry"] = rows
                    except MutationError as exc:
                        st.error(str(exc))
                rows = st.session_state["mutation_registry"]
                score = score_registry(mutants, rows)
                left, right = st.columns(2)
                left.metric("Escore final da campanha", "—" if score["escore_final"] is None else f'{score["escore_final"]:.1f}%')
                right.metric("Escore dos mutantes avaliados", "—" if score["escore_avaliados"] is None else f'{score["escore_avaliados"]:.1f}%')
                st.caption("MS = mortos / (mortos + sobreviventes). Equivalentes e inválidos justificados ficam fora do denominador. Pendências ou erros impedem o escore final.")
                st.caption("Relatórios usam os últimos resultados aplicados. " + score["origem"])
                st.dataframe([{"situação": status, "quantidade": count} for status, count in score["contagens"].items()],
                             hide_index=True, width="stretch")
                st.download_button("Baixar campanha (.json)", json.dumps(catalog_payload(mutants, rows, score), ensure_ascii=False, indent=2),
                                   file_name="campanha_mutacao.json", mime="application/json")
                pdf_actions("Mutantes e escore da campanha", filename, mutation_sections(mutants, notes, rows, score), "mutacao")
    with model_tab:
        st.write("Avalie automaticamente mutações de uma fórmula confirmada. Informe resultados esperados independentes; a fórmula original precisa passar antes de avaliar as variantes.")
        st.caption("Somente números, nomes, +, -, *, / e parênteses. Este experimento mede o modelo aritmético, sem executar a função ou o SQL do TXT.")
        suggestion = re.search(r"^[ \t]*LET[ \t]+[A-Za-z_]\w*[ \t]*=[ \t]*([A-Za-z_0-9 \t+*/().-]+)[ \t]*$", content, re.M | re.I)
        default = suggestion[1].strip() if suggestion else ""
        expression = st.text_input("Fórmula aritmética a avaliar", value=default, key=digest+"_mutation_formula").strip()
        try:
            names = formula_inputs(expression) if expression else []
        except MutationError as exc:
            names = []
            st.info(str(exc))
        if expression:
            with st.form(digest+"_arithmetic_"+str(names)):
                cases_text = st.text_area("Casos da fórmula (CSV)",value=','.join(names+['Esperado'])+'\n',
                                          help="Uma linha por caso, com ponto decimal. O cabeçalho indica a ordem das entradas.",
                                          key=digest+"_mutation_cases_csv_"+str(names))
                confirmed = st.checkbox("Confirmo a fórmula e os resultados esperados para este experimento.")
                run = st.form_submit_button("Avaliar mutações da fórmula", type="primary")
            if run:
                st.session_state.pop("mutation_model_result", None)
                try:
                    if not confirmed:
                        raise MutationError("Confirme a fórmula e os resultados esperados.")
                    rows = parse_cases_csv(cases_text, names)
                    st.session_state["mutation_model_result"] = evaluate_formula_mutation(expression, rows)
                except MutationError as exc:
                    st.error(str(exc))
        result = st.session_state.get("mutation_model_result")
        if result:
            st.metric("Escore no modelo aritmético", "—" if result["escore"] is None else f'{result["escore"]:.1f}%')
            st.caption("Último experimento avaliado: " + result["formula_original"])
            st.caption(result["escopo"])
            st.dataframe([{k: m[k] for k in ("id", "formula", "situacao", "detectado_por")} for m in result["mutantes"]], hide_index=True, width="stretch")
            with st.expander("Ver resultados por teste"):
                st.dataframe([{"mutante": m["id"], "teste": o["teste"], "esperado": o["esperado"],
                               "obtido": o["obtido"], "detectou": "Sim" if o["detectou"] else "Não"}
                              for m in result["mutantes"] for o in m["resultados"]], hide_index=True, width="stretch")
            st.download_button("Baixar experimento (.json)", json.dumps(result, ensure_ascii=False, indent=2),
                               file_name="mutacao_aritmetica.json", mime="application/json")
            pdf_actions("Mutação do modelo aritmético", filename, arithmetic_sections(result), "mutacao_modelo")
    with function_tab:
        source_mutation_view(content, filename, digest)


def source_mutation_sections(result):
    sections = [ReportSection("Critérios da avaliação", [result['escopo'],
                f"Função: {result['funcao']}; mortos: {result['mortos']}; elegíveis: {result['elegiveis']}; inválidos: {result['invalidos']}.",
                "MS = mortos / elegíveis x 100; escore: " + (f"{result['escore']:.2f}%" if result['escore'] is not None else 'não se aplica'),
                "Todos os casos informados passaram no modelo original antes de avaliar os mutantes."] + result['observacoes'])]
    sections.append(ReportSection("Casos e resultados originais", columns=['Caso', 'Entradas', 'Esperado', 'Obtido'],
                                  rows=[[c['id'], json.dumps(c['entradas'], ensure_ascii=False), c['esperado'], c['resultado']] for c in result['casos']]))
    for mutant in result['mutantes']:
        sections.append(ReportSection(mutant['id']+' - '+mutant['situacao'],
                         [f"L{mutant['linha']}: {mutant['alteracao']}", mutant['evidencia']],
                         ['Teste', 'Esperado', 'Obtido', 'Detectou'],
                         [[o['teste'],o['esperado'],o['obtido'],'Sim' if o['detectou'] else 'Não'] for o in mutant['resultados']]))
    return sections


def source_mutation_view(content, filename, digest):
    st.write("Avalie mutantes derivados da função do TXT com entradas e resultados esperados independentes, incluindo NULL.")
    st.caption("Modelo numérico restrito: LET, IF/ELSE e RETURN. Não executa o programa 4GL, SQL ou chamadas externas. Tipos DECIMAL não impõem arredondamento neste modelo.")
    try:
        models, limitations = available_models(content)
    except FlowError as exc:
        st.info(str(exc))
        return
    if limitations:
        with st.expander("Funções fora do modelo restrito"):
            for limitation in limitations:
                st.write(limitation)
    if not models:
        st.info("Nenhuma função numérica compatível encontrada.")
        return
    index = st.selectbox("Função para avaliar mutantes", range(len(models)), format_func=lambda i: models[i].name,
                         key=digest+'_source_mutation_function')
    model = models[index]
    with st.form(digest+'_source_mutation_'+model.name):
        text = st.text_area("Casos para a função (CSV)", value=','.join(model.params+['Esperado'])+'\n',
                            help="Separe as colunas por vírgula. Use ponto decimal e NULL para nulos. Cada linha é um caso.",
                            key=digest+'_source_cases_'+model.name)
        confirmed = st.checkbox("Confirmei as entradas e os resultados esperados da função.")
        run = st.form_submit_button("Avaliar mutantes da função", type='primary')
    if run:
        st.session_state.pop('source_mutation_result', None)
        try:
            if not confirmed:
                raise MutationError("Confirme os critérios antes de avaliar a função.")
            tests = parse_cases_csv(text, model.params)
            st.session_state['source_mutation_result'] = evaluate_source_mutation(content, model.name, tests)
        except MutationError as exc:
            st.error(str(exc))
    result = st.session_state.get('source_mutation_result')
    if result:
        st.caption('Última função avaliada: '+result['funcao'])
        st.metric('Escore dos mutantes da função (modelo)', '—' if result['escore'] is None else f"{result['escore']:.1f}%")
        st.caption(result['escopo'])
        if result['catalogo_parcial']:
            st.warning('O limite de geração foi atingido. O escore considera somente o catálogo parcial gerado.')
        st.dataframe([{k:m[k] for k in ('id','linha','alteracao','situacao','detectado_por')} for m in result['mutantes']], hide_index=True, width='stretch')
        with st.expander('Resultados e trilhas dos casos originais'):
            for case in result['casos']:
                st.write(f"{case['id']}: esperado {case['esperado']}; obtido {case['resultado']}")
                st.dataframe(case['trilha'], hide_index=True, width='stretch')
        with st.expander('Detecção por teste e mutante'):
            st.dataframe([{'mutante':m['id'],**o} for m in result['mutantes'] for o in m['resultados']],hide_index=True,width='stretch')
        st.download_button('Baixar avaliação da função (.json)', json.dumps(result,ensure_ascii=False,indent=2),
                           file_name='mutacao_funcao.json',mime='application/json')
        pdf_actions('Mutação da função - modelo restrito',filename,source_mutation_sections(result),'mutacao_funcao')
