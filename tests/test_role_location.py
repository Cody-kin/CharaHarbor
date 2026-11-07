import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone
from companion.core import Engine,Store,Refused,load
from companion.roles import location_suggestion,load_profile
from companion.tools import clock_context
import test_onboarding as support


class RoleLocationTests(unittest.TestCase):
    setUp=support.SetupTests.setUp
    tearDown=support.SetupTests.tearDown
    send=support.SetupTests.send
    message=support.SetupTests.message
    ready=support.SetupTests.ready
    def test_sourced_suggestion_requires_confirmation_and_survives_restart(self):
        self.c['role_locations']={'小睦':dict(name='合成东京',timezone='Asia/Tokyo',source='https://example.org/canon',timezone_source='https://www.iana.org/time-zones')}
        for text in ('你好','同意','小睦'):self.message(text)
        self.assertEqual(self.e.flow.row('demo-user')[0],'role_location')
        self.assertNotIn('role_timezone',self.e.flow.row('demo-user')[1])
        self.assertIn('example.org/canon',self.sent[-1][1])
        self.s.db.close();self.s=Store(self.root,self.c['account']);self.e=Engine(self.c,self.s,self.model)
        for text in ('确认地点','安静','被动','确认'):self.message(text)
        self.assertEqual(self.e.flow.row('demo-user')[1]['role_timezone'],'Asia/Tokyo')
        self.message('你那里几点了，我这边呢')
        self.assertIn('role_timezone=Asia/Tokyo',self.model.messages[-1][0]['content'])
        self.assertIn('user_timezone=unknown',self.model.messages[-1][0]['content'])
        self.message('进入陪伴设置');self.message('用户时区 Asia/Shanghai');self.message('保存');self.message('我们差多久')
        self.assertIn('user_timezone=Asia/Shanghai',self.model.messages[-1][0]['content'])

    def test_switch_clears_old_location_scene_and_isolates_memories(self):
        self.ready();self.message('/remember tea=红茶');self.message('小睦独有的合成对话')
        oldkey=self.e.memory_peer('demo-user')
        self.message('进入陪伴设置');self.message('所在地 东京 Asia/Tokyo');self.message('场景 合成练习室');self.message('用户所在地 香港');self.message('用户时区 Asia/Hong_Kong');self.message('保存')
        self.message('进入陪伴设置');self.message('角色 原创')
        draft=self.e.flow.row('demo-user')[2]
        self.assertNotIn('role_timezone',draft);self.assertNotIn('scene',draft)
        self.message('保存');self.assertEqual(self.e.flow.row('demo-user')[0],'settings')
        self.message('所在地 纽约 America/New_York');self.message('保存')
        self.message('新角色的合成问候')
        payload=json.dumps(self.model.messages[-1],ensure_ascii=False)
        self.assertNotIn('红茶',payload);self.assertNotIn('小睦独有',payload);self.assertNotIn('合成练习室',payload)
        self.assertIn('America/New_York',payload);self.assertIn('香港',payload)
        self.assertNotEqual(oldkey,self.e.memory_peer('demo-user'))
        self.message('/remember food=面包')
        self.s.db.close();self.s=Store(self.root,self.c['account']);self.e=Engine(self.c,self.s,self.model)
        self.message('进入陪伴设置');self.message('角色 小睦');self.message('地点未知');self.message('保存');self.message('回来继续聊')
        payload=json.dumps(self.model.messages[-1],ensure_ascii=False)
        self.assertIn('红茶',payload);self.assertNotIn('面包',payload)
        self.assertIn('尚未确认',payload);self.assertNotIn('role_timezone=America/New_York',payload)
        self.message('/forget')
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM facts WHERE peer=?',(oldkey,)).fetchone()[0],0)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM facts').fetchone()[0],1)

    def test_user_override_and_unknown_do_not_guess(self):
        for text in ('你好','同意','小睦','确认地点'):self.message(text)
        self.assertEqual(self.e.flow.row('demo-user')[0],'role_location')
        self.message('所在地 虚构城市 Invalid/Zone')
        self.assertEqual(self.e.flow.row('demo-user')[0],'role_location')
        self.message('地点未知');self.message('温柔');self.message('被动');self.message('确认');self.message('你几点了')
        self.assertNotIn('role_timezone=',self.model.messages[-1][0]['content'])
        self.assertIn('尚未确认',self.model.messages[-1][0]['content'])


class GeographyPolicyTests(unittest.TestCase):
    def test_profile_location_must_have_reviewed_sources(self):
        p,_=load_profile('roles/mutsumi.json')
        self.assertIsNone(location_suggestion(p))
        p['sources'] += [dict(id='synthetic-place',url='https://example.org/canon',status='reviewed'),dict(id='tz',url='https://www.iana.org/time-zones',status='reviewed')]
        p['location']=dict(name='合成纽约',timezone='America/New_York',confidence='verified',source='synthetic-place',timezone_source='tz')
        self.assertEqual(location_suggestion(p)['timezone'],'America/New_York')
        p['sources'][-1]['status']='unreviewed';self.assertIsNone(location_suggestion(p))
        p['sources'][-1]['status']='reviewed';p['location']['timezone']='Invalid/Zone'
        with self.assertRaises(KeyError):location_suggestion(p)
    def test_dst_transition_and_cross_date(self):
        before=datetime(2026,11,1,5,30,tzinfo=timezone.utc).timestamp()
        after=datetime(2026,11,1,6,30,tzinfo=timezone.utc).timestamp()
        self.assertIn('01:30:00-04:00',clock_context('America/New_York',before,user_zone='Asia/Tokyo'))
        self.assertIn('01:30:00-05:00',clock_context('America/New_York',after,user_zone='Asia/Tokyo'))
        self.assertIn('2026-11-06T08:30',clock_context('Asia/Tokyo',datetime(2026,11,5,23,30,tzinfo=timezone.utc).timestamp(),user_zone='America/New_York'))
