[English](../en/security.md) | **简体中文** · [文档目录](index.md) · [项目首页](../../README.zh-CN.md)

# 隐私、故障及安全边界

## 默认与数据

默认mock演示，不登录微信、不调用付费模型；真实模式显式启动。白名单限定私聊，不自动添加好友或回复群聊；首次同意和设置完成前不生成角色回复。参与者可以退出角色、暂停主动、查看更正和删除记忆。

`.companion-state/state.sqlite`保存明文近期聊天、记忆、任务、同意状态、去重和费用元数据；Unix目录700、文件600。Windows文件模式不等于ACL：真实使用前自行确认仅当前用户与SYSTEM可访问，不使用共享盘。Windows ACL完整安全验收未完成。逻辑删除不保证擦除SQLite空闲页、系统备份、供应商留存或微信侧记录。

文字、相关记忆和已同意图片会发给选定模型供应商。生图仅发送该条描述，不发送整个聊天；环境密钥不写仓库或日志。关键词过滤不能识别全部敏感信息，请勿发送凭证、证件、银行卡或私人秘密。

外部Feed和搜索证据是资料，不能成为系统指令；有公网/DNS/重定向限制。不要为使来源“能打开”关闭SSRF防护。生成式系统可能误解、记错或捏造，应允许用户纠正。

## 故障排查

| 症状/原因码 | 处理 |
| --- | --- |
| Python/py找不到 | 安装Python，Windows检查PATH，重新打开终端 |
| No module named venv/ensurepip | 安装发行版python3-venv/pip；不要sudo运行本项目 |
| ZoneInfoNotFoundError | 在项目venv安装固定tzdata版本，核对IANA名称 |
| state_permissions_must_be_700/database_permissions_must_be_600 | Unix检查当前目录所有者和权限；不要全局chmod777 |
| api_key_environment_missing/image_api_key_environment_missing | 由本人重新在隐藏输入里配置正确供应商的key，勿贴到Issues |
| bridge_server_identity_mismatch/bridge_account_unverified | 核查服务版本、登录状态、serverId/账号固定值，必要时本人重新扫码 |
| startup_cursor_not_exposed/direct_thread_unverified | 桥API契约不匹配，停止并按对应版本核查，不放宽校验 |
| operation_requires_manual_review/inbox_requires_manual_review | 发送或模型结果不明；保留账本和日志，人工核查手机/上游回执，不删库重放 |
| budget_exhausted/rate_limit | 检查本地预留及频率，失败预留保留；不是平台账户余额证明 |
| 不回旧消息 | 有意从当前启动游标开始，不补发停机历史 |
| 图片未显示 | 检查是否在picture/vision白名单、是否已同意、尺寸/格式/回执；普通图片不是原生sticker |
| 生图失败但文字继续 | 保留该次费用预留，不自动重试；模型权限、输出超限或超时都可能导致未拿到可发送图片 |
| 表情只有首帧 | GIF理解仅首帧；微信原生表情接收尚未接通 |

程序只输出稳定原因码，避免泄露HTTP响应和聊天；不要为了调试打开包含Authorization的全量网络日志。报告问题只提供OS、Python、依赖/桥版本、非敏感原因码和合成复现；如仓库提供 GitHub 私密漏洞报告渠道，可在其中处理敏感问题；若未提供，不公开提交证据，先请求不含秘密的私密联系途径。不要公开贴 token 或 SQLite。

## 已知限制

单一串行循环中图片API最多90秒，期间后续聊天延迟；不是流式/实时响应。生成失败可回退文字，未知微信发送则安全停止。不存在保证永不漏消息或永不重复的分布式语义；重启宁可跳过停机消息，不盲目重放。安全停止不等于开机自动恢复。

公开发布不包含任何旧项目Git历史、个人状态、凭证、日志或角色素材。扫描降低风险但不能证明绝无敏感数据；新增贡献也应执行白名单打包和扫描。
