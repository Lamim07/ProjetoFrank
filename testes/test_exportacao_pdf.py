import unittest

from aplicacao.exportacao_pdf import ReportSection, render_pdf


class PdfTests(unittest.TestCase):
    def test_long_table_and_untrusted_markup_are_exported_without_interpretation(self):
        sections = [ReportSection("Precisão ε e acentuação", [
            '<img src="file:///nao_deve_ser_lido"/>',
            "Cálculo: 0,01; regras e transações.",
        ], ["Entrada", "Evidência"], [["p_val1", "código " * 800]] * 4)]
        data = render_pdf("Relatório de teste", "arquivo.txt", sections)
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        self.assertGreater(len(data), 10000)


if __name__ == "__main__":
    unittest.main()
