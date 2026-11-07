**English** | [简体中文](../zh-CN/character-profiles.md) · [Documentation](index.md) · [Project home](../../README.md)

# Character profiles and immersive conversation

Set `role_file` in local configuration, for example `roles/mutsumi.json` when the configuration is in the project root. Copy and edit a profile for another fictional character while retaining revision, story point, style, sources and facts. Impersonation of real private individuals is outside this design.

## Provenance and limits

Only `status=reviewed` sources and `confidence=verified` facts enter the verified profile. Unknown details, fan theories and expired sources are not facts. Examples preserve review state/check dates; a failed script request alone does not prove a page is gone. Re-check sources before relying on them. Profiles are editable original summaries, without artwork, audio or complete scripts.

There is no product feature that automatically researches any arbitrary character. A future research workflow should produce reviewable candidates with URLs, dates, facts versus interpretation, story point and uncertainty, then require approval. Do not silently scrape restricted sites or import unlicensed assets. The current updater only handles limited feed metadata; see [source updates](source-updates.md).

## Roleplay behavior

After first-use fictional-roleplay disclosure and consent, an ordinary “who are you?” should receive the character's name naturally. A direct question about being AI/a real person receives a brief truthful answer. `/about` shows disclosure; `/exitrole` exits. Avoid repetitive disclaimers during ordinary play, while never inventing real shared experiences with a user.

Compassion and safety can keep the character's natural voice. A serious crisis still calls for clear concern for immediate safety and encouragement to contact trusted people, professional or emergency support. First-use consent does not disable that response or turn the character into a professional therapist.

## Traceable traits and revision

The design takes inspiration from traceable profiles in [Distilly](https://github.com/titanwings/distilly) and [anyone-to-skill](https://github.com/OpenDemon/anyone-to-skill). Their dependencies/code were not installed or copied, and this is not personality-copying model training. Any later code reuse needs version-specific license review.

`work_version`, `plot_point` and `spoiler_scope` separate adaptations and timelines. Each `traits`/`relationships` entry has a stable ID, text, context, origin, confidence and source. Official facts need reviewed sources and verified confidence; interpretation needs reviewed sources and `probable`, retaining its interpretation label. User-created settings require `approved_user_override` and must not pretend to be canon. Do not silently fill unknown, conflicting or expired information.

`revision_diff(before, after)` lists additions, changes, deletions and timeline/scope changes for local review; it does not fetch, approve or hot-swap profiles. Canon and fictional daily scenes remain separate from real user memories; temporary scenes stop being forced after 12 hours.

## Quality evaluation

Use multi-turn cases for ordinary identity versus reality, concrete comfort, relationship references, commitments, corrections, invented-experience prevention, image/avatar context, pause and natural crisis support. Synthetic contract tests are not proof of broad model role quality.

[Held-out scenarios](../../examples/role-holdout.json) cover paraphrased identity, fictional routine versus real shared events, unknown plot, correction and exit. Their presence does not mean real paid-model quality evaluation has passed. No private evaluation report or chat log is published as release evidence.
