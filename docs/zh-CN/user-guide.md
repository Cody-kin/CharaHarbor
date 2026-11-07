[English](../en/user-guide.md) | **简体中文** · [文档目录](index.md) · [项目首页](../../README.zh-CN.md)

# 从安装到使用

## 1. 三端安装入口

先装Python 3.11+与pip/venv；只从python.org或操作系统受信任的软件源安装。Windows安装时选Add to PATH；Ubuntu可用发行版的python3、python3-venv、python3-pip。安装器不会sudo、改防火墙或全局安装软件。

| 平台 | 入口 | 终端替代 |
| --- | --- | --- |
| Windows | 双击 `start.cmd` | `py -3 install.py`，或 `powershell -File start.ps1` |
| macOS | 终端 `sh start.command` | `python3 install.py` |
| Linux | 终端 `sh start.sh` | `python3 install.py` |

macOS如Finder不能直接打开.command，使用上面的终端入口；不要关闭系统安全保护。PowerShell若阻止脚本，用start.cmd，不修改全局执行策略。Python不存在时，入口会失败，需要先完成安装。

安装器创建本项目 `.venv`，安装tzdata 2026.6；Python3.11+额外安装Pillow13.0.0。网络失败时可以修复后再次运行，不会覆盖用户配置。不要在运行中的项目目录升级；先Ctrl+C停止、确认没有未知发送，再在新目录部署。手动依赖安装：

```sh
python3 -m venv .venv
# Windows 把 .venv/bin/python 换为 .venv\Scripts\python.exe
.venv/bin/python -m pip install tzdata==2026.6 Pillow==13.0.0
.venv/bin/python launch.py
```

`python3 install.py --no-deps --smoke`只创建离线核心环境并运行合成演示，不安装依赖、不联系微信或模型。Python3.9仍可运行核心；Windows时区需tzdata，JPEG/GIF的非Mac解码需Python3.11+。

运行菜单和会话设置命令目前为中文；双语文档解释同一套命令，不代表英文输入会自动识别为设置命令。

## 2. 配置向导

菜单2或 `.venv/bin/python launch.py configure`。填写原创角色/性格/语气、用户和角色IANA时区。默认只演示；输入live才创建真实模式配置。角色、模型名、精确私聊白名单、本机桥身份由用户填写。生成 `config.local.json`，拒绝覆盖已有文件。

文字选择 `openai` 或 `deepseek`；模型名按自己的账户权限填写，不保证全部模型支持相同参数。图片选择单独的OpenAI模型，与文字供应商、模型和密钥无关。其他厂商需要实现适配和测试，当前不能声称“任何大厂都已支持”。

运行真实模式时，启动器隐藏询问文字key、现有桥token及（启用时）图片key；只传给子进程环境，不保存文件、不打印。也可自行由OS密钥管理工具注入：

| 环境变量 | 用途 |
| --- | --- |
| `COMPANION_API_KEY` | 所选文字服务商的key |
| `COMPANION_IMAGE_API_KEY` | 独立OpenAI图片key，不回退到文字key |
| `COMPANION_BRIDGE_TOKEN` | 用户已有且限定账号/私聊权限的本机微信桥token |

不要把key放入命令参数、配置、截图、GitHub Issues或聊天。远程多人同机环境可能读取进程环境，个人电脑应锁屏并限制本机访问。

## 3. 首次微信聊天

按[微信指南](wechat-bridge.md)启动并自行扫码。本项目不会添加好友、创建桥凭证或导入原微信profile。菜单3只检查本地配置，不联网；菜单4才运行真实接收循环。首次登录/启动后仅处理新的白名单私聊；首次声明、用户同意、分步角色与互动设置完成前不回复角色内容。

默认 `/settings` 精确独立消息进入设置，可配置安全词。`/about`看说明，`/exitrole`退出，`/acceptrole`重新同意。不要设置易与日常混淆的安全词。它不是密码，角色设置授权仍取决于发送者身份。

## 4. 功能配置

配置修改请先退出进程。`peers`为精确私聊ID；不要昵称、群ID、所有缓存联系人。以下列表只允许白名单子集，默认空：

- `auto_memory_peers`：取得对方同意后启用有限规则记忆；保存明确喜好、经历和约定直到更正或删除。
- `vision_peers`：对方同意图片发往文字/视觉模型；当前要求OpenAI，GIF只看首帧。
- `picture_peers`：允许普通图片发送；图库内容须由用户合法提供，并核对SHA256、标签与rights_confirmed。
- `image_generation.peers`：允许 `/image 描述` 将这条描述发给独立图片服务、再发普通图片。需同时列入picture_peers。
- `adaptive_state_peers`：角色档案配置多状态、关系与表达策略时启用；不是医学诊断，也不会因用户离开而惩罚。

图片示例（替换模型名，图片key独立注入）：

```json
{
  "picture_peers": ["精确私聊ID"],
  "image_generation": {
    "provider": "openai",
    "model": "账户可用的GPT图片模型",
    "quality": "medium",
    "reserve_usd": 0.20,
    "peers": ["精确私聊ID"]
  }
}
```

这是合并到已有配置的片段，不是完整配置。当前仅固定1024方形PNG；输出须符合1MiB/百万像素限制，否则如实回退文字，不自动重试。不会自动加角色参考图，也不传整段私聊或私人记忆给生图服务。生成图不等于现实照片，用户应使用 `/image` 明确请求插画。

## 5. 记忆、任务和退出

`/remember 名称=内容` 保存/更正，`/memory`查看，`/forget 名称`删除事实项，`/forget`删除当前私聊全部事实与近期上下文。**单项/forget不保证清除历史中的同义表达；完全遗忘用/forget。** 自然规则只识别明确句式，例如“我喜欢绿茶”“我去过京都”“我学过吉他”“我们约定周末散步”；可用“更正：我喜欢红茶，不是绿茶”或“忘记我喜欢红茶这件事”。不确定、提问、凭证等不保存，不能保证任意对话都记住。

任务参见examples/tasks.json：daily按配置时区触发，random在最短/最长间隔内随机。每次主动后，未收到用户新文字前不再主动；`/pause`暂停、`/resume`恢复。所有任务共享预算、限速和去重；紧急或错过任务不补发。默认不主动联系任何人，不会自动扩大好友范围。

Ctrl+C前台退出；状态目录中的STOP文件使下轮停止。途中的网络请求可能继续到超时，已经发送的内容不能撤回。重启从当前事件游标开始，停机和聚合中的旧消息可能跳过；有未知发送则拒绝重启并要求人工核查，绝不直接删除账本后重发。

## 6. 常驻与升级

Mac/Windows可保持前台终端打开；Linux可由自己的服务管理器运行 `.venv/bin/python launch.py live`，凭证用受保护的环境文件或OS密钥服务管理。仓库不安装开机服务、不开放远程端口。服务器内存建议至少2GiB，图片解码有额外峰值；不在这里运行本地大模型。

升级前停止当前进程；保留私有配置及数据，使用干净源码目录。数据库版本迁移没有通用自动回滚保证，不要在唯一生产数据上直接试验。再次启动不会补发历史消息。先用独立测试账号验证新桥版本与本项目的事件/回执契约。

## 7. 费用

daily_usd、project_usd、hourly_limit与reserve_usd为程序内保护。预留全额记账、失败/未知费用保留，不是平台硬上限或实际token结算。图片用自己的reserve_usd但共享日/项目账本。若预留低于真实费用，平台费用可能更高；自行检查供应商定价与余额，不凭订阅等级推定API免费。

参考：[OpenAI图片接口](https://developers.openai.com/api/reference/resources/images)、[DeepSeek接口](https://api-docs.deepseek.com/)。参数兼容与模型权限仍需使用者小额实测。
