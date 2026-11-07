"""Single-owner durable receive/merge/schedule loop; no network in demo tests."""
import json
import time
import urllib.error
from pathlib import Path
from .batching import Batcher
from .core import Refused


class Service:
    def __init__(self,engine,bridge,root,clock=time.time):
        self.e,self.b,self.root,self.clock=engine,bridge,Path(root),clock
        if hasattr(bridge,'send_image'):engine.picture_send=bridge.send_image
        self.db=engine.s.db
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS reception(k TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,event TEXT,state TEXT);
        CREATE TABLE IF NOT EXISTS inbox_batches(id TEXT PRIMARY KEY,members TEXT);
        ''')
        self.started=clock()
        self.batch=Batcher(engine.c.get('quiet_seconds',1),engine.c.get('max_batch_wait',3))

    def start(self):
        self.b.verify()
        unknown=self.db.execute("SELECT count(*) FROM inbox WHERE state='processing'").fetchone()[0]
        if unknown:raise Refused('inbox_requires_manual_review')
        if self.db.execute("SELECT 1 FROM ops WHERE state!='complete' LIMIT 1").fetchone():
            raise Refused('operation_requires_manual_review')
        if self.e.flow and self.db.execute("SELECT 1 FROM setup_events WHERE state='pending' LIMIT 1").fetchone():
            raise Refused('setup_send_requires_manual_review')
        # Every process start adopts current head: never auto-replay downtime history.
        cursor=self.b.head()
        self.db.execute("INSERT OR REPLACE INTO reception VALUES ('cursor',?)",(cursor,))
        self.db.execute("UPDATE inbox SET state='restart_skipped' WHERE state='queued'")
        if self.e.flow and self.e.c.get('setup_peer'):
            self.e.flow.offer(self.e.c['setup_peer'],self.b.send)

    def perform(self,event):
        ids=event.get('members',[event['id']])
        self.db.execute('BEGIN IMMEDIATE')
        try:
            rows=[self.db.execute('SELECT state FROM inbox WHERE id=?',(i,)).fetchone() for i in ids]
            if not all(r==('queued',) for r in rows):raise Refused('inbox_member_conflict')
            self.db.execute('INSERT OR REPLACE INTO inbox_batches VALUES (?,?)',(event['id'],json.dumps(ids)))
            self.db.executemany("UPDATE inbox SET state='processing' WHERE id=?",[(i,) for i in ids])
            self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise
        consent=self.db.execute('SELECT state FROM role_consents WHERE peer=?',(event['peer'],)).fetchone()
        setup_ready=not self.e.flow or self.e.flow.ready(event['peer'])
        if event['kind']=='image' and setup_ready and (not self.e.c.get('require_role_consent') or consent==('accepted',)):
            try:
                from .media import normalize
                event['image_bytes'],event['image_first_frame']=normalize(self.b.image(event['id']))
            except Refused as error:
                if not str(error).startswith(('vision_','invalid_png','unsupported_png','png_decode','too_many_png','unsupported_media','media_','invalid_jpeg','unsupported_jpeg','invalid_gif','gif_','decoder_','jpeg_gif_')):raise
                # Known pre-model media refusal: do not block all subsequent text.
                self.db.executemany("UPDATE inbox SET state='unsupported_media',event='{}' WHERE id=?",[(i,) for i in ids])
                return
            except (TimeoutError,urllib.error.URLError):
                self.db.executemany("UPDATE inbox SET state='media_unavailable',event='{}' WHERE id=?",[(i,) for i in ids])
                return
        self.e.process(event,self.b.send,self.clock())
        self.db.executemany("UPDATE inbox SET state='complete',event='{}' WHERE id=?",[(i,) for i in ids])

    def step(self):
        if (self.root/'STOP').exists():return False
        cursor=self.db.execute("SELECT value FROM reception WHERE k='cursor'").fetchone()[0]
        events,next_cursor=self.b.events(cursor)
        for native in events:
            event=self.b.normalize(native,self.started,self.clock())
            if event is None:continue
            inserted=self.db.execute("INSERT OR IGNORE INTO inbox VALUES (?,?,'queued')",(event['id'],json.dumps(event))).rowcount
            if not inserted:continue
            control=event.get('text')
            if control in ('/exitrole','/forget') or (isinstance(control,str) and control.startswith('/forget ')):
                key=(event['account'],event['peer']);pending=self.batch.pending.pop(key,None)
                if pending:self.db.executemany("UPDATE inbox SET state='cancelled_by_control',event='{}' WHERE id=?",[(m['id'],) for m in pending['events']])
                self.perform(event)
                continue
            in_setup=bool(self.e.flow) and (not self.e.flow.ready(event['peer']) or event.get('text','').strip()==self.e.flow.word)
            if event['kind']=='text' and not event['text'].startswith('/') and not in_setup:
                try:self.batch.add(event,self.clock())
                except ValueError:
                    for ready in self.batch.flush(self.clock(),force=True):self.perform(ready)
                    self.batch.add(event,self.clock())
            else:
                for ready in self.batch.flush(self.clock(),force=True):self.perform(ready)
                self.perform(event)
        self.db.execute("UPDATE reception SET value=? WHERE k='cursor'",(next_cursor,))
        for event in self.batch.flush(self.clock()):self.perform(event)
        # Do not inject proactive messages while any owner has a pending inbound batch.
        if not self.batch.pending:
            self.e.tick(self.b.send,self.clock())
            if self.e.research:self.e.research.tick(self.clock())
        return True

    def run(self):
        self.start()
        while self.step():time.sleep(.5)
