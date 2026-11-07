"""Account-scoped native HTTP adapter. No login, token creation or sync writes."""
import json
import hashlib
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from .core import NoRedirect, Refused


def segment(value):
    if not isinstance(value,str) or not value or len(value)>512:raise Refused('invalid_bridge_identifier')
    return urllib.parse.quote(value,safe='')


class Bridge:
    def __init__(self,c):
        self.c=c
        self.base=c.get('bridge_url','http://127.0.0.1:6174/v1')
        u=urllib.parse.urlsplit(self.base)
        if u.scheme!='http' or u.hostname!='127.0.0.1' or u.username or u.password or u.path!='/v1' or u.query or u.fragment:
            raise Refused('bridge_must_be_literal_ipv4_loopback')
        if not c.get('bridge_server_id') or not c.get('own_username'):raise Refused('bridge_identity_pins_required')
        self.prefix='/accounts/'+segment(c['account'])

    def request(self,path,body=None,key=None,content_type='application/json'):
        token=os.environ.get('COMPANION_BRIDGE_TOKEN')
        if not token:raise Refused('bridge_token_environment_missing')
        headers={'Authorization':'Bearer '+token,'Content-Type':content_type}
        if key:headers['Idempotency-Key']=key
        req=urllib.request.Request(self.base+path,headers=headers,
            data=None if body is None else (body if isinstance(body,bytes) else json.dumps(body).encode()))
        # Bypass ambient HTTP proxy for loopback credentials. Reject redirects.
        with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(req,timeout=5) as r:
            data=r.read(524289)
        if len(data)>524288:raise Refused('bridge_response_too_large')
        return json.loads(data)

    def verify(self):
        status=self.request('/status')
        account=self.request(self.prefix)
        if (status.get('serverId')!=self.c['bridge_server_id'] or status.get('state')!='ready'
            or status.get('version',{}).get('apiVersion')!=1):
            raise Refused('bridge_server_identity_mismatch')
        if (account.get('id')!=self.c['account'] or account.get('ownUsername')!=self.c['own_username']
            or account.get('authenticated') is not True or account.get('connection')!='online'):
            raise Refused('bridge_account_unverified')
        return True

    def head(self):
        self.verify()
        r=self.request(self.prefix+'/threads?limit=1')
        cursor=r.get('asOfEventCursor')
        if not isinstance(cursor,str) or not cursor.isdecimal():raise Refused('startup_cursor_not_exposed')
        return cursor

    def events(self,cursor):
        self.verify()
        r=self.request(self.prefix+'/events?after='+segment(cursor)+'&limit=100')
        items=r.get('items')
        if not isinstance(items,list) or len(items)>100:raise Refused('invalid_event_page')
        previous=int(cursor)
        for e in items:
            value=e.get('cursor')
            if not isinstance(value,str) or not value.isdecimal() or int(value)<=previous:
                raise Refused('event_cursor_regressed')
            previous=int(value)
        if str(previous)!=r.get('nextCursor'):raise Refused('event_cursor_mismatch')
        return items,r['nextCursor']

    def normalize(self,e,started,now):
        if e.get('kind')!='message.committed':return None
        data=e.get('data',{})
        if data.get('accountId') not in (None,self.c['account']):raise Refused('event_account_mismatch')
        peer=data.get('threadId')
        # Filter before fetching a private body. Missing routing evidence fails closed.
        if peer not in self.c['peers']:return None
        m=self.request(self.prefix+'/messages/'+segment(data.get('messageId')))
        if (m.get('accountId')!=self.c['account'] or m.get('threadId')!=peer
            or m.get('senderId')!=peer or m.get('direction')!='incoming' or m.get('recall')):
            return None
        thread=self.request(self.prefix+'/threads/'+segment(peer))
        if thread.get('accountId')!=self.c['account'] or thread.get('peerId')!=peer or thread.get('kind')!='direct':
            raise Refused('direct_thread_unverified')
        try:
            parsed=datetime.fromisoformat(m['createdAt'].replace('Z','+00:00'))
            if parsed.tzinfo is None:raise ValueError()
            stamp=parsed.timestamp()
        except (ValueError,TypeError,KeyError):raise Refused('message_time_unverified') from None
        if stamp<started or not -.001<=now-stamp<=120:return None
        stamp=min(stamp,now)  # only ISO microsecond rounding, not future messages
        kind={1:'text',3:'image',47:'sticker'}.get(m.get('type'))
        if kind is None:return None
        if kind!='text' and (kind!='image' or peer not in self.c.get('vision_peers',[])):return None
        if m.get('id')!=data.get('messageId'):raise Refused('message_identity_mismatch')
        return dict(id=m['id'],account=self.c['account'],peer=peer,at=stamp,kind=kind,
                    direction='incoming',group=False,text=m.get('body') if kind=='text' else '',cursor=e['cursor'])

    def image(self,identity):
        self.verify()
        token=os.environ.get('COMPANION_BRIDGE_TOKEN')
        if not token:raise Refused('bridge_token_environment_missing')
        req=urllib.request.Request(self.base+self.prefix+'/messages/'+segment(identity)+'/media?quality=best',headers={'Authorization':'Bearer '+token})
        with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(req,timeout=10) as r:
            mime=r.headers.get_content_type()
            if mime not in ('image/png','image/jpeg','image/gif'):raise Refused('vision_image_type_denied')
            data=r.read(1048577)
        from .vision import png_url
        from .media import geometry
        if mime=='image/png':png_url(data)
        elif geometry(data)[0]!={'image/jpeg':'JPEG','image/gif':'GIF'}[mime]:raise Refused('media_mime_mismatch')
        self.verify()
        return data

    def send(self,peer,text,identity):
        if peer not in self.c['peers']:raise Refused('scope_denied')
        self.verify()
        key='companion:'+hashlib.sha256(identity.encode()).hexdigest()
        r=self.request(self.prefix+'/sends',{'threadId':peer,'text':text},key)
        deadline=time.monotonic()+30
        while r.get('state') in ('queued','sending') and time.monotonic()<deadline:
            time.sleep(.2)
            r=self.request(self.prefix+'/sends/'+segment(r.get('id')))
        self.verify()
        if (r.get('accountId')!=self.c['account'] or r.get('destination')!=peer or
            r.get('state')!='accepted' or r.get('errorCode') is not None or
            not isinstance(r.get('serverId'),str) or not r['serverId'].isdecimal() or int(r['serverId'])<=0):
            raise Refused('bridge_send_outcome_unverified')
        return True

    def lookup_send(self,identity):
        self.verify()
        key='companion:'+hashlib.sha256(identity.encode()).hexdigest()
        result=self.request(self.prefix+'/sends/by-idempotency-key?key='+segment(key))
        self.verify()
        return result

    def send_image(self,peer,path,identity):
        if peer not in self.c.get('picture_peers',[]):raise Refused('picture_scope_denied')
        self.verify()
        from .vision import png_url
        data=path.read_bytes();png_url(data)
        digest=hashlib.sha256(data).hexdigest()
        boundary='companion-'+digest[:24]
        body=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="reaction.png"\r\nContent-Type: image/png\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode()
        source=self.request(self.prefix+'/uploads',body,content_type='multipart/form-data; boundary='+boundary)
        if source.get('sha256')!=digest or source.get('byteLength')!=len(data):raise Refused('uploaded_source_unverified')
        key='companion-image:'+hashlib.sha256(identity.encode()).hexdigest()
        job=self.request(self.prefix+'/sends',dict(threadId=peer,kind='image',sourceId=source['id'],standardSourceId=None,thumbnailSourceId=None,playSeconds=None,durationMs=None),key)
        deadline=time.monotonic()+30
        while job.get('state') in ('queued','running') and time.monotonic()<deadline:
            time.sleep(.2);job=self.request(self.prefix+'/jobs/'+segment(job.get('id')))
        self.verify()
        if (job.get('accountId')!=self.c['account'] or job.get('threadId')!=peer or job.get('kind')!='send'
            or job.get('state')!='accepted' or job.get('phase')!='completed' or job.get('reason') is not None
            or job.get('cancelRequested') is not False or not isinstance(job.get('serverMessageId'),str)
            or not job['serverMessageId'].isdecimal() or int(job['serverMessageId'])<=0
            or type(job.get('totalBytes')) is not int or job['totalBytes']<=0
            or job.get('completedBytes')!=job['totalBytes']):
            raise Refused('picture_send_outcome_uncertain')
        return True
