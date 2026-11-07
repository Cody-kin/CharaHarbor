import tempfile
import unittest
from pathlib import Path
from companion.core import Engine,Store,Refused,load
from companion.onboarding import Onboarding


class CountingModel:
    def __init__(self):self.messages=[]
    def reply(self,m):self.messages.append(m);return 'synthetic-role-reply'


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'state'
        self.c=load('examples/demo.json');self.c.update(onboarding_enabled=True,settings_word='进入陪伴设置',role_choices={'小睦':'角色档案：若叶睦，安静而关心人。','原创':'原创角色：温柔。'})
        self.c['peers'].append('second-user');self.s=Store(self.root,self.c['account'])
        self.model=CountingModel();self.e=Engine(self.c,self.s,self.model);self.sent=[];self.n=0
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def send(self,*args):self.sent.append(args);return True
    def message(self,text,peer='demo-user'):
        self.n+=1
        return self.e.process(dict(id='s'+str(self.n),account=self.c['account'],peer=peer,kind='text',direction='incoming',group=False,at=1700000000.,text=text),self.send,1700000000.)
    def ready(self,interaction='被动'):
        for text in ('你好','同意','小睦','地点未知','简短温柔',interaction,'确认'):self.message(text)
        self.assertEqual(self.e.flow.row('demo-user')[0],'ready')
    def test_first_consent_then_steps_no_model_before_ready(self):
        self.ready()
        self.assertEqual(self.model.messages,[])
        self.assertEqual(len(self.sent),7)
        self.message('你是谁')
        self.assertIn('若叶睦',self.model.messages[-1][0]['content'])
        self.assertIn('简短温柔',self.model.messages[-1][0]['content'])
    def test_decline_stays_quiet_and_can_reopen(self):
        self.message('你好');self.message('不同意');count=len(self.sent)
        self.message('你好');self.message('/acceptrole')
        self.assertEqual(len(self.sent),count);self.assertFalse(self.model.messages)
        self.message('进入陪伴设置');self.assertEqual(self.e.flow.row('demo-user')[0],'await_consent')
    def test_restart_keeps_exact_step_and_draft(self):
        for text in ('你好','同意','小睦'):self.message(text)
        self.s.db.close();self.s=Store(self.root,self.c['account']);self.e=Engine(self.c,self.s,self.model)
        self.assertEqual(self.e.flow.row('demo-user')[0],'role_location')
        self.message('地点未知');self.message('安静');self.message('被动');self.message('确认')
        self.assertEqual(self.e.flow.row('demo-user')[1]['role'],'小睦')
    def test_safe_word_exact_not_substring_or_quote(self):
        self.ready()
        for text in ('我记得进入陪伴设置这几个字','「进入陪伴设置」'):
            self.message(text);self.assertEqual(self.e.flow.row('demo-user')[0],'ready')
        self.message('进入陪伴设置');self.assertEqual(self.e.flow.row('demo-user')[0],'settings')
    def test_settings_save_tasks_timezone_frequency_and_cancel(self):
        self.ready();self.message('进入陪伴设置');self.message('随机 30 60');self.message('定时 09:30 早安');self.message('时区 Asia/Tokyo')
        self.assertEqual(self.e.flow.tasks(),[])
        self.message('保存');tasks=self.e.flow.tasks()
        self.assertEqual(len(tasks),2);self.assertTrue(all(t['peer']=='demo-user' for t in tasks));self.assertEqual(tasks[0]['timezone'],'Asia/Tokyo')
        self.message('进入陪伴设置');self.message('角色 原创');self.message('取消')
        self.assertEqual(self.e.flow.row('demo-user')[1]['role'],'小睦')
    def test_peer_isolation_and_no_proactive_before_ready(self):
        self.ready('随机 5 10')
        self.message('你好',peer='second-user')
        self.assertEqual(self.e.flow.row('second-user')[0],'await_consent')
        self.assertEqual(self.e.flow.row('demo-user')[0],'ready')
        self.assertTrue(all(t['peer']=='demo-user' for t in self.e.flow.tasks()))
    def test_exit_revokes_generation_and_proactive(self):
        self.ready('随机 5 10');self.message('/exitrole');count=len(self.sent)
        self.message('你在吗')
        self.assertEqual(len(self.sent),count);self.assertFalse(self.e.flow.tasks())
        self.assertEqual(self.s.control('demo-user')[0],1)
    def test_unknown_setup_send_no_retry(self):
        self.n+=1
        event=dict(id='unknown',account=self.c['account'],peer='demo-user',kind='text',direction='incoming',group=False,at=1700000000.,text='你好')
        with self.assertRaisesRegex(Refused,'uncertain'):self.e.process(event,lambda *a:False,1700000000.)
        with self.assertRaisesRegex(Refused,'manual_review'):self.message('你好')
        self.assertFalse(self.sent);self.assertFalse(self.model.messages)
    def test_start_offer_only_explicit_target_and_once(self):
        self.e.flow.offer('demo-user',self.send);self.e.flow.offer('demo-user',self.send)
        self.assertEqual(len(self.sent),1)
        with self.assertRaisesRegex(Refused,'scope'):self.e.flow.offer('stranger',self.send)
    def test_invalid_frequency_does_not_change_live_settings(self):
        self.ready();self.message('进入陪伴设置');self.message('随机 0 1');self.message('保存')
        self.assertFalse(self.e.flow.row('demo-user')[1]['proactive']);self.assertEqual(self.e.flow.tasks(),[])
    def test_pause_about_does_not_resume(self):
        self.ready('随机 5 10');self.message('/pause');self.message('/about')
        self.assertEqual(self.s.control('demo-user')[0],1)
    def test_recovery_requires_scoped_existing_bridge_receipt(self):
        self.e.flow.transition
        with self.assertRaises(Refused):self.e.flow.offer('demo-user',lambda *a:False)
        identity=self.s.db.execute("SELECT id FROM setup_events WHERE state='pending'").fetchone()[0]
        class Lookup:
            def lookup_send(_self,key):return dict(accountId=self.c['account'],destination='demo-user',state='accepted',serverId='123',errorCode=None)
        self.assertEqual(self.e.flow.recover(identity,Lookup()),'setup_recovered_without_resending')
        self.assertEqual(self.e.flow.row('demo-user')[0],'await_consent');self.assertFalse(self.sent)
    def test_recovery_wrong_peer_stays_pending(self):
        with self.assertRaises(Refused):self.e.flow.offer('demo-user',lambda *a:False)
        identity=self.s.db.execute("SELECT id FROM setup_events WHERE state='pending'").fetchone()[0]
        class Lookup:
            def lookup_send(_self,key):return dict(accountId=self.c['account'],destination='stranger',state='accepted',serverId='123',errorCode=None)
        with self.assertRaises(Refused):self.e.flow.recover(identity,Lookup())
        self.assertEqual(self.s.db.execute('SELECT state FROM setup_events').fetchone()[0],'pending')
    def test_scene_is_fictional_and_separate_from_user_facts(self):
        self.ready();self.message('进入陪伴设置');self.message('场景 与乐队成员在练习室排练');self.message('保存')
        self.message('你在做什么')
        self.assertIn('角色世界虚构场景',self.model.messages[-1][0]['content'])
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM facts').fetchone()[0],0)
