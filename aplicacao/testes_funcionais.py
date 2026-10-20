"""PCE/AVL determinísticos sobre domínios confirmados pelo usuário."""

import ast
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, localcontext


class DomainError(ValueError):
    pass


def number(value: str) -> Decimal:
    text = str(value).strip().replace(",", ".")
    if len(text) > 45 or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        raise DomainError("Informe números finitos, sem separadores de milhar (ex.: 100,25).")
    result = Decimal(text)
    if result.copy_abs() >= Decimal("1e29"):
        raise DomainError("Use limites com menos de 30 dígitos inteiros.")
    return result


def display(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class NumericDomain:
    name: str
    lower: Decimal
    upper: Decimal
    scale: int = 0
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    null_policy: str = "rejeitar"

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z_]\w*", self.name) or len(self.name) > 50:
            raise DomainError("Use nomes de entrada sem espaços, começando por letra ou sublinhado.")
        if not 0 <= self.scale <= 12:
            raise DomainError("A precisão deve estar entre 0 e 12 casas decimais.")
        if self.null_policy not in ("rejeitar", "aceitar", "zero"):
            raise DomainError("Tratamento de nulo inválido.")
        if not all(v.is_finite() and v.copy_abs() < Decimal("1e29") for v in (self.lower, self.upper)):
            raise DomainError("Os limites precisam ser números finitos com menos de 30 dígitos.")
        if self.lower > self.upper:
            raise DomainError(f"{self.name}: o mínimo deve ser menor ou igual ao máximo.")
        if self.first > self.last:
            raise DomainError(f"{self.name}: não há valor válido nesse intervalo e nessa precisão.")

    @property
    def epsilon(self) -> Decimal:
        return Decimal(1).scaleb(-self.scale)

    @property
    def first(self) -> Decimal:
        with localcontext() as ctx:
            ctx.prec = 64
            value = (self.lower / self.epsilon).to_integral_value(rounding=ROUND_CEILING) * self.epsilon
            return (value + self.epsilon if value == self.lower and not self.lower_inclusive else value).quantize(self.epsilon)

    @property
    def last(self) -> Decimal:
        with localcontext() as ctx:
            ctx.prec = 64
            value = (self.upper / self.epsilon).to_integral_value(rounding=ROUND_FLOOR) * self.epsilon
            return (value - self.epsilon if value == self.upper and not self.upper_inclusive else value).quantize(self.epsilon)

    @property
    def representative(self) -> Decimal:
        with localcontext() as ctx:
            ctx.prec = 64
            steps = ((self.last - self.first) / self.epsilon / 2).to_integral_value(rounding=ROUND_FLOOR)
            return (self.first + steps * self.epsilon).quantize(self.epsilon)

    def accepts(self, value: str | None) -> bool:
        if value is None:
            return self.accepts("0") if self.null_policy == "zero" else self.null_policy == "aceitar"
        try:
            v = number(value)
            with localcontext() as ctx:
                ctx.prec = 64
                return self.first <= v <= self.last and v % self.epsilon == 0
        except (DomainError, InvalidOperation):
            return False


@dataclass
class FunctionalSuite:
    domains: list[NumericDomain]
    partitions: list[dict]
    boundaries: list[dict]
    cases: list[dict]
    formula: str = ""
    notes: list[str] = field(default_factory=list)


def discover_inputs(content: str) -> list[dict]:
    """Only suggest numeric declarations; never derive business bounds."""
    found = []
    seen = set()
    for match in re.finditer(r"\b([A-Za-z_]\w*)\s+(DECIMAL\s*\(\s*\d+\s*,\s*(\d+)\s*\)|INTEGER|SMALLINT)(?!\w)", content, re.I):
        name, declared, scale = match.groups()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        found.append({"nome": name, "casas": min(int(scale or 0), 12), "declaracao": declared})
    return found[:40]


def validate_formula(expression: str, names: set[str]) -> ast.Expression:
    if not expression.strip() or len(expression) > 300:
        raise DomainError("A fórmula deve ter de 1 a 300 caracteres.")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise DomainError("Fórmula inválida. Use nomes de entradas e +, -, *, / e parênteses.") from exc
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UAdd, ast.USub)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise DomainError("A fórmula aceita apenas números, entradas e operações +, -, * e /.")
        if isinstance(node, ast.Name) and node.id not in names:
            raise DomainError(f"A entrada {node.id} da fórmula não tem domínio configurado.")
        if isinstance(node, ast.Constant) and (isinstance(node.value, bool) or not isinstance(node.value, (int, float))):
            raise DomainError("A fórmula aceita apenas constantes numéricas.")
        if isinstance(node, ast.Constant):
            number(ast.get_source_segment(expression, node) or "")
    return tree


def calculate_formula(expression: str, inputs: dict[str, str | None], domains: list[NumericDomain]) -> str:
    tree = validate_formula(expression, {d.name for d in domains})
    policies = {d.name: d.null_policy for d in domains}

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Name):
            value = inputs[node.id]
            if value is None:
                if policies[node.id] == "zero":
                    return Decimal(0)
                raise DomainError("Resultado depende do tratamento de nulo confirmado pelo usuário.")
            return number(value)
        if isinstance(node, ast.Constant):
            return number(ast.get_source_segment(expression, node) or "")
        if isinstance(node, ast.UnaryOp):
            v = visit(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        left, right = visit(node.left), visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise DomainError("Divisão por zero na fórmula confirmada; definir comportamento esperado.")
        return left / right

    with localcontext() as ctx:
        ctx.prec = 64
        return display(visit(tree))


def generate_suite(domains: list[NumericDomain], formula: str = "") -> FunctionalSuite:
    if not domains or len(domains) > 12:
        raise DomainError("Configure entre 1 e 12 entradas numéricas.")
    if len({d.name for d in domains}) != len(domains):
        raise DomainError("Cada entrada deve ter um nome único.")
    if formula:
        validate_formula(formula, {d.name for d in domains})
    suite = FunctionalSuite(domains, [], [], [], formula, [
        "Limites e políticas foram confirmados pelo usuário; não são inferidos do tipo DECIMAL.",
        "ε = 10^(-casas decimais); para inteiros, ε = 1. AVL usa vizinhos da grade numérica.",
        "As partições abaixo/acima do intervalo usam valores na precisão permitida; a partição de precisão inválida fica separada.",
        "Na política de converter NULL em zero, o zero também precisa pertencer ao intervalo confirmado.",
        "Os casos variam uma entrada por vez, mantendo as demais em representantes válidos.",
        "Resultados são previsões do modelo de domínio/fórmula; o código do TXT não foi executado.",
        "A suíte cobre partições e fronteiras individuais; não mede cobertura de combinações.",
    ])
    baseline = {d.name: display(d.representative) for d in domains}

    def add_case(domain, value, technique, purpose):
        inputs = {**baseline, domain.name: value}
        valid = domain.accepts(value)
        expected = "Aceitar conforme o domínio confirmado." if valid else "Rejeitar conforme o domínio confirmado."
        if valid and formula:
            try:
                expected += " Resultado previsto: " + calculate_formula(formula, inputs, domains)
            except DomainError as exc:
                expected += " " + str(exc)
        suite.cases.append({"id": f"CT-{len(suite.cases)+1:03d}", "tecnica": technique,
                            "entrada": domain.name, "objetivo": purpose, "valores": inputs,
                            "classe": "válida" if valid else "inválida", "esperado": expected})

    with localcontext() as ctx:
        ctx.prec = 64
        for d in domains:
            candidates = [
                ("Intervalo válido", display(d.representative)),
                ("Abaixo do mínimo representável", display(d.first - d.epsilon)),
                ("Acima do máximo representável", display(d.last + d.epsilon)),
                ("Precisão não permitida", display(d.first + d.epsilon / 10)),
                ("Tipo não numérico", "texto"),
                ("Valor nulo", None),
            ]
            for label, value in candidates:
                suite.partitions.append({"entrada": d.name, "particao": label,
                                         "representante": "NULL" if value is None else value,
                                         "classe": "válida" if d.accepts(value) else "inválida"})
                add_case(d, value, "PCE", label)
            seen = set()
            for label, boundary in (("inferior", d.first), ("superior", d.last)):
                for offset in (-1, 0, 1):
                    value = display(boundary + offset * d.epsilon)
                    suite.boundaries.append({"entrada": d.name, "fronteira": label,
                                             "posicao": ("antes", "no limite", "depois")[offset+1],
                                             "valor": value, "epsilon": display(d.epsilon),
                                             "classe": "válida" if d.accepts(value) else "inválida"})
                    if value not in seen:
                        add_case(d, value, "AVL", f"Fronteira {label}: deslocamento {offset}ε")
                        seen.add(value)
    return suite
