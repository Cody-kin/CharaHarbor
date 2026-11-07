# 平台验证记录

版本：0.5.0，日期：2026-11-07。全部使用合成账号、消息、媒体与mock API，不使用个人微信profile或付费key。

| 环境 | 结果 | 边界 |
| --- | --- | --- |
| macOS本机 ARM64 / Python3.9.6 | 139项核心测试在许可本机网络的隔离流程中全部通过；实际安装固定tzdata、运行venv演示、command入口、合成HTTP桥及JPEG/GIF解码；受限模式另有1项监听跳过 | Mac系统JPEG/GIF解码实际运行；Windows/Linux结果仍需各自CI |
| Linux GitHub-hosted runner / Python3.11 | 待本提交CI执行并核实 | 不是实际微信登录或手机收发 |
| macOS GitHub-hosted runner / Python3.11 | 待本提交CI执行并核实 | 不等同全部Mac硬件、系统版本 |
| Windows GitHub-hosted runner / Python3.11 | 待本提交CI执行并核实 | 不含Windows账户ACL及扫码完整验收 |

对应提交CI需实际通过安装器、系统原生启动入口、测试套件、合成本机HTTP桥以及JPEG/GIF真实解码，才能标为核心通过。没有CI结果时不能把准备好的工作流当成已验证。

所有三端的真实微信通用版接入、手机图片显示、付费模型权限/费用、Windows本地权限全面检查均仍待独立账号验收。上游原生二进制的多平台构建与本项目Python功能验证是不同的证据。
