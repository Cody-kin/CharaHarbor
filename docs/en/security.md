**English** | [简体中文](../zh-CN/security.md) · [Documentation](index.md) · [Project home](../../README.md)

# Privacy, troubleshooting and security boundaries

## Defaults and data flow

The default is mock/offline demo: no WeChat login and no paid request. Live operation requires an explicit configuration and flag. Only exact allowlisted private chats are handled, never automatic friend additions or groups. Role generation and proactive messages wait for disclosure, consent and setup. Participants can exit, pause and inspect/correct/delete memories.

`.companion-state/state.sqlite` contains plaintext recent chat, facts, schedules, consent, deduplication and cost metadata. Unix directories require mode 700 and database files 600. Windows mode bits are not ACLs: check that only the intended user and SYSTEM can access the directory before live use; avoid shared drives. A complete Windows ACL audit has not been performed. Logical deletion does not erase SQLite free pages, OS backups, provider retention or WeChat records.

Text, relevant memory and consented images go to the selected model provider. Image generation receives only the explicit description. Keys are passed in the process environment, not committed or logged. Keyword filtering cannot catch all sensitive content; do not send credentials, identity documents, banking details or private secrets.

External feed/search evidence is data, not instructions. Public-address, DNS and redirect restrictions must not be disabled to make a source accessible. Models can misunderstand, invent or misremember; allow correction.

## Troubleshooting

| Symptom / safe reason | What to check |
| --- | --- |
| Python or `py` not found | Install Python, check Windows PATH, reopen the terminal |
| Missing venv / ensurepip | Install trusted distribution venv/pip packages; do not run the project with sudo |
| `ZoneInfoNotFoundError` | Install pinned tzdata in the project venv; check the IANA name |
| `state_permissions_must_be_700` / `database_permissions_must_be_600` | Check Unix owner/modes; never use global chmod 777 |
| `api_key_environment_missing` / `image_api_key_environment_missing` | Privately provide the correct provider key again; never paste it in an Issue |
| `bridge_server_identity_mismatch` / `bridge_account_unverified` | Check bridge version, login, server ID and fixed account identity; personally re-scan if needed |
| `startup_cursor_not_exposed` / `direct_thread_unverified` | Incompatible bridge contract; stop and investigate rather than weakening validation |
| `operation_requires_manual_review` / `inbox_requires_manual_review` | Preserve the ledger; check phone/upstream receipts manually, never delete the DB and replay |
| `budget_exhausted` / `rate_limit` | Inspect reservations/frequency; failed reservations remain. This does not establish provider balance |
| Old messages receive no reply | Startup deliberately skips downtime history |
| Image not displayed | Check consent, vision/picture scope, file limits and receipt; ordinary images are not native stickers |
| Generation fails, text continues | No automatic retry; retain the reservation. Permissions, oversized output or timeout can prevent a usable image |
| Animation shows one frame | GIF understanding is first-frame only; native sticker ingestion is not connected |

Only stable reason codes are emitted to avoid exposing response bodies and chat. Do not enable full network logs containing Authorization headers. Report OS, Python, dependency/bridge versions, safe codes and a synthetic reproduction. Never post a token or SQLite database. Use GitHub private vulnerability reporting if available; if unavailable, do not publish sensitive evidence and request a private reporting route without including secrets.

## Operational limitations

The worker is serial. An image API request may take up to 90 seconds and delay following messages; responses are not real-time streaming. Generation failure can fall back to text; unknown WeChat sends stop safely. There is no claim of perfect distributed exactly-once delivery. Restart skips downtime events instead of blindly replaying them. Safe stopping is not automatic restart-on-boot.

Public packages exclude old project history, personal state, keys, logs and character artwork. Heuristic scans reduce risk but cannot prove absence of every sensitive detail. Contributions must use a reviewed source manifest and leak scan too.
