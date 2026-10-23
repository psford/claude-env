"""Disassemble firmware_updater::* from libCore.so; hunt AES instructions and rodata constants."""
import sys
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

SO = '/tmp/sphero-indi/edujr/lib/arm64-v8a/libCore.so'
f = open(SO, 'rb')
elf = ELFFile(f)

secs = {}
for s in elf.iter_sections():
    secs[s.name] = (s['sh_addr'], s['sh_size'], s.data() if s['sh_type'] != 'SHT_NOBITS' else b'')

text_addr, text_size, text_data = secs['.text']

dynsym = elf.get_section_by_name('.dynsym')
fwu = {}
for sym in dynsym.iter_symbols():
    n = sym.name
    if 'firmware_updater' in n and sym['st_value'] and sym['st_size']:
        fwu.setdefault(n.split('C1E')[0].split('C2E')[0], []).append((sym.name, sym['st_value'], sym['st_size']))

targets = [k for k in fwu if 'Hugo' in k or 'SistrHandler' in k]
print('target funcs:')
for t in sorted(targets):
    for name, addr, size in fwu[t]:
        print(f'  {name}  addr=0x{addr:x} size={size}')

md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

def disasm_range(addr, size, label):
    print(f'\n===== {label} @0x{addr:x} (+{size}) =====')
    off = addr - text_addr
    code = text_data[off:off + size]
    n = 0
    for i in md.disasm(code, addr):
        print(f'0x{i.address:x}: {i.mnemonic} {i.op_str}')
        n += 1
        if n > 400:
            print('...(truncated)')
            break

# 1) whole-.text scan for AES instructions
aes_hits = []
for i in md.disasm(text_data, text_addr):
    if i.mnemonic in ('aese', 'aesd', 'aesimc', 'aesmc'):
        aes_hits.append((i.address, i.mnemonic))
print(f'\nAES-instruction hits in .text: {len(aes_hits)}')
for a, m in aes_hits[:10]:
    print(f'  0x{a:x} {m}')

# 2) disassemble HugoStrategy ctor and constructHugoUpdater*
for t in sorted(targets):
    for name, addr, size in fwu[t]:
        if size and size < 3000:
            disasm_range(addr, size, name)
