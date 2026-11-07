**English** | [简体中文](../zh-CN/features.md) · [Documentation](index.md) · [Project home](../../README.md)

# Capabilities and acceptance boundaries

| Area | Implemented | Limits / unverified behavior |
| --- | --- | --- |
| OS entry points | Windows cmd/PowerShell, macOS command and Linux sh; project venv and configuration menu | Python must be installed; WeChat is not zero-configuration; CI validates the core |
| Character/style | Editable sourced profiles, story point, states and kaomoji; first-use consent/settings word | Model quality is not guaranteed; no copyrighted artwork/scripts bundled; private-project quality claims are not release evidence |
| Providers | OpenAI/DeepSeek text contracts; independent OpenAI image model/key/provider boundary | Paid APIs in this release use synthetic HTTP contract tests; other providers require adapters |
| Images | PNG/JPEG/GIF input, GIF first frame; authorized gallery images; explicit `/image description` generation | No three-platform real WeChat/mobile acceptance, automatic reference art or native sticker sending |
| Memory | Peer/character-isolated recent persistence, limited explicit Chinese facts, inspection/correction/deletion | Not arbitrary natural memory; 100 facts per peer/role; deleting one fact does not remove every equivalent history phrase |
| Proactive/scheduled | Daily/random tasks, timezones, shared budget/rate limits, stop-until-user-replies, pause | Off by default; tasks may be skipped; no guilt, psychological punishment or dependence incentives |
| Relationships/states | Configurable profile state/relationship/expression logic with synthetic evaluation | Not a clinical personality model or proof of natural model behavior; private custom behavior is not all ported |
| Current information | Opt-in 12-hour RSS/Atom checks, dual timezones, controlled lookup interfaces | Not real-time whole-web story understanding; failed searches stay uncertain; unsafe DNS is rejected |
| Deduplication/restart | Worker lock, persistent operation state, no replay of unknown sends | Downtime messages are skipped; unknown outcomes need review |
| Voice/phone | Not implemented in this package | No voice notes, outgoing/incoming calls or auto-answer |

See [platform validation](platform-validation.md) for executed tests. A successful simulated API or accepted bridge response is not proof of paid-provider access, character quality or mobile delivery.
