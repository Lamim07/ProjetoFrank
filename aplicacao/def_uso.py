"""Definições alcançantes intraprocedurais, sem executar a entrada."""

import re
from collections import deque
from dataclasses import dataclass, field

from .fluxo_controle import FlowError, FunctionFlow, _build, _mask, _parse, _tokens


NAME = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*"
KEYWORDS = set("AND OR NOT IS NULL TRUE FALSE MOD TO STEP".lower().split())
UNDEFINED = "<sem definição>"


@dataclass
class DataFunction:
    name: str
    graph: FunctionFlow
    events: list[dict]
    pairs: list[dict]
    warnings: list[str]


@dataclass
class DataReport:
    functions: list[DataFunction] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


def function_sources(content: str):
    """Validate function boundaries before returning source ranges."""
    result, current = [], None
    for line_no, text in enumerate(content.splitlines(), 1):
        masked = _mask(text).strip()
        match = re.fullmatch(r"FUNCTION\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", masked, re.I)
        if match:
            if current:
                raise FlowError(f"L{line_no}: FUNCTION aninhada ou sem fechamento.")
            params = [p.strip().lower() for p in match[2].split(",") if p.strip()]
            if any(not re.fullmatch(r"[A-Za-z_]\w*", p) for p in params) or len(set(params)) != len(params):
                raise FlowError(f"L{line_no}: parâmetros não suportados ou duplicados.")
            current = [match[1], params, line_no, []]
            if len(result) >= 100:
                raise FlowError("O relatório aceita até 100 funções.")
        elif re.fullmatch(r"END\s+FUNCTION", masked, re.I):
            if not current:
                raise FlowError(f"L{line_no}: END FUNCTION sem abertura.")
            result.append(current)
            current = None
        elif current:
            current[3].append((line_no, text))
    if current:
        raise FlowError(f"A função {current[0]} não tem END FUNCTION.")
    if not result:
        raise FlowError("Nenhuma função Informix-4GL foi encontrada.")
    return result


def identifiers(expression: str) -> set[str]:
    masked = _mask(expression)
    # Calls, indexing and pointers need an effects/alias model, not lexical guesses.
    if re.search(NAME + r"\s*\(", masked) or re.search(r"[\[\]&]|[A-Za-z_]\w*\.", masked):
        raise FlowError("expressão com chamada, índice ou campo de registro não suportada em Def-Uso")
    masked = re.sub(r"\b\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?\b", " ", masked)
    return {m.group().lower() for m in re.finditer(NAME, masked)
            if m.group().lower() not in KEYWORDS}


def node_effects(node):
    text = _mask(node.text).strip()
    if node.kind in ("entry", "exit"):
        return set(), set()
    if node.kind == "if":
        return set(), identifiers(text)
    if node.kind == "loop":
        if re.match(r"FOR\b", text, re.I):
            raise FlowError(f"L{node.line}: FOR exige modelar a atualização implícita; use WHILE neste módulo")
        return set(), identifiers(re.sub(r"^WHILE\s+", "", text, flags=re.I))
    match = re.fullmatch(r"LET\s+(" + NAME + r")\s*=\s*(.+)", text, re.I)
    if match:
        if "." in match[1]:
            raise FlowError(f"L{node.line}: atribuição a registro exige modelo de aliases")
        return {match[1].lower()}, identifiers(match[2])
    match = re.match(r"^(RETURN|DISPLAY|MESSAGE)\b(.*)$", text, re.I)
    if match:
        return set(), identifiers(match[2])
    raise FlowError(f"L{node.line}: instrução sem modelo de efeitos Def-Uso: {node.text[:65]}")


def _without_declarations(lines):
    result, defining = [], False
    declaration = r"(?:DEFINE\s+)?[A-Za-z_]\w*\s+(?:DECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)|CHAR\s*\(\s*\d+\s*\)|INTEGER|SMALLINT|FLOAT|DATE)\s*,?"
    for line_no, text in lines:
        masked = _mask(text).strip()
        if not masked:
            continue
        if re.match(r"DEFINE\b", masked, re.I) or defining:
            if not re.fullmatch(declaration, masked, re.I):
                raise FlowError(f"L{line_no}: declaração não suportada em Def-Uso")
            defining = masked.endswith(",")
        else:
            result.append((line_no, text))
    if defining:
        raise FlowError("Declaração incompleta.")
    return result


def _analyze(name, params, header_line, lines):
    graph = _build(name, _parse(_tokens(_without_declarations(lines)), group_blocks=False))
    effects = {n.id: node_effects(n) for n in graph.nodes}
    entry = graph.nodes[0].id
    effects[entry] = (set(params), set())
    all_names = set().union(*(d | u for d, u in effects.values()))
    if len(all_names) > 80:
        raise FlowError("Função excede 80 variáveis no módulo Def-Uso.")
    # A synthetic undefined fact preserves paths that never initialized a variable.
    initial = {(v, UNDEFINED) for v in all_names - set(params)}
    before = {n.id: set() for n in graph.nodes}
    after = {n.id: set() for n in graph.nodes}
    predecessors = {n.id: [] for n in graph.nodes}
    successors = {n.id: [] for n in graph.nodes}
    for a, b, label in graph.edges:
        predecessors[b].append(a)
        successors[a].append((b, label))
    changed = True
    while changed:
        changed = False
        for node in graph.nodes:
            incoming = set().union(*(after[p] for p in predecessors[node.id]))
            if node.id == entry:
                incoming |= initial
            defs, _ = effects[node.id]
            outgoing = {(v, d) for v, d in incoming if v not in defs} | {(v, node.id) for v in defs}
            if incoming != before[node.id] or outgoing != after[node.id]:
                before[node.id], after[node.id] = incoming, outgoing
                changed = True

    def witness(start, end, variable):
        queue = deque((n, [start, n]) for n, _ in successors[start])
        visited = set()
        while queue:
            node, path = queue.popleft()
            if node == end:
                return " -> ".join(path)
            if node in visited or variable in effects[node][0]:
                continue
            visited.add(node)
            queue.extend((n, path + [n]) for n, _ in successors[node])
        return ""

    pairs, warnings, used = [], [], set()
    by_id = {n.id: n for n in graph.nodes}
    events = []
    for node in graph.nodes:
        defs, uses = effects[node.id]
        events.append({"nó": node.id, "linha": header_line if node.id == entry else node.line,
                       "instrução": node.text, "define": ", ".join(sorted(defs)), "usa": ", ".join(sorted(uses))})
        for variable in sorted(uses):
            for var, definition in sorted(before[node.id]):
                if var != variable:
                    continue
                if definition == UNDEFINED:
                    warnings.append(f"L{node.line}: {variable} pode ser usado sem definição local; confirme entradas globais.")
                    continue
                used.add((variable, definition))
                branches = successors[node.id] if node.kind in ("if", "loop") else [("", "")]
                for target, label in branches:
                    if len(pairs) >= 5000:
                        raise FlowError("Função excede 5000 pares Def-Uso candidatos.")
                    path = witness(definition, node.id, variable)
                    pairs.append({"variável": variable, "definição": definition,
                                  "linha definição": header_line if definition == entry else by_id[definition].line,
                                  "uso": node.id, "linha uso": node.line,
                                  "tipo": "p-use" if target else "c-use", "aresta": f"{node.id} -> {target} ({label})" if target else "",
                                  "caminho candidato": path + (f" -> {target}" if target else "")})
    for node in graph.nodes:
        for variable in sorted(effects[node.id][0]):
            if (variable, node.id) not in used:
                warnings.append(f"{variable} definido em {node.id} não alcança uso local; pode ser saída externa.")
    return DataFunction(name, graph, events, pairs, list(dict.fromkeys(warnings)))


def analyze_data_flow(content: str) -> DataReport:
    report = DataReport()
    for name, params, header, lines in function_sources(content):
        try:
            report.functions.append(_analyze(name, params, header, lines))
        except (FlowError, RecursionError) as exc:
            report.unsupported.append(f"{name}: {exc if isinstance(exc, FlowError) else 'aninhamento excessivo'}")
    return report
