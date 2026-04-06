"""
Scan pipeline for AI & War News Scout.
No Streamlit dependency; used by app.py and run_scan.py CLI.
Using Hugging Face Hub for storage instead of Google Sheets.
"""
import json
import logging
import io
import random
import re
from typing import List, Dict, Any, Optional

import requests
import pandas as pd
from bs4 import BeautifulSoup
from groq import Groq
from huggingface_hub import hf_hub_download, upload_file

logger = logging.getLogger(__name__)

HF_DATASET_ID = "sonpham172/news-data" # Default, should be configurable
HF_FILENAME = "news.csv"

def load_cached_articles(hf_token: str, repo_id: str) -> List[Dict[str, Any]]:
    """
    Load previously saved articles from Hugging Face Hub CSV file.
    Returns a list of dicts with keys: title, link, summary, image_url, source.
    """
    try:
        if not hf_token or not repo_id:
            return []
            
        file_path = hf_hub_download(
            repo_id=repo_id,
            filename=HF_FILENAME,
            repo_type="dataset",
            token=hf_token
        )
        df = pd.read_csv(file_path)
        # Convert NaN to empty strings for consistency
        df = df.fillna("")
        return df.to_dict('records')
    except Exception as e:
        logger.warning("Could not load cached data from Hugging Face: %s", e)
        return []

def load_config_from_hf(hf_token: str, repo_id: str) -> str:
    """Load the last searched category from a config file on HF (simulating the Config sheet)."""
    try:
        if not hf_token or not repo_id:
            return ""
            
        # We can store config in a separate file or a special row in the CSV
        # For simplicity, let's try to load config.json if it exists
        file_path = hf_hub_download(
            repo_id=repo_id,
            filename="config.json",
            repo_type="dataset",
            token=hf_token
        )
        with open(file_path, 'r') as f:
            config = json.load(f)
            return config.get("categories", "")
    except Exception as e:
        logger.info("Could not load config from HF (expected if first run): %s", e)
        return ""

def save_config_to_hf(categories_str: str, hf_token: str, repo_id: str) -> None:
    """Save the current categories string to config.json on HF."""
    try:
        if not hf_token or not repo_id:
            return
            
        config = {"categories": categories_str}
        config_json = json.dumps(config)
        
        upload_file(
            path_or_fileobj=io.BytesIO(config_json.encode()),
            path_in_repo="config.json",
            repo_id=repo_id,
            repo_type="dataset",
            token=hf_token
        )
    except Exception as e:
        logger.warning("Could not save config to HF: %s", e)

def save_articles_to_hf(
    articles: List[Dict[str, Any]], hf_token: str, repo_id: str
) -> None:
    """
    Save the given list of article dicts into Hugging Face Hub as a CSV,
    overwriting existing content.
    """
    try:
        if not hf_token or not repo_id:
            return

        if not articles:
            return

        df = pd.DataFrame(articles)
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        upload_file(
            path_or_fileobj=csv_buffer,
            path_in_repo=HF_FILENAME,
            repo_id=repo_id,
            repo_type="dataset",
            token=hf_token
        )
    except Exception as e:
        logger.warning("Could not save data to HF: %s", e)


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
    
    # To ensure diversity across sites and categories, shuffle the results
    # before taking the discovery pool.
    shuffled_news = list(raw_news)
    random.shuffle(shuffled_news)
    
    # To save tokens while searching more articles, we only send titles and IDs to the AI
    # Per user requirement: keep limit scan articles to less than 30
    discovery_pool = shuffled_news[:25]
    simplified_news = [{"id": i, "title": n["title"]} for i, n in enumerate(discovery_pool)]

    prompt = (
        f"You are a news curator. Given these titles, pick up to 10 that best match: {target_topics}.\n\n"
        f"TITLES:\n{json.dumps(simplified_news, ensure_ascii=False)}\n\n"
        "For each selected item, return a JSON object with 'id' and 'summary' (a brief 1-2 sentence summary based on the title).\n"
        "Return ONLY a valid JSON array. Example: [{\"id\": 0, \"summary\": \"...\"}]"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = completion.choices[0].message.content.strip()

        # Robust JSON extraction
        match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            selected_items = json.loads(json_str)
        else:
            # Fallback if regex fails but maybe it's raw JSON
            try:
                selected_items = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("AI returned invalid format: %s", content)
                return []
        
        filtered_articles = []
        for item in selected_items:
            idx = item.get("id")
            if idx is not None and 0 <= idx < len(discovery_pool):
                article = discovery_pool[idx].copy()
                article["summary"] = item.get("summary", "")
                filtered_articles.append(article)
        
        return filtered_articles
    except Exception as e:
        logger.error("AI filtering failed: %s", e)
        return []


def run_scan(
    groq_api_key: str,
    hf_token: str,
    hf_repo_id: str,
    categories_str: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Run the full scan pipeline: scrape news, filter with LLM, save to Hugging Face Hub.
    Returns the list of articles.
    """
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required.")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required.")

    if categories_str is None:
        categories_str = load_config_from_hf(hf_token, hf_repo_id)

    client = Groq(api_key=groq_api_key)
    
    all_raw_data = []
    all_raw_data.extend(scrape_vnexpress())
    all_raw_data.extend(scrape_tuoitre())
    all_raw_data.extend(scrape_cafef())
    
    articles = ai_filter_news(all_raw_data, client, categories_str)
    save_articles_to_hf(articles, hf_token, hf_repo_id)
    if categories_str is not None:
        save_config_to_hf(categories_str, hf_token, hf_repo_id)
    return articles