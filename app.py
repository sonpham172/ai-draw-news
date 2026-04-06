import requests
import streamlit as st
from bs4 import BeautifulSoup

from scan import load_cached_articles, load_config_from_hf, run_scan


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


# UI Layout
st.set_page_config(page_title="AI & War News Scout", page_icon="🤖")

# Fix font so Vietnamese and other scripts render correctly
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      html, body {
        font-family: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
      }
      .stMarkdown, .stMarkdown p, .stText, .stCaption {
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

# HF Secrets
hf_token = st.secrets.get("HF_TOKEN")
hf_repo_id = st.secrets.get("HF_REPO_ID", "sonpham172/news-data")

# On first load, try to populate from HF cache
if not st.session_state.articles:
    if hf_token:
        cached = load_cached_articles(hf_token, hf_repo_id)
        cached_cat = load_config_from_hf(hf_token, hf_repo_id)
        st.session_state.categories_str = cached_cat
        if cached:
            st.session_state.articles = cached

cat_input = st.text_input(
    "Categories (e.g., sport, bank, AI)",
    value=st.session_state.get("categories_str", ""),
    help="Leave empty for default (Artificial Intelligence (AI) or Iran/US conflict)",
)
st.session_state.categories_str = cat_input

if st.button("Scan Today's News"):
    status_container = st.empty()
    with st.spinner("Scraping news & calling LLM..."):
        status_container.info("Step 1: Scraping news sites...")
        articles = run_scan(
            st.secrets["GROQ_API_KEY"],
            hf_token,
            hf_repo_id,
            categories_str=st.session_state.get("categories_str", "")
        )
        st.session_state.articles = articles

    if not articles:
        st.warning("Scan complete, but no articles matched your categories among the top 10 checked.")
    else:
        st.success(f"Successfully found {len(articles)} matching articles and saved to Hugging Face.")
    
    st.session_state.view = "list"
    st.session_state.selected_index = None
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