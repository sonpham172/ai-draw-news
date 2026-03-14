#!/usr/bin/env python3
"""
CLI for the daily news scan. Used by GitHub Actions.
Requires env: GROQ_API_KEY, GCP_SERVICE_ACCOUNT_JSON (raw JSON string).
"""
import json
import os
import sys

from scan import run_scan


def main() -> int:
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    gcp_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "").strip()

    if not groq_key:
        print("Error: GROQ_API_KEY not set", file=sys.stderr)
        return 1
    if not gcp_json:
        print("Error: GCP_SERVICE_ACCOUNT_JSON not set", file=sys.stderr)
        return 1

    try:
        gcp = json.loads(gcp_json)
    except json.JSONDecodeError as e:
        print(f"Error: GCP_SERVICE_ACCOUNT_JSON invalid JSON: {e}", file=sys.stderr)
        return 1

    try:
        articles = run_scan(groq_key, gcp)
        print(f"Scan complete. {len(articles)} articles saved to Google Sheet.")
        return 0
    except Exception as e:
        print(f"Scan failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
