# CharaHarbor · 角色的港湾

CharaHarbor 是面向虚构角色陪伴的实验性微信机器人，提供角色、语气、记忆、定时和随机互动。它与腾讯、微信或任何作品官方无关联。文字可选 OpenAI / DeepSeek，图片生成单独配置 OpenAI 模型和密钥。

**单入口安装核心，微信登录仍需本人扫码及配置本机桥；不是零配置的三端微信成品。** 不提供原生贴纸发送或电话，也不承诺所有平台的微信登录兼容。

## 开始使用

1. 从本仓库 **Code → Download ZIP** 下载并解压到自己的目录。
2. 安装 [Python 3.11+](https://www.python.org/downloads/)（Windows勾选PATH；最低3.9仅支持部分媒体功能）。
3. Windows 双击 `start.cmd`；macOS 运行 `sh start.command`；Linux 运行 `sh start.sh`。
4. 安装器仅创建当前目录 `.venv`，从PyPI安装已固定版本的时区/图片库，打开菜单。先选 **1 离线演示**，无需密钥或微信。
5. 真实使用先完成 [微信桥和扫码](docs/WECHAT.md)，再选 **2 配置向导 → 3 检查配置 → 4 启动真实微信**。

首次安装需要联网下载Python依赖。`python3 install.py --no-deps --smoke` 可离线检查核心；没有Python或微信登录材料时不能自动完成全部安装。

## 使用指南

- [完整安装、配置、密钥与常驻运行](docs/USER_GUIDE.md)
- [微信安装、本人扫码、身份与权限](docs/WECHAT.md)
- [功能与验收矩阵](docs/FEATURES.md)
- [隐私和故障排查](docs/SECURITY.md)
- [首次声明与安全词](ONBOARDING.md)、[角色档案与来源](ROLE_GUIDE.md)、[多状态角色](CHARACTER_STATES.md)、[12小时资料更新](RESEARCH.md)
- [三平台自动测试](https://github.com/Cody-kin/CharaHarbor/actions)；具体结果以对应提交的运行记录为准。

默认离线、无主动任务、无自动记忆采集。真实模式限定精确私聊ID，首次声明同意后才开始扮演；群聊与陌生人不会处理。角色是虚构陪伴，不冒充现实真人或专业治疗。

## 保留的能力

按联系人和角色隔离的近期上下文、有限规则长期记忆及查改删，消息停顿聚合与去重，定时/随机主动、未回复退避、暂停，原创或带来源的角色档案、多状态及可配置颜文字，双时区与受控资料查询，图片理解、授权图库普通图片发送，以及显式 `/image 描述` 生成插画。

图片生成接口与文字服务相互独立，例如 DeepSeek 文字 + OpenAI 图片；其他图片供应商需要实现 `ImageProvider.generate` 的适配，不是改个名字就能工作。复杂自动记忆、任意大厂接口、语音及电话未完成。生成图不是现实照片，当前不内置参考立绘或角色素材。

发布仅含源码、公共角色概括、合成测试和示例，不含任何个人微信账号、聊天、记忆库、API key或微信登录数据。新建干净历史，不公开任何现有私有仓库。

## 开发

```sh
python3 -m unittest discover -s tests -v
python3 install.py --smoke
python3 tools/platform_smoke.py
```

三平台CI验证核心、安装器、时区、合成HTTP桥和媒体解码；它不扫码微信，也不调用付费API。手机送达必须使用单独授权的测试账号验收。

MIT许可仅涵盖本项目代码；微信、角色及作品名称归其权利人所有。非官方微信桥有失效和账号受限风险，见[上游平台说明](https://github.com/thisnick/agent-wechat/blob/main/PLATFORM-ACCEPTANCE.md)。
