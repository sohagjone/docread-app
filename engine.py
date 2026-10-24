"""AI engine for DocuLens: OCR, vector search, full analysis, and Q&A."""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Model names change often; check ai.google.dev if one stops working.
# They can be overridden from Streamlit secrets (CHAT_MODEL / EMBEDDING_MODEL).
DEFAULT_CHAT_MODEL = "gemini-3.5-flash"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-2"

MAX_DIRECT_CHARS = 300_000   # analyse the whole text in one call up to this size
MAX_SEGMENTS = 8             # longer documents are condensed in at most this many parts


# ------------------------------------------------------------ output schema
class Topic(BaseModel):
    name: str = ""
    description: str = ""


class Entity(BaseModel):
    name: str = ""
    type: str = Field(default="Other", description="Person, Organization, Location, Date, Amount, Product, Law/Regulation, or Other")
    context: str = Field(default="", description="One short phrase on its role in the document")


class Risk(BaseModel):
    issue: str = ""
    severity: str = Field(default="Medium", description="Low, Medium, or High")
    explanation: str = ""


class ActionItem(BaseModel):
    action: str = ""
    owner: str = ""
    deadline: str = ""


class KeyFact(BaseModel):
    label: str = ""
    value: str = ""
    context: str = ""


class Term(BaseModel):
    term: str = ""
    definition: str = ""


class Analysis(BaseModel):
    title: str = Field(default="", description="Document title, or a short descriptive title")
    document_type: str = Field(default="", description="e.g. contract, report, invoice, research paper, form, dataset")
    language: str = ""
    purpose: str = Field(default="", description="One or two sentences on what the document is for")
    intended_audience: str = ""
    executive_summary: str = Field(default="", description="3 to 5 plain-text paragraphs, no markdown")
    key_points: List[str] = Field(default_factory=list)
    topics: List[Topic] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    key_facts: List[KeyFact] = Field(default_factory=list, description="Important numbers, dates, amounts, deadlines")
    tone: str = ""
    sentiment: str = Field(default="Neutral", description="Positive, Neutral, Negative, or Mixed")
    sentiment_explanation: str = ""
    risks: List[Risk] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    gaps_or_weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    glossary: List[Term] = Field(default_factory=list)
    clarity_score: int = Field(default=0, description="Clarity and organisation from 1 to 10")
    clarity_notes: str = ""
    suggested_questions: List[str] = Field(default_factory=list, description="6 useful questions a reader could ask")


# ---------------------------------------------------------------- helpers
def text_of(content) -> str:
    """Gemini may return a string or a list of content blocks."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                out.append(part.get("text", ""))
        return "".join(out)
    return str(content)


def friendly_error(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "429" in msg or "quota" in low or "rate" in low and "limit" in low:
        return "The AI service is rate-limited right now. Please wait a minute and try again."
    if "api key" in low or "api_key" in low or "permission" in low or "403" in msg or "401" in msg:
        return "The Google API key was rejected. Check GOOGLE_API_KEY in your Streamlit secrets."
    if "404" in msg or "not found" in low and "model" in low:
        return "The configured Gemini model name was not found. Update CHAT_MODEL in secrets or engine.py."
    return f"AI request failed: {msg[:300]}"


def lang_instruction(language: str) -> str:
    if not language or language.lower().startswith("auto"):
        return "Write in the same language as the document."
    return f"Write all output in {language}."


def _retry(fn, tries=3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


# ------------------------------------------------------------------- engine
class Engine:
    def __init__(self, api_key: str, chat_model: str = DEFAULT_CHAT_MODEL,
                 embedding_model: str = DEFAULT_EMBEDDING_MODEL):
        self.llm = ChatGoogleGenerativeAI(model=chat_model, google_api_key=api_key, temperature=0.2)
        self.embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model, google_api_key=api_key)

    # ---- OCR for scanned PDFs / images
    def ocr(self, data: bytes, mime: str) -> str:
        b64 = base64.b64encode(data).decode()
        if mime == "application/pdf":
            block = {"type": "media", "mime_type": mime, "data": b64}
        else:
            block = {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        msg = HumanMessage(content=[
            {"type": "text", "text": "Transcribe ALL text in this document exactly as written, in reading order. "
                                     "Keep tables as rows separated by ' | '. Output only the transcription."},
            block,
        ])
        return text_of(_retry(lambda: self.llm.invoke([msg])).content)

    # ---- vector index
    def build_index(self, docs: list, progress=None) -> InMemoryVectorStore:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
        chunks: List[Document] = []
        for d in docs:
            for label, text in d.units:
                if not text.strip():
                    continue
                for piece in splitter.split_text(text):
                    chunks.append(Document(page_content=piece, metadata={"source": d.name, "unit": label}))
        store = InMemoryVectorStore(self.embeddings)
        batch = 32
        for i in range(0, len(chunks), batch):
            part = chunks[i:i + batch]
            _retry(lambda: store.add_documents(part))
            if progress:
                progress(min(1.0, (i + batch) / max(1, len(chunks))))
        return store

    # ---- full analysis
    def _condense(self, text: str, language: str) -> str:
        """Map step for very long documents: summarise segments, keep facts."""
        seg = -(-len(text) // MAX_SEGMENTS)
        parts = [text[i:i + seg] for i in range(0, len(text), seg)]
        summaries = []
        for n, p in enumerate(parts, 1):
            prompt = (
                f"This is part {n} of {len(parts)} of a long document. Write a dense, factual summary that keeps every "
                "important name, number, date, obligation, risk and conclusion. Use plain text. "
                f"{lang_instruction(language)}\n\n{p}"
            )
            summaries.append(f"--- Part {n} ---\n" + text_of(_retry(lambda: self.llm.invoke(prompt)).content))
        return "\n\n".join(summaries)

    def analyze(self, doc, language: str = "Auto", depth: str = "Standard") -> Analysis:
        text = doc.full_text
        note = ""
        if len(text) > MAX_DIRECT_CHARS:
            text = self._condense(text, language)
            note = "NOTE: the document was very long, so the text below is a condensed version of it.\n"
        size = "6-8 items per list" if depth == "Standard" else "10-15 items per list, with richer detail"
        prompt = f"""You are a senior document analyst. Analyse the document below and fill every field of the schema.
Rules:
- Use ONLY information found in the document. If something is not present, leave that list empty rather than guessing.
- Plain text only. No markdown symbols such as ** or #.
- Depth: {size}. executive_summary must be 3-5 paragraphs.
- risks: legal, financial, compliance, operational or ambiguity risks; set severity honestly.
- suggested_questions: exactly 6 specific questions a reader would find useful.
- {lang_instruction(language)} (keep proper names and quoted terms as written).
{note}
File name: {doc.name}

DOCUMENT:
{text}"""
        try:
            structured = self.llm.with_structured_output(Analysis)
            result = _retry(lambda: structured.invoke(prompt), tries=2)
            if isinstance(result, Analysis):
                return result
            if isinstance(result, dict):
                return Analysis.model_validate(result)
        except Exception as e:
            log.warning("Structured output failed (%s); falling back to JSON mode.", e)
        schema = json.dumps(Analysis.model_json_schema())
        raw = text_of(_retry(lambda: self.llm.invoke(
            prompt + f"\n\nReturn ONLY one valid JSON object that follows this JSON schema:\n{schema}"
        )).content)
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if not m:
            raise ValueError("The AI did not return a readable analysis. Please try again.")
        return Analysis.model_validate(json.loads(m.group(0)))

    # ---- question answering
    def _standalone(self, question: str, history: list) -> str:
        if not history:
            return question
        convo = "\n".join(f"{m['role'].title()}: {m['content'][:600]}" for m in history[-6:])
        prompt = (
            "Rewrite the final user question as a standalone search query, using the conversation for context. "
            "Output only the rewritten question.\n\n"
            f"Conversation:\n{convo}\n\nFinal question: {question}"
        )
        try:
            out = text_of(self.llm.invoke(prompt).content).strip()
            return out or question
        except Exception:
            return question

    def retrieve(self, store, question: str, history: list, scope: Optional[str], k: int = 8):
        q = self._standalone(question, history)
        flt = (lambda d: d.metadata.get("source") == scope) if scope else None
        return store.similarity_search(q, k=k, filter=flt) if flt else store.similarity_search(q, k=k)

    def answer_stream(self, question: str, docs_found: list, history: list, language: str):
        context = "\n\n".join(
            f"[Source {i}: {d.metadata['source']}, {d.metadata['unit']}]\n{d.page_content}"
            for i, d in enumerate(docs_found, 1)
        )
        convo = "\n".join(f"{m['role'].title()}: {m['content'][:800]}" for m in history[-6:])
        prompt = f"""You are an expert assistant answering questions about the user's uploaded document(s).
Rules:
- Answer ONLY from the context below. If the answer is not there, say you could not find it in the document and suggest what to check.
- Be clear and well organised. Use short paragraphs or bullet points, and **bold** key terms.
- Cite where facts came from like (Source 2) using the source numbers given.
- {lang_instruction(language)}

Earlier conversation:
{convo or '(none)'}

Context:
{context}

Question: {question}"""
        for chunk in self.llm.stream(prompt):
            t = text_of(chunk.content)
            if t:
                yield t
