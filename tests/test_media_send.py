import hashlib
import tempfile
import unittest
from pathlib import Path
from companion.core import Refused,load
from test_service import FixtureBridge,png


class MediaBridge(FixtureBridge):
    def __init__(self,c):super().__init__(c);self.corrupt=False;self.image_posts=0
    def request(self,path,body=None,key=None,content_type='application/json'):
        if path.endswith('/uploads'):
            return dict(id='synthetic-source',sha256='wrong' if self.corrupt else hashlib.sha256(png()).hexdigest(),byteLength=len(png()))
        if path.endswith('/sends') and body.get('kind')=='image':
            self.image_posts+=1
            return dict(accountId=self.c['account'],threadId='demo-user',kind='send',state='accepted',phase='completed',reason=None,cancelRequested=False,serverMessageId='123',totalBytes=100,completedBytes=100)
        return super().request(path,body,key)


class MediaContractTests(unittest.TestCase):
    def test_verified_source_and_media_job_receipt(self):
        c=load('examples/demo.json');c.update(bridge_server_id='synthetic-server',own_username='synthetic-self',picture_peers=['demo-user'])
        b=MediaBridge(c)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'reaction.png';p.write_bytes(png())
            self.assertTrue(b.send_image('demo-user',p,'synthetic-message'))
        self.assertEqual(b.image_posts,1)
    def test_corrupt_source_never_submits_image(self):
        c=load('examples/demo.json');c.update(bridge_server_id='synthetic-server',own_username='synthetic-self',picture_peers=['demo-user'])
        b=MediaBridge(c);b.corrupt=True
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'reaction.png';p.write_bytes(png())
            with self.assertRaisesRegex(Refused,'source_unverified'):b.send_image('demo-user',p,'synthetic-message')
        self.assertEqual(b.image_posts,0)
