# CharaHarbor · 角色的港湾

**可配置的微信虚构角色陪伴，让人设、记忆和互动各有归处。**

[English](README.md) | **简体中文**

[![平台验证](https://github.com/Cody-kin/CharaHarbor/actions/workflows/test.yml/badge.svg)](https://github.com/Cody-kin/CharaHarbor/actions/workflows/test.yml)
[![MIT 许可](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

围绕可编辑角色建立陪伴体验：语气与风格、用户和角色各自的时区、持久对话、可纠正记忆、定时或随机互动，以及可选图片能力。文字与图片可独立配置供应商、模型和密钥，例如 DeepSeek 负责文字、OpenAI 负责图片。

**这是实验软件，不是微信官方客户端。** Python 核心与入口已通过 Windows、macOS、Linux CI；真实微信仍需单独安装并授权本机桥，由本人扫码。三平台真实微信登录和手机收发尚未完成验收，不能称为零配置部署。

## 无需账号，先试演示

1. 下载并解压[源码发布包](https://github.com/Cody-kin/CharaHarbor/releases)。
2. 安装带 pip/venv 的 [Python 3.11+](https://www.python.org/downloads/)，Windows 勾选 PATH。
3. 在解压后的项目目录启动：

| Windows | macOS | Linux |
| --- | --- | --- |
| 双击 `start.cmd` | 运行 `sh start.command` | 运行 `sh start.sh` |

安装器创建本地 `.venv`，下载固定版本的时区/媒体依赖并打开菜单。选择 **1 离线演示**，不需要微信、密钥或付费 API。首次安装依赖需要联网。运行菜单和会话设置命令目前为中文，英文指南逐步解释其含义。

`python3 install.py --no-deps --smoke` 可离线检查核心，详见[依赖与平台边界](docs/zh-CN/user-guide.md)。原有入口文件名继续兼容。

## 可以配置什么

| 能力 | 当前范围 |
| --- | --- |
| 角色与表达 | 带来源的角色档案、剧情/剧透范围、风格、有界状态与关系参数、每角色颜文字 |
| 对话与记忆 | 消息聚合/去重、近期上下文、有限中文明确事实提取、查看/更正/遗忘、联系人与角色隔离 |
| 主动互动 | 每日/随机任务、时区、暂停、共享限制、未回复前不继续主动 |
| 图片 | 授权的 PNG/JPEG/GIF 理解（GIF 首帧）、普通图库图片、显式 `/image 描述` 生图 |
| 模型供应商 | OpenAI/DeepSeek 文字适配；独立 OpenAI 图片供应商/模型/密钥，其他供应商需实现和测试 |
| 当前资料 | 真实 IANA 时区时钟、可选 RSS/Atom 元数据更新、受控查询/搜索接口 |

默认离线，没有主动任务、自动记忆采集或图片处理。真实模式限定精确私聊白名单，并分步说明、取得同意；参与者可查看设置和退出扮演。不自动扩大到所有好友，不回复群聊。

## 阅读指南

从[中文文档目录](docs/zh-CN/index.md)开始：

- [安装、配置、运行与升级](docs/zh-CN/user-guide.md)
- [微信桥、身份和本人登录](docs/zh-CN/wechat-bridge.md)
- [首次同意、设置和恢复](docs/zh-CN/onboarding.md)
- [角色档案](docs/zh-CN/character-profiles.md)、[状态与表达](docs/zh-CN/character-states.md)、[资料更新](docs/zh-CN/source-updates.md)
- [功能与限制](docs/zh-CN/features.md)、[隐私与故障排查](docs/zh-CN/security.md)、[平台实测](docs/zh-CN/platform-validation.md)

每篇都有完整英文对应版本与显著切换链接。[English documentation](docs/en/index.md)。

## 真实使用前的限制

- 公开版付费服务测试使用模拟 HTTP，未使用真实付费凭证；账号权限、模型质量、费用和手机送达需独立验收。
- 记忆为保守规则实现，不是无限或任意自然语言记忆；每联系人/角色最多 100 条事实。
- 生图是插画，不是真实照片，不附带参考立绘；普通图片**不是微信原生表情**。原生贴纸发送、语音条和电话未实现。
- 串行图片请求可能让后续聊天等待，超时上限 90 秒。未知发送结果会停止待审，不盲目重试；停机消息可能跳过。
- 程序内费用预留和限速不是供应商硬消费上限。状态为明文存储；Windows 真实使用前需自行检查 ACL。

详见[完整矩阵](docs/zh-CN/features.md)与[安全指南](docs/zh-CN/security.md)。角色扮演是虚构陪伴，不是专业治疗，也不声称是现实真人。本项目与腾讯/微信及任何作品官方无关联。

## 目录与开发

```text
companion/       运行核心、模型供应商、认证微信桥适配器
examples/        合成配置与评测场景
roles/           可编辑、有来源的虚构角色概括
docs/en/         完整英文指南
docs/zh-CN/      完整简体中文指南
tests/           合成测试，不含私人账号或聊天
tools/           平台验收、文档与源码安全检查
start.*          兼容的系统入口
install.py       本地环境/依赖安装器
launch.py        配置及前台启动器
```

```sh
python3 install.py --smoke
python3 tools/platform_smoke.py
python3 tools/check_docs.py
python3 tools/scan_public.py .
```

报告问题请提供 OS、Python/桥版本、安全原因码和合成复现，不附 token、账号 profile、聊天数据库或私人记忆。贡献应保留安全默认，并同步更新**两种语言**；[验收说明](docs/zh-CN/platform-validation.md)明确 CI 能证明什么。

## 许可与分发

[MIT](LICENSE) 仅涵盖项目代码，不涵盖第三方角色、图片、声音或剧本。发布包不含桥二进制、登录资料、私人聊天/记忆或密钥。非官方桥可能失效或引发账号限制，使用前阅读[上游平台说明](https://github.com/thisnick/agent-wechat/blob/main/PLATFORM-ACCEPTANCE.md)。
