from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from aplicacao.interface_requisitos import edited_plan
from testes.test_requisitos import SOURCE, sample_plan


ROOT = Path(__file__).parents[1]


class RequirementInterfaceTests(unittest.TestCase):
    def test_table_revision_accepts_user_edits_and_validates_links(self):
        req = pd.DataFrame([{"ID": "REQ01", "Requisito": "Cadastro de livros.", "Origem": "Especificação",
                             "Evidência": "Cadastro de novos livros informando ISBN, Título e Autor."}])
        uc = pd.DataFrame([{"ID": "UC01", "Nome": "Cadastrar livro", "Ator": "Não informado", "Requisitos": "REQ01",
                            "Pré-condições": "", "Principal": "Informar dados | Cadastrar", "Alternativos": "", "Exceções": ""}])
        ct = pd.DataFrame([{"ID": "CT01", "Cenário": "Cadastro", "Fluxo": "Principal", "Requisitos": "REQ01",
                            "Casos de uso": "UC01", "Pré-condições": "", "Passos": "Informar dados | Salvar",
                            "Esperado": "Livro cadastrado.", "Pendências": ""}])
        plan = edited_plan(req, uc, ct, "Ator a confirmar", SOURCE)
        self.assertEqual(plan.test_cases[0].steps, ["Informar dados", "Salvar"])
        self.assertEqual(plan.gaps, ["Ator a confirmar"])

    def test_generate_review_pdf_and_clear_on_new_upload(self):
        uploaded = BytesIO(SOURCE.encode("utf-8"))
        uploaded.name = "biblioteca_requisitos.txt"
        with patch("streamlit.file_uploader", return_value=uploaded), \
             patch("aplicacao.interface_requisitos.derive_requirements", return_value=sample_plan()):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
            app.radio[0].set_value("Requisitos e RTM").run()
            next(b for b in app.button if b.label == "Derivar requisitos e casos de teste").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["requirements_result"].requirements), 5)
            self.assertFalse(app.session_state["requirements_reviewed"])
            next(c for c in app.checkbox if c.label.startswith("Revisei")).check()
            next(b for b in app.button if b.label == "Aplicar revisão e atualizar RTM").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["requirements_reviewed"])
            next(b for b in app.button if b.label == "Transformar em PDF").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["pdf_requisitos"][1].startswith(b"%PDF-"))
        other = BytesIO(b"outro documento")
        other.name = "outro.txt"
        with patch("streamlit.file_uploader", return_value=other):
            app.run()
            self.assertNotIn("requirements_result", app.session_state)
            self.assertNotIn("pdf_requisitos", app.session_state)


if __name__ == "__main__":
    unittest.main()
