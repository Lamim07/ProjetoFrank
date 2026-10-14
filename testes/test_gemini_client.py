import unittest
from types import SimpleNamespace

from google.genai import errors

from aplicacao.gemini_client import GeminiClient, GeminiError, _status_message


class FakeInteractions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(output_text=self.response)


class FormatRejectingInteractions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "response_format" in kwargs:
            raise errors.ClientError(400, {"message": "Unsupported response_format schema"})
        return SimpleNamespace(output_text='{"ok": true}')


class GeminiClientTests(unittest.TestCase):
    def test_missing_key_does_not_call_api(self):
        client = GeminiClient(api_key=" ")
        with self.assertRaisesRegex(GeminiError, "não está configurada"):
            client.analyze("teste")

    def test_sends_structured_stateless_request(self):
        fake = FakeInteractions(response='{"ok": true}')
        client = GeminiClient(api_key="test-key", sdk_client=SimpleNamespace(interactions=fake))
        self.assertEqual(client.analyze("texto de teste"), '{"ok": true}')
        self.assertEqual(fake.kwargs["input"], "texto de teste")
        self.assertEqual(fake.kwargs["response_format"]["mime_type"], "application/json")
        self.assertIn("business_rules", fake.kwargs["response_format"]["schema"]["properties"])
        self.assertNotIn("minLength", str(fake.kwargs["response_format"]["schema"]))
        self.assertNotIn("$ref", str(fake.kwargs["response_format"]["schema"]))
        self.assertNotIn("$defs", str(fake.kwargs["response_format"]["schema"]))

    def test_maps_invalid_key_without_exposing_exception(self):
        fake = FakeInteractions(error=errors.ClientError(403, {"message": "private detail"}))
        client = GeminiClient(api_key="test-key", sdk_client=SimpleNamespace(interactions=fake))
        with self.assertRaises(GeminiError) as caught:
            client.analyze("teste")
        self.assertIn("chave Gemini foi recusada", str(caught.exception))
        self.assertNotIn("private detail", str(caught.exception))

    def test_rejects_empty_model_response(self):
        fake = FakeInteractions(response="  ")
        client = GeminiClient(api_key="test-key", sdk_client=SimpleNamespace(interactions=fake))
        with self.assertRaisesRegex(GeminiError, "resposta vazia"):
            client.analyze("teste")

    def test_maps_interactions_http_status(self):
        fake = FakeInteractions(
            error=errors.ClientError(403, {"message": "private detail"})
        )
        client = GeminiClient(api_key="test-key", sdk_client=SimpleNamespace(interactions=fake))
        with self.assertRaises(GeminiError) as caught:
            client.analyze("teste")
        self.assertIn("chave Gemini foi recusada", str(caught.exception))
        self.assertNotIn("private detail", str(caught.exception))

    def test_maps_new_interactions_server_error(self):
        class InternalServerError(Exception):
            status_code = 500
            body = {"message": "private server detail"}

        fake = FakeInteractions(error=InternalServerError())
        client = GeminiClient(api_key="test-key", sdk_client=SimpleNamespace(interactions=fake))
        with self.assertRaises(GeminiError) as caught:
            client.analyze("teste")
        self.assertIn("indisponível", str(caught.exception))
        self.assertNotIn("private server detail", str(caught.exception))

    def test_retries_without_response_format_after_schema_rejection(self):
        fake = FormatRejectingInteractions()
        client = GeminiClient(api_key="test-key", sdk_client=SimpleNamespace(interactions=fake))
        self.assertEqual(client.analyze("texto de teste"), '{"ok": true}')
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("response_format", fake.calls[0])
        self.assertNotIn("response_format", fake.calls[1])

    def test_classifies_http_400_without_exposing_server_text(self):
        message = _status_message(400, {"error": {"message": "Unsupported response schema: minLength"}})
        self.assertIn("formato da resposta", message)
        self.assertIn("minLength", message)

    def test_redacts_key_from_http_400_detail(self):
        message = _status_message(
            400,
            {"error": {"message": "Bad schema for key secret-test-key"}},
            "secret-test-key",
        )
        self.assertNotIn("secret-test-key", message)
