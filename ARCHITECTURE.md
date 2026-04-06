# AI Draw News - System Architecture

## System Overview Diagram

```mermaid
flowchart TB
    subgraph User["👤 User"]
        U[User interacts with Streamlit UI]
    end

    subgraph App["📱 Streamlit App (app.py)"]
        UI[Streamlit Interface]
        AUTH[Authentication Check]
        CAT_MGT[Category Management]
        DISPLAY[News Display]
    end

    subgraph Scan["🔄 Scan Pipeline (scan.py)"]
        SCRAPE[Web Scraping]
        FILTER[Groq AI Filtering]
        SAVE[Save to Hugging Face Hub]
    end

    subgraph Sources["📰 News Sources"]
        VNE[VNExpress]
        TT[Tuoi Tre]
        CF[CafeF]
    end

    subgraph External["🌐 External Services"]
        GROQ[Groq API<br/>llama-3.1-8b-instant]
        HF[Hugging Face Hub]
    end

    U --> UI
    UI --> AUTH
    UI --> CAT_MGT
    UI --> DISPLAY
    
    CAT_MGT -->|Save Categories| SAVE
    DISPLAY -->|Trigger Scan| SCRAPE
    
    SCRAPE -->|Scrape| VNE
    SCRAPE -->|Scrape| TT
    SCRAPE -->|Scrape| CF
    
    SCRAPE -->|Raw News| FILTER
    
    FILTER -->|Send Prompt| GROQ
    FILTER -->|Filtered Results| SAVE
    
    SAVE -->|Store Articles| HF
    SAVE -->|Load Cached| HF
    
    HF -->|Return Data| DISPLAY
```

## Detailed Component Flow

### 1. Web Scraping Flow

```mermaid
flowchart LR
    START[Start Scraping] --> VNE_URL[VNExpress URLs]
    START --> TT_URL[Tuoi Tre URLs]
    START --> CF_URL[CafeF URLs]
    
    VNE_URL -->|HTTP Request| VNE_PARSE[Parse HTML]
    TT_URL -->|HTTP Request| TT_PARSE[Parse HTML]
    CF_URL -->|HTTP Request| CF_PARSE[Parse HTML]
    
    VNE_PARSE -->|Extract| VNE_DATA[Title, Link, Image]
    TT_PARSE -->|Extract| TT_DATA[Title, Link, Image]
    CF_PARSE -->|Extract| CF_DATA[Title, Link, Image]
    
    VNE_DATA --> MERGE[Merge All Sources]
    TT_DATA --> MERGE
    CF_DATA --> MERGE
    
    MERGE --> OUTPUT[Raw News List]
```

### 2. AI Filtering Flow (Groq)

```mermaid
flowchart TB
    START[Receive News + Captions] --> LIMIT[Limit to 10 Articles]
    LIMIT --> BUILD[Build Prompt]
    BUILD -->|Include Categories| PROMPT[Create LLM Prompt]
    PROMPT --> SEND[Send to Groq API]
    SEND -->|llama-3.1-8b-instant| RESPONSE[Get JSON Response]
    RESPONSE --> PARSE[Parse JSON]
    PARSE -->|Valid JSON| OUTPUT[Filtered Articles]
    PARSE -->|Invalid JSON| FALLBACK[Return Empty List]
```

### 3. Hugging Face Hub Integration Flow

```mermaid
flowchart TB
    START[HF Hub Operation] --> AUTH{Operation Type?}
    
    AUTH -->|Read Config| READ_CFG[Read categories.txt from HF]
    AUTH -->|Save Config| WRITE_CFG[Write categories.txt to HF]
    AUTH -->|Read Articles| READ_ART[Read articles.json from HF]
    AUTH -->|Save Articles| WRITE_ART[Write articles.json to HF]
    
    READ_CFG --> CFG_DATA[Return Categories]
    WRITE_CFG --> CFG_DONE[Config Saved]
    READ_ART --> ART_DATA[Return Article List]
    WRITE_ART --> ART_DONE[Articles Saved]
```

## Complete Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant App as Streamlit App
    participant Scan as Scan Pipeline
    participant VNE as VNExpress
    participant TT as Tuoi Tre
    participant CF as CafeF
    participant Groq as Groq API
    participant HF as Hugging Face Hub

    U->>App: Open App / Click Scan
    App->>HF: Load Categories
    HF-->>App: Return Categories
    
    App->>Scan: Run Scan with Categories
    Scan->>VNE: Scrape Articles
    Scan->>TT: Scrape Articles
    Scan->>CF: Scrape Articles
    VNE-->>Scan: Raw News Data
    TT-->>Scan: Raw News Data
    CF-->>Scan: Raw News Data
    
    Scan->>Groq: Send News + Categories
    Groq-->>Scan: Filtered JSON Results
    
    Scan->>HF: Save Articles
    HF-->>Scan: Confirmation
    
    Scan-->>App: Return Filtered Articles
    App->>U: Display News List
```

## Technology Stack

```mermaid
mindmap
  root((AI Draw News))
    Frontend
      Streamlit
      Python
    AI/ML
      Groq API
        llama-3.1-8b-instant
    Data Sources
      VNExpress
      Tuoi Tre
      CafeF
    Storage
      Hugging Face Hub
    Libraries
      BeautifulSoup4
      Requests
      huggingface_hub
      pandas
```

## File Structure

```
ai-draw-news/
├── app.py                 # Streamlit UI application
├── scan.py                # Core scanning pipeline
├── run_scan.py           # CLI entry point
├── requirements.txt       # Python dependencies
├── README.md             # Documentation
├── .streamlit/
│   └── secrets.toml      # API keys & config
└── ARCHITECTURE.md       # This file
```

## API Integration Points

| Service | Purpose | Free Tier | Model Used |
|---------|---------|-----------|------------|
| Groq | Text analysis & filtering | 1000 req/day | llama-3.1-8b-instant |
| Hugging Face Hub | Data storage | Free for public/private repos | N/A |

## Key Features

1. **Multi-source Scraping** - Aggregates news from VNExpress, Tuoi Tre, and CafeF
2. **AI-powered Filtering** - Uses Groq LLM to identify relevant articles
3. **Persistent Storage** - Hugging Face Hub for articles and configuration
4. **Interactive UI** - Streamlit for easy user interaction