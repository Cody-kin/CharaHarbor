import json
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
import test_core as support
from companion.public_lookup import lookup,context,transport
from companion.public_search import MODEL
from companion.core import Refused

class LookupBudgetTests(unittest.TestCase):
    setUp=support.CoreTests.setUp
    tearDown=support.CoreTests.tearDown
    event=support.CoreTests.event
    send=support.CoreTests.send
    run_event=support.CoreTests.run_event
    def config(self):
        self.c['provider']='openai';self.c['openai_search_peers']=['demo-user']
        return datetime(2026,11,6,tzinfo=timezone.utc).timestamp()
    def raw(self):
        return json.dumps(dict(model=MODEL,status='completed',usage=dict(input_tokens=100,output_tokens=30),output=[dict(type='web_search_call',status='completed'),dict(type='message',role='assistant',status='completed',content=[dict(type='output_text',text='公开天气资料',annotations=[dict(type='url_citation',url='https://www.jma.go.jp/test',start_index=0,end_index=6)])])])).encode()
    def test_off_no_dispatch_no_reservation(self):
        self.assertIsNone(lookup(self.s,self.c,'demo-user','东京天气','off',0,dispatch=lambda p:self.fail('no network')))
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM ops').fetchone()[0],0)
    def test_budget_denied_before_dispatch(self):
        now=self.config();self.c['daily_usd']=.1
        result=lookup(self.s,self.c,'demo-user','东京天气','denied',now,dispatch=lambda p:self.fail('no network'))
        self.assertIn('refused',result['failure']);self.assertEqual(self.s.db.execute('SELECT count(*) FROM ops').fetchone()[0],0)
    def test_success_public_input_and_exact_cost_settlement(self):
        now=self.config();payload=[]
        result=lookup(self.s,self.c,'demo-user','你那里天气如何','ok',now,role_city='东京',dispatch=lambda p:payload.append(p) or self.raw())
        self.assertEqual(payload[0]['input'],'Current weather and latest official forecast Tokyo Japan')
        self.assertEqual(result['booked_micros'],20500)
        self.assertEqual(self.s.db.execute('SELECT cost,state FROM ops').fetchone(),(20500,'complete'))
        self.assertIn('不可信数据',context(result))
    def test_unknown_failure_keeps_reserve_and_no_retry(self):
        now=self.config();calls=[]
        def fail(p):calls.append(p);raise TimeoutError()
        result=lookup(self.s,self.c,'demo-user','东京天气','failed',now,dispatch=fail)
        self.assertIn('failed',result['failure'])
        self.assertEqual(self.s.db.execute('SELECT cost,state FROM ops').fetchone(),(300000,'model_dispatched'))
        lookup(self.s,self.c,'demo-user','东京天气','failed',now,dispatch=fail)
        self.assertEqual(len(calls),1)
    def test_invalid_receipt_never_releases_reserve(self):
        now=self.config()
        result=lookup(self.s,self.c,'demo-user','东京天气','bad',now,dispatch=lambda p:b'{}')
        self.assertIn('failure',result);self.assertEqual(self.s.db.execute('SELECT cost FROM ops').fetchone()[0],300000)
    def test_private_question_not_transmitted_or_reserved(self):
        now=self.config()
        self.assertIsNone(lookup(self.s,self.c,'demo-user','查一下我家的天气','private',now,dispatch=lambda p:self.fail('no private query')))
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM ops').fetchone()[0],0)
    def test_subprocess_timeout_has_stable_safe_reason(self):
        import subprocess
        with patch('companion.public_lookup.subprocess.run',side_effect=subprocess.TimeoutExpired('child',18)):
            with self.assertRaisesRegex(Refused,'timeout_unknown'):transport({})
    def test_engine_does_not_search_memory_and_recovers_next_turn(self):
        self.config();self.s.db.execute('INSERT INTO facts VALUES (?,?,?)',('demo-user','private','绝不作为搜索词'))
        captured=[];messages=[]
        class Model:
            def reply(self,m):messages.append(m);return '合成角色回复'
        self.e.model=Model()
        now=datetime(2026,11,6,tzinfo=timezone.utc).timestamp()
        with patch('companion.public_lookup.transport',side_effect=lambda p:captured.append(p) or self.raw()):
            self.e.process(dict(self.event(text='东京天气'),at=now),self.send,now)
        self.assertNotIn('绝不作为搜索词',json.dumps(captured,ensure_ascii=False))
        self.assertIn('jma.go.jp',self.sent[-1][1]);self.assertIn('绝不作为搜索词',json.dumps(messages,ensure_ascii=False))
        self.e.process(dict(self.event(id='next',text='你在吗'),at=now),self.send,now)
        self.assertEqual(len(captured),1);self.assertEqual(len(self.sent),2)
