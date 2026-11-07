import importlib.util
import json
import os
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('launcher',Path(__file__).resolve().parents[1]/'launch.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_demo_configuration_exclusive_and_no_secret(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json';answers=iter(['','原创守望者','Asia/Shanghai','Asia/Tokyo'])
            launcher.configure(p,lambda label:next(answers))
            data=json.loads(p.read_text(encoding='utf-8'))
            self.assertEqual(data['mode'],'demo');self.assertNotIn('api_key',data)
            if os.name!='nt':self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(SystemExit):launcher.configure(p)

    def test_live_provider_and_images_are_independent(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json'
            answers=iter(['live','原创角色','UTC','Asia/Tokyo','deepseek','chosen-chat-model','synthetic-account','synthetic-self','synthetic-server','','synthetic-peer','yes','chosen-image-model','0.2'])
            launcher.configure(p,lambda label:next(answers));c=json.loads(p.read_text(encoding='utf-8'))
            self.assertEqual(c['provider'],'deepseek');self.assertEqual(c['image_generation']['provider'],'openai')
            self.assertEqual(c['image_generation']['model'],'chosen-image-model')
            self.assertFalse(c['auto_memory_peers']);self.assertFalse(c.get('tasks'))

    def test_demo_redirected_legacy_console_encoding(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            event=dict(id='encoding-test',account='demo-account',peer='demo-user',
                       at=__import__('time').time(),kind='text',direction='incoming',group=False,text='今天有点累。')
            env=dict(os.environ, PYTHONIOENCODING='cp1252')
            result=subprocess.run([sys.executable,'-m','companion','run','--state',str(Path(td)/'state')],
                cwd=root,input=json.dumps(event).encode('utf-8'),capture_output=True,env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            replies=[json.loads(line) for line in result.stdout.decode('utf-8').splitlines()]
            self.assertTrue(any(r.get('demo_only') for r in replies))
