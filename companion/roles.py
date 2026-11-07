"""Reviewed role dossiers; no unbounded scraping or silent profile activation."""
import json
from pathlib import Path
from urllib.parse import urlsplit


def compile_profile(profile):
    from .core import Refused
    if profile.get('expressions'):
        from .expressions import validate
        validate(profile['expressions'])
    if profile.get('fictional') is not True:raise Refused('fictional_role_required')
    for name in ('name','revision','plot_point','voice_style'):
        if not isinstance(profile.get(name),str) or not 1<=len(profile[name])<=2000:
            raise Refused('invalid_role_profile')
    sources={s['id']:s for s in profile.get('sources',[])}
    for s in sources.values():
        u=urlsplit(s['url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password:
            raise Refused('invalid_role_source_url')
    facts=[]
    for f in profile.get('facts',[]):
        if not isinstance(f.get('text'),str) or len(f['text'])>500 or f.get('source') not in sources:
            raise Refused('unsourced_role_fact')
        if f.get('confidence')=='verified' and sources[f['source']].get('status')=='reviewed':facts.append(f['text'])
    portrait=[]
    for section in ('traits','relationships'):
        for entry in profile.get(section,[]):
            if (not isinstance(entry.get('id'),str) or not isinstance(entry.get('text'),str)
                or len(entry['text'])>500 or entry.get('origin') not in ('official','inference','user_defined')):
                raise Refused('invalid_portrait_entry')
            origin=entry['origin'];source=sources.get(entry.get('source'))
            if origin!='user_defined' and source is None:raise Refused('unsourced_portrait_entry')
            approved=(origin=='user_defined' and entry.get('approved_user_override') is True)
            approved|=(origin=='official' and entry.get('confidence')=='verified' and source.get('status')=='reviewed') if source else False
            approved|=(origin=='inference' and entry.get('confidence')=='probable' and source.get('status')=='reviewed') if source else False
            if approved:portrait.append({'section':section,'origin':origin,'text':entry['text'],'context':entry.get('context','unspecified')[:300],'source':entry.get('source'),'confidence':entry.get('confidence')})
    version=profile.get('work_version','未指定作品版本；不自行混用其他改编')
    spoilers=profile.get('spoiler_scope','未指定剧透范围；不自行引入后续剧情')
    if not isinstance(version,str) or not isinstance(spoilers,str) or len(version)+len(spoilers)>2000:raise Refused('invalid_work_scope')
    prompt=('你在已获同意的虚构角色扮演中以'+profile['name']+'的第一人称交流。\n'
            +'作品版本：'+version+'\n剧情时点：'+profile['plot_point']+'\n剧透范围：'+spoilers+'\n表达方式：'+profile['voice_style']
            +'\n经来源核实的角色设定：'+json.dumps(facts,ensure_ascii=False)
            +'\n有条件的角色画像（inference仅推测，user_defined为用户自设，不冒充官方）：'+json.dumps(portrait,ensure_ascii=False)
            +'\n未核实剧情不当事实；不要把角色设定当成与用户现实发生的经历。'
            +'普通你是谁/叫什么按角色名自然回答，不主动插入AI或虚构说明。'
            +'若用户明确询问现实真实性，简短诚实说明是AI角色扮演，不冗长说教。')
    if len(prompt)>8000:raise Refused('role_profile_too_large')
    return prompt


def load_profile(path):
    p=Path(path)
    if p.stat().st_size>65536:raise ValueError('role profile too large')
    profile=json.loads(p.read_text(encoding='utf-8'))
    return profile,compile_profile(profile)


def revision_diff(before,after):
    """Local review aid; never activates a revised role or fetches source content."""
    compile_profile(before);compile_profile(after)
    def indexed(p):
        return {section+':'+entry['id']:entry for section in ('traits','relationships') for entry in p.get(section,[])}
    a,b=indexed(before),indexed(after)
    return {'from_revision':before['revision'],'to_revision':after['revision'],
            'added':sorted(b.keys()-a.keys()),'removed':sorted(a.keys()-b.keys()),
            'changed':sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]),
            'scope_changed':any(before.get(k)!=after.get(k) for k in ('work_version','plot_point','spoiler_scope'))}


def location_suggestion(profile):
    """Only reviewed, sourced geography is a suggestion, never auto-activated."""
    from zoneinfo import ZoneInfo
    from .core import Refused
    geo=profile.get('location')
    if geo is None:return None
    sources={s['id']:s for s in profile.get('sources',[])}
    if not isinstance(geo,dict):raise Refused('invalid_role_location')
    if geo.get('confidence')!='verified':return None
    source=sources.get(geo.get('source'))
    zone_source=sources.get(geo.get('timezone_source'))
    if not source or not zone_source or any(s.get('status')!='reviewed' for s in (source,zone_source)):
        return None
    place,zone=geo.get('name'),geo.get('timezone')
    if not isinstance(place,str) or not 1<=len(place)<=80 or not isinstance(zone,str):raise Refused('invalid_role_location')
    ZoneInfo(zone)
    return dict(name=place,timezone=zone,source=source['url'],timezone_source=zone_source['url'],revision=profile['revision'])
