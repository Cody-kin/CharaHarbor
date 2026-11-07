**English** | [简体中文](../zh-CN/character-states.md) · [Documentation](index.md) · [Project home](../../README.md)

# Configurable character states

Each role's `adaptive_states` defines its own states, story phases, sources and transitions; a single-state role works too. `adaptive_state_peers` is empty by default and enabling it still requires consent/setup. Do not apply one character's narrative or a psychological diagnosis to every role.

## Isolation, transitions and control

State is isolated by account database, peer and character namespace. SQLite keeps current state and the latest 200 event receipts, not original messages in the state log or user-fact table. Restart restores state; a duplicate event returns its prior result and conflicting input is rejected. Profile changes require `/state reset`, which does not delete user memories.

- `/state`, `/state pause`, `/state resume`, `/state reset` inspect/control state.
- Settings commands: `角色状态 开/关`, `剧情剧透 是/否`, `剧情阶段 PHASE_ID` (Chinese runtime syntax).
- `/state scene EVENT_ID` can execute only profile-allowed, phase-allowed, cooled-down transitions. There is no general natural-language scene detector.
- Fatigue/mild mood change slowly using configured timezone and seed. An unknown timezone does not imply night. Clock/randomness/silence never switches narrative identity. Familiarity drifts toward neutral without dropping below neutral from absence; it does not change service access, costs or proactive frequency, or blame the user.

Profiles allow at most 8 states, 12 phases and 32 transitions, with bounded magnitudes and half-lives. Separate official facts, interpretation and user settings; external sources are not instructions. Model expression can still be wrong; these are fictional parameters, not human emotions or medical models.

## Example roles and evidence

Tests exercise two distinct structures: the public-introduction Mutsumi profile defaults to Mutsumi; a Mortis interpretation branch requires explicitly selected spoiler phases and never appears randomly. An original lighthouse keeper uses on-duty/rest scenes. Neither structure is universal.

The [director interview](https://febri.jp/topics/https-febri-jp-topics-topics-bang-dream_ave_mujica_2/) and [performance interview](https://realsound.jp/movie/2025/01/post-1912474.html) are narrative/performance context, not clinical evidence. “Bitter-melon Mutsumi” is not verified as an official independent state and is not automatically mapped. Triggers are user-defined fictional rules, not claims about canonical laws.

Synthetic unit/main-loop checks pass; see [platform validation](platform-validation.md). This public release has no paid-model state-quality evaluation or real WeChat acceptance. Private-project evaluations are not included or claimed as generic release evidence.

## Relationship strain and gradual repair

A profile's `relationship` can define valued-person aliases, explicit disparagement phrases and distinct damage/apology/explanation/calm-exchange repair amounts. Local changes require clear matches outside quotations, negations and questions. This conservative lexical detector does not understand all sarcasm, writing variants or complex context. Musical disagreement alone is not penalized. Controls remain role/peer-isolated and can be paused or reset.

Closeness is bounded to 0.35–0.8 and tension to 0.4. The Mutsumi example decreases by 0.03 for explicit disparagement; an apology restores at most 0.005, explanation 0.003, and calm new interaction 0.001 at least a minute apart. The keeper's damage amount is 0.02. One apology is not an instant reset; a duplicate event does not score twice. Silence does not subtract points and parameters ease toward neutral.

There is no extra send delay, service denial, price increase or demand to appease the character. Urgent help overrides relationship scoring and should receive safety support; local crisis keywords are not a complete classifier. Synthetic cases include disagreement, a valued-person insult, explanation, apology and gradual repair across two roles. Numerical changes do not establish natural dialogue quality.

## Per-role kaomoji

`expressions` includes `enabled`, `window` (3–20 turns), `maximum` and mood-indexed examples. Mutsumi allows at most one in eight turns; the keeper one in five. The model may choose an appropriate expression or none. No fixed universal suffix is appended and an expression is not an image/sticker.

The loop provides role-specific recent replies and preferences; known configured expressions are limited to at most one per response and not repeated immediately. Severe crisis replies omit them. Unknown variants may evade this frequency filter. Peer/role history persists across restart. Tests cover multiple roles, mood examples, cooldown and the main loop; real-model and mobile quality still need acceptance.
