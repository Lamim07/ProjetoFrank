"""Grafo intraprocedural do subconjunto estruturado de Informix-4GL."""

import json
import re
from dataclasses import dataclass, field


class FlowError(ValueError):
    pass


@dataclass
class Statement:
    kind: str
    text: str
    line: int
    body: list = field(default_factory=list)
    otherwise: list = field(default_factory=list)


@dataclass
class FlowNode:
    id: str
    text: str
    line: int
    kind: str


@dataclass
class FunctionFlow:
    name: str
    nodes: list[FlowNode]
    edges: list[tuple[str, str, str]]
    notes: list[str]

    @property
    def complexity(self) -> int:
        return len(self.edges) - len(self.nodes) + 2

    def dot(self) -> str:
        lines = ['digraph fluxo {', 'rankdir=TB;', 'node [fontname="Arial" fontsize=11 style="rounded,filled" fillcolor="#f2f7f5" color="#678777"];']
        for n in self.nodes:
            shape = "diamond" if n.kind in ("if", "loop") else "oval" if n.kind in ("entry", "exit") else "box"
            text = n.text if len(n.text) <= 180 else n.text[:177] + "..."
            label = n.id + (f" · L{n.line}" if n.line else "") + "\n" + text
            lines.append(f'{n.id} [shape={shape} label={json.dumps(label, ensure_ascii=False)}];')
        for a, b, label in self.edges:
            lines.append(f'{a} -> {b} [label={json.dumps(label, ensure_ascii=False)}];')
        return "\n".join(lines + ['}'])


@dataclass
class FlowReport:
    functions: list[FunctionFlow]
    unsupported: list[str]


def _mask(text: str) -> str:
    """Mask strings and comments, retaining offsets for exact labels."""
    return re.sub(r'''"(?:[^"\\]|\\.|"")*"|'(?:[^'\\]|\\.|'')*'|\#.*$''',
                  lambda m: " " * len(m.group()) if m.group()[0] != "#" else "" , text)


def _tokens(lines: list[tuple[int, str]]) -> list[Statement]:
    tokens = []

    def split(text: str, line: int):
        text = text.strip()
        if not text:
            return
        masked = _mask(text)
        if not masked.strip():
            return
        if re.match(r"^(CASE|FOREACH|GOTO|GO\s+TO|EXIT|CONTINUE|TRY|CATCH|MENU|INPUT|CONSTRUCT|PROMPT|DIALOG|ON|COMMAND|DISPLAY\s+ARRAY|STOP|RAISE|ELSEIF|WHENEVER\s+ERROR\s+CALL)\b", masked, re.I):
            raise FlowError(f"L{line}: construção de controle ainda não suportada: {text[:70]}")
        match = re.match(r"^IF\s+(.+?)\s+THEN\b", masked, re.I)
        if match:
            tokens.append(Statement("if", text[match.start(1):match.end(1)].strip(), line))
            split(text[match.end():], line)
            return
        if re.match(r"^IF\b", masked, re.I):
            raise FlowError(f"L{line}: a condição IF precisa ter THEN na mesma linha.")
        match = re.search(r"\bEND\s+IF\b|\bELSE\b", masked, re.I)
        if match:
            split(text[:match.start()], line)
            tokens.append(Statement("endif" if match.group().upper().startswith("END") else "else", match.group(), line))
            split(text[match.end():], line)
            return
        if re.match(r"^END\s+(WHILE|FOR)\s*$", masked, re.I):
            tokens.append(Statement("endloop", text, line))
        elif re.match(r"^(WHILE|FOR)\b", masked, re.I):
            tokens.append(Statement("loop", text, line))
        else:
            tokens.append(Statement("return" if re.match(r"^RETURN\b", masked, re.I) else "block", text, line))

    for line, text in lines:
        # Remove only a comment outside strings.
        mask = _mask(text)
        if len(mask) < len(text):
            text = text[:len(mask)]
        split(text, line)
    return tokens


def _parse(tokens: list[Statement], group_blocks: bool = True) -> list[Statement]:
    index = 0

    def sequence(stops: set[str]) -> list[Statement]:
        nonlocal index
        result, pending = [], []

        def flush(terminal=False):
            if pending:
                result.append(Statement("return" if terminal else "block", "\n".join(t.text for t in pending), pending[0].line))
                pending.clear()

        while index < len(tokens) and tokens[index].kind not in stops:
            current = tokens[index]
            index += 1
            if current.kind in ("endif", "else", "endloop"):
                raise FlowError(f"L{current.line}: fechamento de bloco sem abertura correspondente.")
            if current.kind in ("block", "return"):
                pending.append(current)
                if current.kind == "return":
                    flush(True)
                elif not group_blocks:
                    flush()
                continue
            flush()
            if current.kind == "if":
                current.body = sequence({"else", "endif"})
                if index < len(tokens) and tokens[index].kind == "else":
                    index += 1
                    current.otherwise = sequence({"endif"})
                if index >= len(tokens) or tokens[index].kind != "endif":
                    raise FlowError(f"L{current.line}: IF sem END IF.")
            else:
                current.body = sequence({"endloop"})
                expected = "WHILE" if current.text.upper().startswith("WHILE") else "FOR"
                if index >= len(tokens) or tokens[index].text.upper().split()[-1] != expected:
                    raise FlowError(f"L{current.line}: laço sem END {expected}.")
            index += 1
            result.append(current)
        flush()
        return result

    return sequence(set())


def _build(name: str, statements: list[Statement]) -> FunctionFlow:
    nodes, edges = [], []

    def node(text, line, kind):
        if len(nodes) >= 200:
            raise FlowError("Função excede o limite de 200 blocos do grafo.")
        n = FlowNode(f"N{len(nodes)+1}", text, line, kind)
        nodes.append(n)
        return n.id

    entry = node("Entrada", 0, "entry")
    exit_node = node("Saída", 0, "exit")

    def build_sequence(items, following):
        for item in reversed(items):
            current = node(item.text, item.line, item.kind)
            if item.kind == "if":
                edges.append((current, build_sequence(item.body, following), "sim"))
                edges.append((current, build_sequence(item.otherwise, following), "não"))
            elif item.kind == "loop":
                edges.append((current, build_sequence(item.body, current), "sim"))
                edges.append((current, following, "não"))
            else:
                edges.append((current, exit_node if item.kind == "return" else following, ""))
            following = current
        return following

    edges.append((entry, build_sequence(statements, exit_node), ""))
    reached = {entry}
    pending = [entry]
    while pending:
        current = pending.pop()
        for a, b, _ in edges:
            if a == current and b not in reached:
                reached.add(b)
                pending.append(b)
    unreachable = [n for n in nodes if n.id not in reached]
    notes = [
        "Grafo intraprocedural: chamadas são blocos; funções externas não são expandidas.",
        "V(G) = E - N + 2, com entrada e saída únicas e somente blocos alcançáveis.",
        "Cada IF ou laço conta como uma decisão. AND/OR não são decompostos em curto-circuito.",
        "Fluxos excepcionais implícitos de SQL e do ambiente não são modelados.",
    ]
    if unreachable:
        notes.append(f"{len(unreachable)} bloco(s) sem caminho a partir da entrada foram excluídos da métrica.")
    return FunctionFlow(name, [n for n in nodes if n.id in reached],
                        [(a, b, c) for a, b, c in edges if a in reached], notes)


def analyze_flow(content: str) -> FlowReport:
    functions, unsupported = [], []
    current_name, current_lines = None, []
    count = 0
    for line_no, line in enumerate(content.splitlines(), 1):
        masked = _mask(line).strip()
        match = re.match(r"^FUNCTION\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*$", masked, re.I)
        if match:
            if current_name:
                raise FlowError(f"L{line_no}: FUNCTION sem fechamento da função anterior.")
            current_name, current_lines = match.group(1), []
            count += 1
            if count > 100:
                raise FlowError("O relatório aceita até 100 funções por arquivo.")
        elif re.match(r"^END\s+FUNCTION\s*$", masked, re.I):
            if not current_name:
                raise FlowError(f"L{line_no}: END FUNCTION sem FUNCTION.")
            try:
                functions.append(_build(current_name, _parse(_tokens(current_lines))))
            except (FlowError, RecursionError) as exc:
                unsupported.append(f"{current_name}: {exc if isinstance(exc, FlowError) else 'aninhamento excessivo'}")
            current_name = None
        elif current_name:
            current_lines.append((line_no, line))
    if current_name:
        raise FlowError(f"A função {current_name} não tem END FUNCTION.")
    if count == 0:
        raise FlowError("Nenhuma função Informix-4GL foi encontrada. Use FUNCTION nome(...) e END FUNCTION.")
    return FlowReport(functions, unsupported)
