from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "testes" / "arquivos_de_exemplo" / "cad0001_item_calculo.txt").read_bytes()


def uploaded(data=SOURCE, name="cad0001_item_calculo.txt"):
    result = BytesIO(data)
    result.name = name
    return result


class InterfaceTests(unittest.TestCase):
    def test_local_flow_and_pdf_do_not_require_gemini(self):
        with patch("streamlit.file_uploader", return_value=uploaded()):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
            app.radio[0].set_value("Fluxo de controle").run()
            next(b for b in app.button if b.label == "Gerar grafo e métricas").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["flow_result"].functions), 5)
            next(b for b in app.button if b.label == "Transformar em PDF").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["pdf_fluxo"][1].startswith(b"%PDF-"))

    def test_generate_functional_suite_and_clear_on_new_upload(self):
        with patch("streamlit.file_uploader", return_value=uploaded()):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
            app.radio[0].set_value("PCE / AVL").run()
            for item in app.text_input:
                if item.label == "Limite mínimo":
                    item.set_value("0")
                elif item.label == "Limite máximo":
                    item.set_value("100")
            next(c for c in app.checkbox if c.label.startswith("Confirmo")).check()
            next(b for b in app.button if b.label.startswith("Gerar PCE")).click().run()
            self.assertFalse(app.exception)
            self.assertGreater(len(app.session_state["functional_result"].cases), 20)
        with patch("streamlit.file_uploader", return_value=uploaded(b"outro conteudo", "outro.txt")):
            app.run()
            self.assertNotIn("functional_result", app.session_state)


if __name__ == "__main__":
    unittest.main()
