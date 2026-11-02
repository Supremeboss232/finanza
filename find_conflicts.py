import re

# Get all tablenames from models_priority_3.py
p3_tables = {}
with open('models_priority_3.py', encoding='utf-8') as f:
    lines = f.readlines()

current_class = None
for i, line in enumerate(lines):
    cm = re.match(r'^class (\w+)\(', line)
    if cm:
        current_class = cm.group(1)
    tm = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', line)
    if tm and current_class:
        p3_tables[tm.group(1)] = (current_class, i+1)

print("models_priority_3.py tables:")
for t, (c, ln) in sorted(p3_tables.items()):
    print(f"  {t!r:40s}  ({c}, line {ln})")

# Get all tablenames from models.py and find conflicts
models_tables = {}
with open('models.py', encoding='utf-8') as f:
    lines = f.readlines()

current_class = None
for i, line in enumerate(lines):
    cm = re.match(r'^class (\w+)\(', line)
    if cm:
        current_class = cm.group(1)
    tm = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', line)
    if tm and current_class:
        models_tables[tm.group(1)] = (current_class, i+1)

print("\nCONFLICTS (in both files):")
for t in sorted(p3_tables):
    if t in models_tables:
        p3c, p3l = p3_tables[t]
        mc, ml = models_tables[t]
        has_extend = False
        # Check if models.py version has extend_existing
        for j in range(ml, min(ml+10, len(lines))):
            if 'extend_existing' in lines[j]:
                has_extend = True
                break
        print(f"  {t!r:40s}  models.py line {ml} ({mc})  extend={has_extend}")
