import json
from app.main import app

schema = app.openapi()
paths = schema.get("paths", {})

routes = []
for path, methods_map in paths.items():
    methods = sorted(methods_map.keys())
    routes.append({"path": path, "methods": methods})

with open("routes_dump.json", "w") as f:
    json.dump(routes, f, indent=2)

print(f"Dumped {len(routes)} paths to routes_dump.json")
