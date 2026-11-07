"""Per-character optional expressions; never append a canned emotion marker."""
import json


def validate(profile):
    from .core import Refused
    if not isinstance(profile,dict) or type(profile.get('enabled',False)) is not bool:
        raise Refused('invalid_expression_profile')
    window=profile.get('window',6);maximum=profile.get('maximum',1)
    if type(window) is not int or not 3<=window<=20 or type(maximum) is not int or not 0<=maximum<=window:
        raise Refused('invalid_expression_frequency')
    moods=profile.get('moods',{})
    if not isinstance(moods,dict) or len(moods)>8:raise Refused('invalid_expression_moods')
    for mood,examples in moods.items():
        if not isinstance(mood,str) or not 1<=len(mood)<=30 or not isinstance(examples,list) or len(examples)>6:
            raise Refused('invalid_expression_moods')
        if any(not isinstance(v,str) or not 1<=len(v)<=24 or any(ord(c)<32 for c in v) for v in examples):
            raise Refused('invalid_expression_example')
    return profile


def tokens(profile):
    return sorted({v for examples in profile.get('moods',{}).values() for v in examples},key=len,reverse=True)


def policy(profile,history,*,urgent=False):
    validate(profile)
    recent=[text for role,text in history if role=='assistant'][:profile.get('window',6)-1]
    choices=tokens(profile)
    used=sum(any(v in text for v in choices) for text in recent)
    allowed=profile.get('enabled',False) and not urgent and used<profile.get('maximum',1)
    last={v for v in choices if recent and v in recent[0]}
    examples={m:[v for v in values if v not in last] for m,values in profile.get('moods',{}).items()}
    return dict(allowed=allowed,examples=examples,blocked=sorted(last))


def context(profile,history,*,urgent=False):
    p=policy(profile,history,urgent=urgent)
    return ('\n此角色颜文字偏好（数据）：'+json.dumps(p,ensure_ascii=False)
            +'。可按当前情绪和上下文选一个，也可完全不用；不要每句添加，不替代实际图片，不凭颜文字制造情绪或要求安慰。allowed=false时本轮不用颜文字；频率控制不代表先前使用有错，不解释内部限制或为先前合适的使用道歉，自然继续聊天。严重危机保持清楚直接。')


def constrain(answer,profile,history,*,urgent=False):
    """Enforce configured known examples only; unknown variants remain model quality."""
    p=policy(profile,history,urgent=urgent);found=[];at=0;choices=tokens(profile)
    while at<len(answer):
        token=next((v for v in choices if answer.startswith(v,at)),None)
        if token:found.append((at,at+len(token),token));at+=len(token)
        else:at+=1
    keep=None
    if p['allowed']:
        keep=next((span for span in found if span[2] not in p['blocked']),None)
    remove=[span for span in found if span!=keep]
    for start,end,_ in sorted(remove,reverse=True):answer=answer[:start]+answer[end:]
    return answer.strip()
