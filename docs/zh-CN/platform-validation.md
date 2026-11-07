[English](../en/platform-validation.md) | **简体中文** · [文档目录](index.md) · [项目首页](../../README.zh-CN.md)

# 平台验证记录

运行基线：0.5.0；双语文档版：0.5.1（保留原运行代码，新增文档检查）。日期：2026-11-07（香港时间）。全部使用合成账号、消息、媒体与 mock API，不使用个人微信 profile 或付费 key。

已验证代码提交：`bd8c28132e59228314d294251f6e1f50a7703514`。三平台 [GitHub Actions 实际运行](https://github.com/Cody-kin/CharaHarbor/actions/runs/42324748815) 全部成功；最终 0.5.0 发布提交 `7050b7b4e89a3ffb2956091cd9d7744b39e06157` 的[三端 CI](https://github.com/Cody-kin/CharaHarbor/actions/runs/42324949751)也已全部通过；后续文档版结果见 [Actions](https://github.com/Cody-kin/CharaHarbor/actions)。

| 环境 | 结果 | 边界 |
| --- | --- | --- |
| macOS 本机 15.7.4 ARM64 / Python 3.9.6 | 140 项测试全部通过；实际安装固定 tzdata、venv 演示、command 入口、本机合成 HTTP 桥及系统 JPEG/GIF 解码 | 另一次受限环境测试有 1 项监听跳过，不用该次跳过结果替代实际验收 |
| Linux GitHub runner / Ubuntu 26.04 x64 / Python 3.11.18 | 140 项中 138 通过、2 项 Mac 专用测试跳过；安装、sh 入口、合成 HTTP 桥及独立 Pillow JPEG/GIF 解码全部成功 | 不代表所有 Linux 发行版 |
| macOS GitHub runner / 26.7.2 ARM64 / Python 3.11.9 | 140 项全部通过；安装、command 入口、合成 HTTP 桥及系统 JPEG/GIF 解码成功 | 不等同全部 Mac 硬件、系统版本 |
| Windows GitHub runner / Server 2025 x64 (10.0.26100) / Python 3.11.9 | 140 项中 138 通过、2 项 Mac 专用测试跳过；安装、PowerShell 入口、合成 HTTP 桥及独立 Pillow JPEG/GIF 解码全部成功 | 不含 Windows 账户 ACL 全面检查；未单独运行 Windows 11 桌面双击流程 |

首轮 Windows 演示失败，原因是重定向控制台采用旧编码时无法输出中文。已在命令行/配置向导边界明确使用 UTF-8，并新增强制 cp1252 环境的子进程回归测试；修复后实际 Windows CI 通过。没有忽略或掩盖原失败。

测试覆盖安装器、角色同意状态、配置、预算预留、记忆更正/删除/重启、消息聚合、去重、未知发送停止、合成 HTTP 桥、图片服务独立密钥契约及媒体解码。两项 Mac 专用测试在 Windows/Linux 跳过，但额外的平台 smoke 确实调用各自 Pillow 解码器处理 JPEG/GIF，并非只模拟平台名。

所有三端的真实微信通用版扫码、手机图片显示、付费模型权限/费用、Windows 本地权限全面检查仍待独立账号验收。本项目 Python 功能验证与上游原生桥二进制的多平台构建是不同证据。不能把三端核心测试通过称为微信全链路或零配置部署通过。
