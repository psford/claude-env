from Crypto.Cipher import AES
import struct

fw = open('HugoFirmware.bin', 'rb').read()
md = open('HugoFirmwareMetadata.bin', 'rb').read()
key = md[2:18]
print('fw len', len(fw), 'header hex:', fw[:24].hex())
print('key:', key.hex())


def score(block, label):
    sp = struct.unpack('<I', block[:4])[0] if len(block) >= 4 else 0
    arm = (sp & 0xFF000000) == 0x20000000
    printable = sum(32 <= b < 127 for b in block) / len(block)
    flag = '  <== ARM SP!' if arm else ''
    print('%-30s %s print=%.2f%s' % (label, block[:12].hex(), printable, flag))
    return arm


score(fw[:24], 'raw header @0')
for off in (0, 24):
    seg = fw[off:off + 48]
    c = AES.new(key, AES.MODE_ECB)
    score(c.decrypt(seg), 'AES-ECB @%d' % off)
    c = AES.new(key, AES.MODE_CBC, b'\x00' * 16)
    score(c.decrypt(seg), 'AES-CBC0 @%d' % off)
    c = AES.new(key, AES.MODE_CBC, md[18:34])
    score(c.decrypt(seg), 'AES-CBCmd @%d' % off)
    x = bytes(seg[i] ^ key[i % 16] for i in range(len(seg)))
    score(x, 'XOR-repeat @%d' % off)
