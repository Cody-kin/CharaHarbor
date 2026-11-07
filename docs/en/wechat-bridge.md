**English** | [简体中文](../zh-CN/wechat-bridge.md) · [Documentation](index.md) · [Project home](../../README.md)

# WeChat bridge, login and permissions

CharaHarbor is not a Tencent client. It uses a separately installed local HTTP bridge, [agent-wechat](https://github.com/thisnick/agent-wechat). No bridge binary, login profile or automatic token creation is included. Unofficial protocols can stop working and may expose an account to restrictions.

## Platform boundary

The [upstream platform notes](https://github.com/thisnick/agent-wechat/blob/main/PLATFORM-ACCEPTANCE.md) describe Linux x64/ARM64, macOS ARM64 and Windows x64/ARM64 build targets. Existing official-profile takeover is described for Linux, not as a verified macOS/Windows migration path. Check the exact upstream release before use: build availability is not CharaHarbor end-to-end acceptance. Do not entrust your only desktop profile to an unverified adapter or run two writers against one profile.

This release validates a synthetic bridge contract on three OS runners. It does not establish successful QR login and mobile send/receive on each platform. Cross-platform Python entry points are not one-click WeChat login.

## User-controlled setup

1. Select the OS/CPU package from [upstream releases](https://github.com/thisnick/agent-wechat/releases). Verify checksums, release notes and system requirements. The upstream [installation guide](https://thisnick.github.io/agent-wechat/setup/install/) also describes its npm CLI. Avoid unknown one-line installer scripts.
2. Follow the upstream desktop hub/profile workflow or [account connection guide](https://thisnick.github.io/agent-wechat/setup/connect/). Personally scan and approve login. Commands may vary by version; this project deliberately does not invent a universal login command.
3. Keep the local bridge bound to `127.0.0.1`. Do not expose its port or disable authentication, TLS checks or firewall protections to make a connection work.
4. Choose/create a token under the upstream version's documented procedure, scoped to the intended account and necessary read/send operations. Do not put it in chat or Issues. The bridge may sync other account chats and contacts: the bot's allowlist is not a bridge-wide read restriction.
5. Obtain `serverId`, account ID and `ownUsername` from the bridge's account/status APIs, and the exact thread/peer ID from an authorized private chat. Never infer identity from a nickname.
6. Enter those fixed identity values and the allowlist in the wizard; provide the token through hidden runtime input. If verification fails, investigate rather than removing identity checks.

The exact minimal scope names depend on the upstream version. This project does not need calls, group administration, friend management or account-wide public access. Reject unexpected prompts to add them.

## First live acceptance check

Use a dedicated test account and verify the recipient. Complete disclosure/consent, send one new text and confirm exactly one reply on the phone. Then explicitly authorize one non-private test image. Generation costs extra; inspect receipts before retrying failed or unknown sends. An `accepted` bridge receipt alone does not prove mobile display.

Native sticker sending, searching/favorites management, voice-note generation and phone calls are not implemented here. A normal PNG is not a native sticker. No outgoing, incoming or automatically answered call is started by this package.
