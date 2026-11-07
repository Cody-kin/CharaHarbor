"""Opt-in official-feed research cache; titles/metadata only, no paid model calls."""
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from .core import Refused

AGENT='CompanionResearch/0.3'


def checked_url(url):
    u=urllib.parse.urlsplit(url)
    if (u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment
        or u.port not in (None,443) or len(url)>2048):raise Refused('research_public_https_url_required')
    return u


def resolve_public(host,mode='system'):
    if mode=='system':
        ips={item[4][0] for item in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)}
    elif mode=='google_https':
        # Fixed resolver only. OS proxy is permitted here, never for a feed URL.
        # TLS verifies dns.google; neither URL nor resolver host is user supplied.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):raise Refused('research_dns_redirect_denied')
        url='https://dns.google/resolve?'+urllib.parse.urlencode({'name':host,'type':'A'})
        with urllib.request.build_opener(NoRedirect()).open(url,timeout=5) as response:
            data=response.read(32769)
            if response.status!=200 or len(data)>32768:raise Refused('research_dns_response_invalid')
        result=json.loads(data)
        questions=result.get('Question',[])
        if (result.get('Status')!=0 or len(questions)!=1 or questions[0].get('type')!=1
            or questions[0].get('name','').rstrip('.').lower()!=host.lower()):
            raise Refused('research_dns_response_invalid')
        ips={answer['data'] for answer in result.get('Answer',[]) if answer.get('type')==1}
    else:raise Refused('research_dns_mode_invalid')
    try:
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):raise Refused('research_private_address_denied')
    except ValueError:raise Refused('research_dns_response_invalid') from None
    return ips


def public_get(url,headers=None,limit=262144,dns_mode='system'):
    u=checked_url(url)
    ips=resolve_public(u.hostname,dns_mode)
    # Pin the resolved public address while retaining certificate hostname checks.
    class Pinned(http.client.HTTPSConnection):
        def connect(self):
            raw=socket.create_connection((sorted(ips)[0],443),timeout=5)
            try:self.sock=ssl.create_default_context().wrap_socket(raw,server_hostname=u.hostname)
            except BaseException:raw.close();raise
    connection=Pinned(u.hostname,timeout=5)
    try:
        connection.request('GET',u.path or '/',headers={'User-Agent':AGENT,**(headers or {})})
        response=connection.getresponse()
        if 300<=response.status<400 and response.status!=304:raise Refused('research_redirect_denied')
        body=response.read(limit+1)
        if len(body)>limit:raise Refused('research_source_too_large')
        return response.status,dict(response.getheaders()),body
    finally:connection.close()


def timestamp(value):
    if not value:return None
    try:
        try:d=datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError:d=parsedate_to_datetime(value)
        return d.isoformat() if d.tzinfo is not None else None
    except (ValueError,TypeError):return None


def parse_feed(data,source):
    if len(data)>262144 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise Refused('research_xml_rejected')
    root=ET.fromstring(data)
    if root.tag.rsplit('}',1)[-1] not in ('rss','feed','RDF'):raise Refused('unsupported_feed_format')
    if sum(1 for _ in root.iter())>2000:raise Refused('research_feed_too_complex')
    def local(tag):return tag.rsplit('}',1)[-1]
    entries=[x for x in root.iter() if local(x.tag) in ('item','entry')]
    out=[];host=checked_url(source['url']).hostname
    for entry in entries[:20]:
        values={local(x.tag):''.join(x.itertext()).strip() for x in list(entry)}
        title=re.sub(r'<[^>]*>','',values.get('title',''))[:200]
        if not title:continue
        link=values.get('link','')
        for child in list(entry):
            if local(child.tag)=='link' and child.get('href'):link=child.get('href')
        try:
            if checked_url(link).hostname not in source.get('link_hosts',[host]):link=source['url']
        except (Refused,ValueError):link=source['url']
        published=timestamp(values.get('published') or values.get('pubDate') or values.get('updated'))
        # Never confuse publication time with performance/plot-event time.
        event_time=timestamp(values.get('eventTime'))
        guid=values.get('guid') or values.get('id') or link+title
        item=dict(title=title,url=link,source_published_at=published,event_at=event_time,
                  event_timezone=source.get('event_timezone') if event_time else None,
                  kind=source['kind'],role=source['role'],confidence='official_feed_report')
        item['id']=hashlib.sha256((source['id']+'\0'+guid).encode()).hexdigest()
        out.append(item)
    return out


class Research:
    def __init__(self,c,store,get=public_get):
        mode=c.get('research_dns','system')
        if mode not in ('system','google_https'):raise Refused('research_dns_mode_invalid')
        self.c,self.db=c,store.db
        self.get=(lambda url,headers,limit:public_get(url,headers,limit,dns_mode=mode)) if get is public_get else get
        self.sources=c.get('research_sources',[]) if c.get('research_enabled',False) else []
        if len(self.sources)>4:raise Refused('too_many_research_sources')
        if len({s['id'] for s in self.sources})!=len(self.sources):raise Refused('duplicate_research_source')
        hosts=[checked_url(s['url']).hostname for s in self.sources]
        if len(set(hosts))!=len(hosts):raise Refused('one_feed_per_host_required')
        for s in self.sources:
            checked_url(s['url'])
            if s.get('approved_official_source') is not True or s.get('kind') not in ('fiction_plot','real_activity') or not isinstance(s.get('role'),str):raise Refused('research_source_approval_required')
            if not 3600<=s.get('interval_seconds',43200)<=604800:raise Refused('research_interval_out_of_bounds')
            if not 3600<=s.get('ttl_seconds',604800)<=2592000:raise Refused('research_ttl_out_of_bounds')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS research_sources(id TEXT PRIMARY KEY,next REAL,last_success REAL,last_failure REAL,error TEXT,etag TEXT,modified TEXT);
        CREATE TABLE IF NOT EXISTS research_items(id TEXT PRIMARY KEY,source TEXT,role TEXT,kind TEXT,payload TEXT,version INTEGER,expires REAL);
        CREATE TABLE IF NOT EXISTS research_robots(id TEXT PRIMARY KEY,url TEXT,body TEXT,status INTEGER,checked REAL,last_request REAL,delay REAL);
        ''')

    def tick(self,now=None):
        now=time.time() if now is None else now
        for source in self.sources:
            row=self.db.execute('SELECT next,last_success,last_failure,error,etag,modified FROM research_sources WHERE id=?',(source['id'],)).fetchone()
            if row and row[0]>now:continue
            interval=source.get('interval_seconds',43200)
            # Reserve next attempt before network; restarts cannot hammer a source.
            self.db.execute('INSERT OR IGNORE INTO research_sources(id,next) VALUES (?,?)',(source['id'],now+interval))
            self.db.execute('UPDATE research_sources SET next=? WHERE id=?',(now+interval,source['id']))
            try:
                u=checked_url(source['url']);origin='https://'+u.hostname
                cached=self.db.execute('SELECT url,body,status,checked,last_request,delay FROM research_robots WHERE id=?',(source['id'],)).fetchone()
                if cached and cached[0]==source['url'] and now-cached[3]<86400:
                    robots=cached[1].encode();status=cached[2]
                else:
                    if cached and now<cached[4]+cached[5]:
                        self.db.execute('UPDATE research_sources SET next=? WHERE id=?',(cached[4]+cached[5],source['id']));break
                    status,_,robots=self.get(origin+'/robots.txt',{},65536)
                    self.db.execute('INSERT OR REPLACE INTO research_robots VALUES (?,?,?,?,?,?,?)',(source['id'],source['url'],robots.decode('utf-8'),status,now,now,0))
                    cached=(source['url'],robots.decode('utf-8'),status,now,now,0)
                delay=0
                if status==200:
                    robot=urllib.robotparser.RobotFileParser();robot.parse(robots.decode('utf-8').splitlines())
                    if not robot.can_fetch(AGENT,source['url']):raise Refused('robots_disallowed')
                    rate=robot.request_rate(AGENT)
                    delay=max(robot.crawl_delay(AGENT) or 0,rate.seconds/rate.requests if rate and rate.requests else 0)
                    self.db.execute('UPDATE research_robots SET delay=? WHERE id=?',(delay,source['id']))
                    if now<cached[4]+delay:
                        self.db.execute('UPDATE research_sources SET next=? WHERE id=?',(cached[4]+delay,source['id']));break
                    interval=max(interval,delay)
                    self.db.execute('UPDATE research_sources SET next=? WHERE id=?',(now+interval,source['id']))
                elif status!=404:raise Refused('robots_unavailable')
                headers={}
                if row and row[4]:headers['If-None-Match']=row[4]
                if row and row[5]:headers['If-Modified-Since']=row[5]
                self.db.execute('UPDATE research_robots SET last_request=? WHERE id=?',(now,source['id']))
                status,returned,data=self.get(source['url'],headers,262144)
                if status==304:
                    # Revalidated metadata; source has not changed.
                    self.db.execute('UPDATE research_items SET expires=? WHERE source=?',(now+source.get('ttl_seconds',604800),source['id']))
                elif status==200:
                    items=parse_feed(data,source)
                    for item in items:
                        payload=json.dumps(item,ensure_ascii=False,sort_keys=True)
                        old=self.db.execute('SELECT payload,version FROM research_items WHERE id=?',(item['id'],)).fetchone()
                        version=1 if not old else old[1]+int(old[0]!=payload)
                        self.db.execute('INSERT OR REPLACE INTO research_items VALUES (?,?,?,?,?,?,?)',(item['id'],source['id'],item['role'],item['kind'],payload,version,now+source.get('ttl_seconds',604800)))
                    self.db.execute('DELETE FROM research_items WHERE source=? AND id NOT IN (SELECT id FROM research_items WHERE source=? ORDER BY expires DESC,rowid DESC LIMIT 100)',(source['id'],source['id']))
                else:raise Refused('research_http_failure')
                h={k.lower():v for k,v in returned.items()}
                self.db.execute('UPDATE research_sources SET last_success=?,error=NULL,etag=?,modified=? WHERE id=?',(now,h.get('etag',row[4] if row else None),h.get('last-modified',row[5] if row else None),source['id']))
            except Exception as error:
                # Record type/stable reason only. No raw response, token or private text.
                code=str(error) if isinstance(error,Refused) else type(error).__name__
                self.db.execute('UPDATE research_sources SET last_failure=?,error=? WHERE id=?',(now,code[:100],source['id']))
            break  # at most one due source per chat-loop iteration
        self.db.execute('DELETE FROM research_items WHERE expires<?',(now,))

    def context(self,role,query,now=None):
        if not self.sources:return []
        now=time.time() if now is None else now
        def terms(text):
            words=set(re.findall(r'[a-z]{3,}',text.lower()))
            for run in re.findall(r'[\u4e00-\u9fff]+',text):words.update(run[i:i+2] for i in range(len(run)-1))
            return words
        q=terms(query);ranked=[]
        allowed={s['id'] for s in self.sources}
        for payload,version,source,last_success in self.db.execute('SELECT i.payload,i.version,i.source,s.last_success FROM research_items i LEFT JOIN research_sources s ON s.id=i.source WHERE i.role=? AND i.expires>=?',(role,now)):
            if source not in allowed:continue
            item=json.loads(payload);score=len(q.intersection(terms(item['title'])))
            if score:
                event=timestamp(item.get('event_at'))
                when=datetime.fromisoformat(event).timestamp() if event else None
                status='time_unknown' if when is None else ('past' if when<now else 'future')
                ranked.append((score,{**item,'version':version,'event_time_status':status,'source_checked_at':last_success}))
        return [x[1] for x in sorted(ranked,key=lambda v:v[0],reverse=True)[:2]]
