# 微信桥、登录及权限

本项目不是腾讯官方客户端。依赖用户单独安装的 [agent-wechat](https://github.com/thisnick/agent-wechat) 本机HTTP桥；不随包附带原生二进制、微信登录文件或自动创建token。非官方协议可能失效或引发账号限制。

## 平台边界

[上游平台验收](https://github.com/thisnick/agent-wechat/blob/main/PLATFORM-ACCEPTANCE.md)列出Linux x64/ARM64、macOS ARM64、Windows x64/ARM64构建目标；已有官方profile接管仍限定Linux。构建目标不等于本项目真实微信端到端验收。不要把Mac/Windows官方微信的唯一profile交给未经验证的适配器，也不要同时运行两个写同一profile的进程。

当前通用版只验证合成桥契约，没有在三端分别完成独立账号扫码和手机收发。核心可跨平台运行，真实微信能力不能因此打包成“已验证三端一键登录”。

## 用户本人操作

1. 访问[上游Releases](https://github.com/thisnick/agent-wechat/releases)，按OS/CPU选择发布包，检查其校验和、版本要求与发布说明。也可按[安装文档](https://thisnick.github.io/agent-wechat/setup/install/)使用其npm CLI。不要复制陌生博客的一键脚本。
2. 桌面版按上游指引选本机hub、创建独立profile，由自己手机扫码确认。CLI方式按[连接账号](https://thisnick.github.io/agent-wechat/setup/connect/)文档操作；本项目不假定不同版本登录命令完全相同。
3. 本机桥只监听127.0.0.1，不公开端口。不为“方便连接”关闭认证、防火墙或证书验证。
4. 使用上游文档创建/选用限定该账号、必要读取与发送权限的token；保密保存，勿发到聊天或Issues。桥自身可能同步账号其他聊天和联系人，机器人白名单不等于桥只能读白名单。
5. 从上游状态/账号列表取serverId、account ID、ownUsername；从已添加联系人私聊取精确thread/peer ID。只确认本人或明确授权对象，不按昵称猜测。
6. 配置向导填写这些身份固定值和白名单，启动时本人隐藏输入token。验证失败必须查明原因，不删除固定值或绕过检查。

token最低权限名称可能随上游版本改变，按对应版本文档配置；本项目不需通话、群管理、好友管理或账户级公开访问。拒绝任何要求扩大这些权限的异常提示。

## 第一次验收

先用专用测试账号，确认收件人准确。完成首次声明同意后，发送一条新文字，检查手机收到一次回复。随后再授权一张非私密测试图片。生成普通图片需要额外图像API费用；失败时先查回执，不重复发送结果未知的任务。不要把服务“accepted”回执直接当成手机已显示。

原生贴纸发送、收藏/搜索表情管理不支持；普通PNG图片并非原生贴纸。电话继续搁置，本包不发起、接听或自动接听通话。当前不提供语音条生成。
