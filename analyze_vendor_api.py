import os, re
src_dir = "tnt-vendor-frontend/src"
used = set()
for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith(('.tsx', '.ts')):
            try:
                with open(os.path.join(root, f), 'r', encoding='utf-8') as fh:
                    for m in re.finditer(r'vendorApi\.(\w+)', fh.read()):
                        used.add(m.group(1))
            except:
                pass
for m in sorted(used):
    print(m)
