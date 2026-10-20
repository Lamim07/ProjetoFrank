import unittest
from pathlib import Path

from aplicacao.fluxo_controle import FlowError, analyze_flow


def function(body):
    return "FUNCTION exemplo()\n" + body + "\nEND FUNCTION"


class FlowTests(unittest.TestCase):
    def test_official_file_exact_complexity(self):
        source = (Path(__file__).parent / "arquivos_de_exemplo" / "cad0001_item_calculo.txt").read_text(encoding="utf-8")
        report = analyze_flow(source)
        self.assertEqual(report.unsupported, [])
        self.assertEqual({f.name: f.complexity for f in report.functions}, {
            "cad0001_main": 1, "cad0001_calcula_valor": 4,
            "cad0001_incluir": 3, "cad0001_alterar": 3, "cad0001_excluir": 3,
        })

    def test_straight_line_is_one_path(self):
        flow = analyze_flow(function("LET x=1\nRETURN x")).functions[0]
        self.assertEqual(flow.complexity, 1)

    def test_nested_decisions_and_return_normalize_exit(self):
        body = "IF x THEN\n IF y THEN RETURN 1 END IF\nELSE\n RETURN 2\nEND IF\nRETURN 3"
        flow = analyze_flow(function(body)).functions[0]
        self.assertEqual(flow.complexity, 3)
        self.assertIn('label="não"', flow.dot())
        exit_node = next(n.id for n in flow.nodes if n.kind == "exit")
        self.assertEqual(sum(b == exit_node for _, b, _ in flow.edges), 3)

    def test_loop_has_back_edge(self):
        flow = analyze_flow(function("WHILE x < 10\n LET x=x+1\nEND WHILE\nRETURN x")).functions[0]
        loop = next(n.id for n in flow.nodes if n.kind == "loop")
        self.assertTrue(any(b == loop for a, b, _ in flow.edges if a != "N1"))
        self.assertEqual(flow.complexity, 2)

    def test_strings_and_comments_do_not_create_decisions(self):
        flow = analyze_flow(function('MESSAGE "IF x THEN ELSE END IF # texto" # IF y THEN\nRETURN 1')).functions[0]
        self.assertEqual(flow.complexity, 1)
        self.assertIn("# texto", next(n.text for n in flow.nodes if n.kind == "return"))

    def test_unreachable_decision_is_excluded(self):
        flow = analyze_flow(function("RETURN 1\nIF x THEN RETURN 2 END IF")).functions[0]
        self.assertEqual(flow.complexity, 1)
        self.assertTrue(any("excluídos" in note for note in flow.notes))

    def test_unknown_control_is_not_given_fake_metric(self):
        for body in ("CASE x\nWHEN 1\nRETURN 1\nEND CASE", 'MENU "Opções"\nEND MENU', "STOP"):
            with self.subTest(body=body):
                report = analyze_flow(function(body))
                self.assertEqual(report.functions, [])
                self.assertIn("não suportada", report.unsupported[0])

    def test_unbalanced_if_has_no_metric(self):
        report = analyze_flow(function("IF x THEN\nRETURN 1"))
        self.assertEqual(report.functions, [])
        self.assertIn("sem END IF", report.unsupported[0])

    def test_other_language_and_missing_function_end(self):
        for source in ("def main(): return 1", "FUNCTION teste()\nRETURN 1"):
            with self.assertRaises(FlowError):
                analyze_flow(source)


if __name__ == "__main__":
    unittest.main()
