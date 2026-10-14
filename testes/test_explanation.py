import json
import unittest
from pathlib import Path

from aplicacao.analyzer import AnalysisError, explain_code, parse_explanation
from aplicacao.documentation import build_documentation
from aplicacao.models import AnalysisResult


CONTENT = (Path(__file__).parent / "arquivos_de_exemplo" / "cad0001_item_calculo.txt").read_text(encoding="utf-8")


class StubClient:
    def __init__(self, response: str):
        self.response = response
        self.schema = None

    def analyze(self, prompt: str, schema: dict | None = None) -> str:
        self.schema = schema
        return self.response


def explanation(evidence: str) -> str:
    return json.dumps({
        "overview": "O programa calcula e grava itens.",
        "execution_flow": [{"description": "Inicia a rotina principal.", "evidence": evidence}],
        "inputs_outputs": [],
        "calculations_rules": [],
        "data_operations": [],
        "unknowns": ["A implementação de cad0001_menu não aparece no TXT."],
    }, ensure_ascii=False)


class ExplanationTests(unittest.TestCase):
    def test_explanation_uses_own_schema_and_literal_evidence(self):
        client = StubClient(explanation("FUNCTION cad0001_main()"))
        result = explain_code(CONTENT, client)
        self.assertEqual(result.execution_flow[0].description, "Inicia a rotina principal.")
        self.assertIn("execution_flow", client.schema["properties"])

    def test_explanation_rejects_missing_evidence(self):
        with self.assertRaisesRegex(AnalysisError, "evidência"):
            parse_explanation(explanation("FUNCTION nao_existe()"), CONTENT)

    def test_documentation_includes_evidence_and_uncertainty(self):
        result = AnalysisResult.model_validate({
            "content_type": "código-fonte",
            "subject": "Cadastro de item",
            "language": "Informix-4GL",
            "language_confidence": "alta",
            "summary": "Calcula itens.",
            "structures": [],
            "functions": [{"description": "Função principal", "evidence": "FUNCTION cad0001_main()"}],
            "business_rules": [],
            "operations": [],
            "transactions": [],
            "uncertainties": ["Menu não definido neste arquivo."],
        })
        document = build_documentation(result, "cad0001_item_calculo.txt")
        self.assertIn("# Documentação de cad0001_item_calculo.txt", document)
        self.assertIn("FUNCTION cad0001_main()", document)
        self.assertIn("Menu não definido neste arquivo.", document)


if __name__ == "__main__":
    unittest.main()
