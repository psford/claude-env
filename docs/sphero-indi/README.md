# Sphero indi — hardware hacking research

Research workspace for reverse-engineering the Sphero indi robot car (codename **Hugo**), with the goal of understanding (and eventually replacing or rewriting) its firmware.

## Status (2026-10-22)

| Question | Answer |
|---|---|
| Is the firmware publicly obtainable? | **Yes** — bundled inside the Sphero Edu Jr Android app (`com.sphero.edujr` v1.1.0), `assets/MiniData/Core/Firmware/HugoFirmware.bin` (315,556 B) |
| Is it encrypted? | **Yes** — full-file high entropy (7.95 bits/byte), no strings, no padding. Encryption is generational: SPRK (nRF51 era) and BOLT's STM32 image ship plaintext; all Nordic-generation images (Mini, BOLT-Nordic, Hugo) are encrypted |
| Where does decryption happen? | **On the robot** (best-supported conclusion — see `crypto-analysis.md`). The app's native updater lib has zero crypto; the app passes ciphertext through |
| What BLE protocol does indi speak? | **Sphero v2 family** — proprietary GATT UUIDs (`0001000x-574f-4f20-5370-6865726f2121`, ASCII suffix "WOO Sphero!!"), `usetheforce...band` antiDoS unlock, SOP `0x8D` / EOP `0xD8` framing. Confirmed present in the app's `libCore.so` |
| Full command API known? | ~574 command/response/notify classes extracted from the il2cpp dump → `artifacts/command-api.txt` (drive, raw motors, LEDs, card config get/set, music box, event log, sensor streaming, bootloader reflash, …) |
| Which MCU? | **nRF52-family confirmed by inference; exact part unresolved** — no public source names it (paper trail exhausted 2026-10-22). Flash-budget analysis: 344,040-byte image region doesn't fit nRF52832+S132 → live hypotheses **nRF52840** vs **nRF52832+S112** (see `research-findings.md` §1). Decisive: "BT Module" photo in original FCC PDF, `sd_req` in a captured DFU init packet, or SWD IDCODE on hardware |
| Can custom firmware be flashed? | Unresolved for indi specifically, but the app itself ships `JumpToBootloader` → `BeginReflash` → `HereIsPage` → `JumpToMain` commands, and the legacy Sphero reflash protocol had **no signature** — testable for $0 once hardware is in hand. SWD+ERASEALL is the fallback (nRF52 `CTRL-AP` erase works even APPROTECT-locked) |

## Contents

- `research-findings.md` — the full write-up: hardware, firmware inventory, app architecture, protocol, updater internals, attack paths
- `crypto-analysis.md` — firmware encryption analysis, including negative results and the on-device-decryption conclusion
- `artifacts/` — firmware blobs (sha256s inside), FCC teardown photo bands, il2cpp string literals, extracted command API
- `scripts/` — analysis scripts (`try_decrypt.py`, `disas_fwu.py`)

## Sources / provenance

- App: Sphero Edu Jr 1.1.0 (versionCode 34), XAPK from APKPure, unpacked at `/tmp/sphero-indi/edujr/` (session-local)
- FCC: `SXO-INDI` internal photos (2-page high-res PDF) → sliced into `artifacts/band-1..8.jpg`
- il2cpp dump: Il2CppDumper PR #922 (Unity 6 / metadata v39) → `dump.cs`, `stringliteral.json`, DummyDLLs at `/tmp/sphero-indi/out/` (session-local; `stringliteral.json` copied to artifacts)

## Open threads (tracked as GitHub issues)

- Read chip markings from FCC photos (needs human eyes — no model in this chain can view images)
- nRF Connect scan on first unit (confirm GATT services, advertised name)
- Verify whether managed `AesManaged` code in libil2cpp is ever invoked (closes the app-side-decrypt hypothesis fully)
- BLE sniffer capture during an app-driven firmware update (are pages ciphertext?)
- Post-update SWD dump attempt (does robot flash hold plaintext after update?)
