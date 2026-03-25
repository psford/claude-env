#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Library introduction research gate.
Blocks Write of HTML/csproj that adds a new CDN script or NuGet package
without a corresponding design-plan or research doc.
Exit code 2 = hard block.
"""
import json, sys, re, os, glob

CDN_SCRIPT = re.compile(r'<script\b[^>]*\bsrc=["\']https?://', re.IGNORECASE)
NUGET_PKG = re.compile(r'<PackageReference\s+Include=["\']([^"\']+)["\']', re.IGNORECASE)
BYPASS = re.compile(r'<!--\s*LIBRARY-RESEARCHED\s*:', re.IGNORECASE)
CDN_NAME = re.compile(r'(?:unpkg\.com|cdn\.jsdelivr\.net/npm|cdnjs\.cloudflare\.com/ajax/libs)/([a-z0-9._-]+)', re.IGNORECASE)

def extract_lib_name(line):
    m = CDN_NAME.search(line)
    if m:
        return m.group(1).lower()
    src = re.search(r'src=["\']([^"\']+)["\']', line, re.IGNORECASE)
    if src:
        segment = src.group(1).rstrip('/').split('/')[-1]
        return re.split(r'[@?]', segment)[0].lower() or None
    return None

def docs_mention(name, root):
    for d in ["docs/design-plans", "docs/research"]:
        search_dir = os.path.join(root, d)
        if not os.path.isdir(search_dir):
            continue
        for md in glob.glob(os.path.join(search_dir, "**", "*.md"), recursive=True):
            try:
                with open(md, "r", encoding="utf-8", errors="ignore") as f:
                    if re.search(re.escape(name), f.read(), re.IGNORECASE):
                        return True
            except OSError:
                continue
    return False

def get_root():
    path = os.getcwd()
    for _ in range(10):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return os.getcwd()

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if hook_input.get("tool_name") != "Write":
        return 0
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    content = hook_input.get("tool_input", {}).get("content", "")
    if not re.search(r'\.(html|csproj)$', file_path, re.IGNORECASE) or not content:
        return 0

    root = get_root()
    violations = []
    for line in content.splitlines():
        if BYPASS.search(line):
            continue
        lib = None
        if re.search(r'\.html$', file_path, re.IGNORECASE) and CDN_SCRIPT.search(line):
            lib = extract_lib_name(line)
        elif re.search(r'\.csproj$', file_path, re.IGNORECASE):
            m = NUGET_PKG.search(line)
            if m:
                lib = m.group(1).lower()
        if lib and not docs_mention(lib, root):
            violations.append((lib, line.strip()[:120]))

    if not violations:
        return 0
    print("BLOCKED: New library introduced without documented API research", file=sys.stderr)
    for lib, line in violations:
        print(f"  Library: {lib}", file=sys.stderr)
        print(f"  Line: {line}", file=sys.stderr)
    print("\nCreate a design-plan or research doc mentioning this library first.", file=sys.stderr)
    print("Or add <!-- LIBRARY-RESEARCHED: reason --> on the line.", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
