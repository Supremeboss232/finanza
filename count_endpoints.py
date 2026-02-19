#!/usr/bin/env python3
"""Count endpoints after fixing prefixes."""

import requests
import json
from collections import defaultdict

try:
    response = requests.get("http://localhost:8000/openapi.json", timeout=5)
    response.raise_for_status()
    
    schema = response.json()
    paths = schema.get("paths", {})
    
    total = len(paths)
    print(f"✅ Server responding!")
    print(f"Total endpoints: {total}")
    print()
    
    # Count by feature
    features = defaultdict(list)
    for path in paths:
        if "scheduled-transfers" in path:
            features["Scheduled Transfers"].append(path)
        elif "webhooks" in path:
            features["Webhooks"].append(path)
        elif "mobile-deposits" in path:
            features["Mobile Deposits"].append(path)
        elif "compliance" in path:
            features["Compliance"].append(path)
        else:
            features["Other/Legacy"].append(path)
    
    for feature, endpoints in sorted(features.items()):
        print(f"{feature}: {len(endpoints)} endpoints")
        for ep in sorted(endpoints):
            print(f"  - {ep}")
    
except Exception as e:
    print(f"❌ Error: {e}")
