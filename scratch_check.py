import json
import re

with open(r'ui/lib/constants/logs.ts', 'r', encoding='utf-8') as f:
    logs_content = f.read()

# Extract KnownProvidersNames
names_match = re.search(r'export const KnownProvidersNames = \[(.*?)\] as const;', logs_content, re.DOTALL)
if names_match:
    raw_names = re.findall(r'"([^"]+)"', names_match.group(1))
    print(f"Total KnownProvidersNames: {len(raw_names)}")
else:
    raw_names = []

# Extract ProviderLabels
labels_match = re.search(r'export const ProviderLabels: Record<ProviderName, string> = \{(.*?)\} as const;', logs_content, re.DOTALL)
labels = {}
if labels_match:
    for line in labels_match.group(1).splitlines():
        line = line.strip()
        m = re.search(r'["\']?([a-zA-Z0-9_-]+)["\']?:\s*["\']([^"\']+)["\']', line)
        if m:
            labels[m.group(1)] = m.group(2)
print(f"Total ProviderLabels: {len(labels)}")

# Inspect icons.tsx
with open(r'ui/lib/constants/icons.tsx', 'r', encoding='utf-8') as f:
    icons_content = f.read()

icon_keys = []
for line in icons_content.splitlines():
    m = re.match(r'^\t(["a-zA-Z0-9_-]+):\s*\(', line)
    if m:
        k = m.group(1).strip('"\'')
        icon_keys.append(k)
print(f"Total Icon definitions in icons.tsx: {len(icon_keys)}")

# Inspect mcp-library.json
with open(r'configs/mcp-library.json', 'r', encoding='utf-8') as f:
    mcp_data = json.load(f)

print(f"MCP Library type: {type(mcp_data)}")
if isinstance(mcp_data, list):
    print(f"Total MCP Servers in mcp-library.json: {len(mcp_data)}")
    categories = set()
    for s in mcp_data[:5]:
        print(f"Sample server: {s.get('name')} | title: {s.get('title')} | category: {s.get('category')} | transport: {s.get('transport') or s.get('type')}")
    for s in mcp_data:
        if 'category' in s:
            categories.add(s['category'])
    print(f"MCP Categories: {categories}")
elif isinstance(mcp_data, dict):
    print(f"MCP Library keys: {list(mcp_data.keys())}")
    if "servers" in mcp_data:
        print(f"Total servers: {len(mcp_data['servers'])}")
