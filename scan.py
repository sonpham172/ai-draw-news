"""
Scan pipeline for AI & War News Scout.
No Streamlit dependency; used by app.py and run_scan.py CLI.
"""
import json
import logging
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from groq import Groq
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

GOOGLE_SHEET_ID = "1VrcsNcyws6wh3ioP9Q_ZNS3PpS1UcbcXZRq3sUxFXvI"
GOOGLE_SHEET_RANGE = "Sheet1"
GOOGLE_SHEET_CONFIG_RANGE = "Config"


def get_gsheet_client(service_account_info: dict) -> gspread.Client:
    """
    Create an authenticated gspread client from a service account info dict.
    """
    if not service_account_info:
        raise RuntimeError(
            "GCP_SERVICE_ACCOUNT is required. "
            "Provide your Google service account config as a dict."
        )
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)


def load_cached_articles(service_account_info: dict) -> List[Dict[str, Any]]:
    """
    Load previously saved articles from the Google Sheet.
    Returns a list of dicts with keys: title, link, summary, image_url, source.
    """
    try:
        client = get_gsheet_client(service_account_info)
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sh.worksheet(GOOGLE_SHEET_RANGE)
        except gspread.WorksheetNotFound:
            ws = sh.sheet1

        rows = ws.get_all_records()
        articles: List[Dict[str, Any]] = []
        for row in rows:
            articles.append(
                {
                    "title": row.get("title") or row.get("Title") or "",
                    "link": row.get("link") or row.get("Link") or "",
                    "summary": row.get("summary") or row.get("Summary") or "",
                    "image_url": row.get("image_url") or row.get("Image") or "",
                    "source": row.get("source") or row.get("Source") or "",
                }
            )
        return articles
    except Exception as e:
        logger.warning("Could not load cached data from Google Sheet: %s", e)
        return []


def load_config_from_sheet(service_account_info: dict) -> str:
    """Load the last searched category from the Config sheet."""
    try:
        client = get_gsheet_client(service_account_info)
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sh.worksheet(GOOGLE_SHEET_CONFIG_RANGE)
        except gspread.WorksheetNotFound:
            return ""
        
        records = ws.get_all_records()
        for row in records:
            if row.get("Key") == "categories":
                return str(row.get("Value") or "")
        return ""
    except Exception as e:
        logger.warning("Could not load config from Google Sheet: %s", e)
        return ""


def save_config_to_sheet(categories_str: str, service_account_info: dict) -> None:
    """Save the current categories string to the Config sheet."""
    try:
        client = get_gsheet_client(service_account_info)
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sh.worksheet(GOOGLE_SHEET_CONFIG_RANGE)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=GOOGLE_SHEET_CONFIG_RANGE, rows="10", cols="2")
        
        ws.clear()
        ws.update("A1", [["Key", "Value"], ["categories", categories_str]])
    except Exception as e:
        logger.warning("Could not save config to Google Sheet: %s", e)


def save_articles_to_sheet(
    articles: List[Dict[str, Any]], service_account_info: dict
) -> None:
    """
    Save the given list of article dicts into the Google Sheet,
    overwriting existing content.
    """
    try:
        client = get_gsheet_client(service_account_info)
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sh.worksheet(GOOGLE_SHEET_RANGE)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=GOOGLE_SHEET_RANGE, rows="1000", cols="5")

        header = ["title", "link", "summary", "image_url", "source"]
        values = [header]
        for a in articles:
            values.append(
                [
                    a.get("title", ""),
                    a.get("link", ""),
                    a.get("summary", ""),
                    a.get("image_url", ""),
                    a.get("source", ""),
                ]
            )

        ws.clear()
        ws.update("A1", values)
    except Exception as e:
        logger.warning("Could not save data to Google Sheet: %s", e)


def scrape_vnexpress() -> List[Dict[str, str]]:
    """Scrape VNExpress for headline links with images and source."""
    urls = [
        "https://vnexpress.net/the-thao",
        "https://vnexpress.net/kinh-doanh",
        "https://vnexpress.net/the-gioi",
        "https://vnexpress.net/so-hoa",
        "https://vnexpress.net/thoi-su",
        "https://vnexpress.net/giai-tri",
    ]
    news_data = []
    for url in urls:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            for item in soup.select("h3.title-news a")[:10]:
                title = item.text.strip()
                href = item.get("href", "")
                
                # Find associated image
                parent = item.find_parent("div")
                img = parent.find("img") if parent else None
                img_src = img.get("data-src") or img.get("src") if img else ""
                
                if href:
                    news_data.append({
                        "title": title,
                        "link": href,
                        "image_url": img_src,
                        "source": "VNExpress",
                    })
        except Exception as e:
            logger.warning("Could not scrape VNExpress (%s): %s", url, e)
    return news_data

def scrape_tuoitre() -> List[Dict[str, str]]:
    """Scrape Tuoi Tre for headline links with images and source."""
    urls = [
        "https://tuoitre.vn/thoi-su.htm",
        "https://tuoitre.vn/kinh-doanh.htm",
        "https://tuoitre.vn/the-thao.htm",
        "https://tuoitre.vn/van-hoa.htm",
        "https://tuoitre.vn/khoa-hoc.htm",
    ]
    news_data = []
    for url in urls:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            for item in soup.select("li.content-item__item--image a.content-item__title")[:10]:
                title = item.text.strip()
                href = "https://tuoitre.vn" + item.get("href", "")
                
                # Find associated image
                parent = item.find_parent("li")
                img = parent.select_one("a.content-item__thumb img") if parent else None
                img_src = img.get("src") if img else ""
                
                if href:
                    news_data.append({
                        "title": title,
                        "link": href,
                        "image_url": img_src,
                        "source": "TuoiTre",
                    })
        except Exception as e:
            logger.warning("Could not scrape Tuoi Tre (%s): %s", url, e)
    return news_data

def scrape_cafef() -> List[Dict[str, str]]:
    """Scrape CafeF for headline links with images and source."""
    urls = [
        "https://cafef.vn/thoi-su.chn",
        "https://cafef.vn/kinh-doanh.chn",
        "https://cafef.vn/thi-truong-chung-khoan.chn",
        "https://cafef.vn/bat-dong-san.chn",
        "https://cafef.vn/doanh-nghiep.chn",
    ]
    news_data = []
    for url in urls:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            for item in soup.select(".tlitem h3 a")[:10]:
                title = item.text.strip()
                href = "https://cafef.vn" + item.get("href", "") if item.get("href", "").startswith("/") else item.get("href", "")
                
                # Find associated image (CafeF often has images directly within or near the .tlitem)
                parent = item.find_parent(".tlitem")
                img = parent.select_one("img.thumb") if parent else None # Adjust image selector for CafeF
                img_src = img.get("src") if img else ""
                
                if href:
                    news_data.append({
                        "title": title,
                        "link": href,
                        "image_url": img_src,
                        "source": "CafeF",
                    })
        except Exception as e:
            logger.warning("Could not scrape CafeF (%s): %s", url, e)
    return news_data


def ai_filter_news(raw_news: List[Dict[str, str]], groq_client: Groq, categories_str: str) -> List[Dict[str, Any]]:
    """Use Groq LLM to filter raw news based on categories; return list of dicts with title, link, summary, image_url, source."""
    target_topics = categories_str if categories_str else "Artificial Intelligence (AI) or Iran/US conflict"
    prompt = (
        "From the following list of news items (each with title, link, image_url, source), "
        f"identify only stories related to: {target_topics}.\n\n"
        f"NEWS_LIST:\n{raw_news}\n\n"
        "For each selected story, create a brief summary (1-2 sentences).\n"
        "Return ONLY a valid JSON array (no markdown, no explanation) with this shape:\n"
        "[{\"title\": \"...\", \"link\": \"...\", \"summary\": \"...\", \"image_url\": \"...\", \"source\": \"...\"}]"
    )

    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    content = completion.choices[0].message.content.strip()

    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(line for line in lines if not line.strip().startswith("```"))

    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return []


def run_scan(
    groq_api_key: str,
    gcp_service_account: dict,
    categories_str: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Run the full scan pipeline: scrape VNExpress, filter with LLM, save to Google Sheet.
    Returns the list of articles. Raises on missing config; logs warnings for sheet I/O errors.
    """
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required.")
    if not gcp_service_account:
        raise RuntimeError("GCP_SERVICE_ACCOUNT is required.")

    if categories_str is None:
        categories_str = load_config_from_sheet(gcp_service_account)

    client = Groq(api_key=groq_api_key)
    
    all_raw_data = []
    all_raw_data.extend(scrape_vnexpress())
    all_raw_data.extend(scrape_tuoitre())
    all_raw_data.extend(scrape_cafef())
    
    articles = ai_filter_news(all_raw_data, client, categories_str)
    save_articles_to_sheet(articles, gcp_service_account)
    if categories_str is not None:
        save_config_to_sheet(categories_str, gcp_service_account)
    return articles
