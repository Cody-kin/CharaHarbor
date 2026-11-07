"""Interactive first-use/settings demonstration. No WeChat, network or API key."""
import json
import argparse
import sys
import time
from companion.core import Engine,Store,load
from companion.__main__ import Lock


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',default='.setup-demo-state');args=parser.parse_args()
    c=load('examples/onboarding-demo.json')
    s=Store(args.state,c['account'])
    try:
        with Lock(args.state):
            engine=Engine(c,s)
            def send(peer,text,identity):print(text,flush=True);return True
            engine.flow.offer(c['peers'][0],send)
            print('离线演示；已有设置会恢复。输入 /quit 退出程序，输入完整安全词可重新进入设置。',flush=True)
            for raw in sys.stdin:
                text=raw.rstrip('\r\n')
                if text=='/quit':break
                now=time.time()
                event=dict(id='demo-'+str(time.time_ns()),account=c['account'],peer=c['peers'][0],at=now,kind='text',direction='incoming',group=False,text=text)
                engine.process(event,send,now)
    finally:s.db.close()


if __name__=='__main__':main()
