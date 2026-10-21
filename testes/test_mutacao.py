import unittest

from aplicacao.mutacao import (MutationError, evaluate_formula_mutation, formula_inputs,
                               generate_mutants, mutant_source, score_registry)


SOURCE = 'FUNCTION f(a,b)\n LET x = a + b # keep + comment\n IF x >= 2 THEN RETURN TRUE ELSE RETURN FALSE END IF\nEND FUNCTION\n'


class MutationTests(unittest.TestCase):
    def test_single_edit_and_source_preservation(self):
        mutants, notes = generate_mutants(SOURCE)
        self.assertEqual(len(mutants), 7)
        for m in mutants:
            changed = mutant_source(SOURCE, m)
            self.assertIn('# keep + comment', changed)
            self.assertEqual(changed[:m.offset], SOURCE[:m.offset])
            self.assertEqual(changed[m.offset+len(m.new):], SOURCE[m.offset+len(m.old):])
        self.assertTrue(notes)

    def test_strings_declarations_and_assignment_not_mutated(self):
        source = 'FUNCTION f()\nDEFINE x DECIMAL(12,2)\nLET x = "a+b >= z"\nRETURN x\nEND FUNCTION'
        self.assertEqual(generate_mutants(source)[0], [])

    def test_limit_and_unsupported_flow(self):
        mutants, notes = generate_mutants(SOURCE, 2)
        self.assertEqual(len(mutants), 2)
        self.assertTrue(any('parcial' in n for n in notes))
        self.assertFalse(generate_mutants('FUNCTION f()\nGOTO x\nEND FUNCTION')[0])
        with self.assertRaises(MutationError):
            generate_mutants(SOURCE, 301)

    def test_unrelated_source_not_accepted(self):
        mutants, _ = generate_mutants(SOURCE)
        with self.assertRaises(MutationError):
            mutant_source('', mutants[0])

    def registry(self):
        mutants, _ = generate_mutants(SOURCE, 3)
        rows = [{'ID': m.id, 'Situação': 'Pendente', 'Evidência': ''} for m in mutants]
        return mutants, rows

    def test_score_pending_and_zero_denominator(self):
        mutants, rows = self.registry()
        score = score_registry(mutants, rows)
        self.assertIsNone(score['escore_final'])
        self.assertIsNone(score['escore_avaliados'])
        self.assertIsNone(score_registry([], [])['escore_final'])

    def test_score_exclusions_and_evidence_required(self):
        mutants, rows = self.registry()
        for row, status in zip(rows, ['Morto', 'Sobrevivente', 'Equivalente']):
            row.update({'Situação': status, 'Evidência': 'CT-01 / justificativa revisada'})
        self.assertEqual(score_registry(mutants, rows)['escore_final'], 50)
        rows[-1]['Evidência'] = ''
        with self.assertRaises(MutationError):
            score_registry(mutants, rows)

    def test_execution_errors_prevent_final_score(self):
        mutants, rows = self.registry()
        for row, status in zip(rows, ['Morto', 'Erro de execução', 'Inválido']):
            row.update({'Situação': status, 'Evidência': 'relatório externo'})
        score = score_registry(mutants, rows)
        self.assertEqual(score['escore_avaliados'], 100)
        self.assertIsNone(score['escore_final'])

    def test_registry_ids_cannot_be_modified(self):
        mutants, rows = self.registry()
        rows[-1]['ID'] = rows[0]['ID']
        with self.assertRaises(MutationError):
            score_registry(mutants, rows)

    def test_arithmetic_independent_expected_results(self):
        result = evaluate_formula_mutation('(a*b)+c', [{'a': '2', 'b': '3', 'c': '4', 'Esperado': '10'}])
        self.assertEqual(result['total'], 6)
        self.assertEqual(result['mortos'], 6)
        self.assertEqual(result['escore'], 100)
        self.assertTrue(all(m['resultados'] for m in result['mutantes']))

    def test_survival_does_not_become_equivalent(self):
        result = evaluate_formula_mutation('a+b', [{'a': '0', 'b': '0', 'Esperado': '0'}])
        self.assertEqual(result['mortos'], 1)  # division by zero differs from successful original
        self.assertEqual(result['total'], 3)
        self.assertEqual(sum(m['situacao'] == 'Sobrevivente' for m in result['mutantes']), 2)

    def test_baseline_failure_blocks_experiment(self):
        with self.assertRaisesRegex(MutationError, 'original retorna'):
            evaluate_formula_mutation('a+b', [{'a': '2', 'b': '3', 'Esperado': '6'}])
        with self.assertRaises(MutationError):
            evaluate_formula_mutation('a/b', [{'a': '2', 'b': '0', 'Esperado': '0'}])

    def test_empty_invalid_and_untrusted_inputs(self):
        for expression in ('__import__("os")', 'a**1000', 'a.attr', '[a]', 'True', 'NaN'):
            with self.subTest(expression=expression):
                with self.assertRaises(MutationError):
                    evaluate_formula_mutation(expression, [{'a': '1', 'Esperado': '0'}])
        for cases in ([], [{'a': 'NaN', 'Esperado': '1'}], [{'Esperado': '1'}]):
            with self.assertRaises(MutationError):
                evaluate_formula_mutation('a+1', cases)


if __name__ == '__main__':
    unittest.main()
