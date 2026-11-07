import unittest
from datetime import datetime,timezone
import test_core as support
from companion.tools import clock_context


class ClockTests(unittest.TestCase):
    def test_separate_zones_day_boundary_and_unknown(self):
        stamp=datetime(2026,11,5,23,30,tzinfo=timezone.utc).timestamp()
        value=clock_context('Asia/Tokyo',stamp,user_zone='America/New_York')
        self.assertIn('2026-11-06T08:30:00+09:00',value)
        self.assertIn('2026-11-05T18:30:00-05:00',value)
        self.assertIn('role_minus_user_minutes=840',value)
        self.assertIn('user_timezone=unknown',clock_context('UTC',stamp))
    def test_daylight_saving_is_instant_specific(self):
        stamp=datetime(2026,7,5,23,30,tzinfo=timezone.utc).timestamp()
        self.assertIn('role_minus_user_minutes=780',clock_context('Asia/Tokyo',stamp,user_zone='America/New_York'))


class LookupTests(unittest.TestCase):
    setUp=support.CoreTests.setUp
    tearDown=support.CoreTests.tearDown
    event=support.CoreTests.event
    send=support.CoreTests.send
    run_event=support.CoreTests.run_event
    def test_no_permission_no_network_or_model(self):
        self.assertIn('未启用',self.e.command('demo-user','/lookup concert'))
    def test_public_feed_summary_uses_role_and_appends_evidence(self):
        self.c['web_lookup_peers']=['demo-user'];self.c['role_timezone']='Asia/Tokyo';self.c['user_timezone']='America/New_York'
        captured=[];ticks=[]
        class Research:
            def tick(self,now=None):ticks.append(now)
            def context(self,*args):return [dict(title='public concert',url='https://example.com/event',source_published_at=None,source_checked_at=1700000000.)]
        class Model:
            def reply(self,messages):captured.extend(messages);return '有一则活动公告。'
        self.e.research=Research();self.e.model=Model()
        self.run_event(text='查一下最新concert')
        self.assertEqual(len(ticks),1)
        self.assertIn('role_timezone=Asia/Tokyo',captured[0]['content'])
        self.assertIn('https://example.com/event',self.sent[-1][1]);self.assertIn('核验UTC',self.sent[-1][1])
    def test_lookup_rejects_private_query_before_network(self):
        self.c['web_lookup_peers']=['demo-user']
        class Research:
            def tick(self):raise AssertionError('must not fetch')
        self.e.research=Research()
        self.assertIn('私人资料',self.e.command('demo-user','/lookup 密码123456'))
