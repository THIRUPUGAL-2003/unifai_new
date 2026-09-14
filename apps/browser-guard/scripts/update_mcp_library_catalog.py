import json

with open("mcp_290_categorized_report.json", "r", encoding="utf-8") as f:
    classified = json.load(f)

header_server_names = set(s["name"] for s in classified if s["status"] == "Headers / API Key Method Supported")
print(f"Total Header Servers to update: {len(header_server_names)}")

with open("configs/mcp-library.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

updated_count = 0
for server in catalog.get("servers", []):
    name = server.get("name")
    if name in header_server_names:
        server["auth_type"] = "headers"
        # Set default required header key
        if not server.get("required_header_keys"):
            if "AWS Marketplace" in name or "aws" in server.get("connection_url", "").lower():
                server["required_header_keys"] = ["Authorization"]
            elif "pinecone" in name.lower() or "pinecone" in server.get("connection_url", "").lower():
                server["required_header_keys"] = ["Api-Key"]
            else:
                server["required_header_keys"] = ["Authorization"]
        
        # Update tags
        tags = server.get("tags", [])
        if "oauth" in tags:
            tags.remove("oauth")
        if "headers" not in tags:
            tags.append("headers")
        server["tags"] = tags
        updated_count += 1

print(f"Successfully updated {updated_count} servers in configs/mcp-library.json to auth_type='headers'")

with open("configs/mcp-library.json", "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2)

print("Saved updated configs/mcp-library.json")
