import hashlib
import tempfile
import unittest
from pathlib import Path
from companion.batching import Batcher
from companion.gallery import select

class UtilityTests(unittest.TestCase):
    def test_batch_isolation_debounce_and_members(self):
        b=Batcher()
        def e(i,p):return dict(id=i,account="a",peer=p,text=i,kind="text",at=1)
        b.add(e("1","p"),0);b.add(e("2","p"),.5);b.add(e("3","other"),.7)
        self.assertEqual(b.flush(1),[])
        result=b.flush(2)
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]["text"],"1\n2")
        self.assertEqual(result[0]["members"],["1","2"])
    def test_batch_dedup_and_command_rejection(self):
        b=Batcher();e=dict(id="a",account="x",peer="p",text="hello",kind="text")
        b.add(e,0);b.add(e,0)
        self.assertEqual(len(b.flush(2)[0]["members"]),1)
        e["text"]="/pause"
        with self.assertRaises(ValueError):b.add(e,0)
    def test_gallery_no_match_no_fallback_or_repeats(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"test.png";data=b"\x89PNG\r\n\x1a\nsynthetic header only";p.write_bytes(data)
            e=dict(id="music",file="test.png",tags=["music"],rights_confirmed=True,sha256=hashlib.sha256(data).hexdigest())
            self.assertIsNone(select(d,[e],["rest"],{},100))
            self.assertEqual(select(d,[e],["music"],{},100),p.resolve())
            self.assertIsNone(select(d,[e],["music"],{"music":99},100))
            e["file"]="../test.png"
            self.assertIsNone(select(d,[e],["music"],{},100))
    def test_gallery_requires_explicit_rights(self):
        self.assertIsNone(select(".",[dict(id="x",file="x.png",tags=["music"])],["music"],{},100))
