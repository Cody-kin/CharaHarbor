import base64
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from companion.core import Store,Refused,Engine,load
from companion.media import normalize,geometry
from companion.memory import apply,extract
import test_service as support
png=support.png

GIF=base64.b64decode('R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==')


class MediaTests(unittest.TestCase):
    def test_optional_decoder_is_version_gated_no_install(self):
        with patch('companion.media.sys.platform','linux'),patch('companion.media.sys.version_info',(3,9)):
            with self.assertRaisesRegex(Refused,'python311'):normalize(GIF)
        with patch('companion.media.sys.platform','linux'),patch('companion.media.sys.version_info',(3,11)),patch('companion.media.importlib.metadata.version',return_value='12.0.0'):
            with self.assertRaisesRegex(Refused,'outdated'):normalize(GIF)
    def test_optional_decoder_contract_with_synthetic_output(self):
        def decode(command,**kwargs):
            self.assertEqual(command[1],'-I');self.assertEqual(kwargs['timeout'],5)
            Path(command[-1]).write_bytes(png())
        with patch('companion.media.sys.platform','linux'),patch('companion.media.sys.version_info',(3,11)),patch('companion.media.importlib.metadata.version',return_value='13.0.0'),patch('companion.media.subprocess.run',side_effect=decode):
            result,first=normalize(GIF);self.assertEqual(result,png());self.assertTrue(first)
    def test_malformed_geometry_and_animation_limits(self):
        self.assertEqual(geometry(GIF),('GIF',1,1,1))
        for data in (GIF[:-1],GIF+b'x',GIF[:6]+struct.pack('<HH',4000,4000)+GIF[10:],b'\xff\xd8bad'):
            with self.assertRaises(Refused):normalize(data)
    @unittest.skipUnless(sys.platform=='darwin','requires existing macOS system decoder')
    def test_real_mac_jpeg_and_gif_decode_metadata_removed(self):
        result,first=normalize(GIF);self.assertTrue(result.startswith(b'\x89PNG'));self.assertTrue(first)
        with tempfile.TemporaryDirectory() as directory:
            src=Path(directory)/'input.png';dst=Path(directory)/'output.jpg';src.write_bytes(png())
            subprocess.run(['/usr/bin/sips','-s','format','jpeg',str(src),'--out',str(dst)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            result,first=normalize(dst.read_bytes());self.assertFalse(first)
            self.assertEqual(struct.unpack('>II',result[16:24]),(1,1))
            self.assertNotIn(b'Exif',result)


class NaturalMemoryTests(unittest.TestCase):
    def test_correction_restart_isolation_forgetting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'private';s=Store(root,'synthetic-account')
            apply(s,'one','我喜欢绿茶','source-1')
            apply(s,'two','我喜欢绿茶','source-2')
            apply(s,'one','更正：我喜欢红茶，不是绿茶','source-3')
            self.assertEqual(s.db.execute('SELECT value FROM facts WHERE peer=?',('one',)).fetchall(),[('我喜欢红茶',)])
            s.db.close();s=Store(root,'synthetic-account')
            self.assertEqual(s.db.execute('SELECT value FROM facts WHERE peer=?',('one',)).fetchone()[0],'我喜欢红茶')
            apply(s,'one','忘记我喜欢红茶这件事','source-4')
            self.assertEqual(s.db.execute('SELECT count(*) FROM facts WHERE peer=?',('one',)).fetchone()[0],0)
            self.assertEqual(s.db.execute('SELECT count(*) FROM fact_evidence WHERE peer=?',('one',)).fetchone()[0],0)
            self.assertEqual(s.db.execute('SELECT value FROM facts WHERE peer=?',('two',)).fetchone()[0],'我喜欢绿茶')
            s.db.close()
    def test_natural_explicit_coverage_without_guessing(self):
        for text in ('我去过京都','我学过吉他','我们约定周末散步'):
            self.assertTrue(extract(text),text)
        for text in ('她去过京都','我可能去过京都','在游戏里我去过京都','我喜欢密码123456','我喜欢什么茶？'):
            self.assertEqual(extract(text),[],text)


class MediaServiceTests(unittest.TestCase):
    setUp=support.IntegrationTests.setUp
    tearDown=support.IntegrationTests.tearDown
    @unittest.skipUnless(sys.platform=='darwin','requires existing macOS system decoder')
    def test_gif_first_frame_real_decoder_to_model_and_send_receipt(self):
        self.c['vision_peers']=['demo-user'];self.bridge.image=lambda identity:GIF
        captured=[]
        class Model:
            def reply(self,messages):captured.extend(messages);return '只看到了首帧。'
        self.engine.model=Model()
        self.bridge.add(1,self.now,kind=3);self.service.step()
        self.assertEqual(len(self.bridge.sent),1)
        self.assertIn('首帧',captured[-1]['content'][0]['text'])
        self.assertTrue(captured[-1]['content'][1]['image_url']['url'].startswith('data:image/png'))
    def test_invalid_jpeg_does_not_reserve_or_block_following_text(self):
        self.c['vision_peers']=['demo-user'];self.bridge.image=lambda identity:b'\xff\xd8bad'
        self.bridge.add(1,self.now,kind=3);self.service.step()
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM ops').fetchone()[0],0)
        self.bridge.add(2,self.now,text='继续聊天');self.service.step();self.now+=2;self.service.step()
        self.assertEqual(len(self.bridge.sent),1)


class RestartRecallTests(unittest.TestCase):
    def test_configured_timezone_clock_and_composite_question(self):
        from companion.tools import clock_context
        self.assertIn('2023-11-15T06:13:20+08:00',clock_context('Asia/Shanghai',1700000000.))
        self.assertIn('星期三',clock_context('Asia/Shanghai',1700000000.))
    def test_reopened_engine_receives_corrected_fact_then_forgets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'state';c=load('examples/demo.json');c['auto_memory_peers']=['demo-user']
            s=Store(root,c['account']);apply(s,'demo-user','我喜欢绿茶','s1');apply(s,'demo-user','更正：我喜欢红茶，不是绿茶','s2');s.db.close()
            s=Store(root,c['account']);engine=Engine(c,s);captured=[]
            class Model:
                def reply(self,messages):captured.append(str(messages));return '红茶。'
            engine.model=Model()
            event=dict(id='new',account=c['account'],peer='demo-user',at=1700000000.,kind='text',direction='incoming',group=False,text='我喜欢什么茶？')
            engine.process(event,lambda *args:True,1700000000.)
            self.assertIn('我喜欢红茶',captured[-1]);self.assertNotIn('我喜欢绿茶',captured[-1])
            s.db.execute('INSERT INTO history VALUES (?,?,?,?)',('demo-user',1700000000.,'user','我喜欢红茶'))
            event.update(id='forget-natural',text='忘记我喜欢红茶这件事')
            self.assertEqual(engine.process(event,lambda *args:True,1700000000.),'local_memory_forgotten')
            self.assertEqual(len(captured),1)
            event.update(id='after-delete',text='记忆里还有什么？');engine.process(event,lambda *args:True,1700000001.)
            self.assertNotIn('我喜欢红茶',captured[-1]);s.db.close()
