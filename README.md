# DocuLens AI

Upload almost any document, get a full AI analysis report, and ask questions about it.

**Formats:** PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx/.xls), CSV/TSV, TXT, Markdown, HTML, JSON, and images (PNG/JPG/WEBP, read with AI OCR). Scanned PDFs are also read with AI OCR.

## Features
- **Overview**: word count, reading time, readability, keyword chart, page/slide browser, data tables for spreadsheets
- **AI Analysis**: executive summary, key points, topics, people/organisations/places, key figures, risks (High/Medium/Low), action items, strengths, gaps, recommendations, glossary, clarity score, sentiment
- **Ask Questions**: chat with your document, follow-up questions, source citations, suggested questions
- **Export**: download the report as Word, HTML or Markdown (optionally with your Q&A)
- Multi-document upload, 10 answer languages (including Bengali), Standard/Detailed depth

## Deploy on Streamlit Community Cloud
1. Push this folder to GitHub (main file: `pdf-app.py`).
2. In the app's **Settings > Secrets** add:
   ```toml
   GOOGLE_API_KEY = "your-key-here"
   # Optional: override models if Google renames them
   # CHAT_MODEL = "gemini-3.5-flash"
   # EMBEDDING_MODEL = "models/gemini-embedding-2"
   ```
3. Reboot the app. Never commit your key to GitHub.

## Run locally
```bash
pip install -r requirements.txt
mkdir -p .streamlit && echo 'GOOGLE_API_KEY="your-key"' > .streamlit/secrets.toml
streamlit run pdf-app.py
```

## Files
| File | Purpose |
|---|---|
| `pdf-app.py` | Streamlit interface (entry point) |
| `docparse.py` | Reads every file type + statistics |
| `engine.py` | Gemini: OCR, search index, analysis, Q&A |
| `report.py` | Word / HTML / Markdown report builders |
| `styles.py`, `.streamlit/config.toml` | Design and theme |
