#!/usr/bin/env python3
"""
CLI for the daily news scan. Used by GitHub Actions.
Requires env: GROQ_API_KEY, HF_TOKEN, HF_REPO_ID (optional).
"""
import os
import sys

from scan import run_scan


def main() -> int:
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    hf_repo_id = os.environ.get("HF_REPO_ID", "sonpham172/news-data").strip()

    if not groq_key:
        print("Error: GROQ_API_KEY not set", file=sys.stderr)
        return 1
    if not hf_token:
        print("Error: HF_TOKEN not set", file=sys.stderr)
        return 1

    try:
        articles = run_scan(groq_key, hf_token, hf_repo_id)
        print(f"Scan complete. {len(articles)} articles cached to Hugging Face: {hf_repo_id}")
        return 0
    except Exception as e:
        print(f"Scan failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())