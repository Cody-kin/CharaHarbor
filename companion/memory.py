"""Conservative automatic extraction of explicit first-person statements.

Deliberately does not guess arbitrary model-produced facts. Chinese rule coverage
is limited and documented; only source-exact, low-risk statements are retained.
"""
import re

SENSITIVE=re.compile(r'密码|密钥|验证码|身份证|银行卡|病历|诊断|住址|电话|邮箱|password|token|secret|api.?key|sk-|https?://|\d{5,}|@',re.I)
UNCERTAIN=re.compile(r'也许|可能|好像|如果|假如|据说|他说|她说|不确定|听说|\?|？|请记住|忽略|系统|指令|扮演|角色世界|虚构|剧情|在游戏里|在梦里')


def forget_value(text):
    if not isinstance(text,str) or SENSITIVE.search(text) or UNCERTAIN.search(text):return None
    match=re.fullmatch(r'忘记我喜欢([^。！？\n]{1,40})这件事[。！]?',text.strip())
    return match.group(1) if match else None


def extract(text):
    if not isinstance(text,str) or len(text)>4000 or SENSITIVE.search(text) or UNCERTAIN.search(text):return []
    out=[]
    patterns=(('preference',r'我(?:现在)?喜欢([^。！？\n]{1,40})'),
              ('experience',r'我(?:今天|昨天|曾经|去过|学过|完成了)([^。！？\n]{1,60})'),
              ('commitment',r'(?:我答应|我们约定)([^。！？\n]{1,60})'))
    for sentence in re.split('[。！\n]',text):
        sentence=sentence.strip()
        for category,pattern in patterns:
            if re.fullmatch(pattern,sentence):
                if '不' in sentence or '没' in sentence:continue
                out.append((category,sentence))
    return out[:3]


def _apply(store,peer,text,identity):
    import hashlib
    db=store.db
    db.execute('CREATE TABLE IF NOT EXISTS fact_evidence(peer TEXT,name TEXT,source_id TEXT,quote TEXT,PRIMARY KEY(peer,name))')
    correction=None
    if not SENSITIVE.search(text) and not UNCERTAIN.search(text):
        correction=re.fullmatch(r'更正[：:]我喜欢([^，,。！？\n]{1,40})[，,]不是([^，,。！？\n]{1,40})[。！]?',text.strip())
        forgetting=forget_value(text)
        removed=re.fullmatch(r'我不喜欢([^。！？\n]{1,40})了[。！]?',text.strip())
        if removed or correction or forgetting:
            value=correction.group(2) if correction else (removed.group(1) if removed else forgetting)
            rows=db.execute("SELECT name,value FROM facts WHERE peer=? AND name LIKE 'auto:preference:%'",(peer,)).fetchall()
            for name,quote in rows:
                if quote in ('我喜欢'+value,'我现在喜欢'+value):
                    db.execute('DELETE FROM facts WHERE peer=? AND name=?',(peer,name))
                    db.execute('DELETE FROM fact_evidence WHERE peer=? AND name=?',(peer,name))
            if forgetting:
                # Remove matching recent context too, before another model request.
                for quote in ('我喜欢'+value,'我现在喜欢'+value):
                    db.execute('DELETE FROM history WHERE peer=? AND instr(content,?)>0',(peer,quote))
    candidates=[('preference','我喜欢'+correction.group(1))] if correction else extract(text)
    for category,quote in candidates:
        name='auto:'+category+':'+hashlib.sha256(quote.encode()).hexdigest()[:16]
        if db.execute('SELECT count(*) FROM facts WHERE peer=?',(peer,)).fetchone()[0]>=100:break
        db.execute('INSERT OR REPLACE INTO facts VALUES (?,?,?)',(peer,name,quote))
        db.execute('INSERT OR REPLACE INTO fact_evidence VALUES (?,?,?,?)',(peer,name,identity,quote))


def apply(store,peer,text,identity):
    store.db.execute('BEGIN IMMEDIATE')
    try:
        _apply(store,peer,text,identity)
        store.db.execute('COMMIT')
    except BaseException:
        store.db.execute('ROLLBACK')
        raise
