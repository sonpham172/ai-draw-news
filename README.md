# ai-draw-news

Streamlit app that scrapes VNExpress, filters AI & conflict news with Groq LLM, and caches results in Google Sheets.

## Run the app

```bash
cd /path/to/ai-draw-news
source .venv/bin/activate
pip install -r requirements.txt
```

Configure `.streamlit/secrets.toml` with `GROQ_API_KEY` and `[GCP_SERVICE_ACCOUNT]`, then:

```bash
streamlit run app.py
```

## Daily scan (GitHub Actions)

The daily scan runs via **GitHub Actions** at **13:00 (1:00 PM) Vietnam time**. No server or cron needed.

1. In your repo: **Settings → Secrets and variables → Actions**, add:
   - **`GROQ_API_KEY`** – your Groq API key
   - **`GCP_SA_JSON`** – the full contents of your Google service account JSON file (paste as one string)

2. The workflow [.github/workflows/daily-scan.yml](.github/workflows/daily-scan.yml) runs on schedule; you can also run it manually: **Actions → Daily news scan → Run workflow**.