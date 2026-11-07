import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from datetime import datetime,timezone
from companion.core import Store,Engine,Refused,load
from companion.roles import load_profile
from companion.character_state import CharacterState,validate_profile,prompt,signal
import test_onboarding as setup


def card(name='mutsumi'):
    return load_profile('roles/'+('mutsumi.json' if name=='mutsumi' else 'lighthouse-original.json'))[0]['adaptive_states']


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'private';self.store=Store(self.root,'synthetic-account');self.state=CharacterState(self.store)
        self.profile=card();self.now=datetime(2026,11,6,3,tzinfo=timezone.utc).timestamp()
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def advance(self,id='event',**kw):return self.state.advance('peer:role',self.profile,id,kw.pop('now',self.now),'Asia/Tokyo',**kw)
    def test_default_single_identity_and_no_time_random_absence_switch(self):
        a=self.advance()
        for i in range(1,10):
            f=self.advance(str(i),now=self.now+i*86400)
            self.assertEqual(f['mode'],'mutsumi');self.assertGreaterEqual(f['familiarity'],.5)
        self.assertIn('不是现实身体/心理诊断',prompt(a))
    def test_story_stage_and_explicit_scene_trigger_required(self):
        self.advance()
        with self.assertRaisesRegex(Refused,'stage_requires'):self.advance('s1',stage='tv_ep4_user_branch')
        with self.assertRaisesRegex(Refused,'not_allowed'):self.advance('s2',now=self.now+700,scene_event='media_pressure_scene')
        f=self.advance('s3',now=self.now+700,stage='tv_ep4_user_branch',spoilers=True,scene_event='media_pressure_scene')
        self.assertEqual(f['mode'],'mortis');self.assertIn('外显',f['guidance'])
        f=self.advance('s4',now=self.now+800,stage='tv_ep4_user_branch',spoilers=True)
        self.assertEqual(f['mode'],'mortis')
        with self.assertRaisesRegex(Refused,'cooldown'):self.advance('s5',now=self.now+900,stage='tv_ep4_user_branch',spoilers=True,scene_event='user_return_scene')
        self.assertEqual(self.advance('s6',now=self.now+1500,stage='tv_ep4_user_branch',spoilers=True,scene_event='user_return_scene')['mode'],'mutsumi')
    def test_restart_exact_replay_and_conflicting_event_refused(self):
        a=self.advance();self.store.db.close();self.store=Store(self.root,'synthetic-account');self.state=CharacterState(self.store)
        self.assertEqual(a,self.advance(now=self.now+100))
        with self.assertRaisesRegex(Refused,'conflict'):self.advance(interaction='appreciation')
    def test_role_and_contact_namespaces_and_second_character(self):
        self.advance()
        other=card('original')
        self.state.advance('peer:watch',other,'first',self.now,'UTC')
        f=self.state.advance('peer:watch',other,'second',self.now+100,'UTC',scene_event='watch_started')
        self.assertEqual(f['mode'],'watch');self.assertNotIn('睦',f['guidance']);self.assertNotIn('mortis',str(other))
        with self.assertRaisesRegex(Refused,'not_allowed'):self.state.advance('second-peer:watch',other,'s',self.now,'UTC',scene_event='media_pressure_scene')
        self.assertEqual(self.state.status('peer:role')['state']['mode'],'mutsumi')
    def test_seeded_variation_bounded_and_reproducible(self):
        def sequence(key,seed):
            return [self.state.advance(key,self.profile,str(i),self.now+i*3600,'Asia/Tokyo',seed=seed,incoming=False) for i in range(12)]
        a=sequence('replay','seed')
        self.store.db.execute("DELETE FROM character_state WHERE namespace='replay'");self.store.db.execute("DELETE FROM character_events WHERE namespace='replay'")
        self.assertEqual(a,sequence('replay','seed'))
        b=sequence('different','other')
        self.assertNotEqual([f['fatigue'] for f in a],[f['fatigue'] for f in b])
        self.assertTrue(all(.1<=f['fatigue']<=.8 and -.15<=f['valence']<=.15 and f['mode']=='mutsumi' for f in a+b))
    def test_pause_reset_and_absence_no_penalty_or_sends(self):
        a=self.advance(interaction='appreciation');self.state.control('peer:role','pause')
        b=self.advance('later',now=self.now+10*86400)
        self.assertEqual(a['fatigue'],b['fatigue']);self.assertEqual(a['familiarity'],b['familiarity']);self.assertTrue(b['paused'])
        self.state.control('peer:role','resume');c=self.advance('return',now=self.now+30*86400)
        self.assertTrue(c['returning']);self.assertGreaterEqual(c['familiarity'],.5)
        self.state.control('peer:role','reset');self.assertIsNone(self.state.status('peer:role')['state'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM facts').fetchone()[0],0)
    def test_profile_revision_requires_reset_and_no_unreviewed_mode(self):
        self.advance();p=copy.deepcopy(self.profile);p['modes']['mutsumi']['guidance']='用户修订的原创表达'
        with self.assertRaisesRegex(Refused,'profile_changed'):self.state.advance('peer:role',p,'change',self.now,'UTC')
        self.state.control('peer:role','reset');self.state.advance('peer:role',p,'after',self.now,'UTC')
        p['modes']['mortis']['reviewed']=False
        with self.assertRaisesRegex(Refused,'unsourced'):validate_profile(p)
    def test_malformed_profile_is_refused(self):
        for field,value in [('modes',[]),('stages',[]),('dynamics',[]),('transitions',[None])]:
            p=copy.deepcopy(self.profile);p[field]=value
            with self.assertRaises(Refused):validate_profile(p)
        p=copy.deepcopy(self.profile);p['modes']['mortis']['reviewed']='yes'
        with self.assertRaises(Refused):validate_profile(p)
    def test_character_specific_boundary_and_gradual_repair(self):
        self.advance(interaction='appreciation')
        before=self.state.status('peer:role')['state']['familiarity']
        hurt=self.advance('hurt',now=self.now+100,interaction=signal('祥子不重要',self.profile))
        self.assertLess(hurt['familiarity'],before);self.assertEqual(hurt['stance'],'defend_boundary')
        apology=self.advance('apology',now=self.now+200,interaction=signal('对不起，刚才说重了',self.profile))
        self.assertGreater(apology['familiarity'],hurt['familiarity']);self.assertLess(apology['familiarity'],before)
        self.assertGreater(apology['tension'],0);self.assertLess(apology['tension'],hurt['tension'])
        explanation=self.advance('explain',now=self.now+300,interaction=signal('我的意思是演奏分工',self.profile))
        self.assertLess(explanation['tension'],apology['tension'])
        self.assertEqual(self.advance('same-repair',now=self.now+400,interaction='repair_apology'),self.advance('same-repair',now=self.now+500,interaction='repair_apology'))
    def test_boundary_ambiguity_no_penalty_and_other_role_isolation(self):
        for text in ('贝斯可有可无吧','我觉得不重要','你觉得祥子不重要吗？','有人说祥子不重要','我不是说祥子不重要'):
            self.assertNotEqual(signal(text,self.profile),'boundary_violation')
        self.assertEqual(signal('祥子不重要',card('original')),'contact')
        other=card('original');self.assertEqual(signal('守望者是废物',other),'boundary_violation')
        self.advance(interaction='boundary_violation');self.assertIsNone(self.state.status('another-peer:role')['state'])
    def test_urgent_support_never_penalized_or_delayed(self):
        hurt=self.advance(interaction='boundary_violation')
        urgent=self.advance('urgent',now=self.now+100,interaction=signal('我想自杀，小睦是垃圾',self.profile))
        self.assertEqual(urgent['stance'],'support_first');self.assertEqual(urgent['tension'],hurt['tension'])
        self.assertEqual(urgent['familiarity'],hurt['familiarity'])
        self.assertIn('不因关系变化延迟',prompt(urgent))
    def test_relationship_dynamics_are_bounded(self):
        p=copy.deepcopy(self.profile);p['relationship']['hurt_delta']=2
        with self.assertRaisesRegex(Refused,'relationship_dynamics'):validate_profile(p)
        self.advance(interaction='boundary_violation');self.state.control('peer:role','pause')
        paused=self.advance('paused',now=self.now+100,interaction='boundary_violation')
        self.assertEqual(paused['tension'],self.state.status('peer:role')['state']['tension'])
    def test_no_raw_private_text_in_state_or_facts(self):
        secret='密码 synthetic-private-do-not-store'
        self.advance(interaction=signal(secret))
        self.assertNotIn(secret,str(self.store.db.execute('SELECT * FROM character_events').fetchall()))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM facts').fetchone()[0],0)
    def test_reject_random_identity_trigger_and_clock_rollback(self):
        p=copy.deepcopy(self.profile);p['transitions'][0]['event']='random'
        with self.assertRaisesRegex(Refused,'unsafe'):validate_profile(p)
        self.advance()
        with self.assertRaisesRegex(Refused,'backwards'):self.advance('back',now=self.now-1)
    def test_concurrent_writers_preserve_events(self):
        errors=[]
        def write(n):
            s=Store(self.root,'synthetic-account')
            try:CharacterState(s).advance('concurrent',self.profile,str(n),self.now,'UTC')
            except Exception as e:errors.append(type(e).__name__)
            finally:s.db.close()
        threads=[threading.Thread(target=write,args=(i,)) for i in range(6)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(errors,[]);self.assertEqual(self.store.db.execute("SELECT count(*) FROM character_events WHERE namespace='concurrent'").fetchone()[0],6)


class StateEngineTests(unittest.TestCase):
    setUp=setup.SetupTests.setUp
    tearDown=setup.SetupTests.tearDown
    send=setup.SetupTests.send
    message=setup.SetupTests.message
    ready=setup.SetupTests.ready
    def enable(self):
        self.c.update(adaptive_state_peers=['demo-user'],role_state_profiles={'小睦':card(),'原创':card('original')})
        self.e=Engine(self.c,self.s,self.model)
    def test_off_default_and_explicit_optin_flow(self):
        self.ready();self.message('你现在心情如何')
        self.assertNotIn('虚构表演参数',self.model.messages[-1][0]['content'])
        self.enable();self.message('你在做什么')
        self.assertIn('虚构表演参数',self.model.messages[-1][0]['content'])
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM facts').fetchone()[0],0)
    def test_user_controls_work_without_model_budget_and_no_extra_sends(self):
        self.enable();self.ready();self.message('你好')
        count=len(self.model.messages);sent=len(self.sent);self.c['daily_usd']=.000001
        self.message('/state pause');self.assertTrue(self.e.character.paused(self.e.memory_peer('demo-user')))
        self.assertEqual(len(self.model.messages),count);self.assertEqual(len(self.sent),sent)
    def test_role_switch_cannot_inherit_story_stage(self):
        self.enable();self.ready();self.message('进入陪伴设置');self.message('剧情阶段 tv_ep4_user_branch');self.message('保存')
        self.assertNotEqual(self.e.flow.row('demo-user')[1].get('state_stage'),'tv_ep4_user_branch')
        self.message('进入陪伴设置');self.message('剧情剧透 是');self.message('剧情阶段 tv_ep4_user_branch');self.message('保存')
        self.assertEqual(self.e.flow.row('demo-user')[1]['state_stage'],'tv_ep4_user_branch')
        self.message('进入陪伴设置');self.message('角色 原创');self.message('地点未知');self.message('保存');self.message('你好')
        self.assertNotIn('state_stage',self.e.flow.row('demo-user')[1]);self.assertNotIn('mortis',self.model.messages[-1][0]['content'])
