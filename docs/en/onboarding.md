**English** | [简体中文](../zh-CN/onboarding.md) · [Documentation](index.md) · [Project home](../../README.md)

# First use, settings and recovery

The operator installs/logs into the bridge and configures exact account/peer identities first. `serve --live` checks server ID, account ID, own username and online authentication before taking the current event cursor. Historical chats are not imported.

With explicit `setup_peer`, a single disclosure is sent only to that allowlisted peer; otherwise setup waits for each allowlisted peer's new text. It explains fictional AI roleplay, the configured model provider, non-professional support and memory/image data use. Declining leaves the bot quiet. Role-model calls and proactive messages remain off until consent and setup finish.

## Persistent state machine

```text
new → await_consent → role → role_location → style → interaction → confirm → ready
          ↓ decline                                                  ↓ settings word
       declined                                                    settings
          ↑ settings word                                 save/cancel → ready
any phase → /exitrole → exited (proactive paused) → settings word → consent again
```

Complete each step: `同意` or `/acceptrole`, exact registered role name, location/timezone confirmation or `所在地 CITY IANA_ZONE` / `地点未知`, style up to 200 characters, `被动` or `随机 90 180`, then `确认`. Consent alone does not bypass configuration. Unknown profiles are reported as unavailable rather than falsely described as already researched.

Runtime setup commands currently use Chinese. Translations below explain them; they are not alternative recognized command strings.

## Settings and participant control

`settings_word` defaults to `/settings`. It must match the complete trimmed message; quoted/embedded words do not trigger settings. It is not a password and grants no access beyond authenticated exact-peer authorization. Never use a secret as the word.

| Exact command example | Meaning |
| --- | --- |
| `角色 小睦` | Select a registered character |
| `风格 简短而温柔` | Set style: short and gentle |
| `场景 与团员在练习室排练` | Set an explicitly fictional rehearsal scene, separately stored and no longer forced after 12 hours |
| `随机 90 180` | Set random minimum/maximum minutes; allowed range 5–10080 |
| `定时 09:30 简短问候` | Add a daily greeting task, at most five |
| `时区 Asia/Shanghai` | Set scheduling timezone |
| `暂停` / `恢复` / `清空定时` | Pause / resume / clear scheduled tasks |
| `保存` / `取消` | Apply draft / discard draft |

Role replies and proactive contact pause while settings are edited; drafts do not take effect early. Roles, styles, scenes, timezones, tasks and consent are per participant. The shared budget day still follows deployment configuration and cannot be reset by a participant changing timezone.

`/pause` and `/forget` work locally even when the budget is exhausted. `/exitrole` revokes role consent locally and pauses proactive contact, but cannot recall a send or cancel every request already in flight. Exit keeps settings and memory; `/forget` removes current-role facts/recent chat, not settings or deduplication metadata. Logical deletion is not guaranteed erasure of database free pages/backups.

## Receipts, restart and recovery

Setup advances only after a verified receipt. An unknown send creates a pending barrier and is not resent automatically. Normal restarts restore the precise step and draft. Operators can inspect private pending IDs:

```sh
python -m companion status --config config.local.json --live
python -m companion recover-setup --config config.local.json --live --event PENDING_EVENT_ID
```

Recovery only queries the existing idempotency-key receipt on the same authenticated bridge; it verifies account, target, accepted status and server ID before advancing. It never sends again. Missing/rejected/unknown receipts remain stopped: do not clear the barrier casually. Status output contains private operational metadata; do not publish it.

`python3 setup_demo.py` runs an offline walkthrough in `.setup-demo-state`, without network or fees. The generic workflow has synthetic cross-platform tests, not live mobile acceptance. Proactive chat is WeChat text, not actual SMS or phone service.

## Character location and memory isolation

A profile may define `location` with `name`, `timezone`, `confidence: verified`, `source` and `timezone_source`; both source fields reference reviewed source IDs. Suggest a location only when both location and timezone have provenance. Do not infer it from a name, nationality or the user's location. Otherwise ask or allow explicit user-defined values. The public Mutsumi example has no verified city and does not automatically claim Tokyo.

A role choice stores suggestions in a draft. `确认地点` or manual location still requires final save. `地点未知` is allowed, but a local-time question then asks for a timezone rather than reusing another role's or the server's timezone. Independent commands include `角色时区 Asia/Tokyo`, `用户时区 Asia/Hong_Kong`, `角色所在地 东京`, `用户所在地 香港`. UTC-to-IANA conversion handles DST and date boundaries. Labels do not prove physical location and are not tracking. Scheduling time and budget-day timezone are independent.

Switching roles clears old location/timezone and temporary scene. Facts, recent chat and extraction evidence use a peer-plus-character namespace within the account database; legacy unscoped facts are not imported automatically. Switching back can retrieve that character's retained memory, not an old location draft. `/memory`, `/remember`, `/forget` affect the current role; switch to another role to delete its memory. Storage remains private plaintext SQLite.

## Opt-in hosted search

`openai_search_peers` is empty by default and supports only OpenAI. Synthetic end-to-end contracts are tested; real search success/model permissions still need acceptance. Controlled public topics come only from new text, not private history/memory; weather needs an explicit city. Each lookup reserves US$0.30, with conservative estimated settlement only after verified success. Failure/timeout/unknown outcomes retain the reservation and are not retried. Shared caps remain application-side, not exact provider hard limits. Evidence includes links/UTC time and is never treated as instructions. This is not automatic whole-web research for every unknown question.
