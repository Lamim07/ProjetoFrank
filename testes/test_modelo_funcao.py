from pathlib import Path
import unittest

from aplicacao.modelo_funcao import (ModelError, available_models, compile_model, evaluate_source_mutation,
                                     expression_tree, parse_cases_csv, run_model)
from aplicacao.mutacao import MutationError
from aplicacao.fluxo_controle import FlowError


SOURCE = (Path(__file__).parent/'arquivos_de_exemplo/cad0001_item_calculo.txt').read_text(encoding='utf-8')
NAME = 'cad0001_calcula_valor'


class SourceMutationTests(unittest.TestCase):
    def test_supported_function_and_explicit_external_limits(self):
        models, limits = available_models(SOURCE)
        self.assertEqual([m.name for m in models],[NAME])
        self.assertEqual(len(limits),4)

    def test_original_function_and_null_handling(self):
        model=compile_model(SOURCE,NAME)
        for values,expected in ((['2','3','4'],'10'),(['NULL','3','4'],'4'),(['2','NULL','4'],'4'),(['2','3','NULL'],'6'),(['NULL']*3,'0')):
            with self.subTest(values=values):
                result=run_model(model,dict(zip(model.params,values)))
                self.assertEqual(result['resultado'],expected)
                self.assertTrue(result['trilha'])

    def test_source_mutants_and_exact_score(self):
        result=evaluate_source_mutation(SOURCE,NAME,[{'p_val1':'2','p_val2':'3','p_val3':'4','Esperado':'10'},
                                                   {'p_val1':'NULL','p_val2':'3','p_val3':'4','Esperado':'4'}])
        self.assertEqual(result['total'],9)
        self.assertEqual(result['mortos'],9)
        self.assertEqual(result['escore'],100)
        self.assertTrue(any(m['alteracao']=='IS NULL -> IS NOT NULL' for m in result['mutantes']))

    def test_baseline_failure_blocks_mutation(self):
        with self.assertRaisesRegex(MutationError,'Corrija a base'):
            evaluate_source_mutation(SOURCE,NAME,[{'p_val1':'2','p_val2':'3','p_val3':'4','Esperado':'11'}])

    def test_branch_return_and_three_valued_null(self):
        model=compile_model('FUNCTION f(a)\nIF a > 0 THEN RETURN TRUE ELSE RETURN FALSE END IF\nEND FUNCTION','f')
        self.assertEqual(run_model(model,{'a':'1'})['resultado'],'TRUE')
        self.assertEqual(run_model(model,{'a':'NULL'})['resultado'],'FALSE')

    def test_undefined_path_and_absent_return(self):
        for body in ('IF a > 0 THEN LET x=1 END IF\nRETURN x','IF a > 0 THEN RETURN 1 END IF'):
            model=compile_model('FUNCTION f(a)\n'+body+'\nEND FUNCTION','f')
            with self.assertRaises(ModelError):run_model(model,{'a':'0'})

    def test_calls_sql_arrays_attributes_and_python_rejected(self):
        for body in ('LET x = __import__(1)\nRETURN x','INSERT INTO t VALUES (1)','RETURN a.x','RETURN a[0]',
                     'RETURN "text"','WHILE a>0\nLET a=a-1\nEND WHILE\nRETURN a'):
            with self.subTest(body=body):
                with self.assertRaises((ModelError,FlowError)):
                    compile_model('FUNCTION f(a)\n'+body+'\nEND FUNCTION','f')

    def test_inputs_strict_and_finite(self):
        model=compile_model(SOURCE,NAME)
        for values in ({'p_val1':'NaN','p_val2':'2','p_val3':'3'}, {'p_val1':'TRUE','p_val2':'2','p_val3':'3'}, {'p_val1':'1'}):
            with self.assertRaises(ModelError):run_model(model,values)

    def test_csv_header_empty_rows_and_limit(self):
        self.assertEqual(parse_cases_csv('a,Esperado\nNULL,0',['a'])[0]['a'],'NULL')
        for text in ('a,Esperado','a,Esperado\n1,','a,Esperado\n1,2,3','a,b,Esperado\n1,2,3','a,Esperado\n'+'1,1\n'*101):
            with self.assertRaises(MutationError):parse_cases_csv(text,['a'])

    def test_constant_no_operators_does_not_publish_score(self):
        result=evaluate_source_mutation('FUNCTION f()\nRETURN 1\nEND FUNCTION','f',[{'Esperado':'1'}])
        self.assertIsNone(result['escore'])

    def test_boolean_and_numeric_return_are_not_equal(self):
        with self.assertRaises(MutationError):
            evaluate_source_mutation('FUNCTION f(a)\nRETURN TRUE\nEND FUNCTION','f',[{'a':'1','Esperado':'1'}])

    def test_recurring_decimal_in_mutant_is_reported_as_value(self):
        result=evaluate_source_mutation('FUNCTION f(a,b)\nRETURN a+b\nEND FUNCTION','f',
                                       [{'a':'2','b':'3','Esperado':'5'}])
        division=next(m for m in result['mutantes'] if m['alteracao']=='+ -> /')
        self.assertTrue(division['resultados'][0]['obtido'].startswith('0.6666'))
        self.assertNotIn('Erro',division['resultados'][0]['obtido'])


if __name__=='__main__':unittest.main()
