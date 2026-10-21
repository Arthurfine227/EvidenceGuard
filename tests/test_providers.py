import io
import json
import unittest
from unittest.mock import patch

from evidencepilot.providers import OpenAICompatibleProvider, ProviderError


class ProviderTests(unittest.TestCase):
    def test_native_tool_call_preserves_id_and_history(self):
        provider = OpenAICompatibleProvider('test-key', 'deepseek-flash', 'https://api.deepseek.com')
        assistant = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call_1', 'type': 'function', 'function': {'name': 'read_document', 'arguments': '{"id":"juniper"}'}}]}
        response = {'model': 'deepseek-flash', 'choices': [{'message': assistant, 'finish_reason': 'tool_calls'}], 'usage': {'total_tokens': 42}}
        history = [{'role': 'user', 'content': 'Read Juniper'}]
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result = provider.complete_tools(history, [], max_tokens=128)
        self.assertEqual(result['tool_calls'][0]['id'], 'call_1')
        body = json.loads(call.call_args.args[0].data)
        self.assertEqual(body['messages'], history)
        self.assertNotIn('response_format', body)
        self.assertEqual(provider.request_metadata[0]['usage']['total_tokens'], 42)

    def setUp(self):
        self.provider = OpenAICompatibleProvider('test-key', 'deepseek-v4-flash', 'https://api.deepseek.com')

    def test_deepseek_request_and_structured_response(self):
        response = {'choices': [{'message': {'content': '{"status":"ok"}'}}]}
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as call:
            self.assertEqual(self.provider.complete_json('Return JSON', 'Check'), {'status': 'ok'})
        body = json.loads(call.call_args.args[0].data)
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['max_tokens'], 2048)

    def test_timeout_has_specific_message(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError):
            with self.assertRaisesRegex(ProviderError, 'timed out after 60s'):
                self.provider.complete_json('JSON', 'Check')

    def test_invalid_json_has_specific_message(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'not-json')):
            with self.assertRaisesRegex(ProviderError, 'not valid JSON'):
                self.provider.complete_json('JSON', 'Check')
