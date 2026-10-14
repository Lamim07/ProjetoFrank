import unittest

from aplicacao.file_reader import read_text
from aplicacao.validators import UploadValidationError


class FileReaderTests(unittest.TestCase):
    def test_utf8_with_bom(self):
        self.assertEqual(read_text(b"\xef\xbb\xbfOl\xc3\xa1"), "Olá")

    def test_invalid_encoding(self):
        with self.assertRaisesRegex(UploadValidationError, "UTF-8"):
            read_text(b"\xff")

    def test_whitespace_only(self):
        with self.assertRaisesRegex(UploadValidationError, "não contém texto"):
            read_text(b"  \n \t")
