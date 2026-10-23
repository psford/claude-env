# Sphero indi research findings

Collected 2026-10-22 by agent session `0e875a-case`. Everything below was verified against artifacts unless marked *inferred*. "Hugo" is Sphero's internal codename for indi (confirmed via app scripts `Assets/Scripts/HugoConfigurator/*`, analytics endpoint `/api/v1/ingress/hugo`, and `SpheroHugoToy` / `SpheroHugoFirmwareRequest` classes).

## 1. Hardware

- FCC ID **SXO-INDI**, grantee Sphero HK Limited, granted 2020-12-07, DTS 2402–2480 MHz, ~-0.8 dBm conducted. Internal photos public; schematics/block diagram permanently confidential.
- Internal photos PDF (18 MB, 2 pages) sliced into 8 JPEG bands (`artifacts/band-*.jpg`). **Chip markings not yet read** — no model in the analysis chain could view images; needs a human.
- **SoC IDENTIFIED (2026-10-23, vision-transcribed from FCC photos, cross-confirmed in ≥3 photos each): indi is a TWO-Nordic-chip design.**
  - **White main board (silkscreen "EP2"): nRF52840 QIAA** — top-mark `nRF52 / 840 / QIAAD0 / 2037CU` (date code 2020-week-37; 1 MB flash, 256 KB RAM, 73-pin aQFN 7×7). The application brain.
  - **Blue chassis board (motor assemblies): nRF52832 QFAA** — top-mark `nRF52 / 832 / QFAA / 2022` (date code 2020-week-22; 512 KB flash, 64 KB RAM, 48-pin aQFN). Motor/sensor node.
  - This resolves: Sphero's documented two-node architecture (RVR precedent), the app's `NordicImagePath`/`StImagePath` updater fields, `HugoStrategy::performUpdate(UpdatableProcessor,…)`, and the flash budget (344,040-byte image region fits the 52840; impossible on a lone 52832).
  - **Debug surface (EP2 board, from photo transcription):** test-point farm TP100–TP117, TP2xx, TP4xx rows; PIO03/08/12/13/15/16/17/20/27 GPIO pads; connectors J2/J18/J21/J22; BTN; VBAT; GND/GND/VBAT and GND/AUDIO/VUSR headers; U401; power/charging IC "TP5054…"; inductors L202/L201. SWD (SWDIO/SWCLK) is almost certainly within the TP1xx row — verify on hardware.
  - 2020 build predates nRF52 rev-3 (glitch-hardened, APPROTECT-on-by-default) silicon; both chips are pre-rev3.
- Corroboration — BOLT+ (2024, `SXO-9200600`): black circular PCB, silkscreen "SPHERO BOLT+ REV 2.0", **FCC ID `2AVRK-BT01` / IC `20706-BT01`** (a module grantee, distinct from SXO), "NORDIC" chip visible, "DRVC" motor-driver area, test pads labeled MCU/PWR/Memory/LED Driver. Same Nordic family, newer generation.
- Wikipedia describes indi's card sensing as an "image sensor" (unverified). If it's a tiny camera/line sensor rather than an I²C RGB sensor (TCS34725-class), reimplementing card-reading in custom firmware is substantially harder.
- Unknown: one MCU or two (RVR/BOLT are documented two-processor designs; `HugoFirmware.bin` being a single image argues for one programmable target, but `HugoStrategy::performUpdate` takes an `UpdatableProcessor` parameter — leaves the question open).

## 2. Firmware inventory (from the app bundle)

`assets/MiniData/Core/Firmware/` in `com.sphero.edujr` 1.1.0:

| File | Size | sha256 | State |
|---|---|---|---|
| `HugoFirmware.bin` | 315,556 | `573607cb1dc33ec4aa8cd82796200076406a3027715befaaaf25fa682f1f5488` | **encrypted** (entropy 7.95 head & tail) |
| `HugoFirmwareMetadata.bin` | 34 | `13a6f6746b72f31680575128074b3be20b773e7c47c654ef38f6f540122e717d` | see crypto-analysis.md |
| `SprkFirmware.bin` | 237,568 | `aa906ee6bf4e296b6e19872490a51a1da283a21fbdbc6ad1a232525599bc9afa` | plaintext; **byte-identical** to `sphero-firmware-production.s3.amazonaws.com/sprkplus/SparkPlus_Mix-7.21.bin` (public, anonymously listable/downloadable) |
| `SpheroFirmware.bin` | 110,592 | `9f89e1e3266d99677cc5337d27634dbf6e80b8a3460a80bb6453c88ce82252bb` | plaintext |
| `BoltStFirmware.bin` | 327,680 | `d87f716e2538c1ff432067a7c330f2bd0ccbcd2d02fdc6fe85e08d69587ac374` | plaintext STM32F4 firmware (source paths visible: `...\STM32F4xx\*.c`) |
| `BoltNordicFirmware.zip` | 97,048 | `f103613aa9efea421494a8d14a0b9307990e015dd79a7dfd5daa2b41b328d313` | zip: `app.bin` (96,804, **encrypted**) + `crc.dat` (14) |
| `SpheroMiniFirmware.bin` | 164,605 | `703fb29ddbe4ea0378a45348310f1a9ae0aa6575327ed107f4610c7f5ff0cefd` | zip: `app.bin` (164,336, **encrypted**) + `crc.dat` (14) |

Legacy bucket (public S3, verified listable): prefixes `bb8/ ollie/ sphero1/ sphero2/ sprkplus/ weball/` — **no `indi/`**; all nRF51-era. Sphero's IT allowlist names `sphero-sprk-mobile-app.s3.amazonaws.com` as serving "latest firmware images" — listing denied (403) but objects likely world-readable if the key is known; no archived keys exist (Wayback never crawled it).

Firmware is *also* delivered via CMS at runtime: app literals include `Robot Firmware Ver: {0}.{1} | Minimum Connectable Firmware Ver: {2}` and `CMS Firmware Ver` — version gating exists server-side.

## 3. App architecture (Edu Jr 1.1.0)

- Unity 6 app (il2cpp, metadata v39, arm64). BLE + firmware-update logic in native `libCore.so` (2.9 MB, `sphero::` C++ namespace, `firmware_updater::` module) + thin C# bridges (`FWUInit/FWUFinal/FWUHandleSistr`, `Sistr` string-message IPC with type chars 'c'=connection, 'f'=firmware).
- C# plugin `Assets/Plugins/Sphero/Dll/autogen/**` — autogenerated toy API (SpheroHugoToy etc.), ~574 command/response/notify classes (`artifacts/command-api.txt`).
- `FirmwareUpdater` (C#) carries `NordicImagePath/NordicMetadataPath/StImagePath/StMetadataPath/AudioUpdatePath` and dispatches by `UpdaterType { V1Robot=1, Mini=2, Bolt=3, Hugo=4, Classic=5 }`.
- Native `firmware_updater` strategies: `V1Strategy, MiniStrategy, BoltStrategy, HugoStrategy, RVRStrategy, LMQStrategy (Lightning McQueen), VD1Strategy, ClassicStrategy`. `HugoStrategy(string, vector<uint8> image, vector<uint8> metadata, int, duration, string)`; construction via `constructHugoUpdaterWithVector / WithFilePaths / WithBase64Data`.
- il2cpp dump (Il2CppDumper PR #922, needed for metadata v39) produced `dump.cs` (18.8 MB), `stringliteral.json` (9,627 literals), DummyDLLs.

## 4. BLE protocol

- GATT (in libCore.so strings, matching spherov2.js family):
  - API v2 service `00010001-574f-4f20-5370-6865726f2121`, chars `00010002` (write+notify) **and `00010003` (new, indi-era?)**
  - DFU service `00020001-…` with chars `00020002` (dfuControl), `00020003` (subs), `00020004` (dfuInfo), `00020005` (antiDoS)
  - Legacy v1 family also present: `22bb746f-2ba0/2ba1/2ba6-7554-2d6f-726568705327`
- `usetheforce...band` unlock string present in libCore.so → same antiDoS handshake as spherov2.js.
- Framing (from spherov2.js, same family): SOP `0x8D`, EOP `0xD8`, ESC `0xAB` mask `0x88`; `SOP|FLAGS|[TID]|DID|CID|SEQ|payload|~chk|EOP`; verified wake packet `8D 0A 13 0D 00 D5 D8`.
- indi-specific commands visible in the autogen API (names, not yet opcode-mapped): drive with heading, raw motors, stop w/ deceleration, LED 16-bit mask, user color get/set, test tone, audio volume, sensor streaming masks (incl. *extended*), ambient light, collision config, battery/charger notifies, **get/set configuration for color card**, music box song get/set, preview game-configuration sound/LED-animation, restore default game configurations, play mode, event log get/clear, board revision, stats id, SKU, UID, deep sleep, jump-to-bootloader, bootloader version, begin reflash, here-is-page, jump-to-main.
- `sphero::` C++ symbols confirm `ApiV21CommandSender` (v2.1 protocol generation) with `sendApiCommandWithRetries(uint8, uint8, …)` — DID/CID byte args, i.e. the v2 opcode scheme.

## 5. Paths to custom firmware (decision tree)

1. **$0 BLE test (first, once hardware arrives):** connect (spherov2.js-style, bypass name-prefix scanner), write antiDoS string, send `JumpToBootloader` → `BeginReflash` → malformed `HereIsPage`; a `checksum error`-style reply (vs disconnect/auth error) means the unsigned page protocol is alive → push our own image over BLE without opening the case.
2. **SWD replace path:** open case, read SoC marking, `nrfjprog --recover` / CTRL-AP ERASEALL (works even APPROTECT-locked on nRF52; erases stock image — dump first if unlocked), flash nRF Connect SDK / Zephyr firmware. Do **not** use ST-Link-class probes (can't reach CTRL-AP); Pi Debug Probe ($12) or J-Link EDU Mini.
3. **Dump stock firmware:** only if SWD is open (or via DEC1 voltage glitch on pre-rev3 silicon). If bootloader decrypts before flashing, post-update flash holds plaintext.
4. **Fallback:** drive stock robot over BLE with a custom client using the extracted API; card-config get/set already exposes the "program the cards" surface.

## 6. Weekend hardware checklist

- nRF Connect scan: record advertised name; check for `00010001-`/`00020001-` services.
- Photos of the opened board → read SoC, sensor, motor driver, SWD pads.
- If Android device available: HCI snoop log of an app connection + (forced) firmware update; check whether `HereIsPage` payloads are ciphertext (entropy) — settles where decryption happens. Also capture the DFU init packet: its `sd_req` field names the SoftDevice, which discriminates nRF52840 (S140) from 512 K-class (S112/S132).
