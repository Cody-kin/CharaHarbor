import argparse
import json
import os
import sys
from pathlib import Path
from .core import Engine, Refused, Store, load


class Lock:
    def __init__(self, root): self.path=Path(root)/"worker.lock"
    def __enter__(self):
        if self.path.is_symlink(): raise Refused("unsafe_lock")
        self.file=open(self.path,"a+b")
        self.file.seek(0)
        if os.name == "nt":
            import msvcrt
            if self.path.stat().st_size == 0:self.file.write(b"0");self.file.flush()
            self.file.seek(0)
            try:msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:
                self.file.close()
                raise Refused("worker_already_running") from None
        else:
            import fcntl
            try:fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:
                self.file.close()
                raise Refused("worker_already_running") from None
        return self
    def __exit__(self,*args):self.file.close()


def main():
    parser=argparse.ArgumentParser(description="Companion core; demo by default, no WeChat login automation")
    parser.add_argument("command",choices=["check","run","serve","tick","status","recover-setup"])
    parser.add_argument("--config",default="examples/demo.json")
    parser.add_argument("--state",default=".companion-state")
    parser.add_argument("--live",action="store_true",help="explicitly permit configured API and wx outbound operations")
    parser.add_argument('--event',help='pending local setup-event id; recovery only reads existing bridge receipt')
    args=parser.parse_args()
    c=load(args.config)
    if args.command=="check":
        print(json.dumps({"status":"valid","mode":c["mode"],"provider":c["provider"],"tasks":len(c.get("tasks",[]))}))
        return
    if (c["mode"]=="live") != args.live:
        raise Refused("explicit_live_flag_required_or_demo_mismatch")
    # Demo must never call a remote provider, even if config was edited.
    if c["mode"]=="demo" and c["provider"]!="mock":
        raise Refused("demo_requires_mock")
    if c["mode"]=="live" and args.command not in ('status','recover-setup') and not os.environ.get("COMPANION_API_KEY"):
        raise Refused("api_key_environment_missing")
    if c['mode']=='live' and args.command=='run':
        raise Refused('live_jsonl_disabled_use_authenticated_serve')
    s=Store(args.state,c["account"])
    if args.command=='status':
        tables={r[0] for r in s.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result={'operations':s.db.execute('SELECT state,count(*) FROM ops GROUP BY state').fetchall(),
                'reserved_usd':s.db.execute('SELECT coalesce(sum(cost),0)/1000000.0 FROM ops').fetchone()[0],
                'setup_pending':s.db.execute("SELECT id,peer,next_phase FROM setup_events WHERE state='pending'").fetchall() if 'setup_events' in tables else [],
                'research':s.db.execute('SELECT id,last_success,last_failure,error,next FROM research_sources').fetchall() if 'research_sources' in tables else []}
        print(json.dumps(result));s.db.close();return
    with Lock(args.state):
        engine=Engine(c,s)
        def send(peer,text,identity):
            if c["mode"]=="live":
                from .bridge import Bridge
                return Bridge(c).send(peer,text,identity)
            print(json.dumps({"demo_only":True,"peer":peer,"text":text},ensure_ascii=False))
            return True
        if args.command=='recover-setup':
            if c['mode']!='live' or not engine.flow or not args.event:raise Refused('live_setup_event_required')
            from .bridge import Bridge
            print(json.dumps({'status':engine.flow.recover(args.event,Bridge(c))}))
        elif args.command=='serve':
            if c['mode']!='live':raise Refused('serve_requires_explicit_live_configuration')
            from .bridge import Bridge
            from .service import Service
            Service(engine,Bridge(c),args.state).run()
        elif args.command=="tick":
            print(json.dumps({"status":engine.tick(send)}))
        else:
            # Trusted adapter contract, NOT an exposed webhook. No history polling/replay.
            while True:
                if (Path(args.state)/"STOP").exists():break
                line=sys.stdin.buffer.readline(16385)
                if not line:break
                if len(line)>16384:raise Refused("event_too_large")
                event=json.loads(line)
                engine.process(event,send)
                print('{"status":"complete"}')
    s.db.close()


if __name__=="__main__":
    try:main()
    except KeyboardInterrupt:sys.exit(130)
    except Refused as e:
        print(json.dumps({"status":"stopped","reason":str(e)}),file=sys.stderr)
        sys.exit(2)
    except Exception:
        # No exception text: HTTP bodies, subprocess output and event data may be private.
        print('{"status":"stopped","reason":"unexpected_failure_no_retry"}',file=sys.stderr)
        sys.exit(3)
