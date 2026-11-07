**English** | [简体中文](../zh-CN/platform-validation.md) · [Documentation](index.md) · [Project home](../../README.md)

# Platform validation record

Release baseline: 0.5.0, verified on 2026-11-07 (Hong Kong date). Documentation release 0.5.1 retains that runtime and adds bilingual documentation checks. All fixtures are synthetic accounts, messages, media and mock APIs; no personal WeChat profile or paid key is used.

The 0.5.0 release commit `7050b7b4e89a3ffb2956091cd9d7744b39e06157` passed [all three CI jobs](https://github.com/Cody-kin/CharaHarbor/actions/runs/42324949751). Runtime fix commit `bd8c28132e59228314d294251f6e1f50a7703514` also passed the [preceding run](https://github.com/Cody-kin/CharaHarbor/actions/runs/42324748815). The [Actions page](https://github.com/Cody-kin/CharaHarbor/actions) records subsequent documentation-release runs.

| Executed environment | Result | Scope |
| --- | --- | --- |
| Local macOS 15.7.4 ARM64 / Python 3.9.6 | 140 tests passed; pinned tzdata installation, venv demo, command launcher, synthetic loopback bridge and system JPEG/GIF decoder executed | A separate restricted run skipped one listener test; the unrestricted synthetic run supplied real loopback evidence |
| GitHub Ubuntu 26.04 x64 / Python 3.11.18 | 138 of 140 passed; two Mac-only tests skipped; installer, sh launcher, loopback bridge and separate real Pillow JPEG/GIF smoke passed | Not all Linux distributions |
| GitHub macOS 26.7.2 ARM64 / Python 3.11.9 | All 140 passed; installer, command launcher, loopback bridge and system JPEG/GIF decoding passed | Not every Mac architecture/version |
| GitHub Windows Server 2025 x64 (10.0.26100) / Python 3.11.9 | 138 of 140 passed; two Mac-only tests skipped; installer, PowerShell launcher, loopback bridge and separate real Pillow JPEG/GIF smoke passed | No full Windows ACL review or Windows 11 desktop double-click acceptance |

The first Windows run failed because a redirected legacy-encoded console could not print Chinese. CLI/wizard boundaries now explicitly use UTF-8. A child-process test forces cp1252 and confirms correct UTF-8 output; the fix passed the real Windows runner. The failure was not ignored.

Coverage includes consent/setup, configuration, budget reservations, memory correction/deletion/restart, batching, deduplication, stopping unknown sends, synthetic HTTP bridge, separate image-key contracts and media decoding. Windows/Linux skip two Mac-specific tests but also execute their actual Pillow decoder; they do not merely patch the platform name.

Still unverified across three platforms: real WeChat QR login, mobile image delivery, paid-model access/costs and comprehensive Windows local permissions. Upstream native bridge builds and this project's Python tests are different evidence. Core CI success is not proof of live WeChat or zero-configuration deployment.
