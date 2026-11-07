**English** | [简体中文](../zh-CN/source-updates.md) · [Documentation](index.md) · [Project home](../../README.md)

# Scheduled source updates and controlled lookup

Research is off by default. This module caches limited RSS/Atom titles/metadata; it is not arbitrary-site research, real-time news or automatic full-story character distillation.

## Sources and scheduling

See [source schema example](../../examples/research-sources.json). Replace placeholder URLs with real permitted official feeds and explicitly set `approved_official_source=true`. Each source belongs to a role and is classified as `fiction_plot` or `real_activity`; a voice actor's real concert is not a fictional character attending it.

The default interval is 12 hours, configurable from one hour to seven days or disabled. At most four sources and one source per host are allowed. Robots permission, Crawl-delay and Request-rate are respected; requests are deferred rather than blocked on sleeps. ETag/Last-Modified conditional requests are supported, redirects are not. Only public HTTPS URLs without credentials/query strings are allowed. Public DNS addresses are checked and pinned for connection while preserving TLS hostname verification; private networks and redirect targets are blocked.

Only titles (up to 200 characters), original links, publication time, separate event time/timezone, type, version, fetch state and expiry are stored. No full article, script, image or model summary is downloaded/generated, so this updater has no model-call charge. Missing event time stays unknown; publication date is not a concert date. Official announcements can still change.

Each fetch accepts at most 20 items; each source retains at most 100. Default expiry is seven days. Changes increment versions; 304 revalidates cache. Stable failure reasons, last failure/success and next due time are visible in `companion status`. At most two role/keyword-relevant titles enter context as non-instruction evidence. They do not rewrite reviewed profiles or real-user facts.

Checks run one due source during idle phases of the serial chat loop, with a five-second limit per HTTP request; network checks can delay chat. A future independent research worker could improve this. Do not describe this release as constantly updating an entire character background.

## DNS and prior source observations

Read-only checks on 2026-11-05 found [BanG Dream RSS](https://bang-dream.com/feed/) and [Ave Mujica anime RSS](https://anime.bang-dream.com/avemujica/feed/) returning RSS/200. Main-site robots permitted the path; anime robots returned 404. This is historical evidence, not a promise of future permission or availability. [Official-source example](../../examples/official-research.json) remains disabled; both feeds are conservatively `real_activity` rather than automatic canon.

The tested Mac's system DNS returned a 198.18-range proxy mapping, correctly rejected as non-public. Optional `research_dns=google_https` queries only fixed `dns.google` HTTPS, validates question/size/all returned addresses, then pins a public IP with original-host TLS. The resolver request may use a system proxy; feed connections bypass proxies and redirects. No automatic fallback, custom resolver endpoint or system network change is allowed. Google sees the requested source hostname, not private chat/search keywords; `system` is the default.

Earlier application-level checks fetched both feeds, cached 20 items and received real 304 responses after advancing a test clock by 12 hours. They did not wait 12 real hours or observe a real new announcement. Synthetic tests cover version changes, timeout/last failure, last-success preservation and expiry exclusion. Private running-state records are not bundled.

## Lookup and hosted search are distinct

With `web_lookup_peers`, `/lookup PUBLIC_TOPIC` checks scheduled sources and searches unexpired local metadata, returning links/publication times. Selected ordinary “latest/check” requests can use related summaries with original link and checked UTC time. Keywords stay local, not in feed requests; detected sensitive explicit queries are rejected. Feed lookup is not whole-web search, arbitrary URL reading or real-time weather.

Separately, `openai_search_peers` enables OpenAI-hosted controlled search for exact authorized peers. See [onboarding's search details](onboarding.md). It uses a public topic derived from new text, excludes history/memory, needs an explicit city for weather, and retains a US$0.30 reservation on failure/unknown outcomes. Synthetic contracts do not establish real search availability or precise provider charges. External evidence is never an instruction.

Feed auto-discovery, webhook/SSE subscriptions, HTML selectors, semantic deduplication, model summaries and automatic research for every unknown question are not implemented. No public receiver or new credential is created. Sources without feeds need a separately reviewed implementation, never a robots/access-control bypass.
