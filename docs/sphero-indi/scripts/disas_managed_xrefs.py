"""Disassemble the managed firmware-update chain from libil2cpp.so (indi / edujr) and
xref every crypto / file-I/O method in the binary.

Method: dump.cs gives RVA + Offset per method (51k methods). The executable PT_LOAD
segment covers .text (runtime) + a custom `il2cpp` section (all C# code). We scan
every 4-byte word in that segment for the AArch64 BL opcode (100101 imm26) and
resolve targets against the dump.cs RVA map — a complete direct-call xref of the
binary. See docs/sphero-indi/crypto-analysis.md for the findings this produced.

Usage: python3 disas_managed_xrefs.py [disasm|fn <hex-rva>]
"""
import json
import re
import struct
import sys
from bisect import bisect_right

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

DUMP = '/tmp/sphero-indi/out/dump.cs'
SO = '/tmp/sphero-indi/edujr/lib/arm64-v8a/libil2cpp.so'
STRLIT = '/tmp/sphero-indi/out/stringliteral.json'
EXEC_BASE = 0x10F5020  # executable PT_LOAD: .text + il2cpp + .plt
EXEC_SIZE = 0x18FB800

# ---------- dump.cs -> {rva: "Namespace.Class::Method"} ----------
rva_re = re.compile(r'^\s*// RVA: (0x[0-9A-Fa-f]+|-1)')
ns_re = re.compile(r'^// Namespace: (.*)$')
type_re = re.compile(r'^[\w.<>\s]*?\b(class|struct|enum|interface)\s+([\w.<>`]+)')

def parse_dump():
    methods, order = {}, []
    cur_ns = cur_type = ''
    lines = open(DUMP, encoding='utf-8', errors='replace').read().splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = ns_re.match(ln)
        if m:
            cur_ns = m.group(1).strip(); i += 1; continue
        m = type_re.match(ln)
        if m and 'TypeDefIndex' in ln:
            cur_type = m.group(2); i += 1; continue
        m = rva_re.match(ln)
        if m and m.group(1) != '-1':
            rva = int(m.group(1), 16)
            j = i + 1; sig = ''
            while j < len(lines) and j < i + 6:
                s = lines[j].strip()
                if s and not s.startswith('//') and not s.startswith('/*') and not s.startswith('|'):
                    sig = s; break
                j += 1
            name = sig.split('(')[0].split()[-1] if sig else '?'
            full = (cur_ns + '.' if cur_ns else '') + cur_type + '::' + name
            if rva not in methods:
                methods[rva] = full; order.append(rva)
            i += 1; continue
        i += 1
    order.sort()
    return methods, order

methods, order = parse_dump()

def enclosing(rva):
    idx = bisect_right(order, rva) - 1
    return (methods[order[idx]], order[idx]) if idx >= 0 else ('<runtime/native>', 0)

f = open(SO, 'rb')
elf = ELFFile(f)
loads = [(s['p_vaddr'], s['p_memsz'], s['p_offset'], s['p_filesz'])
         for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']

def va_to_off(va):
    for vaddr, memsz, off, filesz in loads:
        if vaddr <= va < vaddr + memsz and va - vaddr < filesz:
            return off + (va - vaddr)
    return None

strtab = {int(it['address'], 16): it['value'] for it in json.load(open(STRLIT))}
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

def disasm(rva, label=None, max_ins=1200):
    nm = methods.get(rva) or enclosing(rva)[0]
    idx = bisect_right(order, rva)
    end = order[idx] if idx < len(order) else rva + 0x2000
    f.seek(va_to_off(rva))
    code = f.read(end - rva)
    print(f'===== {label or nm} @0x{rva:x}..0x{end:x} =====')
    adrp, n = {}, 0
    for ins in md.disasm(code, rva):
        ann = ''
        if ins.mnemonic == 'bl':
            tgt = int(ins.op_str.replace('#', ''), 16)
            t = methods.get(tgt)
            ann = f'   ; -> {t}' if t else ''
        elif ins.mnemonic == 'blr':
            ann = '   ; indirect'
        elif ins.mnemonic == 'b' and ins.op_str.startswith('#'):
            t = methods.get(int(ins.op_str[1:], 16))
            if t:
                ann = f'   ; tailcall -> {t}'
        if ins.mnemonic == 'adrp':
            p = ins.op_str.split(', ')
            if len(p) == 2:
                try: adrp[p[0]] = int(p[1].replace('#', ''), 16)
                except ValueError: pass
        ops = ins.op_str.split(', ')
        if ins.mnemonic == 'add' and len(ops) == 3 and ops[0] == ops[1] and ops[2].startswith('#'):
            try:
                b = adrp.get(ops[0])
                imm = int(ops[2][1:], 16) if ops[2].startswith('0x') else int(ops[2][1:])
                if b is not None and (b + imm) in strtab:
                    ann = f'   ; STR "{strtab[b + imm][:70]}"'
            except ValueError: pass
        if ins.mnemonic == 'ldr':
            m = re.match(r'(\w+), \[(\w+), #?(0x[0-9a-f]+|\d+)?\]?', ins.op_str)
            if m:
                b = adrp.get(m.group(2))
                if b is not None:
                    iv = int(m.group(3), 16) if m.group(3) else 0
                    if (b + iv) in strtab:
                        ann = f'   ; STRPTR "{strtab[b + iv][:70]}"'
        print(f'0x{ins.address:x}: {ins.mnemonic} {ins.op_str}{ann}')
        n += 1
        if n > max_ins:
            print('...(truncated)'); break

def xref_scan():
    watch_re = re.compile(
        r'(Crypto|AesManaged|Rijndael|SymmetricAlgorithm|HMAC|SHA\d|MD5|ICryptoTransform'
        r'|File::ReadAllBytes$|File::Open$|File::Copy$|FileStream::.ctor'
        r'|FirmwareUpdater::set_(Nordic|St|Audio|Animation))', re.I)
    watch = {r: n for r, n in methods.items() if watch_re.search(n)}
    f.seek(va_to_off(EXEC_BASE))
    data = f.read(EXEC_SIZE)
    xrefs = {}
    for i in range(len(data) // 4):
        w = struct.unpack_from('<I', data, i * 4)[0]
        if (w >> 26) == 0b100101:  # BL
            imm = w & 0x3FFFFFF
            if imm & 0x2000000:
                imm -= 0x4000000
            tgt = EXEC_BASE + i * 4 + (imm << 2)
            if tgt in watch:
                xrefs.setdefault(tgt, []).append(EXEC_BASE + i * 4)
    for tgt in sorted(xrefs):
        print(f'{watch[tgt]} @0x{tgt:x}: {len(xrefs[tgt])} call site(s)')
        for s in xrefs[tgt][:12]:
            fn, frva = enclosing(s)
            print(f'   0x{s:x} in {fn} (starts 0x{frva:x})')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'disasm'
    if cmd == 'disasm':
        for rva, label in [
            (0x14E1E50, 'SpheroHugoFirmwareRequest::Start'),
            (0x14DD808, 'FirmwareUpdateQueue::StartFirmwareUpdate'),
            (0x1423A88, 'FirmwareUpdater::Start'),
            (0x14248E4, 'FirmwareUpdaterCoreBridge::SendSistr'),
        ]:
            disasm(rva, label)
    elif cmd == 'fn':
        disasm(int(sys.argv[2], 16))
    elif cmd == 'xref':
        xref_scan()
