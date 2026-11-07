import unittest
from companion.expressions import context,constrain,policy,validate
from companion.core import Refused
from companion.roles import load_profile
import test_core as support


class Expressions(unittest.TestCase):
    def setUp(self):self.p=load_profile('roles/mutsumi.json')[0]['expressions']
    def test_two_role_profiles_and_moods_are_distinct(self):
        other=load_profile('roles/lighthouse-original.json')[0]['expressions']
        self.assertIn('TvT',context(self.p,[]));self.assertNotIn('TvT',context(other,[]))
        self.assertIn('轻微难过',context(self.p,[]));self.assertIn('安心',context(other,[]))
    def test_no_forced_expression_and_bounded_repeat(self):
        self.assertEqual(constrain('我在。',self.p,[]),'我在。')
        self.assertEqual(constrain('我在 TvT TvT',self.p,[]).count('TvT'),1)
        recent=[('assistant','先休息吧 TvT'),('user','嗯')]
        self.assertFalse(policy(self.p,recent)['allowed'])
        self.assertNotIn('TvT',constrain('陪你 TvT',self.p,recent))
        self.assertTrue(policy(self.p,[('assistant','平静')]*7+[('assistant','TvT')])['allowed'])
    def test_urgent_disabled_and_invalid_configuration(self):
        self.assertFalse(policy(self.p,[],urgent=True)['allowed'])
        self.assertEqual(constrain('请先联系现实中的人 TvT',self.p,[],urgent=True),'请先联系现实中的人')
        for change in ({'window':True},{'maximum':99},{'moods':{'x':['bad\ntext']}}):
            with self.assertRaises(Refused):validate({**self.p,**change})
    def test_nested_examples_not_corrupted(self):
        p={**self.p,'moods':{'悲伤':['TvT','(TvT)']}}
        self.assertEqual(constrain('嗯 (TvT) TvT',p,[]),'嗯 (TvT)')


class ExpressionIntegration(unittest.TestCase):
    setUp=support.CoreTests.setUp
    tearDown=support.CoreTests.tearDown
    event=support.CoreTests.event
    send=support.CoreTests.send
    run_event=support.CoreTests.run_event
    def test_real_engine_applies_profile_and_recent_history(self):
        self.c['role_name']='reserved'
        self.c['role_expression_profiles']={'reserved':load_profile('roles/mutsumi.json')[0]['expressions']}
        prompts=[]
        class Model:
            def reply(self,messages):prompts.append(messages[0]['content']);return '我在 TvT TvT'
        self.e.model=Model()
        self.run_event()
        self.run_event(id='next')
        self.assertEqual(self.sent[0][1].count('TvT'),1)
        self.assertNotIn('TvT',self.sent[1][1])
        self.assertIn('颜文字偏好',prompts[0]);self.assertIn('"allowed": false',prompts[1])
