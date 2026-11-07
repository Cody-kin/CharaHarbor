"""Per-character fictional state. No medical model, random identity swap, or sends."""
import hashlib
import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo


def validate_profile(p):
    from .core import Refused
    if not isinstance(p,dict) or p.get('version')!=1:raise Refused('invalid_character_state_profile')
    modes,stages=p.get('modes',{}),p.get('stages',{})
    if not isinstance(modes,dict) or not isinstance(stages,dict) or not isinstance(p.get('dynamics',{}),dict):raise Refused('invalid_state_structure')
    if not isinstance(p.get('transitions',[]),list) or len(p.get('transitions',[]))>32:raise Refused('invalid_state_transitions')
    if not 1<=len(modes)<=8 or not 1<=len(stages)<=12 or p.get('default_mode') not in modes:raise Refused('invalid_state_modes')
    for name,mode in modes.items():
        if not isinstance(name,str) or not name or not isinstance(mode,dict) or not isinstance(mode.get('guidance'),str) or not 1<=len(mode['guidance'])<=300:raise Refused('invalid_state_guidance')
        if mode.get('origin') not in ('official','inference','user_defined'):raise Refused('invalid_state_origin')
        if mode['origin']!='user_defined' and (mode.get('reviewed') is not True or not mode.get('sources')):raise Refused('unsourced_character_state')
        if not isinstance(mode.get('sources',[]),list) or any(not isinstance(x,str) for x in mode.get('sources',[])):raise Refused('invalid_state_source')
        from urllib.parse import urlsplit
        for source in mode.get('sources',[]):
            u=urlsplit(source)
            if u.scheme!='https' or not u.hostname or u.username or u.password:raise Refused('invalid_state_source')
    for stage in stages.values():
        if not isinstance(stage,dict) or not isinstance(stage.get('modes'),list) or not stage['modes'] or any(m not in modes for m in stage['modes']) or p['default_mode'] not in stage['modes']:raise Refused('invalid_state_stage')
        if type(stage.get('spoilers',False)) is not bool:raise Refused('invalid_state_spoilers')
    for edge in p.get('transitions',[]):
        if not isinstance(edge,dict) or edge.get('from') not in modes or edge.get('to') not in modes or not isinstance(edge.get('event'),str) or not 1<=len(edge['event'])<=40:raise Refused('invalid_state_transition')
        # Scene transitions are curated interpretation, never presented as a
        # clinical/canon algorithm or inferred from absence/fatigue/randomness.
        if edge.get('origin')!='user_defined' or edge['event'] in ('absence','fatigue','random','negative_feedback'):raise Refused('unsafe_state_transition')
    for field,default,lo,hi in (('fatigue_half_life',10800,1800,86400),('mood_half_life',5400,900,86400),('return_gap_days',7,1,60),('familiarity_half_life_days',14,7,180),('min_mode_seconds',600,60,86400),('random_amplitude',.03,0,.06)):
        value=p.get('dynamics',{}).get(field,default)
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise Refused('invalid_state_dynamics')
    rel=p.get('relationship',{})
    if not isinstance(rel,dict) or type(rel.get('enabled',False)) is not bool:raise Refused('invalid_relationship_profile')
    for field,default,lo,hi in (('hurt_delta',.03,.005,.05),('apology_recovery',.005,.001,.01),('explanation_recovery',.003,.001,.008),('calm_recovery',.001,0,.003)):
        value=rel.get(field,default)
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise Refused('invalid_relationship_dynamics')
    for field in ('cherished_aliases','dismissal_phrases'):
        values=rel.get(field,[])
        if not isinstance(values,list) or len(values)>16 or any(not isinstance(v,str) or not 1<=len(v)<=40 for v in values):raise Refused('invalid_relationship_vocabulary')
    return p


def signal(text,profile=None):
    """Conservative local evidence labels, not a universal sentiment classifier.

    Quoted, negated, ambiguous/question forms do not cause numeric penalties.
    Crisis text bypasses relationship effects; this module never delays sends.
    """
    if re.search(r'自杀|自傷|自伤|不想活|结束生命|suicid|kill myself|hurt myself',text,re.I):return 'urgent_support'
    rel=(profile or {}).get('relationship',{})
    if rel.get('enabled'):
        if not re.search(r'[“”「」『』"?？]|他说|她说|有人说|并不|不觉得|不是|没说',text):
            if any(v in text for v in rel.get('cherished_aliases',[])) and any(v in text for v in rel.get('dismissal_phrases',[])):return 'boundary_violation'
        if re.search(r'道歉个|才不道歉|不道歉|凭什么道歉',text):return 'contact'
        if re.search(r'对不起|對不起|抱歉|说重了|說重了',text):return 'repair_apology'
        if re.search(r'我的意思是|我不是那个意思|我不是那個意思|误会|誤會',text):return 'repair_explanation'
    return 'appreciation' if text.strip() in ('谢谢你','谢谢你。','辛苦了','有你陪着真好') else 'contact'


class CharacterState:
    def __init__(self,store):
        self.db=store.db
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS character_state(namespace TEXT PRIMARY KEY,profile TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS character_events(namespace TEXT,id TEXT,input_hash TEXT,frame TEXT,at REAL,PRIMARY KEY(namespace,id));
        CREATE TABLE IF NOT EXISTS character_controls(namespace TEXT PRIMARY KEY,paused INTEGER DEFAULT 0);
        ''')

    def paused(self,key):
        row=self.db.execute('SELECT paused FROM character_controls WHERE namespace=?',(key,)).fetchone()
        return bool(row and row[0])

    def control(self,key,action):
        from .core import Refused
        if action in ('pause','resume'):
            self.db.execute('INSERT OR REPLACE INTO character_controls VALUES (?,?)',(key,int(action=='pause')))
        elif action=='reset':
            # State reset is distinct from deleting the user's conversation facts.
            self.db.execute('DELETE FROM character_state WHERE namespace=?',(key,))
        else:raise Refused('unknown_state_control')

    def status(self,key):
        row=self.db.execute('SELECT body FROM character_state WHERE namespace=?',(key,)).fetchone()
        return dict(paused=self.paused(key),state=json.loads(row[0]) if row else None)

    def advance(self,key,profile,identity,now,zone,*,stage='public_intro',spoilers=False,interaction='contact',scene_event=None,incoming=True,seed='default'):
        from .core import Refused
        validate_profile(profile)
        if interaction not in ('contact','appreciation','boundary_violation','repair_apology','repair_explanation','urgent_support') or type(incoming) is not bool:raise Refused('invalid_state_signal')
        if not isinstance(identity,str) or not 1<=len(identity)<=256 or type(now) not in (int,float) or not math.isfinite(now):raise Refused('invalid_state_event')
        if stage not in profile['stages'] or (profile['stages'][stage].get('spoilers') and not spoilers):raise Refused('state_stage_requires_explicit_choice')
        digest=hashlib.sha256(json.dumps(profile,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        fingerprint=hashlib.sha256(json.dumps([digest,zone,stage,spoilers,interaction,scene_event,incoming,seed],ensure_ascii=False).encode()).hexdigest()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old_event=self.db.execute('SELECT input_hash,frame FROM character_events WHERE namespace=? AND id=?',(key,identity)).fetchone()
            if old_event:
                if old_event[0]!=fingerprint:raise Refused('state_event_conflict')
                self.db.execute('COMMIT');return json.loads(old_event[1])
            row=self.db.execute('SELECT profile,body FROM character_state WHERE namespace=?',(key,)).fetchone()
            if row and row[0]!=digest:raise Refused('state_profile_changed_reset_required')
            local=datetime.fromtimestamp(now,ZoneInfo(zone or 'UTC'));night=bool(zone) and (local.hour>=22 or local.hour<6)
            dynamics=profile.get('dynamics',{})
            s=json.loads(row[1]) if row else dict(mode=profile['default_mode'],at=now,mode_since=now,last_contact=None,familiarity=.5,fatigue=.65 if night else .25,valence=0.,stage=stage)
            if now<s['at']:raise Refused('state_clock_went_backwards')
            dt=now-s['at'];quiet_days=max(0,(now-s['last_contact'])/86400) if s['last_contact'] is not None else 0
            returning=incoming and quiet_days>=dynamics.get('return_gap_days',7)
            paused=self.paused(key)
            rel=profile.get('relationship',{});tension=s.get('tension',0.)
            stance='support_first' if interaction=='urgent_support' else 'neutral'
            reason='held'
            if s['mode'] not in profile['stages'][stage]['modes']:
                s.update(mode=profile['default_mode'],mode_since=now);reason='stage_boundary'
            if scene_event:
                edge=next((e for e in profile.get('transitions',[]) if e['from']==s['mode'] and e['event']==scene_event and e['to'] in profile['stages'][stage]['modes']),None)
                if not edge or paused:raise Refused('scene_transition_not_allowed')
                if now-s['mode_since']<dynamics.get('min_mode_seconds',600):raise Refused('state_transition_cooldown')
                s.update(mode=edge['to'],mode_since=now);reason='explicit_fictional_scene:'+scene_event
            if not paused:
                bucket=int(now//3600)
                n=int.from_bytes(hashlib.sha256(json.dumps([seed,key,bucket]).encode()).digest()[:4],'big')/(2**32-1)
                target=(.65 if night else .25)+(n-.5)*2*dynamics.get('random_amplitude',.03)
                s['fatigue']=round(max(.1,min(.8,target+(s['fatigue']-target)*2**(-dt/dynamics.get('fatigue_half_life',10800)))),4)
                s['valence']=round(max(-.15,min(.15,(n-.5)*.1+(s.get('valence',0)-(n-.5)*.1)*2**(-dt/dynamics.get('mood_half_life',5400)) + (.01 if incoming and interaction=='appreciation' else 0))),4)
                # No neglect penalty: familiarity only drifts toward a neutral
                # baseline. It never grants/revokes service or drives messaging.
                if quiet_days>2:s['familiarity']=.5+(s['familiarity']-.5)*2**(-dt/(dynamics.get('familiarity_half_life_days',14)*86400))
                if incoming and interaction not in ('boundary_violation','urgent_support'):s['familiarity']=min(.8,s['familiarity']+(.015 if interaction=='appreciation' else .003 if tension==0 else 0))
                if rel.get('enabled') and incoming and interaction!='urgent_support':
                    # One bounded event per actual turn, never a global/user-value score.
                    if interaction=='boundary_violation':
                        delta=rel.get('hurt_delta',.03);tension=min(.4,tension+delta);s['familiarity']-=delta;stance='defend_boundary'
                    elif tension>0:
                        repair=rel.get('apology_recovery',.005) if interaction=='repair_apology' else rel.get('explanation_recovery',.003) if interaction=='repair_explanation' else rel.get('calm_recovery',.001) if dt>=60 else 0
                        repaired=min(tension,repair);tension-=repaired;s['familiarity']+=repaired
                        stance='consider_repair' if interaction.startswith('repair_') else 'reserved'
                s['familiarity']=round(max(.35 if rel.get('enabled') else .5,s['familiarity']),4)
            s['tension']=round(tension,4)
            if interaction=='urgent_support':stance='support_first'
            if incoming:s['last_contact']=now
            s.update(at=now,stage=stage)
            frame=dict(mode=s['mode'],guidance=profile['modes'][s['mode']]['guidance'],origin=profile['modes'][s['mode']]['origin'],sources=profile['modes'][s['mode']].get('sources',[]),fatigue=s['fatigue'],valence=s.get('valence',0),familiarity=s['familiarity'],returning=returning and not paused,paused=paused,reason=reason,fictional_only=True,tension=s['tension'],stance=stance)
            self.db.execute('INSERT OR REPLACE INTO character_state VALUES (?,?,?)',(key,digest,json.dumps(s)))
            self.db.execute('INSERT INTO character_events VALUES (?,?,?,?,?)',(key,identity,fingerprint,json.dumps(frame,ensure_ascii=False),now))
            self.db.execute('DELETE FROM character_events WHERE namespace=? AND rowid NOT IN (SELECT rowid FROM character_events WHERE namespace=? ORDER BY at DESC,rowid DESC LIMIT 200)',(key,key))
            self.db.execute('COMMIT');return frame
        except BaseException:
            if self.db.in_transaction:self.db.execute('ROLLBACK')
            raise


def prompt(frame):
    # The state engine has no tools, sends, factual memory writes, or authority to
    # weaken identity honesty and crisis safety. Scores are not a human diagnosis.
    visible={k:frame[k] for k in ('mode','guidance','fatigue','valence','familiarity','returning','paused','fictional_only','tension','stance')}
    return ('\n经配置允许的角色状态（虚构表演参数，不是现实身体/心理诊断，不是用户事实）：'+json.dumps(visible,ensure_ascii=False)
            +'。保持当前剧情与人物关系连续；普通疲惫、时间、未回复不改变叙事身份。疲惫只轻微影响节奏，不编造熬夜/受伤等现实原因，不拒绝服务。'
            +'久别可稍重新找聊天节奏，但不责怪、索取解释、惩罚、吃醋控制或催促；任何分数不代表用户价值或义务。不要在日常报分数或报状态。'
            +'被贬低自己或珍视的人时，可以按角色表达不满、明确为对方说话；不要误把音乐偏好分歧当侮辱，不机械辩论。解释或道歉可逐步缓和，不要求讨好、不立即抹掉上下文。紧急求助优先关心安全，不因关系变化延迟、忽略或拒绝；这些参数不改变实际发送延迟、权限或预算。'
            +'回应贬低时先表达自己的界限与在意之处，不反复科普或每次都以“不是的”开头。用户澄清后接住其具体意思，不因表达界限而自动自责道歉；上一轮已接受道歉，下一轮可自然续聊，不重复道歉、安抚或回顾冲突。'
            +'这是用户已选择的剧情状态；不主动泄露未允许剧情。不把虚构行动记成与用户现实共同经历。')
