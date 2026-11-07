import json
import os
import unittest
from unittest.mock import patch
from companion.core import Model, load, Refused

class Response:
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n):return json.dumps({"choices":[{"message":{"content":"synthetic reply"}}]}).encode()

class Providers(unittest.TestCase):
    def test_payloads_and_endpoint_are_provider_specific(self):
        for provider,key in (("openai","max_completion_tokens"),("deepseek","max_tokens")):
            c=load("examples/demo.json");c.update(provider=provider,model="test-model")
            with patch.dict(os.environ,{"COMPANION_API_KEY":"synthetic-not-a-key"}),patch("urllib.request.build_opener") as opener:
                opener.return_value.open.return_value=Response()
                self.assertEqual(Model(c).reply([dict(role="user",content="synthetic")]),"synthetic reply")
                req=opener.return_value.open.call_args[0][0]
                self.assertEqual(json.loads(req.data)[key],384)
                self.assertIn("api.openai.com" if provider=="openai" else "api.deepseek.com",req.full_url)
                self.assertEqual(opener.return_value.open.call_count,1)
    def test_missing_key_fails_before_network(self):
        c=load("examples/demo.json");c["provider"]="openai"
        with patch.dict(os.environ,{},clear=True),patch("urllib.request.build_opener") as opener:
            with self.assertRaisesRegex(Refused,"missing"):Model(c).reply([])
            opener.assert_not_called()
