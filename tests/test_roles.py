import tempfile
import unittest
from pathlib import Path
from companion.roles import load_profile,compile_profile,revision_diff
from companion.core import Refused
import test_core as support


class RoleProfileTests(unittest.TestCase):
    def test_reviewed_facts_only_and_plot_point(self):
        profile,prompt=load_profile('roles/mutsumi.json')
        self.assertIn('吉他手',prompt);self.assertIn('不自行触发Mortis',prompt)
        self.assertNotIn('学校、人物关系',prompt)
        self.assertIn('你是谁',prompt)
    def test_reject_unsourced_fact(self):
        p,_=load_profile('roles/mutsumi.json');p['facts'][0]['source']='invented'
        with self.assertRaisesRegex(Refused,'unsourced'):compile_profile(p)
    def test_origin_and_conditional_traits_are_explicit(self):
        p,prompt=load_profile('roles/mutsumi.json')
        self.assertIn('user_defined',prompt);self.assertIn('对方疲惫',prompt)
        self.assertIn('spoiler',str(p.keys()))
        self.assertNotIn('幼年关系细节',prompt)
    def test_incremental_review_does_not_activate_changes(self):
        import copy
        p,_=load_profile('roles/mutsumi.json');next_profile=copy.deepcopy(p)
        next_profile['revision']='test-next';next_profile['traits'][0]['text']='改为更简洁的表达'
        d=revision_diff(p,next_profile)
        self.assertEqual(d['changed'],['traits:care-style']);self.assertEqual(p['revision'],'public-introduction-2')


class ConsentTests(unittest.TestCase):
    setUp=support.CoreTests.setUp
    tearDown=support.CoreTests.tearDown
    event=support.CoreTests.event
    send=support.CoreTests.send
    run_event=support.CoreTests.run_event
    def test_first_notice_once_then_accept_and_exit(self):
        self.c['require_role_consent']=True
        self.assertEqual(self.run_event(),'role_consent_required')
        self.assertEqual(self.run_event(id='again'),'role_consent_required')
        self.assertEqual(len(self.sent),1)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM ops').fetchone()[0],0)
        self.run_event(id='accept',text='/acceptrole')
        self.run_event(id='chat')
        self.assertEqual(len(self.sent),2)
        self.run_event(id='exit',text='/exitrole')
        self.run_event(id='after')
        self.assertEqual(len(self.sent),2)
