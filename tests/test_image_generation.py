import base64
import json
import os
import unittest
from unittest.mock import patch
import test_core as support
from companion.core import Engine, Model, Refused, load, validate
from companion.image_generation import ImageProvider


class ImageGeneration(unittest.TestCase):
    tearDown=support.CoreTests.tearDown
    event=support.CoreTests.event
    run_event=support.CoreTests.run_event
    send=support.CoreTests.send
    def setUp(self):
        support.CoreTests.setUp(self)
        self.c.update(picture_peers=['demo-user'],image_generation={'provider':'mock','model':'synthetic','peers':['demo-user'],'reserve_usd':.1})
        self.e=Engine(self.c,self.s);self.pictures=[]
        self.e.picture_send=lambda peer,path,identity:self.pictures.append((peer,path.read_bytes(),identity)) or True

    def test_generation_uses_shared_budget_and_no_text_model(self):
        with patch.object(self.e.model,'reply',side_effect=AssertionError('text model must not generate images')):
            self.assertEqual(self.run_event(text='/image 原创吉他插画'),'generated_picture_complete')
        self.assertEqual(len(self.pictures),1)
        self.assertEqual(self.s.db.execute('SELECT cost,state FROM ops').fetchone(),(100000,'complete'))
        self.assertFalse(list(self.root.glob('generated-*')))
        with self.assertRaisesRegex(Refused,'duplicate'):self.run_event(text='/image 原创吉他插画')

    def test_generation_failure_continues_text_without_retry(self):
        with patch.object(ImageProvider,'generate',side_effect=TimeoutError()):self.run_event(text='/image 合成图片')
        self.assertFalse(self.pictures);self.assertIn('没有拿到',self.sent[0][1])
        self.run_event(id='next',text='你好')
        self.assertEqual(len(self.sent),2)

    def test_unknown_media_send_is_not_replayed(self):
        self.e.picture_send=lambda *args:False
        with self.assertRaisesRegex(Refused,'uncertain'):self.run_event(text='/image 合成图')
        self.assertEqual(self.s.db.execute('SELECT state FROM ops').fetchone()[0],'submitting')
        with self.assertRaisesRegex(Refused,'duplicate'):self.run_event(text='/image 合成图')

    def test_scope_and_reservation_validation(self):
        self.c['image_generation']['peers']=['stranger']
        with self.assertRaisesRegex(Refused,'scope'):validate(self.c)


class IndependentCredentials(unittest.TestCase):
    def test_only_image_key_reaches_image_endpoint(self):
        data=ImageProvider({'provider':'mock'}).generate('synthetic')
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps({'data':[{'b64_json':base64.b64encode(data).decode()}]}).encode()
        def opened(request,timeout):
            self.assertEqual(request.full_url,'https://api.openai.com/v1/images/generations')
            self.assertEqual(request.get_header('Authorization'),'Bearer synthetic-image-key')
            self.assertEqual(json.loads(request.data)['model'],'configured-image-model')
            return Response()
        with patch.dict(os.environ,{'COMPANION_API_KEY':'synthetic-chat-key','COMPANION_IMAGE_API_KEY':'synthetic-image-key'}),patch('urllib.request.OpenerDirector.open',side_effect=opened):
            self.assertEqual(ImageProvider({'provider':'openai','model':'configured-image-model'}).generate('原创风景'),data)

    def test_url_results_are_not_fetched(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b'{"data":[{"url":"https://untrusted.invalid/image"}]}'
        with patch.dict(os.environ,{'COMPANION_IMAGE_API_KEY':'synthetic'}),patch('urllib.request.OpenerDirector.open',return_value=Response()) as call:
            with self.assertRaisesRegex(Refused,'base64'):ImageProvider({'provider':'openai','model':'configured'}).generate('test')
            self.assertEqual(call.call_count,1)
