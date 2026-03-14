"""
Daily scan script: scrape VNExpress, filter with Groq, save to Google Sheet.
Runs from GitHub Actions (or cron) using env vars only — no Streamlit.

Required env:
  GROQ_API_KEY
  GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)
    OR GCP_SERVICE_ACCOUNT_JSON (raw JSON string)
"""
import json
import os
import sys
import tempfile
from typing import Any, Dict, List

import gspread
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from groq import Groq

GOOGLE_SHEET_ID = "1VrcsNcyws6wh3ioP9Q_ZNS3PpS1UcbcXZRq3sUxFXvI"
GOOGLE_SHEET_RANGE = "Sheet1"


def get_groq_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY environment variable is not set")
    return Groq(api_key=api_key)


def get_gsheet_client() -> gspread.Client:
    raw = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if raw:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(raw)
            path = f.name
        try:
            creds = Credentials.from_service_account_file(
                path,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            return gspread.authorize(creds)
        finally:
            os.unlink(path)

    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not path or not os.path.isfile(path):
        raise SystemExit(
            "Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON path, "
            "or set GCP_SERVICE_ACCOUNT_JSON to the raw JSON string."
        )
    creds = Credentials.from_service_account_file(
        path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def scrape_vnexpress() -> List[Dict[str, str]]:
    urls = ["https://vnexpress.net/the-gioi", "https://vnexpress.net/so-hoa"]
    news_data: List[Dict[str, str]] = []
    for url in urls:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        for item in soup.select("h3.title-news a")[:10]:
            news_data.append({"title": item.text.strip(), "link": item["href"]})
    return news_data


def ai_filter_news(raw_news: List[Dict[str, str]], client: Groq) -> List[Dict[str, Any]]:
    prompt = (
        "From the following list of news items (each with a title and link), "
        "identify only stories related to either Artificial Intelligence (AI) "
        "or Iran/US conflict.\n\n"
        f"NEWS_LIST:\n{raw_news}\n\n"
        "Return ONLY a valid JSON array (no markdown, no explanation) with this shape:\n"
        '[{"title": "...", "link": "...", "summary": "..."}]'
    )
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    content = completion.choices[0].message.content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(l for l in lines if not l.strip().startswith("```"))
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def save_articles_to_sheet(articles: List[Dict[str, Any]]) -> None:
    gs = get_gsheet_client()
    sh = gs.open_by_key(GOOGLE_SHEET_ID)
    try:
        ws = sh.worksheet(GOOGLE_SHEET_RANGE)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=GOOGLE_SHEET_RANGE, rows=1000, cols=3)
    header = ["title", "link", "summary"]
    values = [header]
    for a in articles:
        values.append([
            a.get("title", ""),
            a.get("link", ""),
            a.get("summary", ""),
        ])
    ws.clear()
    ws.update("A1", values)


def main() -> None:
    print("Daily scan: scraping VNExpress...")
    raw = scrape_vnexpress()
    print(f"  Got {len(raw)} raw items")
    client = get_groq_client()
    print("  Filtering with Groq...")
    articles = ai_filter_news(raw, client)
    print(f"  Filtered to {len(articles)} articles")
    save_articles_to_sheet(articles)
    print("  Saved to Google Sheet. Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
