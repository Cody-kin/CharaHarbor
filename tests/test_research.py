import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from companion.core import Store,load,Refused
from companion.research import Research,parse_feed,public_get,resolve_public

FEED=b'<rss><channel><item><guid>one</guid><title>Hong Kong music concert</title><link>https://example.com/news/one</link><pubDate>Thu, 05 Nov 2026 12:00:00 +0000</pubDate></item></channel></rss>'


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.c=load('examples/demo.json');self.s=Store(Path(self.tmp.name)/'state',self.c['account'])
        self.source=dict(id='official-test',url='https://example.com/feed.xml',role='小睦',kind='real_activity',approved_official_source=True)
        self.c.update(research_enabled=True,research_sources=[self.source]);self.calls=[];self.status=200;self.body=FEED
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def get(self,url,headers,limit):
        self.calls.append((url,headers))
        if url.endswith('robots.txt'):return 404,{},b''
        return self.status,{'ETag':'test-v1'},self.body
    def test_default_12_hour_poll_conditional_get_no_model(self):
        r=Research(self.c,self.s,self.get);r.tick(1000)
        self.assertEqual(len(self.calls),2)
        r.tick(1001);self.assertEqual(len(self.calls),2)
        self.status=304;r.tick(44200)
        self.assertEqual(self.calls[-1][1]['If-None-Match'],'test-v1')
        self.assertEqual(self.s.db.execute('SELECT version FROM research_items').fetchone()[0],1)
    def test_publication_not_mistaken_for_event_date(self):
        r=Research(self.c,self.s,self.get);r.tick(1000);items=r.context('小睦','music concert',1001)
        self.assertEqual(items[0]['kind'],'real_activity');self.assertIsNone(items[0]['event_at'])
        self.assertEqual(items[0]['event_time_status'],'time_unknown');self.assertIsNotNone(items[0]['source_published_at'])
        self.assertEqual(r.context('other-role','concert',1001),[])
    def test_version_and_expiry(self):
        r=Research(self.c,self.s,self.get);r.tick(1000)
        self.body=FEED.replace(b'concert',b'concert rescheduled');r.tick(44200)
        self.assertEqual(self.s.db.execute('SELECT version FROM research_items').fetchone()[0],2)
        self.assertEqual(r.context('小睦','concert',44200+604801),[])
    def test_disabled_does_not_fetch(self):
        self.c['research_enabled']=False;r=Research(self.c,self.s,self.get);r.tick(1000);self.assertFalse(self.calls)
    def test_robots_deny_and_failure_metadata(self):
        def get(url,h,l):self.calls.append(url);return 200,{},b'User-agent: *\nDisallow: /'
        r=Research(self.c,self.s,get);r.tick(1000)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.s.db.execute('SELECT error,last_failure FROM research_sources').fetchone(),('robots_disallowed',1000.))
    def test_crawl_delay_defers_feed_without_sleep(self):
        def get(url,h,l):
            self.calls.append(url)
            return (200,{},b'User-agent: *\nAllow: /\nCrawl-delay: 2') if url.endswith('robots.txt') else (200,{},FEED)
        r=Research(self.c,self.s,get);r.tick(1000);self.assertEqual(len(self.calls),1)
        r.tick(1001);self.assertEqual(len(self.calls),1)
        r.tick(1002);self.assertEqual(len(self.calls),2)
    def test_entities_and_html_not_accepted_as_feed(self):
        for content in (b'<!DOCTYPE rss><rss/>',b'<html><body>not a feed</body></html>'):
            with self.assertRaises(Refused):parse_feed(content,self.source)
    def test_dns_private_target_rejected_before_connection(self):
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaisesRegex(Refused,'private'):public_get('https://example.com/feed.xml')
    def test_unapproved_source_refused(self):
        self.source['approved_official_source']=False
        with self.assertRaisesRegex(Refused,'approval'):Research(self.c,self.s,self.get)
    def test_public_dns_never_accepts_private_or_wrong_question(self):
        import json
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps(self.body).encode()
        r=Response()
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=r
            r.body={'Status':0,'Question':[{'name':'example.com.','type':1}],'Answer':[{'type':1,'data':'127.0.0.1'}]}
            with self.assertRaisesRegex(Refused,'private'):resolve_public('example.com','google_https')
            r.body['Answer'][0]['data']='8.8.8.8';r.body['Question'][0]['name']='foreign.example'
            with self.assertRaisesRegex(Refused,'invalid'):resolve_public('example.com','google_https')
            r.body['Question'][0]['name']='example.com.'
            self.assertEqual(resolve_public('example.com','google_https'),{'8.8.8.8'})
    def test_no_dns_fallback_and_failure_preserves_last_success(self):
        r=Research(self.c,self.s,self.get);r.tick(1000)
        def fail(*args):raise TimeoutError()
        r.get=fail;r.tick(44200)
        row=self.s.db.execute('SELECT last_success,last_failure,error,next FROM research_sources').fetchone()
        self.assertEqual(row,(1000.,44200.,'TimeoutError',87400.))
        self.assertEqual(r.context('小睦','concert',1000+604801),[])
