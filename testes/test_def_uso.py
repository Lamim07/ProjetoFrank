import unittest
from pathlib import Path

from aplicacao.def_uso import analyze_data_flow
from aplicacao.fluxo_controle import FlowError


def program(body, params="a"):
    return f"FUNCTION exemplo({params})\n{body}\nEND FUNCTION"


class DataFlowTests(unittest.TestCase):
    def report(self, body, params="a"):
        report = analyze_data_flow(program(body, params))
        self.assertFalse(report.unsupported)
        return report.functions[0]

    def test_sequential_redefinition_kills_previous_definition(self):
        result = self.report("LET x = a\nLET x = 2\nRETURN x")
        x_pairs = [p for p in result.pairs if p["variável"] == "x"]
        self.assertEqual(len(x_pairs), 1)
        self.assertEqual(x_pairs[0]["linha definição"], 3)
        self.assertEqual(x_pairs[0]["linha uso"], 4)
        self.assertTrue(any("não alcança uso" in w for w in result.warnings))

    def test_branch_merge_reaches_both_definitions(self):
        result = self.report("IF a > 0 THEN\nLET x = 1\nELSE\nLET x = 2\nEND IF\nRETURN x")
        pairs = [p for p in result.pairs if p["variável"] == "x"]
        self.assertEqual({p["linha definição"] for p in pairs}, {3, 5})
        self.assertEqual(len([p for p in result.pairs if p["tipo"] == "p-use"]), 2)
        self.assertTrue(all(p["caminho candidato"] for p in result.pairs))

    def test_loop_fixed_point_and_read_before_write(self):
        result = self.report("LET x = 0\nWHILE x < a\nLET x = x + 1\nEND WHILE\nRETURN x")
        self.assertTrue(any(p["linha definição"] == p["linha uso"] == 4 for p in result.pairs))
        self.assertTrue(any(p["linha definição"] == 4 and p["linha uso"] == 3 for p in result.pairs))

    def test_possible_uninitialized_use_on_one_branch(self):
        result = self.report("IF a > 0 THEN\nLET x = 1\nEND IF\nRETURN x")
        self.assertTrue(any("x pode ser usado sem definição" in w for w in result.warnings))

    def test_inline_if_keeps_distinct_events(self):
        result = self.report("IF a IS NULL THEN LET a = 0 END IF\nRETURN a")
        self.assertEqual(len([p for p in result.pairs if p["linha uso"] == 3]), 2)

    def test_comments_strings_and_case_are_not_variables(self):
        result = self.report('LET X = A # ghost\nMESSAGE "ghost", x\nRETURN X')
        self.assertFalse(any("ghost" in p["variável"] for p in result.pairs))
        self.assertFalse(result.warnings)

    def test_declarations_keep_original_line_numbers(self):
        result = self.report("DEFINE a DECIMAL(12,2),\n       x INTEGER\n\nLET x = a\nRETURN x")
        self.assertTrue(any(p["linha definição"] == 5 and p["linha uso"] == 6 for p in result.pairs))

    def test_unsupported_effects_skip_entire_function(self):
        for body in ("CALL other(a)", "INSERT INTO t VALUES (a)", "LET x = other(a)", "FOR i = 1 TO a\nEND FOR", "LET x = a[1]"):
            with self.subTest(body=body):
                result = analyze_data_flow(program(body))
                self.assertFalse(result.functions)
                self.assertTrue(result.unsupported)

    def test_unreachable_use_does_not_generate_pairs(self):
        result = self.report("RETURN a\nLET x = z")
        self.assertFalse(any(p["variável"] == "z" for p in result.pairs))

    def test_invalid_boundaries_rejected(self):
        for source in ("RETURN a", "FUNCTION f(a)\nRETURN a", "END FUNCTION", program("RETURN a", "a,a")):
            with self.assertRaises(FlowError):
                analyze_data_flow(source)

    def test_official_fixture_computation_function(self):
        source = (Path(__file__).parent / 'arquivos_de_exemplo/cad0001_item_calculo.txt').read_text(encoding='utf-8')
        report = analyze_data_flow(source)
        self.assertEqual([f.name for f in report.functions], ['cad0001_calcula_valor'])
        self.assertEqual(len(report.unsupported), 4)
        self.assertEqual(len(report.functions[0].pairs), 13)


if __name__ == '__main__':
    unittest.main()
