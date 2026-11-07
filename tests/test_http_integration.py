"""Real loopback HTTP; synthetic account/message/token only; no WeChat or API."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from companion.bridge import Bridge
from companion.core import Engine,Store,load
from companion.service import Service
from test_service import FixtureBridge


class HTTPIntegration(unittest.TestCase):
    def test_real_http_receive_model_and_send(self):
        c=load('examples/demo.json');c.update(bridge_server_id='synthetic-server',own_username='synthetic-self')
        fixture=FixtureBridge(c)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def handle_request(self):
                if self.headers.get('Authorization')!='Bearer synthetic-loopback-token':
                    self.send_error(401);return
                path=self.path[3:]
                body=None
                if self.command=='POST':body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                try:data=fixture.request(path,body,self.headers.get('Idempotency-Key'))
                except Exception:
                    self.send_error(400);return
                raw=json.dumps(data).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            do_GET=handle_request
            do_POST=handle_request
        try:server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        except PermissionError:
            self.skipTest('execution sandbox denies loopback listener; run this test with explicit local-network permission')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c['bridge_url']='http://127.0.0.1:'+str(server.server_port)+'/v1'
            with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'COMPANION_BRIDGE_TOKEN':'synthetic-loopback-token'}):
                s=Store(Path(d)/'state',c['account'])
                try:
                    now=[1700000000.]
                    service=Service(Engine(c,s),Bridge(c),Path(d)/'state',lambda:now[0])
                    service.start();fixture.add(1,now[0]);service.step();now[0]+=2;service.step()
                    self.assertEqual(len(fixture.sent),1)
                    self.assertTrue(fixture.sent[0][1].startswith('companion:'))
                    self.assertEqual(s.db.execute('SELECT state FROM ops').fetchone()[0],'complete')
                finally:s.db.close()
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
