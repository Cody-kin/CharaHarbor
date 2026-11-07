**English** | [简体中文](../zh-CN/user-guide.md) · [Documentation](index.md) · [Project home](../../README.md)

# Installation and user guide

## 1. Choose an installation entry point

Install [Python 3.11+](https://www.python.org/downloads/) with pip and venv first. Python 3.9 is the minimum for the core, with reduced media support. On Windows, enable **Add Python to PATH** and reopen your terminal. On Ubuntu, use the distribution's trusted Python, venv and pip packages. Do not run this project as root.

Download and extract the [release source package](https://github.com/Cody-kin/CharaHarbor/releases), then work inside the extracted project folder.

| System | Entry point | Terminal alternative |
| --- | --- | --- |
| Windows | Double-click `start.cmd` | `py -3 install.py`, or `powershell -File start.ps1` |
| macOS | `sh start.command` in Terminal | `python3 install.py` |
| Linux | `sh start.sh` | `python3 install.py` |

The installer creates only this project's `.venv`, installs pinned `tzdata==2026.6`, and installs `Pillow==13.0.0` on Python 3.11+. It does not install the WeChat bridge, scan a login code, configure system services, use sudo, or change firewall rules. Initial dependency installation needs network access. If Finder cannot open the command file, use Terminal. If PowerShell blocks scripts, use `start.cmd`; do not disable system-wide protections.

The menu currently uses Chinese labels: **1 离线演示** (offline demo), **2 配置向导** (configure), **3 检查配置** (doctor), **4 启动真实微信** (start live). These guides are bilingual; the runtime UI and built-in conversational setup commands have not been translated into English.

```sh
python3 install.py --no-deps --smoke
```

This offline check creates a core-only environment and runs synthetic messages without keys, WeChat or paid APIs. Windows still needs installed timezone data; JPEG/GIF decoding outside macOS needs Python 3.11+ and the pinned Pillow dependency. A manual setup is also possible:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install tzdata==2026.6 Pillow==13.0.0
.venv/bin/python launch.py
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

## 2. Configure the project

Choose menu 2 or run `.venv/bin/python launch.py configure`. Provide a fictional character/persona, style, and separate user/character IANA timezones. Demo is the default; entering `live` explicitly enables live configuration. Supply the bridge identity and exact private-chat allowlist yourself. Configuration is written to `config.local.json`; an existing file is never overwritten.

Text supports `openai` and `deepseek`; specify a model your account can use. Parameter compatibility varies by model. Image generation independently supports `openai`, its own model and key. Other providers need implemented and tested adapters, not just a different configuration string.

The live launcher requests secrets with hidden input and passes them only to the child process environment. It does not save or print them. Alternatively inject these variables with your OS credential-management tools:

| Variable | Purpose |
| --- | --- |
| `COMPANION_API_KEY` | Selected text provider's API key |
| `COMPANION_IMAGE_API_KEY` | Independent OpenAI image key; never falls back to the text key |
| `COMPANION_BRIDGE_TOKEN` | Existing local bridge token, scoped to the authorized account and operations |

Do not put secrets in CLI arguments, configuration, screenshots, Issues or chat. Other users/processes on a shared host may be able to inspect process environments.

## 3. Connect WeChat and obtain consent

Follow the [bridge guide](wechat-bridge.md) and personally confirm login. Menu 3 checks local configuration without contacting WeChat; menu 4 starts the authenticated receive loop. This project does not add friends, create bridge credentials or import an existing official-client profile.

Only new allowlisted private-chat messages are processed. Before role replies or proactive messages, the participant receives a disclosure, agrees, and completes the staged setup. See [onboarding and recovery](onboarding.md). Exact standalone `/settings` opens settings by default; `/about` shows the explanation, `/exitrole` exits, and `/acceptrole` starts consent again. The settings word is not a password or a way to authorize strangers.

## 4. Enable optional capabilities

Stop the process before editing configuration. Each list below must be a subset of exact `peers`, never nicknames or group IDs; defaults are empty.

| Configuration | Permission |
| --- | --- |
| `auto_memory_peers` | Save limited explicit preferences, experiences and commitments; provide relevant memories to the text model after consent |
| `vision_peers` | Send authorized images to the vision-capable text model; currently OpenAI, GIF first frame only |
| `picture_peers` | Send ordinary images from a legally supplied gallery; verify SHA-256, labels and `rights_confirmed` |
| `image_generation.peers` | Accept explicit `/image description`, call the separate image service and send the resulting ordinary image; also requires `picture_peers` |
| `adaptive_state_peers` | Use configured character states, relationship parameters and expression guidance after setup |

Merge this fragment into an existing configuration; it is not a complete configuration:

```json
{
  "picture_peers": ["EXACT_PRIVATE_CHAT_ID"],
  "image_generation": {
    "provider": "openai",
    "model": "YOUR_AVAILABLE_IMAGE_MODEL",
    "quality": "medium",
    "reserve_usd": 0.20,
    "peers": ["EXACT_PRIVATE_CHAT_ID"]
  }
}
```

Generation currently requests a 1024×1024 PNG. Output must fit the bridge's 1 MiB / 1,048,576-pixel limits. An oversized response or failure produces an honest text fallback, with no automatic retry. Only the explicit description goes to the image service, not the entire chat or memory. No reference artwork is bundled or attached automatically. Generated illustrations are not real photographs; ordinary images are not native WeChat stickers.

## 5. Memory, schedules and stopping

`/remember name=value` creates or corrects a fact; `/memory` lists facts. `/forget name` deletes a fact, while `/forget` clears current-role facts and recent conversation. Single-fact deletion does not remove every equivalent phrase from recent history; use the full command for that scope. This is logical deletion, not forensic erasure.

Automatic extraction is a conservative Chinese rule set, not general natural-language understanding: examples include `我喜欢绿茶` (I like green tea), `我去过京都` (I have visited Kyoto), `我学过吉他` (I learned guitar), and `我们约定周末散步` (we agreed to walk at the weekend). Correction: `更正：我喜欢红茶，不是绿茶`; forgetting: `忘记我喜欢红茶这件事`. Uncertain statements, questions and detected sensitive material are rejected. Each peer/role has at most 100 facts. English translation of these examples is explanatory; it is not an additional supported extraction syntax.

See [task examples](../../examples/tasks.json). `daily` uses the configured scheduling timezone; `random` samples within the configured interval. After proactive contact, another proactive message waits for new user text. `/pause` and `/resume` control proactive contact. Tasks share spending, rate limits and deduplication; missed tasks are not replayed and the allowlist never expands automatically.

Ctrl+C stops the foreground worker. A `STOP` file in the state directory stops the next loop; an already-started network request may continue until timeout, and sent messages cannot be recalled. Restart begins at the current event cursor: downtime and not-yet-flushed messages can be skipped. Unknown sends require manual review rather than replay.

## 6. Long-running operation and upgrades

Keep the foreground terminal open, or configure your own service manager to run `.venv/bin/python launch.py live`. Supply secrets through an appropriately protected OS mechanism. No startup service or public listener is installed. A server with at least 2 GiB RAM is suggested; media decoding creates additional peaks. This project does not run a local language model.

Stop before upgrading, preserve private configuration/data, and deploy source into a separate clean directory. Generic database rollback/migration guarantees are not provided. Test the bridge contract and receipts with a separate authorized account before production use. Restart does not replay old chats.

## 7. Costs

`daily_usd`, `project_usd`, `hourly_limit` and `reserve_usd` are application-side controls. Reservations count against the ledger; failed or unknown operations retain them. Image reservations are separate per request but share the daily/project budget. These are neither provider hard caps nor exact token-cost settlement. If reservations underestimate actual charges, provider spending can be higher. Check prices and billing independently; a subscription does not imply free API use.

References: [OpenAI Images API](https://developers.openai.com/api/reference/resources/images) and [DeepSeek API](https://api-docs.deepseek.com/). Paid-provider availability and mobile delivery were not tested by this public release's synthetic CI.
