"""Visual theme for DocuLens (navy + teal, card based)."""
import html

NAVY, TEAL = "#0B2545", "#0E9AA7"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 4rem; padding-bottom: 5rem; max-width: 1200px; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #E2E8F0; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
.brand {{ background: linear-gradient(135deg, {NAVY} 0%, #134074 60%, {TEAL} 100%);
  border-radius: 16px; padding: 18px 18px 16px; color: #fff; margin-bottom: 18px;
  box-shadow: 0 8px 20px rgba(11,37,69,.22); }}
.brand .logo {{ font-size: 22px; font-weight: 800; letter-spacing: -.3px; }}
.brand .logo span {{ color: #7EE0E8; }}
.brand .tag {{ font-size: 12px; opacity: .85; margin-top: 2px; }}
.side-title {{ font-size: 11px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  color: #64748B; margin: 18px 0 6px; }}
.doc-pill {{ display:flex; justify-content:space-between; align-items:center; gap:8px; background:#F1F5F9;
  border:1px solid #E2E8F0; border-radius:10px; padding:8px 10px; margin-bottom:6px; font-size:13px; }}
.doc-pill b {{ color:{NAVY}; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:150px; display:inline-block; }}
.doc-pill i {{ color:#64748B; font-style:normal; font-size:11px; }}

/* ---------- hero ---------- */
.hero {{ background: linear-gradient(120deg, {NAVY} 0%, #134074 55%, {TEAL} 130%);
  border-radius: 20px; padding: 30px 34px; color:#fff; margin-bottom: 22px;
  box-shadow: 0 12px 30px rgba(11,37,69,.18); position: relative; overflow: hidden; }}
.hero:after {{ content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px;
  background: radial-gradient(circle, rgba(126,224,232,.35), transparent 65%); }}
.hero h1 {{ margin:0 0 6px; font-size: 30px; font-weight: 800; letter-spacing: -.5px; color:#fff; }}
.hero p {{ margin:0; font-size: 15px; opacity:.9; max-width: 720px; }}
.hero .chips {{ margin-top: 14px; display:flex; gap:8px; flex-wrap:wrap; }}
.chip {{ background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.25);
  padding:4px 11px; border-radius: 999px; font-size: 12px; font-weight:500; }}

/* ---------- cards ---------- */
.card {{ background:#fff; border:1px solid #E2E8F0; border-radius:16px; padding:20px 22px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04), 0 6px 16px rgba(15,23,42,.04); margin-bottom: 16px; }}
.card h3 {{ margin:0 0 10px; font-size:16px; font-weight:700; color:{NAVY}; }}
.card p {{ margin:0 0 10px; line-height:1.7; color:#334155; }}
.card.accent {{ border-left: 5px solid {TEAL}; }}
.stat {{ min-height: 84px; background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:14px 16px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04); }}
.stat .v {{ font-size: 26px; font-weight:800; color:{NAVY}; line-height:1.1; }}
.stat .l {{ font-size: 11px; font-weight:600; text-transform:uppercase; letter-spacing:.07em; color:#64748B; margin-top:4px; }}
.section-title {{ font-size: 19px; font-weight: 800; color:{NAVY}; margin: 26px 0 12px; letter-spacing:-.2px; }}
.section-title:before {{ content:""; display:inline-block; width:5px; height:18px; background:{TEAL};
  border-radius:3px; margin-right:10px; vertical-align:-3px; }}

/* ---------- badges / lists ---------- */
.badge {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; }}
.b-high {{ background:#FEE2E2; color:#B91C1C; }} .b-medium {{ background:#FEF3C7; color:#B45309; }}
.b-low {{ background:#DCFCE7; color:#15803D; }} .b-info {{ background:#E0F2FE; color:#0369A1; }}
.b-pos {{ background:#DCFCE7; color:#15803D; }} .b-neg {{ background:#FEE2E2; color:#B91C1C; }}
.b-neu {{ background:#E2E8F0; color:#334155; }} .b-mix {{ background:#FEF3C7; color:#B45309; }}
.risk {{ border:1px solid #E2E8F0; border-left-width:5px; border-radius:12px; padding:12px 16px; margin-bottom:10px; background:#fff; }}
.risk.high {{ border-left-color:#DC2626; }} .risk.medium {{ border-left-color:#F59E0B; }} .risk.low {{ border-left-color:#16A34A; }}
.risk b {{ color:{NAVY}; }}
.kp {{ display:flex; gap:12px; align-items:flex-start; padding:9px 0; border-bottom:1px dashed #E2E8F0; color:#334155; line-height:1.55; }}
.kp:last-child {{ border-bottom:none; }}
.kp .n {{ flex:0 0 26px; height:26px; border-radius:8px; background:{TEAL}; color:#fff; font-weight:700;
  font-size:12px; display:flex; align-items:center; justify-content:center; }}
.topic {{ background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:12px 14px; height:100%; }}
.topic b {{ color:{NAVY}; display:block; margin-bottom:3px; }} .topic span {{ color:#475569; font-size:14px; }}

/* ---------- empty state ---------- */
.feature {{ background:#fff; border:1px solid #E2E8F0; border-radius:16px; padding:20px; height:100%;
  box-shadow: 0 6px 16px rgba(15,23,42,.04); }}
.feature .ic {{ width:42px; height:42px; border-radius:12px; background:linear-gradient(135deg,{NAVY},{TEAL});
  color:#fff; display:flex; align-items:center; justify-content:center; font-size:20px; margin-bottom:12px; }}
.feature b {{ color:{NAVY}; font-size:15px; }} .feature p {{ color:#64748B; font-size:13.5px; margin:6px 0 0; line-height:1.55; }}

/* ---------- widgets ---------- */
.stButton > button, .stDownloadButton > button {{ border-radius: 10px; font-weight: 600; border:1px solid #CBD5E1; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {NAVY}, #134074); border:none; color:#fff; }}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.15); }}
[data-testid="stFileUploaderDropzone"] {{ border:2px dashed #94A3B8; border-radius:14px; background:#F8FAFC; }}
[data-testid="stChatMessage"] {{ background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:12px 16px; margin-bottom:10px; }}
[data-testid="stDataFrame"] {{ border-radius:12px; overflow:hidden; }}
details {{ border-radius:12px !important; }}
</style>
"""


def esc(s) -> str:
    return html.escape(str(s))


def hero(title: str, subtitle: str, chips=()):
    chip_html = "".join(f"<span class='chip'>{esc(c)}</span>" for c in chips)
    return f"<div class='hero'><h1>{esc(title)}</h1><p>{esc(subtitle)}</p><div class='chips'>{chip_html}</div></div>"


def stat(value, label):
    return f"<div class='stat'><div class='v'>{esc(value)}</div><div class='l'>{esc(label)}</div></div>"


def section(title: str):
    return f"<div class='section-title'>{esc(title)}</div>"


def severity_class(s: str) -> str:
    s = (s or "").lower()
    return "high" if "high" in s else "low" if "low" in s else "medium"


def sentiment_class(s: str) -> str:
    s = (s or "").lower()
    return "b-pos" if "pos" in s else "b-neg" if "neg" in s else "b-mix" if "mix" in s else "b-neu"
