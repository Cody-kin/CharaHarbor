# CharaHarbor

**A configurable home for fictional-character companions on WeChat.**

**English** | [简体中文](README.zh-CN.md)

[![Platform validation](https://github.com/Cody-kin/CharaHarbor/actions/workflows/test.yml/badge.svg)](https://github.com/Cody-kin/CharaHarbor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Build a companion around an editable character: voice and style, separate user/character timezones, persistent conversation, correctable memories, scheduled or random contact, and optional images. Text and image generation have independent provider/model/key configuration—for example, DeepSeek text with OpenAI images.

**Experimental software, not an official WeChat client.** The Python core and entry points pass Windows, macOS and Linux CI. Live WeChat still needs a separately installed, authorized local bridge and personal QR confirmation. Three-platform real WeChat login/mobile delivery is not verified. This is not zero-configuration deployment.

## Try it without an account

1. Download the [source release](https://github.com/Cody-kin/CharaHarbor/releases) and extract it.
2. Install [Python 3.11+](https://www.python.org/downloads/) with pip/venv; enable PATH on Windows.
3. Start from the extracted project folder:

| Windows | macOS | Linux |
| --- | --- | --- |
| Double-click `start.cmd` | Run `sh start.command` | Run `sh start.sh` |

The installer creates a local `.venv`, downloads pinned timezone/media dependencies and opens the menu. Select **1 离线演示** (offline demo). No WeChat, key or paid API is used. Initial dependency installation needs the internet. The runtime menu/setup commands currently use Chinese; complete English instructions explain each step.

An offline core-only smoke check is available with `python3 install.py --no-deps --smoke`; see [dependency/platform limits](docs/en/user-guide.md). Existing entry-point filenames remain supported.

## What you can configure

| Capability | Current scope |
| --- | --- |
| Character and expression | Sourced profiles, story/spoiler scope, style, bounded states/relationship parameters and per-character kaomoji |
| Conversation and memory | Message aggregation/deduplication, recent context, limited explicit Chinese fact extraction, view/correct/forget, peer-and-role isolation |
| Initiative | Daily/random schedules, timezones, pause, shared limits and stop-until-user-replies behavior |
| Images | Authorized PNG/JPEG/GIF understanding (GIF first frame), ordinary gallery images, explicit `/image description` generation |
| Model providers | OpenAI/DeepSeek text adapters; separate OpenAI image provider/model/key. Other providers need implementation and testing |
| Current information | Real IANA timezone clock, opt-in RSS/Atom metadata updates and controlled lookup/search interfaces |

Default configuration is offline, with no proactive tasks, automatic memory collection or image processing. Live chats use exact private-chat allowlists and staged disclosure/consent. Participants can inspect settings and leave roleplay. No auto-expansion to all friends or group replies.

## Read the guides

Start with the [documentation index](docs/en/index.md), then:

- [Install, configure, run and upgrade](docs/en/user-guide.md)
- [WeChat bridge, identity and personal login](docs/en/wechat-bridge.md)
- [First-use consent, settings and recovery](docs/en/onboarding.md)
- [Character profiles](docs/en/character-profiles.md), [states and expressions](docs/en/character-states.md), [source updates](docs/en/source-updates.md)
- [Capabilities and limits](docs/en/features.md), [privacy/troubleshooting](docs/en/security.md), [executed platform tests](docs/en/platform-validation.md)

Every guide has a matching Chinese page and a visible language switch. [中文文档目录](docs/zh-CN/index.md).

## Know the limits before live use

- The public release's paid-provider tests use mock HTTP, not real paid credentials. Account permissions, model quality, costs and phone delivery need separate acceptance.
- Memory is a conservative rule-based feature, not unlimited or arbitrary natural-language recall; at most 100 facts per peer/role.
- Generated images are illustrations, not real photographs; no reference artwork is included. Ordinary images are **not native WeChat stickers**. Native sticker sending, voice notes and phone calls are not implemented.
- A serial image request can delay later chat by up to its 90-second timeout. Unknown sends stop for review rather than blindly retrying; downtime events may be skipped.
- Program-side reservations/rate limits are not provider-enforced spending caps. State is plaintext; review Windows ACLs yourself before live use.

See the [full matrix](docs/en/features.md) and [security guide](docs/en/security.md). Character play is fictional companionship, not professional treatment or a claim to be a real person. CharaHarbor is unaffiliated with Tencent/WeChat or any fictional work.

## Project layout and development

```text
companion/       Runtime core, providers and authenticated bridge adapter
examples/        Synthetic configuration and evaluation scenarios
roles/           Editable, sourced fictional-character summaries
docs/en/        Complete English guides
docs/zh-CN/     Complete Simplified Chinese guides
tests/           Synthetic tests; no personal accounts or private chats
tools/           Platform smoke, documentation and source-safety checks
start.*          Compatible OS entry points
install.py       Local environment/dependency installer
launch.py        Configuration and foreground launcher
```

```sh
python3 install.py --smoke
python3 tools/platform_smoke.py
python3 tools/check_docs.py
python3 tools/scan_public.py .
```

Report bugs with OS, Python/bridge versions, a safe reason code and a synthetic reproduction. Never attach tokens, account profiles, chat databases or private memories. Contributions should preserve safe defaults and update **both** language versions; [validation details](docs/en/platform-validation.md) describe what CI actually proves.

## License and distribution

[MIT](LICENSE) covers this project's code, not third-party characters, artwork, voices or scripts. No bridge binary, login material, private conversation, personal memory or key is bundled. Unofficial bridge use can fail or lead to account restrictions; consult [upstream platform notes](https://github.com/thisnick/agent-wechat/blob/main/PLATFORM-ACCEPTANCE.md).
