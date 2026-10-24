# DocuLens AI - document intelligence for Streamlit Cloud (Gemini + LangChain)
# Entry point is still pdf-app.py so your existing Streamlit Cloud deployment keeps working.

import logging
import os

import pandas as pd
import streamlit as st

import docparse
import report
import styles
from engine import DEFAULT_CHAT_MODEL, DEFAULT_EMBEDDING_MODEL, Engine, friendly_error

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="DocuLens AI | Document Intelligence", page_icon=":material/neurology:", layout="wide")
st.markdown(styles.CSS, unsafe_allow_html=True)

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "data", "BOI.pdf")
LANGUAGES = {
    "Auto (same as document)": "Auto", "English": "English", "বাংলা (Bengali)": "Bengali",
    "हिन्दी (Hindi)": "Hindi", "العربية (Arabic)": "Arabic", "Español": "Spanish",
    "Français": "French", "Deutsch": "German", "中文": "Chinese", "日本語": "Japanese",
}
MIME = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
GENERIC_QUESTIONS = [
    "Summarize this document in 5 bullet points.",
    "What are the key dates, deadlines and amounts?",
    "What risks or red flags should I know about?",
    "Explain the most important terms in simple words.",
]

# ------------------------------------------------------------------ API key
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("Missing GOOGLE_API_KEY. Add it in your app's Streamlit secrets (Settings > Secrets).")
    st.stop()


@st.cache_resource(show_spinner=False)
def get_engine(key: str, chat_model: str, embedding_model: str) -> Engine:
    return Engine(key, chat_model, embedding_model)


try:
    engine = get_engine(
        API_KEY,
        st.secrets.get("CHAT_MODEL", DEFAULT_CHAT_MODEL),
        st.secrets.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
    )
except Exception as e:
    st.error(friendly_error(e))
    st.stop()

# -------------------------------------------------------------------- state
S = st.session_state
S.setdefault("parsed", {})        # digest -> ParsedDoc
S.setdefault("stats", {})         # digest -> stats dict
S.setdefault("analyses", {})      # (digest, language, depth) -> Analysis
S.setdefault("index", None)
S.setdefault("index_key", None)
S.setdefault("chat", [])
S.setdefault("uploader_key", 0)
S.setdefault("use_sample", False)


def reset_all():
    for k in ("parsed", "stats", "analyses", "chat"):
        S[k] = {} if k != "chat" else []
    S.index, S.index_key, S.use_sample = None, None, False
    S.uploader_key += 1


def load_doc(name: str, data: bytes) -> docparse.ParsedDoc:
    import hashlib
    digest = hashlib.md5(data).hexdigest()
    if digest in S.parsed:
        return S.parsed[digest]
    doc = docparse.parse_document(name, data)
    if doc.needs_ocr and doc.ext in MIME and len(data) < 20 * 1024 * 1024:
        try:
            with st.spinner(f"Reading scanned content in {name} with AI..."):
                docparse.apply_ocr_text(doc, engine.ocr(data, MIME[doc.ext]))
            doc.warnings = [w for w in doc.warnings if "scanned" not in w]
        except Exception as e:
            doc.warnings.append(f"Text recognition failed: {friendly_error(e)}")
    S.parsed[digest] = doc
    S.stats[digest] = docparse.compute_stats(doc)
    return doc


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(
        "<div class='brand'><div class='logo'>Docu<span>Lens</span> AI</div>"
        "<div class='tag'>Upload. Analyze. Ask anything.</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='side-title'>1. Upload documents</div>", unsafe_allow_html=True)
    uploads = st.file_uploader(
        "Documents", type=docparse.SUPPORTED_TYPES, accept_multiple_files=True,
        key=f"uploader_{S.uploader_key}", label_visibility="collapsed",
        help="PDF, Word, PowerPoint, Excel, CSV, text, HTML, JSON and images (up to 50 MB each).",
    )
    st.caption("PDF · Word · PowerPoint · Excel · CSV · TXT · HTML · JSON · Images")

    if os.path.exists(SAMPLE_PATH):
        if not S.use_sample:
            if st.button("Try a sample document", icon=":material/description:", width="stretch"):
                S.use_sample = True
                st.rerun()
        else:
            if st.button("Remove sample", icon=":material/close:", width="stretch"):
                S.use_sample = False
                st.rerun()

    st.markdown("<div class='side-title'>2. Preferences</div>", unsafe_allow_html=True)
    lang_label = st.selectbox("Answer & report language", list(LANGUAGES), index=0)
    LANG = LANGUAGES[lang_label]
    DEPTH = st.radio("Analysis depth", ["Standard", "Detailed"], horizontal=True,
                     help="Detailed produces longer lists and richer explanations.")

# -------------------------------------------------------------- load documents
sources = [(f.name, f.getvalue()) for f in (uploads or [])]
if S.use_sample and os.path.exists(SAMPLE_PATH):
    with open(SAMPLE_PATH, "rb") as fh:
        sources.append(("Sample - BOI.pdf", fh.read()))

docs = [load_doc(n, b) for n, b in sources]
docs = [d for d in docs if d.units or d.warnings]

with st.sidebar:
    if docs:
        st.markdown("<div class='side-title'>Loaded documents</div>", unsafe_allow_html=True)
        for d in docs:
            st.markdown(
                f"<div class='doc-pill'><b title='{styles.esc(d.name)}'>{styles.esc(d.name)}</b>"
                f"<i>{d.ext.upper()} · {docparse.human_size(d.size)}</i></div>",
                unsafe_allow_html=True,
            )
        st.button("Clear everything", icon=":material/delete:", on_click=reset_all, width="stretch")
    st.divider()
    st.caption("Answers are generated by AI from your document. Always verify critical details.")

# ------------------------------------------------------------------- welcome
if not docs:
    st.markdown(
        styles.hero(
            "Understand any document in minutes",
            "Upload a file and get a full AI analysis report, then ask questions and get answers grounded in your document.",
            ["PDF", "Word", "PowerPoint", "Excel & CSV", "Images (OCR)", "Multi-language"],
        ),
        unsafe_allow_html=True,
    )
    feats = [
        ("📑", "Full analysis report", "Executive summary, key points, topics, entities, figures, risks, action items and a glossary."),
        ("💬", "Ask your document", "Chat in plain language. Every answer is grounded in the file and shows its sources."),
        ("📊", "Instant insights", "Word counts, reading time, readability and keyword charts without waiting for AI."),
        ("📥", "Export anywhere", "Download the report as Word, HTML or Markdown, optionally with your Q&A."),
    ]
    cols = st.columns(4)
    for c, (ic, t, p) in zip(cols, feats):
        c.markdown(f"<div class='feature'><div class='ic'>{ic}</div><b>{t}</b><p>{p}</p></div>", unsafe_allow_html=True)
    st.markdown(styles.section("How it works"), unsafe_allow_html=True)
    st.markdown("**1.** Upload one or more files in the sidebar &nbsp;→&nbsp; **2.** Generate the AI analysis &nbsp;→&nbsp; "
                "**3.** Ask questions &nbsp;→&nbsp; **4.** Download your report")
    st.stop()

# -------------------------------------------------------------- build index
usable = [d for d in docs if d.plain_text.strip()]
for d in docs:
    for w in d.warnings:
        st.warning(f"{d.name}: {w}")

index_key = tuple(sorted(d.digest for d in usable))
if usable and S.index_key != index_key:
    bar = st.progress(0.0, text="Indexing your documents for search...")
    try:
        S.index = engine.build_index(usable, progress=lambda f: bar.progress(f, text="Indexing your documents for search..."))
        S.index_key = index_key
        S.chat = []
    except Exception as e:
        S.index, S.index_key = None, None
        st.error(friendly_error(e))
    bar.empty()
elif not usable:
    S.index, S.index_key = None, None

if not usable:
    st.error("No readable text was found in the uploaded file(s).")
    st.stop()

# ---------------------------------------------------------------- header/nav
names = [d.name for d in usable]
current = usable[0]
if len(usable) > 1:
    pick = st.selectbox("Active document", names, help="Used for the Overview, Analysis and Export views.")
    current = usable[names.index(pick)]
stats = S.stats[current.digest]
a_key = (current.digest, LANG, DEPTH)
analysis = S.analyses.get(a_key)

st.markdown(
    styles.hero(
        analysis.title if analysis and analysis.title else current.name,
        analysis.purpose if analysis and analysis.purpose else
        f"{stats['words']:,} words · {stats['units']} {current.unit_name.lower()} · about {stats['read_minutes']} min read",
        [current.ext.upper(), docparse.human_size(current.size), f"{len(usable)} document(s) loaded"],
    ),
    unsafe_allow_html=True,
)

VIEWS = {
    "overview": ":material/dashboard: Overview",
    "analysis": ":material/insights: AI Analysis",
    "ask": ":material/chat: Ask Questions",
    "export": ":material/download: Export Report",
}
view = st.segmented_control("View", list(VIEWS), format_func=VIEWS.get, default="overview",
                            label_visibility="collapsed", key="view") or "overview"


# ------------------------------------------------------------------ renderers
def render_overview():
    items = [
        (f"{stats['units']}", current.unit_name),
        (f"{stats['words']:,}", "Words"),
        (f"{stats['read_minutes']} min", "Reading time"),
        (f"{stats['avg_sentence']}", "Avg. sentence length"),
        (docparse.readability_label(stats["flesch"]), "Readability"),
        (f"{stats['unique_ratio']}%", "Vocabulary variety"),
    ]
    for c, (v, l) in zip(st.columns(6), items):
        c.markdown(styles.stat(v, l), unsafe_allow_html=True)

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        st.markdown(styles.section("Top keywords"), unsafe_allow_html=True)
        if stats["keywords"]:
            kdf = pd.DataFrame(stats["keywords"], columns=["keyword", "mentions"])
            st.bar_chart(kdf, x="keyword", y="mentions", color="#0E9AA7", horizontal=True, sort="-mentions", height=380)
        else:
            st.info("Not enough text to extract keywords.")
    with right:
        st.markdown(styles.section(f"Browse {current.unit_name.lower()}"), unsafe_allow_html=True)
        labels = [l for l, t in current.units if t.strip()]
        if labels:
            sel = st.selectbox("Section", labels, label_visibility="collapsed", key=f"unit_{current.digest}")
            text = dict(current.units)[sel]
            st.text_area("Content", text, height=330,
                         label_visibility="collapsed", key=f"txt_{current.digest}_{sel}")
    if current.tables:
        st.markdown(styles.section("Data preview"), unsafe_allow_html=True)
        for sheet, df in current.tables.items():
            with st.expander(f"{sheet}  ·  {len(df):,} rows × {len(df.columns)} columns", expanded=len(current.tables) == 1):
                st.dataframe(df.head(500), width="stretch")
                num = df.select_dtypes("number")
                if not num.empty:
                    st.caption("Numeric summary")
                    st.dataframe(num.describe().T, width="stretch")
    if not analysis:
        st.info("Open **AI Analysis** to generate the full report: summary, risks, action items and more.", icon=":material/insights:")


def table_df(rows, cols):
    return pd.DataFrame(rows, columns=cols)


def render_analysis(a):
    badges = []
    if a.document_type:
        badges.append(f"<span class='badge b-info'>{styles.esc(a.document_type)}</span>")
    if a.language:
        badges.append(f"<span class='badge b-neu'>{styles.esc(a.language)}</span>")
    badges.append(f"<span class='badge {styles.sentiment_class(a.sentiment)}'>Sentiment: {styles.esc(a.sentiment)}</span>")
    if a.tone:
        badges.append(f"<span class='badge b-neu'>Tone: {styles.esc(a.tone)}</span>")
    paras = "".join(f"<p>{styles.esc(p)}</p>" for p in a.executive_summary.split("\n") if p.strip())
    st.markdown(
        f"<div class='card accent'><h3>Executive summary</h3><div style='margin-bottom:12px'>{' '.join(badges)}</div>{paras}"
        + (f"<p><b>Intended audience:</b> {styles.esc(a.intended_audience)}</p>" if a.intended_audience else "")
        + "</div>", unsafe_allow_html=True)

    m = st.columns(4)
    m[0].markdown(styles.stat(f"{a.clarity_score}/10" if a.clarity_score else "n/a", "Clarity score"), unsafe_allow_html=True)
    m[1].markdown(styles.stat(len(a.key_points), "Key points"), unsafe_allow_html=True)
    m[2].markdown(styles.stat(len(a.risks), "Risks flagged"), unsafe_allow_html=True)
    m[3].markdown(styles.stat(len(a.action_items), "Action items"), unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(styles.section("Key points"), unsafe_allow_html=True)
        rows = "".join(f"<div class='kp'><div class='n'>{i}</div><div>{styles.esc(p)}</div></div>" for i, p in enumerate(a.key_points, 1))
        st.markdown(f"<div class='card'>{rows or 'None found.'}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(styles.section("Main topics"), unsafe_allow_html=True)
        for i in range(0, len(a.topics), 2):
            cols = st.columns(2)
            for col, t in zip(cols, a.topics[i:i + 2]):
                col.markdown(f"<div class='topic'><b>{styles.esc(t.name)}</b><span>{styles.esc(t.description)}</span></div><div style='height:10px'></div>", unsafe_allow_html=True)
        if not a.topics:
            st.caption("No topics identified.")

    if a.key_facts or a.entities:
        t1, t2 = st.columns(2, gap="large")
        with t1:
            st.markdown(styles.section("Key facts & figures"), unsafe_allow_html=True)
            if a.key_facts:
                st.dataframe(table_df([[f.label, f.value, f.context] for f in a.key_facts], ["Item", "Value", "Context"]), hide_index=True, width="stretch")
            else:
                st.caption("None found.")
        with t2:
            st.markdown(styles.section("People, organisations & places"), unsafe_allow_html=True)
            if a.entities:
                st.dataframe(table_df([[e.name, e.type, e.context] for e in a.entities], ["Name", "Type", "Role"]), hide_index=True, width="stretch")
            else:
                st.caption("None found.")

    r1, r2 = st.columns(2, gap="large")
    with r1:
        st.markdown(styles.section("Risks & concerns"), unsafe_allow_html=True)
        order = {"high": 0, "medium": 1, "low": 2}
        for r in sorted(a.risks, key=lambda x: order[styles.severity_class(x.severity)]):
            sc = styles.severity_class(r.severity)
            st.markdown(
                f"<div class='risk {sc}'><span class='badge b-{sc}'>{sc.title()}</span> <b>{styles.esc(r.issue)}</b>"
                f"<div style='color:#475569;font-size:14px;margin-top:5px'>{styles.esc(r.explanation)}</div></div>",
                unsafe_allow_html=True)
        if not a.risks:
            st.success("No significant risks were identified in the document.")
    with r2:
        st.markdown(styles.section("Action items"), unsafe_allow_html=True)
        if a.action_items:
            st.dataframe(table_df([[x.action, x.owner or "-", x.deadline or "-"] for x in a.action_items], ["Action", "Owner", "Deadline"]), hide_index=True, width="stretch")
        else:
            st.caption("No action items found.")

    if a.strengths or a.gaps_or_weaknesses or a.recommendations:
        st.markdown(styles.section("Assessment"), unsafe_allow_html=True)
        cols = st.columns(3, gap="medium")
        for col, title, items in zip(cols, ["Strengths", "Gaps & weaknesses", "Recommendations"],
                                     [a.strengths, a.gaps_or_weaknesses, a.recommendations]):
            li = "".join(f"<li style='margin-bottom:6px'>{styles.esc(x)}</li>" for x in items) or "<li>None</li>"
            col.markdown(f"<div class='card'><h3>{title}</h3><ul style='padding-left:18px;color:#334155;margin:0'>{li}</ul></div>", unsafe_allow_html=True)
    if a.clarity_notes:
        st.caption(f"Clarity notes: {a.clarity_notes}")
    if a.glossary:
        with st.expander(f"Glossary ({len(a.glossary)} terms)"):
            st.dataframe(table_df([[t.term, t.definition] for t in a.glossary], ["Term", "Definition"]), hide_index=True, width="stretch")


def run_analysis():
    try:
        with st.spinner("Reading the whole document and writing your report. This usually takes under a minute..."):
            S.analyses[a_key] = engine.analyze(current, LANG, DEPTH)
    except Exception as e:
        st.error(friendly_error(e))
        return
    st.rerun()


def render_ask():
    scope = None
    if len(usable) > 1:
        choice = st.selectbox("Search in", ["All documents"] + names)
        scope = None if choice == "All documents" else choice
    if S.index is None:
        st.error("The search index could not be built. Please re-upload your document.")
        return

    head = st.columns([5, 1])
    head[0].markdown(styles.section("Ask your document"), unsafe_allow_html=True)
    if S.chat and head[1].button("Clear chat", icon=":material/refresh:", width="stretch"):
        S.chat = []
        st.rerun()

    for m in S.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("sources"):
                with st.expander("Sources"):
                    for i, s in enumerate(m["sources"], 1):
                        st.markdown(f"**Source {i}** · {s['source']} · {s['unit']}")
                        st.caption(s["text"])

    q = st.chat_input("Ask anything about your document...")
    q = q or S.pop("pending_q", None)

    if not S.chat and not q:
        st.markdown("<div class='card'><h3>Not sure where to start?</h3><p style='margin:0'>Pick a suggested question or type your own below.</p></div>", unsafe_allow_html=True)
        suggestions = (analysis.suggested_questions[:4] if analysis and analysis.suggested_questions else GENERIC_QUESTIONS)
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            if cols[i % 2].button(s, key=f"sug_{i}", width="stretch"):
                S.pending_q = s
                st.rerun()

    if q:
        history = [{"role": m["role"], "content": m["content"]} for m in S.chat]
        S.chat.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching the document..."):
                    hits = engine.retrieve(S.index, q, history, scope)
                if not hits:
                    answer, srcs = "I could not find anything relevant in the document for that question.", []
                    st.markdown(answer)
                else:
                    answer = st.write_stream(engine.answer_stream(q, hits, history, LANG))
                    srcs = [{"source": h.metadata["source"], "unit": h.metadata["unit"], "text": h.page_content[:350] + "..."} for h in hits[:5]]
                    with st.expander("Sources"):
                        for i, s in enumerate(srcs, 1):
                            st.markdown(f"**Source {i}** · {s['source']} · {s['unit']}")
                            st.caption(s["text"])
                S.chat.append({"role": "assistant", "content": answer, "sources": srcs})
            except Exception as e:
                S.chat.pop()
                st.error(friendly_error(e))


def render_export():
    st.markdown(styles.section("Download your report"), unsafe_allow_html=True)
    if not analysis:
        st.info("You have not generated the AI analysis yet. The report will only contain document statistics. "
                "Generate the analysis first for the full report.", icon=":material/info:")
        if st.button("Generate AI analysis now", type="primary", icon=":material/auto_awesome:"):
            run_analysis()
    include_chat = st.toggle("Include my questions and answers", value=bool(S.chat), disabled=not S.chat)
    chat = [{"role": m["role"], "content": m["content"]} for m in S.chat] if include_chat else None
    blocks = report.build_blocks(current, stats, analysis, chat)
    base = os.path.splitext(current.name)[0].replace(" ", "_")[:60] + "_report"
    c = st.columns(3)
    c[0].download_button("Word (.docx)", report.to_docx(blocks), f"{base}.docx",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         type="primary", icon=":material/description:", width="stretch")
    c[1].download_button("Web page (.html)", report.to_html(blocks), f"{base}.html", "text/html",
                         icon=":material/language:", width="stretch")
    c[2].download_button("Markdown (.md)", report.to_markdown(blocks), f"{base}.md", "text/markdown",
                         icon=":material/code:", width="stretch")
    with st.expander("Preview (Markdown)"):
        st.markdown(report.to_markdown(blocks))


# ---------------------------------------------------------------------- main
if view == "overview":
    render_overview()
elif view == "analysis":
    if analysis:
        top = st.columns([4, 1])
        top[0].caption(f"Language: {lang_label}  ·  Depth: {DEPTH}")
        if top[1].button("Regenerate", icon=":material/refresh:", width="stretch"):
            S.analyses.pop(a_key, None)
            run_analysis()
        render_analysis(analysis)
    else:
        st.markdown(
            "<div class='card accent'><h3>Generate the full analysis</h3><p>The AI reads your entire document and builds a "
            "structured report: executive summary, key points, topics, people and organisations, figures, risks, action items, "
            "strengths, gaps, recommendations and a glossary.</p></div>", unsafe_allow_html=True)
        if st.button("Generate full analysis", type="primary", icon=":material/auto_awesome:"):
            run_analysis()
elif view == "ask":
    render_ask()
else:
    render_export()
