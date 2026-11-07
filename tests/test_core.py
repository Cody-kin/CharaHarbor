import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from companion.core import Engine, Model, NoRedirect, Refused, Store, load, validate
from companion.__main__ import Lock


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/"private"
        self.c=load("examples/demo.json")
        self.s=Store(self.root,self.c["account"])
        self.e=Engine(self.c,self.s)
        self.sent=[]
        self.now=1700000000.
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def event(self,id="one",peer="demo-user",text="你好"):
        return dict(id=id,account="demo-account",peer=peer,kind="text",direction="incoming",group=False,at=self.now,text=text)
    def send(self,*v):self.sent.append(v);return True
    def run_event(self,**kw):return self.e.process(self.event(**kw),self.send,self.now)
    def test_reply_and_duplicate(self):
        self.run_event()
        with self.assertRaisesRegex(Refused,"duplicate"):self.run_event()
        self.assertEqual(len(self.sent),1)
    def test_scope_and_group_and_age(self):
        for update in (dict(peer="stranger"),dict(account="other"),dict(group=True),dict(at=self.now-121),dict(kind="image"),dict(direction="outgoing")):
            v=self.event();v.update(update)
            with self.assertRaises(Refused):self.e.process(v,self.send,self.now)
        self.assertEqual(self.sent,[])
    def test_budget_no_model_dispatch(self):
        self.c["daily_usd"]=.02;self.c["reserve_usd"]=.02
        self.run_event()
        with self.assertRaisesRegex(Refused,"budget"):self.run_event(id="two")
        self.assertEqual(len(self.sent),1)
    def test_uncertain_send_no_retry_restart(self):
        with self.assertRaisesRegex(Refused,"uncertain"):
            self.e.process(self.event(),lambda *a:False,self.now)
        self.s.db.close();self.s=Store(self.root,self.c["account"]);self.e=Engine(self.c,self.s)
        with self.assertRaisesRegex(Refused,"duplicate"):self.run_event()
        self.assertEqual(self.s.db.execute("SELECT state FROM ops").fetchone()[0],"submitting")
    def test_model_timeout_preserves_reservation(self):
        class Broken:
            def reply(self,m):raise TimeoutError()
        self.e.model=Broken()
        with self.assertRaises(TimeoutError):self.run_event()
        self.assertEqual(self.s.db.execute("SELECT state,cost FROM ops").fetchone(),("model_dispatched",20000))
        self.assertFalse(self.sent)
    def test_memory_correction_deletion_isolation(self):
        self.c["peers"].append("other")
        self.run_event(text="/remember 喜欢=绿茶")
        self.run_event(id="two",text="/remember 喜欢=红茶")
        self.run_event(id="three",peer="other",text="/memory")
        self.assertEqual(self.sent[-1][1],"{}")
        self.run_event(id="four",text="/memory")
        self.assertIn("红茶",self.sent[-1][1]);self.assertNotIn("绿茶",self.sent[-1][1])
        self.run_event(id="five",text="/forget")
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM facts").fetchone()[0],0)
    def test_credentials_not_explicitly_stored(self):
        self.run_event(text="/remember api_key=synthetic")
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM facts").fetchone()[0],0)
    def test_proactive_pause_unanswered(self):
        self.run_event(text="/pause")
        with self.assertRaisesRegex(Refused,"paused"):self.e.process(self.event("t"),self.send,self.now,proactive=True)
        self.run_event(id="resume",text="/resume")
        self.e.process(self.event("p"),self.send,self.now,proactive=True)
        with self.assertRaisesRegex(Refused,"unanswered"):self.e.process(self.event("p2"),self.send,self.now,proactive=True)
        self.run_event(id="reply")
        self.e.process(self.event("p3"),self.send,self.now,proactive=True)
    def test_random_schedule_persists_and_fires_once(self):
        self.c["tasks"]=[dict(id="r",kind="random",peer="demo-user",prompt="关心近况",min_seconds=300,max_seconds=300)]
        self.e.tick(self.send,self.now)
        self.assertFalse(self.sent)
        self.e.tick(self.send,self.now+300)
        self.e.tick(self.send,self.now+300)
        self.assertEqual(len(self.sent),1)
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM ops").fetchone()[0],1)
    def test_daily_timezone_schedule(self):
        self.c["tasks"]=[dict(id="d",kind="daily",peer="demo-user",prompt="问候",at="09:30")]
        self.e.tick(self.send,self.now)
        due=self.s.db.execute("SELECT next FROM schedules").fetchone()[0]
        from datetime import datetime
        from zoneinfo import ZoneInfo
        self.assertEqual(datetime.fromtimestamp(due,ZoneInfo("Asia/Shanghai")).strftime("%H:%M"),"09:30")
        self.assertGreater(due,self.now)
    def test_account_database_cannot_be_reused(self):
        with self.assertRaisesRegex(Refused,"scope"):Store(self.root,"foreign")
        self.assertEqual(self.s.db.execute("SELECT account FROM scope").fetchall(),[(self.c["account"],)])
        reopened=Store(self.root,self.c["account"]);reopened.db.close()
    def test_lock_excludes_second_worker(self):
        with Lock(self.root):
            with self.assertRaises(Refused):
                with Lock(self.root):pass
    def test_hourly_limit(self):
        self.c["hourly_limit"]=1
        self.run_event()
        with self.assertRaisesRegex(Refused,"rate_limit"):self.run_event(id="two")
    def test_invalid_configuration(self):
        for patch in (dict(provider="random"),dict(daily_usd=float('nan')),dict(peers=["x@chatroom"]),dict(mode="live"),dict(history_turns=99)):
            c=copy.deepcopy(self.c);c.update(patch)
            with self.assertRaises(Refused):validate(c)
    def test_redirect_rejected(self):
        with self.assertRaisesRegex(Refused,"redirect"):NoRedirect().redirect_request(None,None,None,None,None,None)
    def test_history_expiry_and_bounded_context(self):
        self.c["history_turns"]=1
        self.run_event()
        self.run_event(id="two")
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM history").fetchone()[0],2)
        self.s.db.execute("UPDATE history SET at=?",(self.now-90000,))
        self.run_event(id="three")
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM history WHERE at<?",(self.now-86400,)).fetchone()[0],0)
    def test_pause_and_forget_work_after_budget_exhaustion(self):
        self.c["hourly_limit"]=1
        self.run_event(text="/remember preference=tea")
        self.run_event(id="pause",text="/pause")
        self.run_event(id="forget",text="/forget")
        self.assertEqual(self.s.control("demo-user")[0],1)
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM facts").fetchone()[0],0)
        self.assertEqual(len(self.sent),1)
    def test_missed_schedule_does_not_send(self):
        self.c["tasks"]=[dict(id="r",kind="random",peer="demo-user",prompt="hi",min_seconds=300,max_seconds=300)]
        self.e.tick(self.send,self.now)
        self.assertEqual(self.e.tick(self.send,self.now+601),["missed_trigger_skipped"])
        self.assertFalse(self.sent)


if __name__=="__main__":unittest.main()
