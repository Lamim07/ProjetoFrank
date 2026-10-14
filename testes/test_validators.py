import unittest

from aplicacao.validators import MAX_FILE_BYTES, UploadValidationError, validate_upload


class ValidatorTests(unittest.TestCase):
    def test_accepts_txt_case_insensitive(self):
        validate_upload("programa.TXT", b"FUNCTION main()")

    def test_rejects_other_extension(self):
        with self.assertRaisesRegex(UploadValidationError, "extensão"):
            validate_upload("programa.sql", b"SELECT 1")

    def test_rejects_empty(self):
        with self.assertRaisesRegex(UploadValidationError, "vazio"):
            validate_upload("programa.txt", b"")

    def test_rejects_large_file(self):
        with self.assertRaisesRegex(UploadValidationError, "1 MB"):
            validate_upload("programa.txt", b"a" * (MAX_FILE_BYTES + 1))
