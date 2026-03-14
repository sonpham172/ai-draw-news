import json
from typing import List, Dict, Any

import requests
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq
import gspread
from google.oauth2.service_account import Credentials

# 1. Setup Groq (Key is stored in Streamlit Secrets)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# 2. Google Sheets configuration
GOOGLE_SHEET_ID = "1VrcsNcyws6wh3ioP9Q_ZNS3PpS1UcbcXZRq3sUxFXvI"
GOOGLE_SHEET_RANGE = "Sheet1"  # adjust if your sheet/tab name is different


def get_gsheet_client() -> gspread.Client:
    """
    Create an authenticated gspread client using a service account JSON
    stored in Streamlit secrets under key 'GCP_SERVICE_ACCOUNT'.
    """
    service_info = st.secrets.get("GCP_SERVICE_ACCOUNT")
    if not service_info:
        raise RuntimeError(
            "GCP_SERVICE_ACCOUNT not found in Streamlit secrets. "
            "Add your Google service account JSON under that key."
        )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(service_info, scopes=scopes)
    return gspread.authorize(creds)


def load_cached_articles() -> List[Dict[str, Any]]:
    """
    Load previously saved articles from the Google Sheet.
    Returns a list of dicts with keys: title, link, summary.
    """
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        # Use the first worksheet or a named one
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
                }
            )
        return articles
    except Exception as e:
        st.warning(f"Could not load cached data from Google Sheet: {e}")
        return []


def save_articles_to_sheet(articles: List[Dict[str, Any]]) -> None:
    """
    Save the given list of article dicts into the Google Sheet,
    overwriting existing content.
    """
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sh.worksheet(GOOGLE_SHEET_RANGE)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=GOOGLE_SHEET_RANGE, rows="1000", cols="3")

        # Prepare data: header row + data rows
        header = ["title", "link", "summary"]
        values = [header]
        for a in articles:
            values.append(
                [
                    a.get("title", ""),
                    a.get("link", ""),
                    a.get("summary", ""),
                ]
            )

        ws.clear()
        ws.update("A1", values)
    except Exception as e:
        st.warning(f"Could not save data to Google Sheet: {e}")

def scrape_vnexpress():
    # Targets the 'World' and 'Tech' sections
    urls = ["https://vnexpress.net/the-gioi", "https://vnexpress.net/so-hoa"]
    news_data = []
    for url in urls:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        for item in soup.select("h3.title-news a")[:10]:
            news_data.append({"title": item.text.strip(), "link": item["href"]})
    return news_data


def scrape_article_body(url: str) -> str:
    """
    Fetch and extract the main article content from the original news page.
    Currently tuned for VNExpress layout.
    """
    if not url:
        return ""

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
    except Exception as e:
        st.warning(f"Could not fetch full article content: {e}")
        return ""

    soup = BeautifulSoup(res.text, "html.parser")

    # VNExpress articles typically use these containers
    container = soup.select_one(".article-body") or soup.select_one(".fck_detail")
    if not container:
        # Fallback: try main content area
        container = soup.select_one("article") or soup.select_one("div#main_detail")

    if not container:
        return ""

    # Join paragraphs with blank lines to resemble original flow
    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    text = "\n\n".join(p for p in paragraphs if p)
    return text.strip()

def ai_filter_news(raw_news):
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
        content = "\n".join(line for line in lines if not line.strip().startswith("```"))

    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return []

# 2. UI Layout
st.set_page_config(page_title="AI & War News Scout", page_icon="🤖")

# Fix font so Vietnamese and other scripts render correctly
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] {
        font-family: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
      }
      .stMarkdown, .stMarkdown p {
        font-family: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        word-wrap: break-word;
        overflow-wrap: break-word;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🛡️ Early Morning Intelligence")

if "view" not in st.session_state:
    st.session_state.view = "list"
if "articles" not in st.session_state:
    st.session_state.articles = []
if "selected_index" not in st.session_state:
    st.session_state.selected_index = None

# On first load, try to populate from Google Sheet cache
if not st.session_state.articles:
    cached = load_cached_articles()
    if cached:
        st.session_state.articles = cached

if st.button("Scan Today's News"):
    # Always fetch fresh data from the internet + LLM and update the sheet
    with st.spinner("Scraping VnExpress & CafeF and calling LLM..."):
        raw_data = scrape_vnexpress()
        articles = ai_filter_news(raw_data)
        st.session_state.articles = articles
        save_articles_to_sheet(articles)

    st.success("Feed refreshed from web + LLM and cached to Google Sheets.")
    st.session_state.view = "list"
    st.session_state.selected_index = None

if st.session_state.view == "list":
    if not st.session_state.articles:
        st.info("Click 'Scan Today's News' to fetch the latest AI & conflict headlines.")
    else:
        for idx, article in enumerate(st.session_state.articles):
            with st.container(border=True):
                st.markdown(
                    f"### {article.get('title', f'Article {idx + 1}')}",
                    help="AI-filtered headline",
                )
                link = article.get("link", "")
                if link:
                    st.markdown(f"[Open original source]({link})", help="Opens the news site")
                summary = article.get("summary", "")
                if summary:
                    st.write(summary)

                cols = st.columns([1, 1])
                with cols[0]:
                    if st.button("View details", key=f"view-{idx}"):
                        st.session_state.selected_index = idx
                        st.session_state.view = "detail"
                        st.rerun()
                with cols[1]:
                    if link:
                        st.link_button("Go to source ↗", link, use_container_width=True)

elif st.session_state.view == "detail":
    idx = st.session_state.selected_index
    articles = st.session_state.articles

    if idx is None or not articles or idx < 0 or idx >= len(articles):
        st.warning("No article selected.")
    else:
        article = articles[idx]
        top_cols = st.columns([1, 3])
        with top_cols[0]:
            if st.button("← Back to list"):
                st.session_state.view = "list"
                st.session_state.selected_index = None
                st.rerun()
        with top_cols[1]:
            st.caption("AI & War News Scout · Detail view")

        title = article.get("title", "Selected article")
        link = article.get("link")
        summary = article.get("summary")

        # Fetch full article content from the source site
        body_text = ""
        if link:
            with st.spinner("Loading full article from source..."):
                body_text = scrape_article_body(link)

        # Hero section similar to a news article header
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg,#020617,#0f172a);
                padding: 1.5rem 1.75rem;
                border-radius: 1rem;
                margin-bottom: 1.5rem;
                color: #e5e7eb;
            ">
              <div style="font-size:0.75rem;letter-spacing:0.08em;text-transform:uppercase;color:#9ca3af;margin-bottom:0.25rem;">
                Early Morning Intelligence
              </div>
              <h1 style="font-size:1.6rem;line-height:1.3;margin:0 0 0.75rem 0;font-weight:700;color:#f9fafb;">
                {title}
              </h1>
              {"<a href='" + link + "' style='font-size:0.85rem;color:#a5b4fc;text-decoration:none;' target='_blank' rel='noopener noreferrer'>View original article ↗</a>" if link else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Article body card
        st.markdown(
            """
            <style>
            .article-card {
                background: #ffffff;
                border-radius: 1rem;
                padding: 1.5rem 1.75rem;
                box-shadow: 0 18px 45px rgba(15,23,42,0.18);
                border: 1px solid #e5e7eb;
            }
            .article-card h3 {
                margin-top: 0;
                margin-bottom: 0.85rem;
                font-size: 1.05rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            st.markdown('<div class="article-card">', unsafe_allow_html=True)
            st.markdown("### Summary", unsafe_allow_html=True)
            if summary:
                st.write(summary)
            else:
                st.write("No summary available for this article.")

            if body_text:
                st.markdown("---")
                st.markdown("### Full article (from source)")
                for para in body_text.split("\n\n"):
                    st.write(para)
            else:
                st.markdown("---")
                st.caption(
                    "Full article content could not be extracted. "
                    "Use the link above to read on the original site."
                )

            st.markdown("</div>", unsafe_allow_html=True)