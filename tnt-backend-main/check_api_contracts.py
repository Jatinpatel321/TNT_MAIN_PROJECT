import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

with open("routes_dump.json") as f:
    routes = json.load(f)

# Build canonical backend patterns: each {param} -> "*"
backend_canonical = set()
for r in routes:
    p = r["path"]
    canon = re.sub(r"\{[^}]+\}", "*", p)
    backend_canonical.add(canon)

def matches_backend(canon_candidate):
    return canon_candidate in backend_canonical

def normalize_canonical(raw):
    """Return set of canonical backend paths this frontend literal could map to."""
    v = raw.strip()
    # Remove template expr ${...} -> {x}
    v = re.sub(r"\$\{[^}]+\}", "{x}", v)
    # Strip query
    v = v.split("?")[0]
    # Strip trailing slash
    v = v.rstrip("/")
    if not v:
        return set()
    # If it's a full URL, extract path
    if v.startswith("http"):
        m = re.match(r"https?://[^/]+(.*)", v)
        v = m.group(1) if m else v
    # Canonicalize all {param} -> *
    canon = re.sub(r"\{[^}]+\}", "*", v)
    candidates = set()
    if canon.startswith("/v1"):
        candidates.add(canon)
        candidates.add(canon[3:] or "/")
    else:
        candidates.add("/v1" + canon)
        candidates.add(canon)
    return candidates

scan_dirs = [
    ("user", "../tnt-user-frontend/src/services"),
    ("vendor", "../tnt-vendor-frontend/src/services"),
    ("admin", "../tnt-admin/src/api"),
]

string_re = re.compile(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|`([^`\\]|\\.)*`")

found_paths = {}
missing = {}

for label, d in scan_dirs:
    full = os.path.normpath(os.path.join(BASE, d))
    if not os.path.isdir(full):
        print(f"[{label}] directory missing: {full}")
        continue
    for root, _, files in os.walk(full):
        for fn in sorted(files):
            if not fn.endswith(".ts") and not fn.endswith(".tsx"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                if "apiClient" not in line and ".get(" not in line and ".post(" not in line and ".put(" not in line and ".delete(" not in line and ".patch(" not in line:
                    continue
                for m in string_re.finditer(line):
                    inner = m.group(0)[1:-1]
                    if " " in inner:
                        continue
                    if not inner.startswith("/"):
                        continue
                    if inner.startswith("//") or inner.startswith("/uploads"):
                        continue
                    if inner == "/":
                        continue
                    candidates = normalize_canonical(inner)
                    resolved = any(matches_backend(c) for c in candidates)
                    key = inner
                    # Only record user/vendor/admin services paths (skip non-API strings)
                    if not resolved:
                        missing[key] = {"label": label, "file": os.path.relpath(fp, BASE), "line": idx}
                    else:
                        found_paths[key] = {"label": label}

print(f"Total distinct API path literals found: {len(found_paths) + len(missing)}")
print(f"MISSING paths: {len(missing)}")
print("=" * 70)
for k, v in sorted(missing.items()):
    print(f"[{v['label']:6}] {k}   <- {v['file']}:{v['line']}")
print("=" * 70)
print("Resolved (count):", len(found_paths))
