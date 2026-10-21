"""Modelo numérico restrito de funções 4GL; não carrega programas nem executa SQL."""

import ast
import csv
from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext
from io import StringIO
import re

from .def_uso import function_sources, _without_declarations
from .fluxo_controle import FlowError, _parse, _tokens
from .mutacao import MutationError, generate_mutants, mutant_source
from .testes_funcionais import DomainError, number


class ModelError(ValueError):
    pass


@dataclass
class ModelStatement:
    kind: str
    line: int
    expression: str
    tree: ast.Expression
    target: str = ""
    body: list | None = None
    otherwise: list | None = None


@dataclass
class FunctionModel:
    name: str
    params: list[str]
    statements: list[ModelStatement]


def expression_tree(expression: str):
    if not expression.strip() or len(expression) > 300:
        raise ModelError("Expressão deve ter de 1 a 300 caracteres.")
    pattern = r"\d+(?:\.\d+)?|[A-Za-z_][A-Za-z_0-9]*|<>|<=|>=|[=<>+*/()-]"
    pieces, position = [], 0
    keywords = {"NULL": "None", "TRUE": "True", "FALSE": "False", "AND": "and", "OR": "or", "NOT": "not", "IS": "is"}
    for match in re.finditer(pattern, expression):
        if expression[position:match.start()].strip():
            raise ModelError("Expressão contém literal, campo de registro ou operador não suportado.")
        token = match.group()
        pieces.append(keywords.get(token.upper(), {"=": "==", "<>": "!="}.get(token, token.lower())))
        position = match.end()
    if expression[position:].strip():
        raise ModelError("Expressão contém construção não suportada.")
    translated = " ".join(pieces)
    try:
        tree = ast.parse(translated, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ModelError("Expressão inválida no modelo numérico.") from exc
    allowed = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.BinOp, ast.UnaryOp,
               ast.BoolOp, ast.Compare, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
               ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ModelError("Chamadas, atributos, índices e código Python não são permitidos no modelo.")
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise ModelError("Use uma comparação por expressão, unidas com AND/OR quando necessário.")
            if isinstance(node.ops[0], (ast.Is, ast.IsNot)) and not (isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value is None):
                raise ModelError("IS é suportado somente com NULL.")
        if isinstance(node, ast.Constant) and node.value is not None and not isinstance(node.value, bool):
            try:
                number(ast.get_source_segment(translated, node))
            except DomainError as exc:
                raise ModelError(str(exc)) from exc
    return translated, tree


def compile_model(content: str, name: str) -> FunctionModel:
    sources = function_sources(content)
    selected = [f for f in sources if f[0].lower() == name.lower()]
    if len(selected) != 1:
        raise ModelError("A função deve existir e ter nome único no TXT.")
    function, params, _, lines = selected[0]
    if len(params) > 12:
        raise ModelError("O modelo aceita até 12 parâmetros.")
    parsed = _parse(_tokens(_without_declarations(lines)), group_blocks=False)
    count, names = 0, set(params)

    def convert(statements):
        nonlocal count
        result = []
        for statement in statements:
            count += 1
            if count > 200:
                raise ModelError("O modelo aceita até 200 instruções.")
            target = ""
            if statement.kind == "if":
                expr = statement.text
            elif statement.kind == "return":
                expr = re.sub(r"^RETURN\s*", "", statement.text, flags=re.I)
            elif statement.kind == "block":
                match = re.fullmatch(r"LET\s+([A-Za-z_]\w*)\s*=\s*(.+)", statement.text, re.I)
                if not match:
                    raise ModelError(f"L{statement.line}: somente LET escalar, IF/ELSE e RETURN são modelados.")
                target, expr = match[1].lower(), match[2]
                names.add(target)
            else:
                raise ModelError(f"L{statement.line}: laços e instruções externas não são modelados.")
            translated, tree = expression_tree(expr)
            result.append(ModelStatement(statement.kind, statement.line, translated, tree, target,
                                         convert(statement.body), convert(statement.otherwise)))
        return result

    try:
        statements = convert(parsed)
    except RecursionError as exc:
        raise ModelError("Aninhamento excessivo.") from exc
    if len(names) > 80:
        raise ModelError("O modelo aceita até 80 variáveis.")

    def check(items):
        for item in items:
            unknown = {n.id for n in ast.walk(item.tree) if isinstance(n, ast.Name)} - names
            if unknown:
                raise ModelError(f"L{item.line}: entrada global ou variável sem atribuição: {', '.join(sorted(unknown))}")
            check(item.body)
            check(item.otherwise)
    check(statements)
    return FunctionModel(function, params, statements)


def available_models(content):
    models, limitations = [], []
    for name, _, _, _ in function_sources(content):
        try:
            models.append(compile_model(content, name))
        except (ModelError, FlowError, RecursionError) as exc:
            limitations.append(f"{name}: {exc}")
    return models, limitations


def parse_value(value, internal=False):
    text = str(value).strip()
    if text.upper() == "NULL":
        return None
    if text.upper() in ("TRUE", "FALSE"):
        return text.upper() == "TRUE"
    if internal:
        if len(text) > 170 or not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',text):
            raise ModelError("Saída numérica inválida no modelo.")
        result=Decimal(text)
        if not result.is_finite() or result.copy_abs() >= Decimal('1e100'):
            raise ModelError("Saída excede o limite numérico do modelo.")
        return result
    try:
        return number(text)
    except DomainError as exc:
        raise ModelError(str(exc)) from exc


def display_value(value):
    return "NULL" if value is None else "TRUE" if value is True else "FALSE" if value is False else format(value, 'f')


def run_model(model: FunctionModel, inputs: dict) -> dict:
    if set(inputs) != set(model.params):
        raise ModelError("Entradas devem corresponder exatamente aos parâmetros da função.")
    env = {name: parse_value(value) for name, value in inputs.items()}
    if any(isinstance(v, bool) for v in env.values()):
        raise ModelError("Entradas do modelo devem ser numéricas ou NULL.")
    trace = []

    def truth(value):
        if value is None or isinstance(value, bool):
            return value
        raise ModelError("Condições e operadores lógicos exigem comparação booleana.")

    def visit(node, source):
        if isinstance(node, ast.Expression):
            return visit(node.body, source)
        if isinstance(node, ast.Constant):
            return node.value if node.value is None or isinstance(node.value, bool) else number(ast.get_source_segment(source, node))
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise ModelError(f"Variável {node.id} usada antes da definição neste caminho.")
            return env[node.id]
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand, source)
            if isinstance(node.op, ast.Not):
                value = truth(value)
                return None if value is None else not value
            if value is None:
                return None
            if isinstance(value, bool):
                raise ModelError("Booleano não é operando aritmético.")
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BoolOp):
            values = [truth(visit(n, source)) for n in node.values]
            if isinstance(node.op, ast.And):
                return False if False in values else None if None in values else True
            return True if True in values else None if None in values else False
        left = visit(node.left, source)
        right = visit(node.comparators[0] if isinstance(node, ast.Compare) else node.right, source)
        if isinstance(node, ast.Compare):
            op = node.ops[0]
            if isinstance(op, (ast.Is, ast.IsNot)):
                return (left is not None) if isinstance(op, ast.IsNot) else (left is None)
            if left is None or right is None:
                return None
            if type(left) is not type(right):
                raise ModelError("Comparação entre tipos diferentes.")
            for kind, operation in ((ast.Eq, lambda: left == right), (ast.NotEq, lambda: left != right),
                                    (ast.Lt, lambda: left < right), (ast.LtE, lambda: left <= right),
                                    (ast.Gt, lambda: left > right), (ast.GtE, lambda: left >= right)):
                if isinstance(op, kind):
                    return operation()
        if left is None or right is None:
            return None
        if isinstance(left, bool) or isinstance(right, bool):
            raise ModelError("Booleano não é operando aritmético.")
        if isinstance(node.op, ast.Add):
            value = left + right
        elif isinstance(node.op, ast.Sub):
            value = left - right
        elif isinstance(node.op, ast.Mult):
            value = left * right
        else:
            value = left / right
        if not value.is_finite() or value.copy_abs() >= Decimal('1e100'):
            raise ModelError("Resultado excede o limite numérico do modelo.")
        return value

    def sequence(statements):
        for statement in statements:
            value = visit(statement.tree, statement.expression)
            trace.append({"linha": statement.line, "tipo": statement.kind,
                          "destino": statement.target, "valor": display_value(value)})
            if statement.kind == "return":
                return True, value
            if statement.kind == "if":
                branch = statement.body if truth(value) is True else statement.otherwise
                returned, result = sequence(branch)
                if returned:
                    return returned, result
            else:
                env[statement.target] = value
        return False, None

    try:
        with localcontext() as context:
            context.prec = 64
            returned, value = sequence(model.statements)
            if not returned:
                raise ModelError("Caminho sem RETURN explícito.")
            return {"resultado": display_value(value), "trilha": trace}
    except (DecimalException, DomainError, RecursionError) as exc:
        raise ModelError(f"Falha no modelo: {type(exc).__name__}") from exc


def parse_cases_csv(text: str, params: list[str]):
    reader = csv.DictReader(StringIO(text.strip()))
    expected = params + ['Esperado']
    if reader.fieldnames != expected:
        raise MutationError("Use o cabeçalho CSV: " + ','.join(expected))
    rows = list(reader)
    if not rows or len(rows) > 100 or any(None in r or any(v is None or not v.strip() for v in r.values()) for r in rows):
        raise MutationError("Informe de 1 a 100 linhas completas; use NULL para valores nulos.")
    return rows


def evaluate_source_mutation(content: str, name: str, tests: list[dict]):
    try:
        model = compile_model(content, name)
        if not tests or len(tests) > 100:
            raise ModelError("Informe de 1 a 100 casos.")
        baselines = []
        for i, row in enumerate(tests, 1):
            if set(row) != set(model.params) | {'Esperado'}:
                raise ModelError("Cada caso deve conter os parâmetros e Esperado, sem colunas extras.")
            inputs = {p: row[p] for p in model.params}
            expected = parse_value(row['Esperado'])
            original = run_model(model, inputs)
            obtained = parse_value(original['resultado'],internal=True)
            if type(obtained) is not type(expected) or obtained != expected:
                raise ModelError(f"CT-{i:03d}: original retornou {original['resultado']}, esperado {display_value(expected)}. Corrija a base.")
            baselines.append({"id": f"CT-{i:03d}", "entradas": inputs, "esperado": display_value(expected), **original})
        mutants, notes = generate_mutants(content, 300, function_name=name)
        results = []
        for mutant in mutants:
            try:
                variant = compile_model(mutant_source(content, mutant), name)
            except (ModelError, FlowError, RecursionError) as exc:
                results.append({"id": mutant.id, "linha": mutant.line, "alteracao": mutant.operator,
                                "situacao": "Inválido", "evidencia": str(exc), "resultados": [], "detectado_por": []})
                continue
            outcomes = []
            for case in baselines:
                try:
                    actual = run_model(variant, case['entradas'])['resultado']
                    expected, value = parse_value(case['esperado']), parse_value(actual,internal=True)
                    detected = type(value) is not type(expected) or value != expected
                except ModelError as exc:
                    actual, detected = 'Erro no modelo: '+str(exc), True
                outcomes.append({"teste": case['id'], "esperado": case['esperado'], "obtido": actual, "detectou": detected})
            killed_by = [o['teste'] for o in outcomes if o['detectou']]
            results.append({"id": mutant.id, "linha": mutant.line, "alteracao": mutant.operator,
                            "situacao": "Morto" if killed_by else "Sobrevivente", "evidencia": "Avaliação automática no modelo restrito",
                            "detectado_por": killed_by, "resultados": outcomes})
        eligible = [m for m in results if m['situacao'] != 'Inválido']
        killed = sum(m['situacao'] == 'Morto' for m in eligible)
        return {"funcao": model.name, "casos": baselines, "mutantes": results, "mortos": killed,
                "total": len(results), "invalidos": len(results)-len(eligible), "elegiveis": len(eligible),
                "catalogo_parcial": any('parcial' in note for note in notes),
                "escore": 100*killed/len(eligible) if eligible else None, "observacoes": notes,
                "escopo": "Avaliação de modelo numérico derivado da função TXT (LET, IF/ELSE, RETURN, NULL). Não compila/executa programa 4GL, SQL ou chamadas externas; não modela arredondamento de DECIMAL. Sobrevivente não significa equivalente."}
    except (ModelError, FlowError, RecursionError) as exc:
        raise MutationError(str(exc)) from exc
