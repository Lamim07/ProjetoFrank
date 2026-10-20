import copy
import csv
import json
from io import StringIO
from pathlib import Path
import unittest

from aplicacao.analyzer import AnalysisError
from aplicacao.requisitos import RequirementPlan, build_rtm, derive_requirements, parse_requirements, requirements_schema, rtm_csv


SOURCE = (Path(__file__).parent / "arquivos_de_exemplo" / "biblioteca_requisitos.txt").read_text(encoding="utf-8")


def sample_payload():
    descriptions = [line.split(": ", 1) for line in SOURCE.splitlines() if line.startswith("REQ0")]
    return {
        "requirements": [{"id": rid, "description": text, "origin": "especificacao", "evidence": text} for rid, text in descriptions],
        "use_cases": [
            {"id": "UC01", "title": "Cadastrar, buscar e reservar", "actor": "Não informado",
             "requirement_ids": ["REQ01", "REQ04", "REQ05"], "preconditions": [],
             "main_flow": ["Cadastrar livro com ISBN, título e autor.", "Buscar por título ou categoria.", "Emitir comprovante de reserva por e-mail."],
             "alternative_flows": [], "exception_flows": []},
            {"id": "UC02", "title": "Liberar empréstimo", "actor": "Usuário",
             "requirement_ids": ["REQ02"], "preconditions": [], "main_flow": ["Validar pendências antes de liberar o empréstimo."],
             "alternative_flows": [], "exception_flows": ["Bloquear empréstimo para usuário com dívida."]},
            {"id": "UC03", "title": "Calcular multa", "actor": "Não informado", "requirement_ids": ["REQ03"],
             "preconditions": [], "main_flow": ["Verificar atraso na devolução."],
             "alternative_flows": ["Calcular R$ 2,00 por dia de atraso."], "exception_flows": []},
        ],
        "test_cases": [
            {"id": "CT01", "title": "Caminho feliz", "flow_type": "principal", "requirement_ids": ["REQ01", "REQ04", "REQ05"],
             "use_case_ids": ["UC01"], "preconditions": [], "steps": ["Cadastrar, buscar e solicitar comprovante de reserva."],
             "expected_result": "Livro cadastrado, busca realizada e comprovante emitido por e-mail.", "pending": []},
            {"id": "CT02", "title": "Bloqueio por dívida", "flow_type": "excecao", "requirement_ids": ["REQ02"],
             "use_case_ids": ["UC02"], "preconditions": ["Usuário com dívida."], "steps": ["Solicitar empréstimo."],
             "expected_result": "Empréstimo bloqueado.", "pending": []},
            {"id": "CT03", "title": "Multa por atraso", "flow_type": "alternativo", "requirement_ids": ["REQ03"],
             "use_case_ids": ["UC03"], "preconditions": [], "steps": ["Devolver livro com atraso."],
             "expected_result": "Multa de R$ 2,00 por dia de atraso.", "pending": ["Confirmar contagem de dias e fronteiras de datas."]},
        ],
        "gaps": ["O ator responsável pelo cadastro e os critérios de validade do ISBN não foram definidos."],
    }


def sample_plan():
    return parse_requirements(json.dumps(sample_payload(), ensure_ascii=False), SOURCE)


class RequirementTests(unittest.TestCase):
    def test_lesson_example_has_bidirectional_many_to_many_links(self):
        matrix = build_rtm(sample_plan())
        self.assertEqual(len(matrix.forward), 5)
        self.assertEqual(matrix.linked_percentage, 100)
        self.assertEqual(matrix.forward[0]["testes"], "CT01")
        self.assertEqual(matrix.reverse[0]["requisitos"], "REQ01, REQ04, REQ05")
        self.assertEqual(matrix.pending_tests, ["CT03"])
        self.assertEqual({r["execução"] for r in matrix.reverse}, {"Não executado"})

    def test_uncovered_and_orphan_are_reported_independently(self):
        payload = sample_payload()
        payload["test_cases"] = payload["test_cases"][:1]
        extra = copy.deepcopy(payload["test_cases"][0])
        extra.update(id="CT04", requirement_ids=[], use_case_ids=[])
        payload["test_cases"].append(extra)
        matrix = build_rtm(RequirementPlan.model_validate(payload))
        self.assertEqual(matrix.uncovered_requirements, ["REQ02", "REQ03"])
        self.assertEqual(matrix.orphan_tests, ["CT04"])
        self.assertEqual(matrix.linked_percentage, 60)

    def test_empty_plan_has_no_misleading_coverage_percentage(self):
        matrix = build_rtm(RequirementPlan(requirements=[], use_cases=[], test_cases=[], gaps=[]))
        self.assertIsNone(matrix.linked_percentage)

    def test_duplicate_ids_are_rejected_in_all_groups(self):
        for group in ("requirements", "use_cases", "test_cases"):
            with self.subTest(group=group):
                payload = sample_payload()
                payload[group].append(copy.deepcopy(payload[group][0]))
                with self.assertRaisesRegex(AnalysisError, "duplicados"):
                    parse_requirements(json.dumps(payload), SOURCE)
        payload = sample_payload()
        payload["requirements"][0]["id"] = "UC01"
        with self.assertRaisesRegex(AnalysisError, "duplicados"):
            parse_requirements(json.dumps(payload), SOURCE)

    def test_missing_references_and_repeated_links_are_rejected(self):
        for key, value in (("requirement_ids", ["REQ999"]), ("use_case_ids", ["UC999"]),
                           ("requirement_ids", ["REQ01", "REQ01"])):
            payload = sample_payload()
            payload["test_cases"][0][key] = value
            with self.assertRaises(AnalysisError):
                parse_requirements(json.dumps(payload), SOURCE)

    def test_hallucinated_requirement_evidence_is_rejected(self):
        payload = sample_payload()
        payload["requirements"][0]["evidence"] = "ISBN deve obrigatoriamente ter 13 dígitos."
        with self.assertRaisesRegex(AnalysisError, "evidência"):
            parse_requirements(json.dumps(payload), SOURCE)

    def test_whitespace_normalization_keeps_literal_evidence(self):
        payload = sample_payload()
        payload["requirements"][0]["evidence"] = payload["requirements"][0]["evidence"].replace(" ", "\n")
        self.assertEqual(len(parse_requirements(json.dumps(payload), SOURCE).requirements), 5)

    def test_observed_code_is_distinguished_from_specification(self):
        payload = sample_payload()
        payload["requirements"][0]["origin"] = "observado_no_codigo"
        plan = parse_requirements(json.dumps(payload), SOURCE)
        self.assertEqual(build_rtm(plan).forward[0]["origem"], "observado_no_codigo")

    def test_use_case_does_not_implicitly_cover_unlinked_requirements(self):
        payload = sample_payload()
        payload["test_cases"][0]["requirement_ids"] = ["REQ01"]
        matrix = build_rtm(RequirementPlan.model_validate(payload))
        self.assertIn("REQ04", matrix.uncovered_requirements)
        self.assertIn("REQ05", matrix.uncovered_requirements)

    def test_conflicting_use_case_references_get_warning(self):
        payload = sample_payload()
        payload["test_cases"][0]["use_case_ids"] = ["UC02"]
        self.assertTrue(build_rtm(RequirementPlan.model_validate(payload)).warnings)

    def test_csv_neutralizes_spreadsheet_formula_cells(self):
        plan = sample_plan()
        plan.requirements[0].description = '=HYPERLINK("https://example.invalid")'
        data = rtm_csv(build_rtm(plan))
        rows = list(csv.DictReader(StringIO(data.decode("utf-8-sig"))))
        self.assertTrue(rows[0]["descrição"].startswith("'="))

    def test_schema_is_inline_and_small(self):
        schema = requirements_schema()
        encoded = json.dumps(schema)
        for forbidden in ("$ref", "$defs", "minLength", "pattern", "additionalProperties"):
            self.assertNotIn(forbidden, encoded)
        self.assertIn("test_cases", schema["properties"])

    def test_derivation_uses_specific_prompt_and_schema(self):
        class Stub:
            def analyze(self, prompt, schema):
                self.prompt, self.schema = prompt, schema
                return json.dumps(sample_payload())
        client = Stub()
        plan = derive_requirements(SOURCE, client)
        self.assertEqual(len(plan.test_cases), 3)
        self.assertIn("Não execute código", client.prompt)
        self.assertIn(SOURCE, client.prompt)
        self.assertIn("requirements", client.schema["properties"])

    def test_invalid_or_oversized_response_is_rejected(self):
        for data in ("{}", "sem json", " " * 500_001):
            with self.assertRaises(AnalysisError):
                parse_requirements(data, SOURCE)


if __name__ == "__main__":
    unittest.main()
