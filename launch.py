"""Interactive foreground launcher; entered keys live only in the child environment."""
import argparse
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys


def configure(path,ask=input):
    from companion.console import configure as configure_console
    configure_console()
    if path.exists():raise SystemExit('Config exists; edit it yourself. No overwrite performed.')
    c=json.loads(Path('examples/demo.json').read_text(encoding='utf-8'))
    print('配置不保存API key。真实模式需已安装并登录的本机微信桥；请先读 docs/WECHAT.md。')
    live=ask('启用真实微信/API? 输入 live，否则离线演示: ').strip()=='live'
    c['persona']=ask('角色、人设与说话风格（留空使用原创默认）: ').strip() or c['persona']
    c['timezone']=ask('用户IANA时区 [Asia/Shanghai]: ').strip() or 'Asia/Shanghai'
    c['role_timezone']=ask('角色IANA时区 [Asia/Tokyo]: ').strip() or 'Asia/Tokyo'
    if live:
        c.update(mode='live',provider=ask('文字供应商 openai/deepseek: ').strip(),model=ask('文字模型名（按账户权限填写）: ').strip(),
            account=ask('桥的精确 account ID: ').strip(),own_username=ask('登录账号的 ownUsername: ').strip(),bridge_server_id=ask('桥的 serverId: ').strip(),
            bridge_url=ask('本机桥URL [http://127.0.0.1:6174/v1]: ').strip() or 'http://127.0.0.1:6174/v1')
        c['peers']=[p.strip() for p in ask('允许的私聊精确ID（逗号分隔，不填昵称）: ').split(',') if p.strip()]
        c['onboarding_enabled']=True;c['settings_word']='/settings'
        c['setup_peer']=c['peers'][0] if c['peers'] else None
        c['auto_memory_peers']=[];c['vision_peers']=[];c['picture_peers']=[]
        print('默认不采集长期记忆、不理解图片、不主动联系。取得参与者同意后按指南配置。')
        if ask('配置独立OpenAI图片服务? 输入 yes: ').strip()=='yes':
            c['picture_peers']=list(c['peers'])
            c['image_generation']={'provider':'openai','model':ask('图片模型名: ').strip(),'quality':'medium',
                'reserve_usd':float(ask('每图程序内预留美元（不是供应商硬上限）: ')), 'peers':list(c['peers'])}
    from companion.core import validate
    validate(c)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(c,f,ensure_ascii=False,indent=2)
    print('配置已写入 config.local.json；首次私聊仍需声明同意。')


def main():
    from companion.console import configure as configure_console
    configure_console()
    os.chdir(Path(__file__).resolve().parent)
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',choices=['demo','configure','doctor','live']);args=p.parse_args()
    action=args.action
    if action is None:
        print('1 离线演示  2 配置向导  3 检查配置  4 启动真实微信（前台）')
        action={'1':'demo','2':'configure','3':'doctor','4':'live'}.get(input('选择: ').strip(),'demo')
    if action=='demo':return subprocess.call([sys.executable,'demo.py'])
    config=Path('config.local.json')
    if action=='configure':configure(config);return 0
    if not config.exists():raise SystemExit('先运行 launch.py configure')
    from companion.core import load
    c=load(config)
    if action=='doctor':
        from zoneinfo import ZoneInfo
        ZoneInfo(c['timezone'])
        print(json.dumps({'config':'valid','python':sys.version.split()[0],'platform':sys.platform,'mode':c['mode'],
            'chat_provider':c['provider'],'image_provider':c.get('image_generation',{}).get('provider','disabled'),
            'wechat':'not_contacted','network':'not_contacted'}));return 0
    if c['mode']!='live':raise SystemExit('当前配置为离线模式；真实模式必须显式配置。')
    environment=dict(os.environ)
    for key,label in [('COMPANION_API_KEY','文字API key'),('COMPANION_BRIDGE_TOKEN','现有本机桥token')]:
        if not environment.get(key):environment[key]=getpass.getpass(label+'（隐藏输入，不保存）: ')
    if c.get('image_generation',{}).get('peers') and not environment.get('COMPANION_IMAGE_API_KEY'):
        environment['COMPANION_IMAGE_API_KEY']=getpass.getpass('独立图片API key（隐藏输入，不保存）: ')
    return subprocess.call([sys.executable,'-m','companion','serve','--config',str(config),'--state','.companion-state','--live'],env=environment)


if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:raise SystemExit(130)
