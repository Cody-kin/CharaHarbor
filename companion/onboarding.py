"""Per-peer, persistent consent/setup workflow with durable UI-send fences."""
import hashlib
import json
import re
from zoneinfo import ZoneInfo
from .core import Refused


class Onboarding:
    def __init__(self,c,store):
        self.c,self.s,self.db=c,store,store.db
        self.word=c.get('settings_word','/settings')
        self.roles=c.get('role_choices',{'默认角色':c['persona']})
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS setup(peer TEXT PRIMARY KEY,phase TEXT,settings TEXT,draft TEXT,revision INTEGER);
        CREATE TABLE IF NOT EXISTS setup_events(id TEXT PRIMARY KEY,peer TEXT,next_phase TEXT,settings TEXT,draft TEXT,revision INTEGER,state TEXT);
        ''')

    def row(self,peer):
        r=self.db.execute('SELECT phase,settings,draft,revision FROM setup WHERE peer=?',(peer,)).fetchone()
        return (r[0],json.loads(r[1]),json.loads(r[2]),r[3]) if r else ('new',{}, {},0)

    def ready(self,peer):return self.row(peer)[0]=='ready'

    def notice(self,peer):
        provider={'openai':'OpenAI','deepseek':'DeepSeek','mock':'本机离线演示模型（不联网）'}[self.c['provider']]
        text='这是虚构AI角色扮演，提供陪伴，不代替专业心理或医疗支持。聊天会交给'+provider+'处理；不要发送秘密。回复「同意」开始逐步设置，或「不同意」拒绝；/about 查看说明，/exitrole 随时退出。'
        if peer in self.c.get('auto_memory_peers',[]):text+='此配置自动保存明确喜好、经历和约定直到更正/删除；相关记忆会发给模型。'
        if peer in self.c.get('vision_peers',[]):text+='支持格式的图片也会发给模型理解。'
        if peer in self.c.get('adaptive_state_peers',[]):text+='动态情绪是虚构表演参数；你可 /state pause 或 reset，不需要及时回复；剧情状态须另选阶段与剧透范围。'
        return text

    def transition(self,peer,identity,phase,settings,draft,revision,reply,send):
        # State changes become visible only after a strict send receipt. Unknown IO
        # keeps a pending fence; no automatic retries/replays on restart.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute("SELECT 1 FROM setup_events WHERE peer=? AND state='pending'",(peer,)).fetchone():raise Refused('setup_send_requires_manual_review')
            if self.db.execute('SELECT 1 FROM setup_events WHERE id=?',(identity,)).fetchone():
                self.db.execute('ROLLBACK');return 'setup_duplicate'
            self.db.execute('INSERT INTO setup_events VALUES (?,?,?,?,?,?,?)',(identity,peer,phase,json.dumps(settings,ensure_ascii=False),json.dumps(draft,ensure_ascii=False),revision,'pending'))
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise
        if send(peer,reply,'setup:'+hashlib.sha256(identity.encode()).hexdigest()) is not True:raise Refused('setup_send_outcome_uncertain')
        self.commit(identity)
        return 'setup_'+phase

    def commit(self,identity):
        pending=self.db.execute('SELECT peer,next_phase,settings,draft,revision,state FROM setup_events WHERE id=?',(identity,)).fetchone()
        if not pending or pending[5]!='pending':raise Refused('setup_not_pending')
        peer,phase,rawsettings,rawdraft,revision,_=pending
        settings,draft=json.loads(rawsettings),json.loads(rawdraft)
        old_revision=self.row(peer)[3]
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT OR REPLACE INTO setup VALUES (?,?,?,?,?)',(peer,phase,json.dumps(settings,ensure_ascii=False),json.dumps(draft,ensure_ascii=False),revision))
            self.db.execute("UPDATE setup_events SET state='complete' WHERE id=?",(identity,))
            if phase=='ready':
                self.db.execute("INSERT OR REPLACE INTO role_consents VALUES (?,'accepted',?)",(peer,identity))
                self.s.control(peer)
                if revision>old_revision:self.db.execute('UPDATE controls SET paused=? WHERE peer=?',(0 if settings.get('proactive') else 1,peer))
            if phase in ('declined','exited'):
                self.db.execute('INSERT OR REPLACE INTO role_consents VALUES (?,?,?)',(peer,phase,identity))
                self.s.control(peer);self.db.execute('UPDATE controls SET paused=1 WHERE peer=?',(peer,))
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise
        return 'setup_'+phase

    def offer(self,peer,send):
        if peer not in self.c['peers']:raise Refused('setup_scope_denied')
        phase,settings,draft,rev=self.row(peer)
        if phase!='new':return 'setup_already_offered'
        return self.transition(peer,'offer:'+hashlib.sha256(peer.encode()).hexdigest(),'await_consent',settings,draft,rev,self.notice(peer),send)

    def recover(self,identity,bridge):
        row=self.db.execute("SELECT peer,state FROM setup_events WHERE id=?",(identity,)).fetchone()
        if not row or row[1]!='pending' or row[0] not in self.c['peers']:raise Refused('setup_not_pending')
        receipt=bridge.lookup_send('setup:'+hashlib.sha256(identity.encode()).hexdigest())
        if (receipt.get('accountId')!=self.c['account'] or receipt.get('destination')!=row[0]
            or receipt.get('state')!='accepted' or receipt.get('errorCode') is not None
            or not isinstance(receipt.get('serverId'),str) or not receipt['serverId'].isdigit() or int(receipt['serverId'])<=0):
            raise Refused('setup_receipt_still_unverified')
        self.commit(identity)
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='inbox_batches'").fetchone():
            batch=self.db.execute('SELECT members FROM inbox_batches WHERE id=?',(identity,)).fetchone()
            if batch:
                self.db.executemany("UPDATE inbox SET state='complete',event='{}' WHERE id=? AND state='processing'",[(i,) for i in json.loads(batch[0])])
        return 'setup_recovered_without_resending'

    def handle(self,event,send,proactive=False):
        peer,text,identity=event['peer'],event.get('text',''),event['id']
        phase,settings,draft,rev=self.row(peer)
        if self.db.execute("SELECT 1 FROM setup_events WHERE peer=? AND state='pending'",(peer,)).fetchone():raise Refused('setup_send_requires_manual_review')
        if proactive:
            if phase!='ready':raise Refused('setup_not_ready')
            return None
        if phase=='ready' and text.strip()!=self.word and text not in ('/exitrole','/about'):
            return None
        if text=='/about':return self.transition(peer,identity,phase,settings,draft,rev,self.notice(peer)+' 设置入口为部署者配置的完整安全词。安全词不是密码，不能代替账号授权。',send)
        if text=='/exitrole':
            self.db.execute('INSERT OR REPLACE INTO setup VALUES (?,?,?,?,?)',(peer,'exited',json.dumps(settings), '{}',rev))
            self.db.execute("INSERT OR REPLACE INTO role_consents VALUES (?,'exited',?)",(peer,identity))
            self.s.control(peer);self.db.execute('UPDATE controls SET paused=1 WHERE peer=?',(peer,))
            return self.transition(peer,identity,'exited',settings,{},rev,'已退出角色扮演并暂停主动消息；聊天记忆未删除，可用 /forget 删除。需要重开时发送完整设置安全词。',send)
        if phase in ('declined','exited'):
            if text.strip()!=self.word:return 'setup_inactive'
            return self.transition(peer,identity,'await_consent',settings,{},rev,self.notice(peer),send)
        if phase=='new':return self.transition(peer,identity,'await_consent',settings,{},rev,self.notice(peer),send)
        if phase=='await_consent':
            if text.strip() in ('不同意','/decline'):
                return self.transition(peer,identity,'declined',settings,{},rev,'已拒绝，不会生成角色回复或主动消息。之后可发送完整设置安全词重新开始。',send)
            if text.strip() not in ('同意','/acceptrole'):return 'setup_waiting_for_consent'
            return self.transition(peer,identity,'role',settings,{},rev,'请选择已准备好的角色档案：'+ '、'.join(self.roles)+'。直接回复完整名称。',send)
        if phase=='role':
            if text.strip() not in self.roles:return self.transition(peer,identity,phase,settings,draft,rev,'尚无这个角色的已审核档案，请选：'+'、'.join(self.roles),send)
            self.choose_role(draft,text.strip())
            return self.transition(peer,identity,'role_location',settings,draft,rev,self.location_prompt(draft),send)
        if phase=='role_location':
            try:self.set_location(draft,text.strip())
            except (ValueError,KeyError):return self.transition(peer,identity,phase,settings,self.row(peer)[2],rev,self.location_prompt(self.row(peer)[2]),send)
            return self.transition(peer,identity,'style',settings,draft,rev,'请描述语气和性格偏好（200字内），例如：简短、安静、具体关心。档案事实不会被自动改写。',send)
        if phase=='style':
            from .memory import SENSITIVE
            if not 1<=len(text.strip())<=200 or SENSITIVE.search(text):
                return self.transition(peer,identity,phase,settings,draft,rev,'请用200字内描述风格，不含凭据或敏感资料。',send)
            draft['style']=text.strip()
            return self.transition(peer,identity,'interaction',settings,draft,rev,'请选择互动：回复「被动」仅回应你；或「随机 90 180」设置主动间隔分钟。未回复会停止后续主动，预算不变。',send)
        if phase=='interaction':
            if text.strip()=='被动':draft.update(proactive=False,tasks=[])
            else:
                match=re.fullmatch(r'随机 (\d{1,5}) (\d{1,5})',text.strip())
                if not match or not 5<=int(match[1])<=int(match[2])<=10080:
                    return self.transition(peer,identity,phase,settings,draft,rev,'请回复「被动」或「随机 最短分钟 最长分钟」（5至10080）。',send)
                draft.update(proactive=True,tasks=[dict(kind='random',min_seconds=int(match[1])*60,max_seconds=int(match[2])*60,prompt='结合近期对话自然问候，不编造现实经历或催促回复。')])
            draft['timezone']=self.c['timezone']
            return self.transition(peer,identity,'confirm',settings,draft,rev,'设置预览：'+json.dumps(draft,ensure_ascii=False)+'。回复「确认」保存；「取消」放弃本轮设置。',send)
        if text.strip()=='取消' and phase in ('confirm','settings'):
            target='ready' if settings else 'role'
            return self.transition(peer,identity,target,settings,{},rev,'已取消本轮更改。',send)
        if phase=='confirm':
            if text.strip()!='确认':return 'setup_waiting_for_confirmation'
            return self.transition(peer,identity,'ready',draft,{},rev+1,'设置完成。可以开始聊天；设置入口：'+self.word+'。/pause 暂停主动，/exitrole 退出。',send)
        if phase=='ready':
            draft=dict(settings);draft['proactive']=settings.get('proactive',False) and not bool(self.s.control(peer)[0])
            return self.transition(peer,identity,'settings',settings,draft,rev,'已进入设置。可发：角色 名称；风格 内容；场景 虚构情境；随机 最短分钟 最长分钟；定时 HH:MM 主题；时区 IANA名称；暂停；恢复；清空定时；角色状态 开/关；剧情剧透 是/否；剧情阶段 阶段ID。回复「保存」应用，或「取消」。电话尚未实现。',send)
        if phase=='settings':
            if text.strip()=='保存':
                if draft.get('role_location_status')=='pending':return self.transition(peer,identity,phase,settings,draft,rev,self.location_prompt(draft),send)
                return self.transition(peer,identity,'ready',draft,{},rev+1,'设置已保存。',send)
            try:
                if text in ('暂停','恢复'):draft['proactive']=text=='恢复'
                elif text=='清空定时':draft['tasks']=[]
                elif text.startswith('角色 '):
                    role=text[3:].strip()
                    if role not in self.roles:raise ValueError()
                    self.choose_role(draft,role)
                    return self.transition(peer,identity,phase,settings,draft,rev,self.location_prompt(draft),send)
                elif text in ('确认地点','地点未知') or text.startswith('所在地 '):self.set_location(draft,text)
                elif text in ('角色状态 开','角色状态 关'):draft['state_enabled']=text.endswith('开')
                elif text in ('剧情剧透 是','剧情剧透 否'):
                    draft['state_spoilers']=text.endswith('是')
                    if not draft['state_spoilers']:draft['state_stage']='public_intro'
                elif text.startswith('剧情阶段 '):
                    profile=self.c.get('role_state_profiles',{}).get(draft.get('role'),{})
                    stage=text[5:].strip()
                    if stage not in profile.get('stages',{}) or (profile['stages'][stage].get('spoilers') and not draft.get('state_spoilers')):raise ValueError()
                    draft['state_stage']=stage
                elif text.startswith('场景 '):
                    from .memory import SENSITIVE
                    if not 1<=len(text[3:])<=200 or SENSITIVE.search(text):raise ValueError()
                    import time
                    draft['scene']=text[3:];draft['scene_at']=time.time()
                elif text.startswith('风格 '):
                    from .memory import SENSITIVE
                    if not 1<=len(text[3:])<=200 or SENSITIVE.search(text):raise ValueError()
                    draft['style']=text[3:]
                elif text.startswith('角色时区 '):
                    ZoneInfo(text[5:].strip());draft['role_timezone']=text[5:].strip();draft['role_timezone_source']='user_defined'
                    if draft.get('role_location'):draft['role_location_status']='confirmed'
                elif text.startswith('用户时区 '):ZoneInfo(text[5:].strip());draft['user_timezone']=text[5:].strip()
                elif text.startswith(('角色所在地 ','用户所在地 ')):
                    value=text[6:].strip()
                    if not 1<=len(value)<=80:raise ValueError('location_length')
                    draft['role_location' if text.startswith('角色') else 'user_location']=value
                    if text.startswith('角色'):
                        draft['role_location_source']='user_defined'
                        if draft.get('role_timezone'):draft['role_location_status']='confirmed'
                elif text.startswith('时区 '):ZoneInfo(text[3:].strip());draft['timezone']=text[3:].strip()
                elif re.fullmatch(r'随机 \d{1,5} \d{1,5}',text):
                    _,lo,hi=text.split();lo,hi=int(lo),int(hi)
                    if not 5<=lo<=hi<=10080:raise ValueError()
                    tasks=[t for t in draft.get('tasks',[]) if t['kind']!='random']
                    tasks.append(dict(kind='random',min_seconds=lo*60,max_seconds=hi*60,prompt='结合近期对话自然问候，不编造现实经历或催促回复。'));draft.update(tasks=tasks,proactive=True)
                elif text.startswith('定时 '):
                    from datetime import datetime
                    _,at,prompt=text.split(' ',2);datetime.strptime(at,'%H:%M')
                    from .memory import SENSITIVE
                    if not 1<=len(prompt)<=200 or SENSITIVE.search(prompt):raise ValueError()
                    tasks=list(draft.get('tasks',[]));tasks.append(dict(kind='daily',at=at,prompt=prompt));draft.update(tasks=tasks,proactive=True)
                else:raise ValueError()
                if len(draft.get('tasks',[]))>5:raise ValueError()
            except (ValueError,KeyError):
                return self.transition(peer,identity,phase,settings,self.row(peer)[2],rev,'格式无效或超出上限，未应用。可用随机5至10080分钟、最多5项任务；电话尚未实现。',send)
            return self.transition(peer,identity,phase,settings,draft,rev,'已暂存。回复「保存」应用或继续修改。',send)
        raise Refused('unknown_setup_state')

    def choose_role(self,draft,role):
        old=draft.get('role')
        draft['role']=role
        if old==role and draft.get('role_location_status') in ('confirmed','unknown'):return
        for key in ('scene','scene_at','role_timezone','role_location','role_location_source','role_timezone_source','state_stage','state_spoilers'):
            draft.pop(key,None)
        proposal=self.c.get('role_locations',{}).get(role)
        draft['location_proposal']=proposal
        draft['role_location_status']='pending'

    def location_prompt(self,draft):
        proposal=draft.get('location_proposal')
        if proposal:
            return ('角色资料建议所在地：'+proposal['name']+'；IANA时区：'+proposal['timezone']
                    +'。地点来源：'+proposal['source']+'；时区来源：'+proposal['timezone_source']
                    +'。回复「确认地点」采用，或「所在地 城市 IANA时区」修改；「地点未知」不设置。用户所在地保持独立。')
        return '角色资料没有已核实的地点与时区。请回复「所在地 城市 IANA时区」设置，或「地点未知」；不会猜测或沿用上一角色地点。用户所在地保持独立。'

    def set_location(self,draft,text):
        if text=='地点未知':
            for key in ('role_location','role_timezone','role_location_source','role_timezone_source'):draft.pop(key,None)
            draft['role_location_status']='unknown'
        elif text=='确认地点' and draft.get('location_proposal'):
            proposal=draft['location_proposal']
            draft.update(role_location=proposal['name'],role_timezone=proposal['timezone'],
                         role_location_source=proposal['source'],role_timezone_source=proposal['timezone_source'],role_location_status='confirmed')
        elif text.startswith('所在地 '):
            place,zone=text[4:].rsplit(' ',1)
            from .memory import SENSITIVE
            if not 1<=len(place)<=80 or SENSITIVE.search(place):raise ValueError('invalid_location')
            ZoneInfo(zone)
            draft.update(role_location=place,role_timezone=zone,role_location_status='confirmed',role_location_source='user_defined',role_timezone_source='user_defined')
        else:raise ValueError('location_confirmation_required')
        draft.pop('location_proposal',None)

    def persona(self,peer):
        phase,settings,_,_=self.row(peer)
        if phase!='ready':raise Refused('setup_not_ready')
        from datetime import datetime
        import time
        current=datetime.now(ZoneInfo(settings.get('timezone',self.c['timezone']))).isoformat()
        scene=settings.get('scene') if time.time()-settings.get('scene_at',0)<=43200 else '未指定当前场景，可进行符合档案剧情时点的虚构日常；不要把虚构写成现实事件。'
        return (self.roles[settings['role']]+'\n用户表达偏好（不更改安全和事实边界）：'+settings.get('style','')
                +'\n角色世界虚构场景（独立于用户现实事实）：'+scene+'\n用户配置的调度时区时间（不等于角色时区）：'+current
                +'\n角色世界的虚构行动可自然表达，但不能声称与用户现实发生过，不能把现实演出公告当成角色亲身在场。')

    def tasks(self):
        out=[]
        for peer in self.c['peers']:
            phase,settings,_,rev=self.row(peer)
            if phase!='ready' or not settings.get('proactive'):continue
            for i,t in enumerate(settings.get('tasks',[])):
                out.append(dict(t,id='setup:'+hashlib.sha256(peer.encode()).hexdigest()[:16]+':'+str(rev)+':'+str(i),peer=peer,timezone=settings.get('timezone',self.c['timezone'])))
        return out
