# HugoFirmware.bin encryption analysis

Question: is the indi firmware blob decryptable offline from app-side material?

## The artifacts

`HugoFirmware.bin` — 315,556 bytes, entropy 7.95/7.90 (head/tail 4 KiB), no plaintext strings, no padding, no ARM vector table anywhere at aligned offsets.

`HugoFirmwareMetadata.bin` — 34 bytes:

```
01 00 | 35 51 79 45 5f 67 29 bf 0f 93 31 e4 36 c7 e4 8c | 00 00 00 00 00 00 00 00 | 8c d0 04 00 | e8 3f 05 00
 ver? |              16 bytes high-entropy (key? hash?)                  |      zeros      |  315,532 LE | 343,272 LE
```

Note `0x0004D08C = 315,532 = len(blob) − 24` → blob likely has a 24-byte header; `0x00053FE8 = 343,272` looks like an allocated flash-region size.

## Experiments (all negative — that's the finding)

1. **AES-128 with metadata bytes `md[2:18]` as key** against blob offsets 0 and 24, modes ECB / CBC(iv=0) / CBC(iv=md[18:34]): no output resembling an ARM vector table (`0x2000xxxx` initial SP) or code. Script: `scripts/try_decrypt.py`.
2. **Repeating-XOR with the same 16 bytes**: no structure.
3. **AES S-box search** (byte and int32 encodings) in `libCore.so` and `libil2cpp.so`: **not found**.
4. **ARM crypto-extension scan** (`aese/aesd/aesimc/aesmc`) across the full `.text` of `libCore.so` (capstone): **zero hits**. `libCore.so` contains no AES at all.
5. `Decrypt128` / `m_decryptKeyExpansion` / `DecryptData` identifiers in the il2cpp dump are **Mono runtime internals** (`System.Security.Cryptography.RijndaelManagedTransform`), not app crypto — their presence proves nothing about firmware decryption.
6. No plausible key literal among the 9,627 il2cpp string literals (top-entropy candidates are all runtime alphabets/tables).

## Conclusion

The app's native updater (`firmware_updater::HugoStrategy`) receives the image and metadata as byte vectors and performs **no decryption** — no AES implementation exists anywhere in `libCore.so`, and the metadata's 16 bytes do not function as an offline AES key. Best-supported model: **the on-robot bootloader decrypts** (with a key fused/embedded on-device), and the 16 metadata bytes are most plausibly a **truncated hash/checksum** used for version validation (`FirmwareValidationRequest`, `FirmwareUpdaterCoreBridge`).

Residual (unverified) alternative: managed C# code in `libil2cpp.so` decrypting before handing vectors to native code. Considered unlikely because (a) the S-box for Mono's managed AES is absent from the binary, and (b) the pass-through of an encrypted blob with accompanying metadata to the native layer matches the "device-side decrypt" design. Open follow-up: disassemble the `SpheroHugoFirmwareRequest.Start()` RVA chain (dump.cs gives RVAs) to close this fully, or capture a live update over BLE.

## Implications

- Offline decryption of `HugoFirmware.bin` is **not possible from app material alone**.
- Plaintext firmware exists (if anywhere) **inside the robot**: either transiently at update time or persistently in flash. → post-update SWD read (if the chip is unlocked; dump before any ERASEALL) or DEC1 voltage glitch (2020–21 silicon predates rev-3 hardening) are the dump paths.
- A BLE capture of an app-driven update should show ciphertext pages (high-entropy `HereIsPage` payloads) — worth confirming on hardware as a sanity check of this whole model.
