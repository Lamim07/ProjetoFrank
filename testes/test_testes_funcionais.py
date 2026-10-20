import unittest
from decimal import Decimal
from pathlib import Path

from aplicacao.testes_funcionais import DomainError, NumericDomain, calculate_formula, discover_inputs, generate_suite, number


class FunctionalTests(unittest.TestCase):
    def domain(self, **kwargs):
        return NumericDomain("valor", Decimal("0"), Decimal("100"), **kwargs)

    def test_decimal_epsilon_has_no_float_rounding(self):
        d = self.domain(scale=2)
        suite = generate_suite([d])
        self.assertEqual(d.epsilon, Decimal("0.01"))
        self.assertEqual([r["valor"] for r in suite.boundaries], ["-0.01", "0.00", "0.01", "99.99", "100.00", "100.01"])

    def test_exclusive_integer_limits(self):
        d = self.domain(lower_inclusive=False, upper_inclusive=False)
        self.assertEqual((d.first, d.last), (Decimal(1), Decimal(99)))
        self.assertFalse(d.accepts("0"))
        self.assertTrue(d.accepts("1"))

    def test_non_aligned_limits_use_representable_grid(self):
        d = NumericDomain("x", Decimal("0.005"), Decimal("0.025"), 2)
        self.assertEqual((d.first, d.last), (Decimal("0.01"), Decimal("0.02")))

    def test_empty_domain_is_rejected(self):
        with self.assertRaises(DomainError):
            NumericDomain("x", Decimal("1"), Decimal("1"), lower_inclusive=False)

    def test_reversed_and_non_finite_domains_are_rejected(self):
        for low, high in (("2", "1"), ("NaN", "1"), ("0", "Infinity")):
            with self.assertRaises(DomainError):
                NumericDomain("x", Decimal(low), Decimal(high))

    def test_null_precision_and_type_classes(self):
        d = self.domain(scale=2, null_policy="zero")
        self.assertTrue(d.accepts(None))
        self.assertFalse(d.accepts("0.001"))
        self.assertFalse(d.accepts("texto"))
        self.assertFalse(self.domain().accepts(None))
        self.assertFalse(NumericDomain("x", Decimal(1), Decimal(10), null_policy="zero").accepts(None))

    def test_one_input_varies_and_formula_is_exact(self):
        domains = [NumericDomain(name, Decimal(0), Decimal(10), 2) for name in ("a", "b", "c")]
        suite = generate_suite(domains, "a*b+c")
        case = next(r for r in suite.cases if r["entrada"] == "a" and r["tecnica"] == "AVL" and r["valores"]["a"] == "0.01")
        self.assertEqual(case["valores"]["b"], "5.00")
        self.assertIn("5.0500", case["esperado"])
        self.assertEqual(calculate_formula("0.1+0.2", {}, []), "0.3")

    def test_formula_calls_and_unknown_names_are_rejected(self):
        for formula in ("__import__('os').system('dir')", "valor ** 100", "outro+1", "valor[0]"):
            with self.assertRaises(DomainError):
                generate_suite([self.domain()], formula)

    def test_null_to_zero_and_division_by_zero(self):
        d = self.domain(null_policy="zero")
        self.assertEqual(calculate_formula("valor+1", {"valor": None}, [d]), "1")
        suite = generate_suite([d], "1/valor")
        self.assertTrue(any("Divisão por zero" in r["esperado"] for r in suite.cases))

    def test_discovery_does_not_invent_bounds(self):
        text = (Path(__file__).parent / "arquivos_de_exemplo" / "cad0001_item_calculo.txt").read_text(encoding="utf-8")
        inputs = discover_inputs(text)
        p = next(i for i in inputs if i["nome"] == "p_val1")
        self.assertEqual(p["casas"], 2)
        self.assertNotIn("minimo", p)
        self.assertNotIn("maximo", p)

    def test_number_accepts_comma_but_rejects_ambiguous_values(self):
        self.assertEqual(number("-1,25"), Decimal("-1.25"))
        for value in ("NaN", "Infinity", "1,000.00", "1e999999", ""):
            with self.assertRaises(DomainError):
                number(value)


if __name__ == "__main__":
    unittest.main()
