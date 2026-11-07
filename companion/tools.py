"""Read-only local tools; web access remains separately opt-in and source bounded."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo


def clock_context(zone,at=None,user_zone=None):
    current=datetime.now(timezone.utc) if at is None else datetime.fromtimestamp(at,timezone.utc)
    local=current.astimezone(ZoneInfo(zone))
    weekday=('星期一','星期二','星期三','星期四','星期五','星期六','星期日')[local.weekday()]
    value='\nTRUSTED_RUNTIME_TIME '+local.isoformat(timespec='seconds')+' '+weekday+' role_timezone='+zone
    if user_zone:
        user=current.astimezone(ZoneInfo(user_zone))
        value+='; configured_user_time='+user.isoformat(timespec='seconds')+' user_timezone='+user_zone
        value+=' role_minus_user_minutes='+str(int((local.utcoffset()-user.utcoffset()).total_seconds()/60))
    else:value+='; user_timezone=unknown'
    return value+'。这是服务器生成时刻，不是模型记忆或联网。角色时区是虚构设定，不证明用户位置；用户时区未知时询问。问你那里据角色时间，问我这里据用户时区；完整回应复合问题，不说无法知道当前时间，不编造天气新闻。'
