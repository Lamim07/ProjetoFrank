"""Mutação de primeira ordem e experimento aritmético restrito, sem executar TXT."""

import ast
import copy
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, DecimalException

from .def_uso import function_sources
from .fluxo_controle import FlowError, _mask, _tokens
from .testes_funcionais import DomainError, NumericDomain, calculate_formula, number, validate_formula


class MutationError(ValueError):
    pass


@dataclass
class Mutant:
    id: str
    function: str
    line: int
    operator: str
    before: str
    after: str
    offset: int
    old: str
    new: str


REPLACEMENTS = {"+": ("-", "*", "/"), "-": ("+", "*", "/"),
                "*": ("+", "-", "/"), "/": ("+", "-", "*"),
                "=": ("<>",), "<>": ("=",), "<": ("<=", ">"),
                "<=": ("<", ">="), ">": (">=", "<"), ">=": (">", "<="),
                "AND": ("OR",), "OR": ("AND",), "TRUE": ("FALSE",), "FALSE": ("TRUE",)}
TOKEN = r"\bIS\s+(?:NOT\s+)?NULL\b|<>|<=|>=|[+*/=<>-]|\b(?:AND|OR|TRUE|FALSE)\b"
REPLACEMENTS.update({"IS NULL": ("IS NOT NULL",), "IS NOT NULL": ("IS NULL",)})
STATUSES = ("Pendente", "Morto", "Sobrevivente", "Equivalente", "Inválido", "Erro de execução")


def generate_mutants(content: str, limit: int = 100, function_name: str | None = None):
    if not 1 <= limit <= 300:
        raise MutationError("Gere entre 1 e 300 mutantes por análise.")
    lines = content.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    mutants, notes, seen = [], [], set()
    try:
        sources = function_sources(content)
    except FlowError as exc:
        raise MutationError(str(exc)) from exc
    for name, _, _, body in sources:
        if function_name is not None and name.lower() != function_name.lower():
            continue
        try:
            statements = _tokens(body)
        except FlowError as exc:
            notes.append(f"{name}: não gerado: {exc}")
            continue
        for statement in statements:
            text = statement.text
            masked = _mask(text)
            expression_start = 0
            if statement.kind == "block":
                match = re.match(r"LET\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*=\s*", masked, re.I)
                if not match:
                    continue
                expression_start = match.end()
            elif statement.kind == "return":
                expression_start = re.match(r"RETURN\s*", masked, re.I).end()
            elif statement.kind == "loop":
                if not re.match(r"WHILE\b", masked, re.I):
                    continue
                expression_start = re.match(r"WHILE\s+", masked, re.I).end()
            elif statement.kind != "if":
                continue
            # No mutations in declarations, strings, comments, calls or SQL.
            expression = masked[expression_start:]
            if re.search(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*\(|[\[\]]", expression):
                notes.append(f"{name} L{statement.line}: expressão com chamada/índice ignorada.")
                continue
            source_line = lines[statement.line-1].rstrip("\r\n")
            pos = source_line.find(text)
            if pos < 0:
                notes.append(f"{name} L{statement.line}: posição não identificada; ignorada.")
                continue
            for match in re.finditer(TOKEN, expression, re.I):
                old = text[expression_start + match.start():expression_start + match.end()]
                for new in REPLACEMENTS[' '.join(old.upper().split())]:
                    relative = pos + expression_start + match.start()
                    absolute = starts[statement.line-1] + relative
                    identity = (absolute, new)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    if len(mutants) >= limit:
                        notes.append(f"Limite de {limit} mutantes atingido; catálogo parcial.")
                        return mutants, list(dict.fromkeys(notes))
                    after = source_line[:relative] + new + source_line[relative+len(old):]
                    mutants.append(Mutant(f"M-{len(mutants)+1:03d}", name, statement.line,
                                          f"{old} -> {new}", source_line.strip(), after.strip(), absolute, old, new))
    notes.append("Mutantes de primeira ordem: uma substituição por variante. Compilação e equivalência não são presumidas.")
    return mutants, list(dict.fromkeys(notes))


def mutant_source(content: str, mutant: Mutant) -> str:
    if content[mutant.offset:mutant.offset+len(mutant.old)] != mutant.old:
        raise MutationError("O mutante não corresponde ao arquivo atual. Gere o catálogo novamente.")
    return content[:mutant.offset] + mutant.new + content[mutant.offset+len(mutant.old):]


def score_registry(mutants: list[Mutant], rows: list[dict]) -> dict:
    expected = {m.id for m in mutants}
    if len(expected) != len(mutants) or len(rows) != len(expected) or {r.get("ID") for r in rows} != expected:
        raise MutationError("A revisão precisa conter exatamente uma linha por mutante, sem alterar IDs.")
    counts = {s: 0 for s in STATUSES}
    for row in rows:
        status = row.get("Situação")
        if status not in counts:
            raise MutationError("Situação de mutante inválida.")
        if status != "Pendente" and not str(row.get("Evidência", "")).strip():
            raise MutationError(f"{row['ID']}: informe teste/resultado ou justificativa para a classificação.")
        counts[status] += 1
    denominator = counts["Morto"] + counts["Sobrevivente"]
    partial = 100 * counts["Morto"] / denominator if denominator else None
    complete = bool(mutants) and not counts["Pendente"] and not counts["Erro de execução"]
    return {"contagens": counts, "escore_avaliados": partial,
            "escore_final": partial if complete else None, "concluido": complete,
            "origem": "Classificação e evidências informadas pelo usuário; execução externa não verificada."}


def formula_inputs(expression: str) -> list[str]:
    names = sorted(set(re.findall(r"\b[A-Za-z_]\w*\b", expression)))
    if len(names) > 12 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", n) for n in names):
        raise MutationError("Use até 12 entradas com nomes ASCII na fórmula.")
    try:
        validate_formula(expression, set(names))
    except DomainError as exc:
        raise MutationError(str(exc)) from exc
    return names


def formula_mutants(expression: str) -> list[str]:
    formula_inputs(expression)
    tree = ast.parse(expression, mode="eval")
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp)]
    results = []
    for index, original in enumerate(nodes):
        for op in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            if isinstance(original.op, op):
                continue
            clone = copy.deepcopy(tree)
            target = [n for n in ast.walk(clone) if isinstance(n, ast.BinOp)][index]
            target.op = op()
            candidate = ast.unparse(clone)
            if len(candidate) > 300:
                raise MutationError("A fórmula formatada excede 300 caracteres. Simplifique-a antes do experimento.")
            if candidate not in results:
                results.append(candidate)
    return results


def evaluate_formula_mutation(expression: str, tests: list[dict]) -> dict:
    names = formula_inputs(expression)
    if not tests or len(tests) > 100:
        raise MutationError("Informe de 1 a 100 casos com entradas e resultado esperado numérico.")
    domains = [NumericDomain(n, Decimal('-1e28'), Decimal('1e28'), 12) for n in names]
    validated = []
    try:
        for index, test in enumerate(tests, 1):
            inputs = {n: str(test[n]).strip() for n in names}
            for value in inputs.values():
                number(value)
            expected = number(test["Esperado"])
            actual = number(calculate_formula(expression, inputs, domains))
            if actual != expected:
                raise MutationError(f"CT-{index:03d}: a fórmula original retorna {actual}, diferente do esperado {expected}. Corrija a base antes da mutação.")
            validated.append({"id": f"CT-{index:03d}", "entradas": inputs, "esperado": str(expected)})
    except (DomainError, DecimalException, KeyError, TypeError) as exc:
        raise MutationError(f"Caso ou fórmula original inválidos: {exc}") from exc
    results = []
    for index, formula in enumerate(formula_mutants(expression), 1):
        outcomes = []
        for case in validated:
            try:
                actual = calculate_formula(formula, case["entradas"], domains)
                killed = Decimal(actual) != Decimal(case["esperado"])
            except (DomainError, DecimalException) as exc:
                actual, killed = f"Erro aritmético: {exc}", True
            outcomes.append({"teste": case["id"], "esperado": case["esperado"], "obtido": actual, "detectou": killed})
        killed_by = [o["teste"] for o in outcomes if o["detectou"]]
        results.append({"id": f"MA-{index:03d}", "formula": formula,
                        "situacao": "Morto" if killed_by else "Sobrevivente", "detectado_por": killed_by, "resultados": outcomes})
    killed = sum(r["situacao"] == "Morto" for r in results)
    return {"formula_original": expression, "casos": validated, "mutantes": results,
            "mortos": killed, "total": len(results), "escore": 100*killed/len(results) if results else None,
            "escopo": "Experimento no modelo aritmético confirmado; não executa nem mede o programa TXT. Sobrevivência não comprova equivalência."}


def catalog_payload(mutants, rows, score):
    return {"mutantes": [asdict(m) for m in mutants], "revisao": rows, "escore": score}
