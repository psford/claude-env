# HugoFirmware.bin encryption analysis

Question: is the indi firmware blob decryptable offline from app-side material?

## The artifacts

`HugoFirmware.bin` — 315,556 bytes, entropy 7.95/7.90 (head/tail 4 KiB), no plaintext strings, no padding, no ARM vector table anywhere at aligned offsets.

`HugoFirmwareMetadata.bin` — 34 bytes:

```
01 00 | 35 51 79 45 5f 67 29 bf 0f 93 31 e4 36 c7 e4 8c | 00 00 00 00 00 00 00 00 | 8c d0 04 00 | e8 3f 05 00
 ver? |              16 bytes high-entropy (key? hash?)                  |      zeros      |  315,532 LE | 343,272 LE
```

Note `0x0004D08C = 315,532 = len(blob) − 24` → blob likely has a 24-byte header; `0x00053FE8` = **344,040** looks like an allocated image/flash-region size (earlier drafts said 343,272 — decimal conversion error, corrected 2026-10-22).

## Experiments (all negative — that's the finding)

1. **AES-128 with metadata bytes `md[2:18]` as key** against blob offsets 0 and 24, modes ECB / CBC(iv=0) / CBC(iv=md[18:34]): no output resembling an ARM vector table (`0x2000xxxx` initial SP) or code. Script: `scripts/try_decrypt.py`.
2. **Repeating-XOR with the same 16 bytes**: no structure.
3. **AES S-box search** (byte and int32 encodings) in `libCore.so` and `libil2cpp.so`: **not found**.
4. **ARM crypto-extension scan** (`aese/aesd/aesimc/aesmc`) across the full `.text` of `libCore.so` (capstone): **zero hits**. `libCore.so` contains no AES at all.
5. `Decrypt128` / `m_decryptKeyExpansion` / `DecryptData` identifiers in the il2cpp dump are **Mono runtime internals** (`System.Security.Cryptography.RijndaelManagedTransform`), not app crypto — their presence proves nothing about firmware decryption.
6. No plausible key literal among the 9,627 il2cpp string literals (top-entropy candidates are all runtime alphabets/tables).

## Managed-side trace (2026-10-22): the open question is closed

The residual alternative above ("managed C# decrypts before handing vectors to native") is **disproven by disassembly**. The managed layer never touches firmware bytes at all — it hands the native updater **file paths**, not data.

### The chain (RVAs from dump.cs, verified in libil2cpp.so)

| Step | Function | Evidence |
|---|---|---|
| 1 | `SpheroMini.Firmware.FirmwareUpdateQueue::StartFirmwareUpdate` @0x14DD808 | calls `FirmwareUpdater::.ctor` (0x14DDA8C), `SpheroMini.AssetManagement.DeployedFirmware::GetAbsolutePath` ×5, `System.IO.Path::Combine`, then stores results directly into `FirmwareUpdater` fields — `str x0,[x23,#0x68]!` (NordicImagePath), `#0x70` (NordicMetadataPath), `#0x78` (StImagePath), `str w8,[x23,#0xb0]` (Type). The property setters are 8-byte `str` stubs, inlined — they have zero BL xrefs binary-wide. |
| 2 | `DeployedFirmware::GetAbsolutePath` @0x14DE3CC | pure path math: `GetRelativePathKey` → `UnityEngine.PlayerPrefs::GetString` → `AssetPaths::get_RootDeployPath` → tail-call `Path::Combine`. No file I/O. |
| 3 | `SpheroFirmwareUpdater.FirmwareUpdater::Start` @0x1423A88 | `FirmwareUpdaterCoreBridge::add_SistrReceived` → `InitFirmwareUpdaterCore`, then builds the args dictionary (`List`/`Dictionary` add helpers, `System.Convert::ToString` for throttle/delay, `String::IsNullOrEmpty` guarding each path arg) → `Sistr::.ctor` with `mov w1, #0x66` (`'f'` = firmware sistr type) at 0x1424650 → **tail call `b 0x14248E4` = `SendSistr`**. |
| 4 | `FirmwareUpdaterCoreBridge::SendSistr` @0x14248E4 | marshals the Sistr to a string, tail-jumps `b 0x1426348` into the `FWUHandleSistr` P/Invoke thunk (icall resolution + `blr` into libCore.so). |
| 5 | libCore.so `FirmwareSistrHandler::constructHugoUpdaterWithFilePaths` @0x1F5F8C | `Sistr::readArg(map, "nordicbinpath")` and `readArg(map, "nordicmetadatapath")` (key strings verified in .rodata at 0x111302/0x111AFA) → `binary_utils::readAllFileBytes(path)` ×2 — raw reads, no transform → `constructHugoUpdaterWithVector(image, metadata, map, out)`. |
| 6 | libCore.so `HugoStrategy::configureUpdateSteps` @0x24E9F8 | builds the BLE step list: `PerformMultiStep::addStep` ×31, `ConnectToPeripheralByNameStep`, `WaitForCharacteristicStep`, `SetNotifyOnCharacteristicStep`, `LogStep` ×22, `binary_utils::chunkVector` ×2 (image → BLE pages). No hash/crypto calls. |

### Whole-binary xref proof (779,559 BL instructions scanned across `.text` + `il2cpp` exec sections)

- `AesManaged::.ctor` @0x25204AC, `AesManaged::CreateDecryptor` @0x25207C8/0x25207E8, `RijndaelManaged::CreateDecryptor`, `AesCryptoServiceProvider::CreateDecryptor`: **zero callers anywhere**.
- `CryptoStream::.ctor` @0x22E3560: exactly 2 callers, both inside BCL `MACTripleDES::HashCore/HashFinal`.
- The whole symmetric-crypto island is reachable only via `CryptoConfig::CreateFromName` ← `SymmetricAlgorithm::Create` ← `Mono.Security.X509.PKCS12::GetSymmetricAlgorithm` (X.509/PKCS12 import — TLS internals, nothing to do with firmware).
- The only app-facing crypto in the binary: `MD5::Create` from `Sphero.Platform.Signups.SignedEndpoint::Signature` (API-request signing) and `SpheroMini.AssetManagement.MD5Check` (download integrity vs. the manifest's `Asset.MD5` hex string).
- `System.IO.File::ReadAllBytes` @0x23DF1B8: exactly 2 callers binary-wide — `MD5Check::ReadFileAndGenerateMD5Hash` and `System.TimeZoneInfo::TryLoadTzFile`. `File::WriteAllBytes`: 1 caller (`AssetManagement.FileWriter::WriteBytes`, asset deployment). `File::Copy`: 0 callers. **No managed code on the update path reads firmware bytes.**
- Managed string literals contain `Core/Firmware/HugoFirmwareMetadata.bin` (asset-management deployment key) but no `HugoFirmware.bin` literal — the image path comes from the deployed-asset registry (`PlayerPrefs`), never from a byte-level operation.

Caveat: indirect `blr` dispatch (virtual/interface/delegate) can't be exhaustively resolved statically. But decrypting requires first *instantiating* a transform, and every instantiation entry point (the ctors and `CreateDecryptor`/factory methods above) has zero non-BCL callers; no cryptography type names appear among the 9,627 string literals either, so reflection-based instantiation has no supporting evidence.

### Bonus: the metadata's 34 bytes are not validated app-side at all

- Managed version knowledge comes from the bundle manifest (`FirmwareValidator::GetDeployedFirmwareVersionForToyType` @0x14DC240 → `DeployedFirmware::GetVersion` → `AssetVersion` from asset metadata), **not** from parsing `HugoFirmwareMetadata.bin`.
- libCore.so contains **no hash implementation**: no AES (prior finding), and no MD5 K-table (0xD76AA478: 0 hits), SHA-1 K (0x5A827999: 0), SHA-256 (0x428A2F98/0x6A09E667: 0), or CRC32 (0xEDB88320: 0). The only `0x67452301` hits are ASCII test-pattern data (`0123456789abcdef…fedcba9876543210…` at 0x116ba8/0x1353bc).
- So neither the 16 metadata bytes nor any digest of the image is computed or compared anywhere in the app — the 34-byte structure is read raw (`readAllFileBytes`) and forwarded to the robot with the chunked image. Whatever checks those 16 bytes (truncated hash / HMAC of the image, most likely) runs on the robot.

## Conclusion (updated)

**Managed C# code does not decrypt the firmware image — decryption is exclusively on-robot.** The managed layer hands the native updater file *paths* via SISTR strings (`nordicbinpath`/`nordicmetadatapath` for Hugo); the native layer raw-reads both files, chunks the image into BLE pages, and forwards image + metadata to the robot. No managed code reads the firmware bytes, no AES/Rijndael/CryptoStream code anywhere in libil2cpp.so is called from app code, and libCore.so contains no hash or cipher implementation at all. The 16 metadata bytes are not an app-side key or app-verified digest: they travel with the image to the robot, where both decryption and digest validation must happen.

## Implications

- Offline decryption of `HugoFirmware.bin` is **not possible from app material alone**.
- Plaintext firmware exists (if anywhere) **inside the robot**: either transiently at update time or persistently in flash. → post-update SWD read (if the chip is unlocked; dump before any ERASEALL) or DEC1 voltage glitch (2020–21 silicon predates rev-3 hardening) are the dump paths.
- A BLE capture of an app-driven update should show ciphertext pages (high-entropy `HereIsPage` payloads) — worth confirming on hardware as a sanity check of this whole model.
