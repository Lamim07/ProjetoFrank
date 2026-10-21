from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).parents[1]
SOURCE = 'FUNCTION f(a,b)\nLET x = a+b\nIF x > 0 THEN RETURN x ELSE RETURN 0 END IF\nEND FUNCTION'


def upload(text=SOURCE):
    result = BytesIO(text.encode('utf-8'))
    result.name = 'avancado.txt'
    return result


def click(app, label):
    next(b for b in app.button if b.label == label).click().run()
    if app.exception:
        raise AssertionError(str(app.exception))


class AdvancedInterfaceTests(unittest.TestCase):
    def test_data_flow_generate_pdf_and_clear(self):
        with patch('streamlit.file_uploader', return_value=upload()):
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
            app.radio[0].set_value('Pares Def-Uso').run()
            click(app, 'Analisar definições e usos')
            self.assertTrue(app.session_state['data_flow_result'].functions[0].pairs)
            click(app, 'Transformar em PDF')
            self.assertTrue(app.session_state['pdf_def_uso'][1].startswith(b'%PDF'))
        with patch('streamlit.file_uploader', return_value=upload('outro documento')):
            app.run()
            self.assertNotIn('data_flow_result', app.session_state)
            self.assertNotIn('pdf_def_uso', app.session_state)

    def test_mutant_catalog_revision_pdf_and_new_upload(self):
        def reviewed(frame, **kwargs):
            result = frame.copy()
            if 'Situação' in result.columns:
                result['Situação'] = 'Morto'
                result['Evidência'] = 'CT-01: original passou, variante falhou; relatório externo.'
            return result
        with patch('streamlit.file_uploader', return_value=upload()), patch('streamlit.data_editor', side_effect=reviewed):
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
            app.radio[0].set_value('Mutação').run()
            click(app, 'Gerar catálogo de mutantes')
            self.assertTrue(app.session_state['mutation_catalog'][0])
            click(app, 'Aplicar resultados e calcular escore')
            self.assertTrue(all(r['Situação'] == 'Morto' for r in app.session_state['mutation_registry']))
            click(app, 'Transformar em PDF')
            self.assertTrue(app.session_state['pdf_mutacao'][1].startswith(b'%PDF'))
        with patch('streamlit.file_uploader', return_value=upload('novo TXT')):
            app.run()
            self.assertNotIn('mutation_catalog', app.session_state)
            self.assertNotIn('mutation_registry', app.session_state)
            self.assertNotIn('pdf_mutacao', app.session_state)

    def test_arithmetic_model_baseline_and_pdf(self):
        with patch('streamlit.file_uploader', return_value=upload()):
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
            app.radio[0].set_value('Mutação').run()
            self.assertEqual(next(t.value for t in app.text_input if t.label == 'Fórmula aritmética a avaliar'), 'a+b')
            next(t for t in app.text_area if t.label == 'Casos da fórmula (CSV)').set_value('a,b,Esperado\n2,3,5')
            next(c for c in app.checkbox if c.label.startswith('Confirmo a fórmula')).check()
            click(app, 'Avaliar mutações da fórmula')
            self.assertEqual(app.session_state['mutation_model_result']['escore'], 100)
            click(app, 'Transformar em PDF')
            self.assertTrue(app.session_state['pdf_mutacao_modelo'][1].startswith(b'%PDF'))
        with patch('streamlit.file_uploader', return_value=None):
            app.run()
            self.assertNotIn('mutation_model_result', app.session_state)
            self.assertNotIn('pdf_mutacao_modelo', app.session_state)


if __name__ == '__main__':
    unittest.main()
