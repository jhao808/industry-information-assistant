import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from config import environment

class EnvironmentTests(unittest.TestCase):
    def run_config(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '.env'
            path.write_text('DASHSCOPE_API_KEY=file-test\nBOCHA_API_KEY=Bearer test-search\nLLM_BASE_URL=https://example.com/v1\nLLM_MAIN_MODEL=main-test\n')
            with patch.dict(os.environ, {'DASHSCOPE_API_KEY':'env-test', 'APP_CONFIG_SOURCE':mode}, clear=True), patch.object(environment,'ENV_PATH',path), patch.object(environment,'_loaded',False):
                environment.load_environment()
                self.assertEqual(os.environ['DASHSCOPE_API_KEY'], 'file-test' if mode=='file' else 'env-test')
                self.assertEqual(os.environ['BOCHA_API_KEY'],'test-search')
                self.assertEqual(os.environ['OPENAI_BASE_URL'],'https://example.com/v1')
                self.assertEqual(os.environ['OPENAI_MODEL'],'main-test')
    def test_local(self): self.run_config('file')
    def test_deployment(self): self.run_config('environment')

if __name__ == '__main__': unittest.main()
