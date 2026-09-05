
import json
import os
from datetime import datetime
from pathlib import Path
import urllib.error
import urllib.request
import urllib.parse
import subprocess
import socket
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import streamlit.components.v1 as components
import streamlit as st
from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()



# ============================================================
# PAGE CONFIG + POLISHED UI
# ============================================================
st.set_page_config(
    page_title="Abuse-Ring Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ============================================================
   ABUSE-RING SENTINEL — LIGHT BLUE / HIGH CONTRAST THEME
   Distinct navy sidebar + soft blue main workspace.
   ============================================================ */

.stApp {
    background: linear-gradient(180deg, #e5eef5 0%, #f2f7fb 52%, #e9f2f8 100%) !important;
    color: #15263d !important;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #e5eef5 0%, #f2f7fb 52%, #e9f2f8 100%) !important;
}

[data-testid="stHeader"] {
    background: rgba(229,238,245,.97) !important;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.25rem;
    padding-bottom: 2.5rem;
}

/* ---------- Main text ---------- */
.stApp p,
.stApp li,
.stApp label,
.stApp [data-testid="stMarkdownContainer"] p {
    color: #20344d;
}

h1, h2, h3, h4, h5 {
    color: #14243a !important;
}

/* ============================================================
   SIDEBAR — DARKER THAN MAIN CONTENT
   ============================================================ */

section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 20% 5%, rgba(78,116,220,.22), transparent 28%),
        linear-gradient(180deg, #172b4b 0%, #1b3155 52%, #202957 100%) !important;
    border-right: 1px solid #304b70;
    box-shadow: 7px 0 28px rgba(25,50,80,.20);
}

section[data-testid="stSidebar"] > div {
    background: transparent !important;
    padding-top: 1.1rem;
}

section[data-testid="stSidebar"] * {
    color: #edf5ff;
}

.sentinel-brand {
    padding: .8rem .75rem 1rem;
    margin-bottom: .45rem;
    border-radius: 15px;
    background: linear-gradient(135deg, #263f70, #303b78) !important;
    border: 1px solid #5876a8;
    box-shadow: 0 8px 24px rgba(0,0,0,.22);
}

.brand-title {
    color: #ffffff !important;
    font-size: 1.38rem;
    font-weight: 850;
}

.brand-sub {
    color: #b9cce5 !important;
    font-size: .78rem;
}

.nav-caption {
    color: #a8c0df !important;
    font-size: .68rem;
    text-transform: uppercase;
    letter-spacing: .11em;
    font-weight: 850;
    margin: .75rem 0 .45rem .25rem;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: rgba(255,255,255,.055) !important;
    border: 1px solid transparent;
    border-radius: 12px;
    padding: .62rem .72rem;
    margin-bottom: .18rem;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    color: #dbe8f7 !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(96,142,231,.22) !important;
    border-color: #5d7eae;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(100deg, #3474e8, #5751df) !important;
    border-color: #9bb9f5;
    box-shadow: inset 3px 0 0 #e3edff, 0 7px 18px rgba(49,95,232,.28);
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
    color: #ffffff !important;
    font-weight: 800;
}

/* ============================================================
   HERO / SECTION BANNERS
   ============================================================ */

.hero {
    background: linear-gradient(135deg, #f6faff 0%, #edf5fa 100%) !important;
    border: 1px solid #aec7df;
    border-radius: 20px;
    padding: 1.25rem 1.35rem;
    box-shadow: 0 8px 24px rgba(42,62,91,.10);
    margin-bottom: 1.15rem;
}

.hero-title {
    color: #14243a !important;
    font-size: 2rem;
    font-weight: 850;
    letter-spacing: -.04em;
}

.hero-sub {
    color: #4c627a !important;
    font-size: .96rem;
}

/* Existing custom section banners */
div[style*="border-radius:18px"] {
    color: #172b43 !important;
}

div[style*="border-radius:18px"] div {
    color: #172b43 !important;
}

/* ============================================================
   METRICS
   ============================================================ */

[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #b9cede;
    border-radius: 15px;
    padding: .8rem .9rem;
    box-shadow: 0 6px 18px rgba(42,62,91,.09);
}

[data-testid="stMetricLabel"] {
    color: #536b84 !important;
}

[data-testid="stMetricValue"] {
    color: #14243a !important;
}

[data-testid="stMetricDelta"] {
    color: #52677e !important;
}

/* ============================================================
   INPUTS
   ============================================================ */

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stTextInput input,
.stNumberInput input {
    background: #ffffff !important;
    color: #172b43 !important;
    border: 1px solid #aebfd1 !important;
    border-radius: 10px !important;
}

div[data-baseweb="select"] *,
div[data-baseweb="input"] *,
.stTextInput input::placeholder,
.stNumberInput input::placeholder {
    color: #334b64 !important;
}

.stTextInput label,
.stNumberInput label,
.stSelectbox label {
    color: #20344d !important;
    font-weight: 650;
}

div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="input"] > div:focus-within {
    border-color: #4c78df !important;
    box-shadow: 0 0 0 1px #4c78df !important;
}

div[role="listbox"] {
    background: #ffffff !important;
}

div[role="option"] {
    color: #172b43 !important;
}

/* ============================================================
   BUTTONS
   ============================================================ */

.stButton > button {
    color: #ffffff !important;
    background: linear-gradient(135deg, #3474e8, #5751df) !important;
    border: 1px solid #5576df !important;
    border-radius: 10px !important;
    font-weight: 750 !important;
    box-shadow: 0 6px 16px rgba(49,95,232,.20);
}

.stButton > button p,
.stButton > button span {
    color: #ffffff !important;
}

/* ============================================================
   ALL STREAMLIT ALERTS — LIGHT + READABLE
   Covers st.info / st.success / st.warning / st.error
   and prevents the dim black-on-dark problem.
   ============================================================ */

[data-testid="stAlert"],
.stAlert,
div[role="alert"],
[data-baseweb="notification"] {
    border-radius: 12px !important;
    box-shadow: 0 4px 14px rgba(42,62,91,.07) !important;
    opacity: 1 !important;
}

[data-testid="stAlert"] *,
.stAlert *,
div[role="alert"] *,
[data-baseweb="notification"] * {
    opacity: 1 !important;
}

/* INFO — AI explanation + neutral messages */
[data-testid="stAlert"]:has([data-testid="stNotificationIcon-info"]),
.stAlert:has([data-testid="stNotificationIcon-info"]),
div[role="alert"]:has([data-testid="stNotificationIcon-info"]) {
    background: #e5f2fb !important;
    border: 1px solid #a9c8ed !important;
}

[data-testid="stAlert"]:has([data-testid="stNotificationIcon-info"]) *,
.stAlert:has([data-testid="stNotificationIcon-info"]) *,
div[role="alert"]:has([data-testid="stNotificationIcon-info"]) * {
    color: #122842 !important;
}

/* SUCCESS — release / PASS */
[data-testid="stAlert"]:has([data-testid="stNotificationIcon-success"]),
.stAlert:has([data-testid="stNotificationIcon-success"]),
div[role="alert"]:has([data-testid="stNotificationIcon-success"]) {
    background: #e3f5ea !important;
    border: 1px solid #9ed8b8 !important;
}

[data-testid="stAlert"]:has([data-testid="stNotificationIcon-success"]) *,
.stAlert:has([data-testid="stNotificationIcon-success"]) *,
div[role="alert"]:has([data-testid="stNotificationIcon-success"]) * {
    color: #123a28 !important;
}

/* WARNING — verify / hold */
[data-testid="stAlert"]:has([data-testid="stNotificationIcon-warning"]),
.stAlert:has([data-testid="stNotificationIcon-warning"]),
div[role="alert"]:has([data-testid="stNotificationIcon-warning"]) {
    background: #fff4c9 !important;
    border: 1px solid #e3c968 !important;
}

[data-testid="stAlert"]:has([data-testid="stNotificationIcon-warning"]) *,
.stAlert:has([data-testid="stNotificationIcon-warning"]) *,
div[role="alert"]:has([data-testid="stNotificationIcon-warning"]) * {
    color: #3c300d !important;
}

/* ERROR — block / fail */
[data-testid="stAlert"]:has([data-testid="stNotificationIcon-error"]),
.stAlert:has([data-testid="stNotificationIcon-error"]),
div[role="alert"]:has([data-testid="stNotificationIcon-error"]) {
    background: #fde3e6 !important;
    border: 1px solid #e5a9b2 !important;
}

[data-testid="stAlert"]:has([data-testid="stNotificationIcon-error"]) *,
.stAlert:has([data-testid="stNotificationIcon-error"]) *,
div[role="alert"]:has([data-testid="stNotificationIcon-error"]) * {
    color: #4a1720 !important;
}

/* ============================================================
   DATAFRAMES
   ============================================================ */

[data-testid="stDataFrame"] {
    background: #ffffff;
    border: 1px solid #b9cede;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 5px 16px rgba(42,62,91,.07);
}

/* ============================================================
   EXPANDERS / TABS / DIVIDERS
   ============================================================ */

[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #b9cede;
    border-radius: 12px;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #172b43 !important;
}

button[data-baseweb="tab"] {
    color: #4f647b !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #315fe8 !important;
}

hr {
    border-color: #b8cbdc !important;
}

/* ============================================================
   EXISTING CUSTOM DARK PANELS
   Keep these intentionally darker, but readable.
   ============================================================ */

.sentinel-dark-panel {
    background: #294766 !important;
    color: #f7fbff !important;
    border: 1px solid #456482;
    border-radius: 14px;
    padding: 1rem;
}

.sentinel-dark-panel * {
    color: #f7fbff !important;
}

/* Inline cards that may have inherited dark styling:
   force their text to match their light surfaces. */
div[style*="background:#edf5fa"] *,
div[style*="background:linear-gradient(135deg,#edf5fa"] *,
div[style*="background:linear-gradient(135deg,#f0edf4"] *,
div[style*="background:linear-gradient(135deg,#e9f6ee"] * {
    color: #172b43 !important;
}

/* Policy cards: black text */
div[style*="background:#9BE7B1"] *,
div[style*="background:#F7DF63"] *,
div[style*="background:#E88B9B"] * {
    color: #000000 !important;
}

/* ============================================================
   DISTINCT CONTENT CARDS
   Main background stays slate-blue; content blocks stay lighter.
   ============================================================ */

[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #c0d0dc !important;
}

[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}

/* Keep common bordered containers visibly lighter than page */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: #ffffff;
    border-radius: 14px;
}

/* Progress bars */
div[data-testid="stProgress"] {
    background: #e1eaf1 !important;
    border-radius: 999px;
}

/* ============================================================
   MOBILE
   ============================================================ */

@media (max-width: 768px) {
    .block-container {
        padding: .75rem .8rem 2rem;
    }

    .hero {
        padding: 1rem;
        border-radius: 16px;
    }

    .hero-title {
        font-size: 1.45rem;
    }

    .hero-sub {
        font-size: .84rem;
    }

    [data-testid="stMetric"] {
        padding: .65rem;
        border-radius: 12px;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
    }

    h1 { font-size: 1.7rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.15rem !important; }
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = Path(__file__).resolve().parent

FEATURES_PATH = str(PROJECT_ROOT / "data/cluster_features.csv")
SCORES_PATH = str(PROJECT_ROOT / "reports/cluster_risk_scores.csv")
METRICS_PATH = str(PROJECT_ROOT / "reports/metrics.json")
LEDGER_PATH = str(PROJECT_ROOT / "reports/bonus_ledger_demo.jsonl")
AUDIT_PATH = str(PROJECT_ROOT / "reports/audit_log.jsonl")
USERS_PATH = str(PROJECT_ROOT / "data/users.csv")
REFERRALS_PATH = str(PROJECT_ROOT / "data/referrals.csv")
PAYMENTS_PATH = str(PROJECT_ROOT / "data/payments.csv")
WEBHOOK_EVENTS_PATH = str(PROJECT_ROOT / "reports/webhook_events.jsonl")
MAPPING_PATH = str(PROJECT_ROOT / "data/razorpay_cluster_mapping.json")


# ============================================================
# HELPERS
# ============================================================

def load_json(path):

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}


def load_jsonl(path):

    if not os.path.exists(path):
        return []

    records = []

    try:

        with open(path, "r", encoding="utf-8") as f:

            for line in f:

                line = line.strip()

                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except Exception:
                    continue

    except Exception:
        pass

    return records


@st.cache_data(ttl=5)
def load_features():

    if not os.path.exists(FEATURES_PATH):
        return pd.DataFrame()

    return pd.read_csv(FEATURES_PATH)


@st.cache_data(ttl=5)
def load_scores():

    if not os.path.exists(SCORES_PATH):
        return pd.DataFrame()

    return pd.read_csv(SCORES_PATH)


@st.cache_data(ttl=5)
def load_csv_optional(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def build_referral_graph(users_df):
    """Recreate the same weakly-connected referral components used by the pipeline."""
    if users_df.empty or "user_id" not in users_df.columns:
        return nx.DiGraph(), pd.Series(dtype=object)

    g = nx.DiGraph()
    g.add_nodes_from(users_df["user_id"].astype(str).tolist())

    if "referred_by" in users_df.columns:
        for _, r in users_df.iterrows():
            parent = r.get("referred_by")
            child = r.get("user_id")
            if pd.notna(parent) and str(parent).strip() and pd.notna(child):
                g.add_edge(str(parent), str(child))

    comp_map = {}
    for i, component in enumerate(nx.connected_components(g.to_undirected())):
        for node in component:
            comp_map[node] = f"comp_{i}"

    return g, pd.Series(comp_map, name="graph_cluster_id")



def complete_referral_graph_figure(users_df, payments_df, scores_df, graph):
    """Show every user and referral edge, grouped visually by dataset cluster_type."""
    if users_df.empty or graph.number_of_nodes() == 0:
        return None

    import math

    clean = users_df.copy()
    clean["user_id"] = clean["user_id"].astype(str)
    if "cluster_id" in clean.columns:
        clean["cluster_id"] = clean["cluster_id"].astype(str)
    lookup = clean.set_index("user_id")

    # Fast deterministic placement: one compact neighborhood per cluster.
    clusters = {}
    for uid in graph.nodes:
        cluster = str(lookup.loc[uid].get("cluster_id", "unknown")) if uid in lookup.index else "unknown"
        clusters.setdefault(cluster, []).append(uid)

    names = list(clusters)
    cols = max(1, int(math.ceil(math.sqrt(max(len(names), 1)))))
    spacing = 12.0
    pos = {}
    for i, cluster in enumerate(names):
        cx = (i % cols) * spacing
        cy = (i // cols) * spacing
        members = clusters[cluster]
        n = len(members)
        radius = 0.8 + min(3.0, 0.18 * math.sqrt(n))
        if n == 1:
            pos[members[0]] = (cx, cy)
        else:
            for j, uid in enumerate(members):
                angle = 2 * math.pi * j / n
                pos[uid] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    # Attach payment evidence to nodes.
    payment_count = {}
    payment_value = {}
    if not payments_df.empty and "user_id" in payments_df.columns:
        p = payments_df.copy()
        p["user_id"] = p["user_id"].astype(str)
        if "amount" in p.columns:
            p["amount"] = pd.to_numeric(p["amount"], errors="coerce").fillna(0)
        grp = p.groupby("user_id")
        payment_count = grp.size().to_dict()
        if "amount" in p.columns:
            payment_value = grp["amount"].sum().to_dict()

    # Attach model risk to nodes through cluster_id.
    risk_lookup = {}
    if not scores_df.empty and "cluster_id" in scores_df.columns:
        for _, r in scores_df.iterrows():
            risk_lookup[str(r["cluster_id"])] = float(r.get("risk_score", 0))

    specs = {
        "FRAUD_RING": ("🚨 Fraudsters", 10, "#E53935"),
        "FAMILY_FRIEND": ("👥 Friends / Family", 9, "#43A047"),
        "ORGANIC_SINGLE": ("👤 Organic users", 6, "#90A4AE"),
    }

    traces = []
    for group, (label, size, color) in specs.items():
        xs, ys, hovers = [], [], []
        subset = clean[clean.get("cluster_type", pd.Series(index=clean.index, dtype=object)).astype(str) == group]
        for _, r in subset.iterrows():
            uid = str(r["user_id"])
            if uid not in pos:
                continue
            x, y = pos[uid]
            cluster = str(r.get("cluster_id", "unknown"))
            risk = risk_lookup.get(cluster)
            risk_text = f"{risk:.3f}" if risk is not None else "not scored"
            bonus = float(r.get("bonus_amount_claimed", 0) or 0)
            hovers.append(
                f"User: {uid}<br>Group: {group}<br>Cluster: {cluster}<br>"
                f"Risk score: {risk_text}<br>Referrer: {r.get('referred_by', '-')}<br>"
                f"Payments: {int(payment_count.get(uid, 0))}<br>"
                f"Payment value: ₹{float(payment_value.get(uid, 0)):,.2f}<br>"
                f"Device: {r.get('device_id', '-')}<br>IP: {r.get('signup_ip', '-')}<br>"
                f"Instrument: {r.get('payment_instrument_id', '-')}<br>Bonus: ₹{bonus:,.2f}"
            )
            xs.append(x); ys.append(y)
        if xs:
            traces.append(go.Scattergl(
                x=xs, y=ys, mode="markers", name=label,
                hovertext=hovers, hoverinfo="text",
                marker=dict(size=size, color=color, line=dict(width=0.5)),
            ))

    edge_specs = {
        "FRAUD_RING": ("🚨 Fraud referral edges", "#E53935"),
        "FAMILY_FRIEND": ("👥 Friend/family referral edges", "#43A047"),
        "OTHER": ("Referral edges", "#90A4AE"),
    }
    edge_data = {k: ([], []) for k in edge_specs}
    for source, target in graph.edges():
        if source not in pos or target not in pos:
            continue
        group = str(lookup.loc[target].get("cluster_type", "OTHER")) if target in lookup.index else "OTHER"
        key = group if group in edge_data else "OTHER"
        ex, ey = edge_data[key]
        x0, y0 = pos[source]; x1, y1 = pos[target]
        ex += [x0, x1, None]; ey += [y0, y1, None]
    for key, (label, color) in edge_specs.items():
        ex, ey = edge_data[key]
        if ex:
            traces.insert(0, go.Scattergl(
                x=ex, y=ey, mode="lines", name=label,
                hoverinfo="none", line=dict(width=0.8, color=color), opacity=0.30,
            ))

    fig = go.Figure(traces)
    fig.update_layout(
        title="Complete referral network — all users and referral edges",
        height=760,
        margin=dict(l=10, r=10, t=70, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig

def referral_graph_figure(users_df, graph, selected_cluster):
    """Interactive Plotly network for one actual referral component."""
    if users_df.empty or graph is None or not selected_cluster:
        return None

    _, comp_map = build_referral_graph(users_df)
    member_ids = [
        user_id
        for user_id, comp_id in comp_map.items()
        if comp_id == selected_cluster
    ]

    if not member_ids:
        return None

    sub = graph.subgraph(member_ids).copy()

    # Tree-friendly layout. spring_layout keeps small components readable.
    pos = nx.spring_layout(sub, seed=42, k=1.6)

    edge_x, edge_y = [], []
    for source, target in sub.edges():
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1.5),
        hoverinfo="none",
    )

    user_lookup = users_df.copy()
    user_lookup["user_id"] = user_lookup["user_id"].astype(str)
    user_lookup = user_lookup.set_index("user_id")

    node_x, node_y, labels, hover = [], [], [], []
    for node in sub.nodes():
        x, y = pos[node]
        row = user_lookup.loc[node] if node in user_lookup.index else {}
        parent = row.get("referred_by", "-") if isinstance(row, pd.Series) else "-"
        bonus = row.get("bonus_amount_claimed", 0) if isinstance(row, pd.Series) else 0
        device = row.get("device_id", "-") if isinstance(row, pd.Series) else "-"
        instrument = row.get("payment_instrument_id", "-") if isinstance(row, pd.Series) else "-"

        node_x.append(x)
        node_y.append(y)
        labels.append(node[-6:])
        hover.append(
            f"User: {node}<br>Referred by: {parent}<br>"
            f"Bonus claimed: ₹{float(bonus):,.2f}<br>"
            f"Device: {device}<br>Payment instrument: {instrument}"
        )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=labels,
        textposition="bottom center",
        hovertext=hover,
        hoverinfo="text",
        marker=dict(size=22, line=dict(width=1)),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"Actual referral graph — {selected_cluster} ({len(member_ids)} users)",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=480,
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def money(value):

    try:
        return f"₹{float(value):,.2f}"
    except Exception:
        return "₹0.00"


def risk_label(score):

    score = float(score)

    if score < 0.30:
        return "RELEASE"

    if score < 0.70:
        return "VERIFY"

    return "BLOCK"


def risk_color(score):

    score = float(score)

    if score < 0.30:
        return "🟢"

    if score < 0.70:
        return "🟡"

    return "🔴"


# ============================================================
# GROQ EXPLANATION LAYER
# ============================================================

GROQ_MODEL = "openai/gpt-oss-20b"


def generate_groq_explanation(row, initial_action, final_action, checks):
    """Generate a grounded operator explanation with Groq.

    IMPORTANT: Groq is explanation-only. The ML score and deterministic
    policy already decided the action. For high/low-risk clusters there
    are no verification results, so the prompt explicitly forbids Groq
    from inventing them.
    """
    if Groq is None:
        return "Groq SDK is not installed. Run: pip install groq"

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY is not configured in .env."

    def num(name, digits=3):
        value = row.get(name, None)
        try:
            value = float(value)
            return round(value, digits)
        except (TypeError, ValueError):
            return None

    # Build ONLY facts that actually exist in the selected cluster row.
    # Do not pass empty verification checks as if they were evidence.
    facts = {
        "cluster_id": str(row.get("cluster_id", "unknown")),
        "risk_score": num("risk_score", 4),
        "model_action": initial_action,
        "final_policy_action": final_action,
        "cluster_size": num("cluster_size", 2),
        "referral_edges": num("n_referral_edges", 2),
        "device_reuse_ratio": num("device_reuse_ratio", 3),
        "ip_reuse_ratio": num("ip_reuse_ratio", 3),
        "instrument_reuse_ratio": num("instrument_reuse_ratio", 3),
    }

    # Add behavioral/transaction evidence only when it is present.
    optional_fields = [
        "avg_txn_post_signup",
        "avg_active_days_post_signup",
        "avg_txn_value_post_signup",
        "pct_zero_engagement",
        "total_bonus_claimed",
    ]
    for field in optional_fields:
        value = num(field, 3)
        if value is not None:
            facts[field] = value

    verification_required = initial_action == "HOLD_FOR_VERIFICATION"
    verification_facts = {}
    if verification_required and checks:
        verification_facts = checks

    prompt = f"""
You are the AI explanation layer for a referral-bonus fraud system.

The ML model and deterministic policy have ALREADY made the decision.
You are NOT allowed to change, question, or recommend a different action.
Your only job is to explain the decision using the supplied facts.

CRITICAL GROUNDING RULES:
1. Use ONLY facts explicitly present below.
2. NEVER invent a verification result, transaction value, activity score,
   threshold, user behavior, or other number.
3. Verification checks exist ONLY when verification_required is true and
   verification_facts contains entries. Otherwise say nothing about
   verification checks.
4. Do not call this a "transaction". Explain it as a referral cluster and
   bonus decision.
5. Do not claim real money moved. This dashboard is in test/demo mode.
6. The final action MUST remain exactly: {final_action}.

Return exactly this format:

DECISION:
One sentence stating the final action for the referral bonus.

WHY:
- Exactly 2 or 3 evidence-based bullet points using only the supplied facts.

NEXT ACTION:
One sentence describing the operational action implied by the final policy.

SUPPLIED FACTS:
{json.dumps(facts, indent=2, default=str)}

verification_required: {verification_required}
verification_facts:
{json.dumps(verification_facts, indent=2, default=str)}
"""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a grounded fraud-risk explanation assistant. "
                        "Never invent facts. Never invent missing verification "
                        "checks. The supplied final action is authoritative."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_completion_tokens=1200,
            reasoning_effort="low",
            include_reasoning=False,
            stream=False,
        )

        message = response.choices[0].message
        content = getattr(message, "content", None)

        # GPT-OSS is a reasoning model. Explicitly disabling returned reasoning
        # and using low reasoning effort keeps the completion budget available
        # for the actual analyst explanation.
        if not content:
            # Defensive compatibility for SDK response variants.
            content = getattr(message, "output_text", None)

        if not content or not str(content).strip():
            # Never show an empty AI panel. Use the grounded fallback below.
            content = None

        explanation = content.strip() if content else None

        # A lightweight grounding guard. If Groq nevertheless introduces
        # verification claims when no verification was performed, discard
        # that generated text and show a deterministic explanation instead.
        if not verification_required:
            forbidden_markers = [
                "verification check",
                "verification checks",
                "threshold 1.0",
                "threshold 2.0",
                "threshold 100",
                "post-signup activity score",
                "sustained activity score",
                "meaningful transaction value",
            ]
            lower = explanation.lower()
            if any(marker in lower for marker in forbidden_markers):
                explanation = None

        if explanation:
            return explanation

        # Grounded fallback: still show the AI layer's safe result if the
        # model tried to introduce unsupported facts.
        cluster_id = facts["cluster_id"]
        risk = facts["risk_score"]
        cluster_size = facts["cluster_size"]
        referral_edges = facts["referral_edges"]
        instrument = facts["instrument_reuse_ratio"]
        device = facts["device_reuse_ratio"]
        ip = facts["ip_reuse_ratio"]

        action_word = {
            "RELEASE": "RELEASED",
            "HOLD_FOR_VERIFICATION": "HELD FOR VERIFICATION",
            "BLOCK_BONUS": "BLOCKED",
        }.get(final_action, final_action)

        if final_action == "RELEASE":
            next_action = "Release the approved referral bonus; this dashboard is in test mode."
        elif final_action == "HOLD_FOR_VERIFICATION":
            next_action = "Keep the bonus on hold until the automated verification requirements are satisfied."
        else:
            next_action = "Keep the referral bonus blocked; no payout should be released."

        return (
            f"DECISION:\n"
            f"The referral bonus for cluster {cluster_id} is {action_word}.\n\n"
            f"WHY:\n"
            f"- The model assigned a risk score of {risk:.3f}.\n"
            f"- The cluster contains {cluster_size:.0f} users and "
            f"{referral_edges:.0f} referral edges.\n"
            f"- Reuse signals are present across payment instruments "
            f"({instrument:.1%}), devices ({device:.1%}), and IPs ({ip:.1%}).\n\n"
            f"NEXT ACTION:\n"
            f"{next_action}"
        )

    except Exception as exc:
        return (
            f"Groq explanation unavailable: "
            f"{type(exc).__name__}: {exc}"
        )



def generate_claim_groq_explanation(result):
    """Explain one live bonus-claim decision using only returned claim evidence.

    Groq is explanation-only: the backend's deterministic claim decision is
    authoritative and cannot be changed by the model.
    """
    if Groq is None:
        return "Groq SDK is not installed. Run: pip install groq"

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY is not configured in .env."

    risk = result.get("risk_score", 0)
    level = result.get("risk_level", "UNKNOWN")
    action = result.get("action", "UNKNOWN")
    decision = result.get("decision", "UNKNOWN")
    bonus_amount = result.get("bonus_amount_inr", 0)
    user_id = result.get("user_id", "")
    referrer_id = result.get("referrer_id", "")
    reasons = result.get("reasons", []) or []
    signals = result.get("signals", {}) or {}

    facts = {
        "user_id": str(user_id),
        "referrer_id": str(referrer_id),
        "bonus_amount_inr": float(bonus_amount or 0),
        "risk_score": float(risk or 0),
        "risk_level": str(level),
        "claim_action": str(action),
        "final_decision": str(decision),
        "signals": signals,
        "reasons": reasons,
        "dry_run": bool(result.get("dry_run", True)),
        "money_moved": bool(result.get("money_moved", False)),
    }

    prompt = f"""
You are the AI explanation layer for Abuse-Ring Sentinel, an autonomous
referral-bonus fraud protection system.

The deterministic claim-risk engine has ALREADY made the decision.
You MUST NOT change, question, override, or recommend a different decision.
Your only job is to explain the exact decision to an operator.

GROUNDING RULES:
1. Use ONLY the supplied facts.
2. Do not invent user behavior, transaction history, verification results,
   thresholds, locations, identities, or other facts.
3. These are CLAIM-TIME signals. Do not mention future behavior unless it is
   explicitly present in the supplied facts.
4. Explain this as a referral-bonus claim, not as a payment transaction.
5. Never claim real money moved. This is a test/demo environment.
6. The final decision is authoritative and MUST remain exactly:
   {decision}

Return exactly:

DECISION:
One concise sentence stating the final decision for the referral bonus.

WHY:
- Exactly 2 or 3 evidence-based bullet points using the supplied signals.
- Make the strongest coordinated-abuse evidence clear when present.
- If the evidence is weak, say that the claim has no significant coordinated-abuse
  signals rather than inventing reassurance.

NEXT ACTION:
One sentence describing the operational action implied by the existing decision.

SUPPLIED FACTS:
{json.dumps(facts, indent=2, default=str)}
"""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a grounded fraud-risk explanation assistant. "
                        "The supplied claim decision is authoritative. "
                        "Never invent facts and never change the decision."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_completion_tokens=900,
            reasoning_effort="low",
            include_reasoning=False,
            stream=False,
        )

        message = response.choices[0].message
        content = getattr(message, "content", None)
        if not content:
            content = getattr(message, "output_text", None)

        if content and str(content).strip():
            explanation = str(content).strip()

            # Basic grounding guard for the live claim path.
            forbidden = [
                "post-signup activity",
                "transaction history",
                "verification check",
                "verification checks",
                "future behavior",
            ]

            # The live claim path is autonomous. A rejected claim must never
            # be described as being sent to manual review.
            if decision == "REJECTED":
                forbidden += [
                    "manual review",
                    "flag the claim for review",
                    "send for review",
                ]

            if not any(x in explanation.lower() for x in forbidden):
                return explanation

        return _claim_groq_fallback(facts)

    except Exception as exc:
        return (
            f"Groq explanation unavailable: {type(exc).__name__}: {exc}"
        )


def _claim_groq_fallback(facts):
    """Deterministic, grounded fallback for the live claim explanation."""
    decision = facts["final_decision"]
    risk = facts["risk_score"]
    signals = facts["signals"]
    reasons = facts["reasons"]

    action_text = {
        "APPROVED": "APPROVED",
        "VERIFICATION_REQUIRED": "HELD FOR VERIFICATION",
        "REJECTED": "REJECTED",
    }.get(decision, decision)

    evidence = reasons[:3]
    if not evidence:
        evidence = ["No significant coordinated-abuse signals were detected."]

    bullets = "\n".join(f"- {item}" for item in evidence)

    if decision == "APPROVED":
        next_action = (
            "Release the approved referral bonus; the demo is configured "
            "so that no real money moves."
        )
    elif decision == "VERIFICATION_REQUIRED":
        next_action = (
            "Keep the bonus protected pending the existing verification workflow."
        )
    else:
        next_action = "Keep the referral bonus blocked; no payout should be released."

    return (
        f"DECISION:\n"
        f"The referral bonus is {action_text} at a risk score of {risk:.2f}.\n\n"
        f"WHY:\n"
        f"{bullets}\n\n"
        f"NEXT ACTION:\n"
        f"{next_action}"
    )


# ============================================================
# LIVE CLAIM API
# ============================================================

def _get_sentinel_api_url():
    """Resolve the Sentinel API URL for local or Streamlit Cloud use."""
    # Streamlit Cloud: use the app secret when configured.
    try:
        secret_url = st.secrets.get("SENTINEL_API_URL")
    except Exception:
        secret_url = None

    # Local development / other hosts: fall back to environment variable.
    configured = secret_url or os.getenv("SENTINEL_API_URL")
    if configured:
        return str(configured).rstrip("/")
    if os.name == "nt":
        return "http://127.0.0.1:8000"
    return "https://abuse-ring-sentinel-ie88.onrender.com"


SENTINEL_API_URL = _get_sentinel_api_url()


def _sentinel_port_open():
    """Return True when the local Sentinel API port is accepting connections."""
    try:
        parsed = urllib.parse.urlparse(SENTINEL_API_URL)
        host = parsed.hostname or "127.0.0.1"

        # Remote API: it is not local to this Streamlit process.
        if host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
            return True

        port = parsed.port or 8000
        with socket.create_connection((host, port), timeout=0.7):
            return True
    except Exception:
        return False


def _ensure_sentinel_api():
    """Ensure local FastAPI is available without spawning it on Streamlit Cloud."""
    parsed = urllib.parse.urlparse(SENTINEL_API_URL)
    host = parsed.hostname or "127.0.0.1"

    # A deployed dashboard talks to the Render API. Never start FastAPI here.
    if host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        return True, None

    if _sentinel_port_open():
        return True, None

    project_root = Path(__file__).resolve().parent
    app_module = "src.api.main:app"

    try:
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        subprocess.Popen(
            [
                os.environ.get("PYTHON", "python"),
                "-m",
                "uvicorn",
                app_module,
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as exc:
        return False, (
            "Sentinel API is not running and could not be started automatically. "
            f"Start it manually with: python -m uvicorn {app_module} --host 127.0.0.1 --port 8000. "
            f"Details: {exc}"
        )

    for _ in range(30):
        if _sentinel_port_open():
            return True, None
        time.sleep(0.2)

    return False, (
        "Sentinel API did not become available on port 8000. "
        "Run `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000` "
        "in the project folder and reload the dashboard."
    )

def _local_claim_fallback(user_id, referrer_id, bonus_amount, payment_id=""):
    """Use the same deterministic claim engine when the API is unreachable."""
    try:
        from src.features.claim_features import ClaimFeatureBuilder
        from src.pipeline.claim_risk import ClaimRiskScorer
        builder = ClaimFeatureBuilder(
            users_path=str(PROJECT_ROOT / "data" / "users.csv"),
            referrals_path=str(PROJECT_ROOT / "data" / "referrals.csv"),
        )
        features = builder.build(
            user_id=str(user_id),
            referrer_id=str(referrer_id) if referrer_id else None,
        )
        result = ClaimRiskScorer().score(features)
        if result.action == "APPROVE_BONUS":
            decision, status, obs = "APPROVED", "RELEASED_SIMULATED", "NOT_REQUIRED"
        elif result.action == "VERIFY_CLAIM":
            decision, status, obs = "VERIFICATION_REQUIRED", "HELD", "PENDING"
        else:
            decision, status, obs = "REJECTED", "NOT_RELEASED", "NOT_REQUIRED"
        now = datetime.utcnow().isoformat()
        claim_id = f"claim_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        record = {
            "claim_id": claim_id, "user_id": str(user_id),
            "referrer_id": str(result.referrer_id),
            "bonus_amount": float(bonus_amount), "bonus_amount_inr": float(bonus_amount),
            "payment_id": payment_id or None,
            "risk_score": result.risk_score, "initial_risk_score": result.risk_score,
            "risk_level": result.risk_level, "engine_action": result.action,
            "action": result.action, "decision": decision, "final_decision": decision,
            "bonus_status": status, "reasons": result.reasons,
            "claim_time_features": features, "signals": features,
            "observation_status": obs,
            "observation_source": "not_started" if obs == "PENDING" else None,
            "policy": {"low_action":"APPROVE_BONUS", "medium_action":"HOLD_AND_OBSERVE",
                       "high_action":"REJECT_BONUS", "policy_version":"1.2-autonomous-observation"},
            "dry_run": True, "money_moved": False, "timestamp": now, "created_at": now,
        }
        return record, None
    except Exception as exc:
        return None, f"Local claim engine failed: {type(exc).__name__}: {exc}"


def _local_observation_fallback(claim):
    """Use the project's real post-signup observation engine as a fallback."""
    try:
        from src.pipeline.claim_observation import ClaimObservationEngine
        engine = ClaimObservationEngine(users_path=str(PROJECT_ROOT / "data" / "users.csv"))
        observation = engine.observe(user_id=str(claim["user_id"]))
        if observation.action == "APPROVE_BONUS":
            decision, status = "APPROVED", "RELEASED_SIMULATED"
        elif observation.action == "KEEP_HELD":
            decision, status = "VERIFICATION_REQUIRED", "HELD"
        else:
            decision, status = "REJECTED", "NOT_RELEASED"
        return {
            "claim_id": claim.get("claim_id"), "user_id": claim.get("user_id"),
            "referrer_id": claim.get("referrer_id", ""),
            "bonus_amount": claim.get("bonus_amount", 0),
            "bonus_amount_inr": claim.get("bonus_amount_inr", claim.get("bonus_amount", 0)),
            "payment_id": claim.get("payment_id"),
            "initial_decision": claim.get("decision"),
            "initial_risk_score": claim.get("risk_score", 0),
            "risk_score": claim.get("risk_score", 0), "risk_level": claim.get("risk_level", "MEDIUM"),
            "observation_score": observation.observation_score,
            "behavior_score": observation.observation_score,
            "observation_action": observation.action,
            "observation_evidence": observation.reasons,
            "reasons": observation.reasons, "decision": decision, "final_decision": decision,
            "bonus_status": status,
            "observation_status": "STILL_HELD" if observation.action == "KEEP_HELD" else "RESOLVED",
            "observation_source": "post_signup_behavior_replay",
            "dry_run": True, "money_moved": False, "timestamp": datetime.utcnow().isoformat(),
        }, None
    except Exception as exc:
        return None, f"Local observation engine failed: {type(exc).__name__}: {exc}"


def submit_bonus_claim(user_id, referrer_id, bonus_amount, payment_id=""):
    """Call the real local FastAPI claim endpoint."""
    payload = {
        "user_id": str(user_id),
        "bonus_amount": float(bonus_amount),
    }

    if referrer_id:
        payload["referrer_id"] = str(referrer_id)

    if payment_id:
        payload["payment_id"] = str(payment_id)

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{SENTINEL_API_URL}/claim-bonus",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        api_ready, startup_error = _ensure_sentinel_api()
        if not api_ready:
            return None, startup_error

        with urllib.request.urlopen(request, timeout=20) as response:
            return normalize_claim_result(json.loads(response.read().decode("utf-8"))), None
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return None, f"API returned HTTP {exc.code}: {detail}"
    except Exception as exc:
        fallback, fallback_error = _local_claim_fallback(
            user_id, referrer_id, bonus_amount, payment_id
        )
        if fallback is not None:
            return fallback, None
        return None, (
            "Could not reach Sentinel API and local fallback failed. "
            f"API error: {exc}. Local error: {fallback_error}"
        )


def normalize_claim_result(result):
    """Normalize claim API responses so the dashboard supports both
    initial claim decisions and later autonomous observation resolutions.
    """
    if not isinstance(result, dict):
        return result

    normalized = dict(result)

    # New backend field names -> existing dashboard field names.
    if "bonus_amount_inr" not in normalized:
        normalized["bonus_amount_inr"] = normalized.get("bonus_amount", 0)

    if "action" not in normalized:
        normalized["action"] = normalized.get("engine_action", normalized.get("observation_action", ""))

    if "signals" not in normalized:
        normalized["signals"] = normalized.get("claim_time_features", {}) or {}

    # Resolution responses contain observation evidence separately.
    if normalized.get("observation_evidence") and not normalized.get("reasons"):
        normalized["reasons"] = normalized.get("observation_evidence")

    return normalized


def resolve_held_claim(claim_id):
    """Ask Sentinel to autonomously resolve a previously held claim."""
    encoded_claim_id = urllib.parse.quote(str(claim_id), safe="")
    url = (
        f"{SENTINEL_API_URL}/claim-observation/"
        f"{encoded_claim_id}/resolve"
    )

    request = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        api_ready, startup_error = _ensure_sentinel_api()
        if not api_ready:
            return None, startup_error

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return normalize_claim_result(data), None

    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return None, f"Observation API returned HTTP {exc.code}: {detail}"

    except Exception as exc:
        claim = st.session_state.get("last_claim_result")
        if claim and str(claim.get("claim_id", "")) == str(claim_id):
            fallback, fallback_error = _local_observation_fallback(claim)
            if fallback is not None:
                return fallback, None
        return None, (
            "Could not reach Sentinel observation API and local fallback failed. "
            f"Details: {exc}"
        )


def render_claim_result(result):
    """Render an autonomous claim decision returned by the backend."""
    result = normalize_claim_result(result)

    risk = float(result.get("risk_score", result.get("initial_risk_score", 0)) or 0)
    level = str(result.get("risk_level", "UNKNOWN"))
    decision = str(result.get("decision", result.get("final_decision", "UNKNOWN")))
    bonus_status = str(result.get("bonus_status", "UNKNOWN"))
    amount = float(result.get("bonus_amount_inr", result.get("bonus_amount", 0)) or 0)

    # A resolved claim keeps the original claim-time risk level. If the
    # resolution response does not contain it, derive a display level.
    if level == "UNKNOWN":
        if risk >= 0.70:
            level = "HIGH"
        elif risk >= 0.30:
            level = "MEDIUM"
        else:
            level = "LOW"

    st.markdown("### 🛡️ Sentinel Decision")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Risk Score", f"{risk:.2f}")
    with c2:
        if level == "HIGH":
            st.error(f"🔴 {level} RISK")
        elif level == "MEDIUM":
            st.warning(f"🟡 {level} RISK")
        else:
            st.success(f"🟢 {level} RISK")
    with c3:
        if decision == "REJECTED":
            st.error("❌ BONUS REJECTED")
        elif decision == "VERIFICATION_REQUIRED":
            st.warning("🟡 BONUS HELD")
        else:
            st.success("✅ BONUS APPROVED")

    if decision == "REJECTED":
        st.error(
            f"❌ **BONUS REJECTED — {money(amount)} NOT RELEASED**"
        )
    elif decision == "VERIFICATION_REQUIRED":
        st.warning(
            f"🟡 **BONUS HELD — {money(amount)} remains protected**"
        )
    else:
        st.success(
            f"✅ **BONUS APPROVED — {money(amount)} RELEASED (SIMULATED)**"
        )

    # ------------------------------------------------------------
    # AUTONOMOUS OBSERVATION WORKFLOW
    # ------------------------------------------------------------
    claim_id = result.get("claim_id")
    observation_status = result.get("observation_status")

    if decision == "VERIFICATION_REQUIRED" and claim_id:
        st.markdown("---")
        st.markdown("### 🤖 Autonomous Claim Resolution")
        st.caption(
            "This claim was initially held because claim-time signals were "
            "inconclusive. Sentinel can now evaluate post-signup behavioural "
            "evidence and resolve the held bonus without manual review."
        )

        if observation_status in ("PENDING", "NOT_STARTED", None):
            st.info(
                "⏳ **CLAIM HELD** — no bonus has been released."
            )

            if st.button(
                "🤖 Run Autonomous Observation",
                type="primary",
                use_container_width=True,
                key=f"observe_claim_{claim_id}",
            ):
                with st.spinner(
                    "Analysing post-signup behavioural evidence..."
                ):
                    resolved, observation_error = resolve_held_claim(
                        claim_id
                    )

                if observation_error:
                    st.error(observation_error)
                else:
                    st.session_state["last_claim_result"] = resolved
                    st.session_state["last_claim_user"] = str(
                        resolved.get("user_id", result.get("user_id", ""))
                    )
                    st.session_state["claim_groq_explanation"] = None
                    st.session_state["claim_groq_key"] = None
                    st.rerun()

        elif observation_status in ("RESOLVED", "STILL_HELD"):
            st.info(
                "🤖 **Autonomous observation completed.**"
            )

    # ------------------------------------------------------------
    # EVIDENCE
    # ------------------------------------------------------------
    reasons = result.get("reasons", []) or []
    if reasons:
        st.markdown("### 🔎 Evidence")
        for reason in reasons:
            st.write(f"• {reason}")

    signals = result.get("signals", {}) or {}
    if signals:
        st.markdown("### 📡 Claim-Time Signals")
        signal_rows = [
            ("Device matches", signals.get("device_match_count", 0)),
            ("IP matches", signals.get("ip_match_count", 0)),
            ("Payment-instrument matches", signals.get("instrument_match_count", 0)),
            ("Connected accounts", signals.get("connected_user_count", 0)),
            ("Referrer referrals", signals.get("referral_count", 0)),
            ("Shared signals with referrer", signals.get("shared_signals_with_referrer", 0)),
            ("Multi-signal overlap", signals.get("multi_signal_overlap", 0)),
            ("Strong overlap", signals.get("strong_overlap", 0)),
            ("Very strong overlap", signals.get("very_strong_overlap", 0)),
        ]
        st.dataframe(
            pd.DataFrame(
                signal_rows,
                columns=["Signal", "Value"],
            ),
            use_container_width=True,
            hide_index=True,
        )

    # ------------------------------------------------------------
    # OBSERVATION EVIDENCE
    # ------------------------------------------------------------
    observation_evidence = result.get(
        "observation_evidence",
        [],
    ) or []

    if observation_evidence:
        st.markdown("### 🔬 Behavioural Observation Evidence")

        observation_score = result.get(
            "observation_score",
            result.get("behavior_score"),
        )

        if observation_score is not None:
            st.metric(
                "Behaviour Observation Score",
                f"{float(observation_score):.2f}",
            )

        for evidence in observation_evidence:
            st.write(f"• {evidence}")

        source = result.get(
            "observation_source",
            "post_signup_behavior_replay",
        )

        st.caption(
            f"Observation source: {source}"
        )

    st.caption(
        f"Policy: {result.get('policy', {}).get('policy_version', '1.2-autonomous-observation')} • "
        f"Dry run: {result.get('dry_run', True)} • "
        f"Money moved: {result.get('money_moved', False)}"
    )

    # ------------------------------------------------------------
    # AI EXPLANATION
    # ------------------------------------------------------------
    st.markdown("### 🧠 AI Risk Analyst")
    st.caption(
        "Groq explains the supplied Sentinel decision and evidence. "
        "It does not make or change the fraud decision."
    )

    claim_key = (
        f"{result.get('claim_id', '')}|"
        f"{result.get('user_id', '')}|"
        f"{result.get('risk_score', '')}|"
        f"{result.get('decision', '')}|"
        f"{result.get('observation_score', '')}|"
        f"{result.get('timestamp', '')}"
    )

    if st.button(
        "Generate AI Explanation",
        type="secondary",
        key=f"generate_claim_groq_{claim_key}",
        use_container_width=True,
    ):
        with st.spinner("Generating grounded claim explanation..."):
            explanation = generate_claim_groq_explanation(result)

        st.session_state["claim_groq_explanation"] = explanation
        st.session_state["claim_groq_key"] = claim_key

    if (
        st.session_state.get("claim_groq_explanation")
        and st.session_state.get("claim_groq_key") == claim_key
    ):
        st.info(st.session_state["claim_groq_explanation"])


# ============================================================
# LOAD DATA
# ============================================================

features = load_features()
scores = load_scores()
users = load_csv_optional(USERS_PATH)
referrals = load_csv_optional(REFERRALS_PATH)
payments = load_csv_optional(PAYMENTS_PATH)
webhook_events = load_jsonl(WEBHOOK_EVENTS_PATH)
razorpay_mapping = load_json(MAPPING_PATH)
metrics = load_json(METRICS_PATH)
ledger = load_jsonl(LEDGER_PATH)
audit = load_jsonl(AUDIT_PATH)
referral_graph, graph_cluster_map = build_referral_graph(users)

# ============================================================
# MODEL EXPLAINABILITY
# ============================================================

def load_global_feature_importance():
    try:
        import joblib
        paths=(PROJECT_ROOT/"reports"/"fraud_ring_model.joblib", PROJECT_ROOT/"src"/"reports"/"fraud_ring_model.joblib")
        for path in paths:
            if path.exists():
                model=joblib.load(path)
                vals=getattr(model,"feature_importances_",None)
                if vals is None: return pd.DataFrame()
                names=list(getattr(model,"feature_names_in_",[])) or [
                    "cluster_size","n_referral_edges","referral_tree_depth","graph_density","fan_out_ratio",
                    "signup_span_hours","signups_per_hour","n_unique_devices","n_unique_ips","n_unique_instruments",
                    "device_reuse_ratio","ip_reuse_ratio","instrument_reuse_ratio","addr_concentration_ratio",
                    "top_instrument_share","top_device_share","avg_txn_post_signup","avg_txn_value_post_signup",
                    "avg_active_days_post_signup","pct_zero_engagement","total_bonus_claimed","avg_bonus_claimed"]
                n=min(len(names),len(vals))
                return pd.DataFrame({"Parameter":names[:n],"Global importance":[float(x)*100 for x in vals[:n]]}).sort_values("Global importance",ascending=False)
    except Exception:
        pass
    return pd.DataFrame()


def render_risk_reasoning(selected_row, risk_score, action):
    st.markdown("### 🧠 How the AI formed this risk score")
    st.caption("Gradient Boosting is an ensemble of decision trees, not a linear weighted formula. Global feature importance below shows which parameters mattered most during training; the second table shows this cluster's actual values.")
    a,b,c,d=st.columns(4)
    a.metric("Risk score",f"{float(risk_score):.4f}")
    b.metric("Model","Gradient Boosting")
    c.metric("Trees","200")
    d.metric("Max depth","3")
    left,right=st.columns(2)
    with left:
        st.markdown("#### Top model-important parameters")
        imp=load_global_feature_importance()
        if imp.empty: st.info("Model importance is unavailable.")
        else: st.dataframe(imp.head(7),use_container_width=True,hide_index=True,column_config={"Global importance":st.column_config.NumberColumn(format="%.2f%%")})
    with right:
        st.markdown("#### Actual values for this cluster")
        names=["cluster_size","n_referral_edges","referral_tree_depth","graph_density","fan_out_ratio","signup_span_hours","signups_per_hour","n_unique_devices","n_unique_ips","n_unique_instruments","device_reuse_ratio","ip_reuse_ratio","instrument_reuse_ratio","addr_concentration_ratio","top_instrument_share","top_device_share","avg_txn_post_signup","avg_txn_value_post_signup","avg_active_days_post_signup","pct_zero_engagement","total_bonus_claimed","avg_bonus_claimed"]
        vals=[{"Parameter":n,"Observed value":selected_row[n]} for n in names if n in selected_row.index and pd.notna(selected_row[n])]
        st.dataframe(pd.DataFrame(vals),use_container_width=True,hide_index=True)
    st.info(f"Model score {float(risk_score):.4f} → {str(action).replace('_',' ')}. The autonomous payout policy then applies its thresholds.")

# ============================================================
# DERIVED VALUES (AVAILABLE TO EVERY WORKSPACE)
# ============================================================
default_metrics = metrics.get("metrics_at_default_threshold", {}) or {}
precision = float(default_metrics.get("precision", 0) or 0)
recall = float(default_metrics.get("recall", 0) or 0)
f1 = float(default_metrics.get("f1", 0) or 0)
roc_auc = float(default_metrics.get("roc_auc", 0) or 0)

released = blocked = 0
released_money = blocked_money = 0.0

if not scores.empty:
    _exposure = scores.copy()
    _exposure["cluster_id"] = _exposure["cluster_id"].astype(str)
    if not features.empty and "total_bonus_claimed" in features.columns:
        _bonus = features[["cluster_id", "total_bonus_claimed"]].copy()
        _bonus["cluster_id"] = _bonus["cluster_id"].astype(str)
        _exposure = _exposure.merge(_bonus, on="cluster_id", how="left")
    if "total_bonus_claimed" not in _exposure.columns:
        _exposure["total_bonus_claimed"] = 0.0
    _exposure["total_bonus_claimed"] = pd.to_numeric(
        _exposure["total_bonus_claimed"], errors="coerce"
    ).fillna(0)
    _exposure["risk_score"] = pd.to_numeric(
        _exposure["risk_score"], errors="coerce"
    ).fillna(0)
    _release_mask = _exposure["risk_score"] < 0.30
    _block_mask = _exposure["risk_score"] >= 0.70
    released = int(_release_mask.sum())
    blocked = int(_block_mask.sum())
    released_money = float(_exposure.loc[_release_mask, "total_bonus_claimed"].sum())
    blocked_money = float(_exposure.loc[_block_mask, "total_bonus_claimed"].sum())


# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="hero">
  <div class="hero-title">🛡️ Abuse-Ring Sentinel</div>
  <div class="hero-sub">Autonomous referral-bonus fraud protection • defense-only AI risk manager</div>
  <div style="margin-top:.7rem">
    <span class="status-chip">● ONLINE</span>
    <span class="status-chip">⚡ AUTONOMOUS</span>
    <span class="status-chip">🧪 RAZORPAY TEST MODE</span>
    <span class="status-chip">NO REAL PAYOUTS</span>
  </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div class="sentinel-brand">
      <div class="brand-title">🛡️ Sentinel</div>
      <div class="brand-sub">Risk operations console</div>
    </div>
    <div class="nav-caption">Workspaces</div>
    """, unsafe_allow_html=True)

    active_section = st.radio(
        "Navigation",
        [
            "🏠 Overview",
            "⚡ Live Bonus Claim",
            "🔗 Cluster Analysis",
            "🗃️ Data & Referral Graph",
            "🧠 Autonomous Policy",
            "📊 Model Performance",
            "📈 Risk Distribution",
            "🔗 Ring Signals",
            "📜 Audit Trail",
            "💰 Bonus Protection",
        ],
        label_visibility="collapsed",
        key="sentinel_workspace_navigation",
    )
    st.markdown("---")
    st.markdown("""
    <div style="
        padding:.7rem .75rem;
        border-radius:12px;
        background:rgba(15,23,42,.28);
        border:1px solid rgba(148,163,184,.15);
        margin-top:.3rem;">
      <div style="font-size:.72rem;color:#93c5fd;font-weight:800;">SYSTEM STATUS</div>
      <div style="font-size:.76rem;color:#b7c5df;margin-top:.3rem;">● Policy 1.1-autonomous</div>
      <div style="font-size:.76rem;color:#b7c5df;">● Defense-only • Test Mode</div>
      <div style="font-size:.76rem;color:#b7c5df;">● Users: {len(users):,} • Clusters: {len(features):,}</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# OVERVIEW
# ============================================================
if active_section == "🏠 Overview":
    st.subheader("Command Center")
    st.caption("Detection quality, protected bonus exposure and autonomous decisioning at a glance.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Users observed", f"{len(users):,}")
    k2.metric("Referral clusters", f"{len(features):,}")
    k3.metric("High-risk clusters", f"{blocked:,}")
    _overview_total_exposure = (
        float(features["total_bonus_claimed"].sum())
        if not features.empty and "total_bonus_claimed" in features.columns
        else 0.0
    )
    _overview_blocked_pct = (
        blocked_money / _overview_total_exposure * 100.0
        if _overview_total_exposure > 0 else 0.0
    )
    k4.metric(
        "Bonus exposure blocked",
        f"{_overview_blocked_pct:.1f}%",
        delta=money(blocked_money),
        delta_color="off",
    )
    st.caption(
        f"₹{blocked_money:,.0f} protected out of "
        f"₹{_overview_total_exposure:,.0f} total synthetic bonus exposure."
    )

    st.markdown("### Autonomous decision flow")
    f1c, f2c, f3c, f4c = st.columns(4)
    flow = [
        ("01", "Claim arrives", "Capture user, referrer and claim-time signals."),
        ("02", "Risk score", "Score coordinated-abuse evidence."),
        ("03", "Policy action", "Approve, verify or reject autonomously."),
        ("04", "Observation", "Resolve held claims using later behaviour."),
    ]
    for col, (num, title, desc) in zip([f1c, f2c, f3c, f4c], flow):
        with col:
            st.markdown(f"**{num} · {title}**")
            st.caption(desc)

    st.markdown("### Held-out model performance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precision", f"{precision:.3f}")
    m2.metric("Recall", f"{recall:.3f}")
    m3.metric("F1", f"{f1:.3f}")
    m4.metric("ROC-AUC", f"{roc_auc:.3f}")
    st.caption("Metrics are from the held-out synthetic test set.")

    st.markdown("### Policy posture")
    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown(
            """
            <div style="
                background:#9BE7B1;
                border-radius:12px;
                padding:16px;
                text-align:center;
                border:1px solid #65c987;
            ">
                <div style="font-size:1.05rem;font-weight:800;color:#000;">
                    🟢 LOW RISK
                </div>
                <div style="font-size:.95rem;font-weight:700;color:#000;margin-top:4px;">
                    RELEASE
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Risk < 0.30")

    with p2:
        st.markdown(
            """
            <div style="
                background:#F7DF63;
                border-radius:12px;
                padding:16px;
                text-align:center;
                border:1px solid #d7bd32;
            ">
                <div style="font-size:1.05rem;font-weight:800;color:#000;">
                    🟡 MEDIUM RISK
                </div>
                <div style="font-size:.95rem;font-weight:700;color:#000;margin-top:4px;">
                    VERIFY
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("0.30 ≤ risk < 0.70")

    with p3:
        st.markdown(
            """
            <div style="
                background:#E88B9B;
                border-radius:12px;
                padding:16px;
                text-align:center;
                border:1px solid #d66b7c;
            ">
                <div style="font-size:1.05rem;font-weight:800;color:#000;">
                    🔴 HIGH RISK
                </div>
                <div style="font-size:.95rem;font-weight:700;color:#000;margin-top:4px;">
                    BLOCK
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Risk ≥ 0.70")

elif active_section == "⚡ Live Bonus Claim":
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#edf5fa,#e6f2ff);border:1px solid #bfdbfe;border-radius:18px;padding:18px 20px;margin:4px 0 18px 0;">
          <div style="font-size:1.55rem;font-weight:800;color:#0f172a;">⚡ Live Bonus Claim</div>
          <div style="color:#475569;margin-top:4px;">Claim-level analysis • evaluate one referral-bonus claim using immediate evidence.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if users.empty:
        st.warning("users.csv is not available, so the live claim simulator cannot be populated.")
    else:
        claim_users = users.copy()
        claim_users["user_id"] = claim_users["user_id"].astype(str)

        # Put known demo cases first so the pitch demo is one click away.
        preferred = [
            "u_aa9fcf81d4",
            "u_52ec14b2e5",
            "u_7b5d4c1d8f",
        ]
        existing_preferred = [u for u in preferred if u in set(claim_users["user_id"])]
        remaining = [u for u in claim_users["user_id"].tolist() if u not in existing_preferred]
        claim_options = existing_preferred + remaining

        selected_claim_user = st.selectbox(
            "User attempting to claim",
            claim_options,
            key="live_claim_user",
        )

        selected_user_rows = claim_users[
            claim_users["user_id"] == selected_claim_user
        ]

        selected_user = selected_user_rows.iloc[0]

        default_referrer = selected_user.get("referred_by", "")
        if pd.isna(default_referrer):
            default_referrer = ""

        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input(
                "User ID",
                value=selected_claim_user,
                disabled=True,
                key="claim_user_display",
            )
        with c2:
            st.text_input(
                "Referrer ID",
                value=str(default_referrer),
                disabled=True,
                key="claim_referrer_display",
            )
        with c3:
            claim_bonus = st.number_input(
                "Bonus amount (₹)",
                min_value=1.0,
                value=500.0,
                step=50.0,
                key="claim_bonus_amount",
            )

        payment_id = st.text_input(
            "Payment ID (optional)",
            value="",
            placeholder="pay_test_...",
            key="claim_payment_id",
        )

        user_type = str(selected_user.get("cluster_type", "UNKNOWN"))
        st.info(
            f"Dataset context: **{user_type}**. "
            "This label is shown for demo context only; it is NOT sent to the claim API "
            "and is NOT used by the live decision."
        )

        if st.button(
            "🚀 CLAIM BONUS",
            type="primary",
            use_container_width=True,
            key="claim_bonus_button",
        ):
            with st.spinner("Sentinel is evaluating claim-time signals..."):
                claim_result, claim_error = submit_bonus_claim(
                    user_id=selected_claim_user,
                    referrer_id=str(default_referrer) if default_referrer else None,
                    bonus_amount=claim_bonus,
                    payment_id=payment_id.strip(),
                )

            if claim_error:
                st.error(claim_error)
            else:
                st.session_state["last_claim_result"] = claim_result
                st.session_state["last_claim_user"] = selected_claim_user
                st.rerun()

        last_claim = st.session_state.get("last_claim_result")
        last_claim_user = st.session_state.get("last_claim_user")

        if last_claim and last_claim_user == selected_claim_user:
            render_claim_result(last_claim)
        else:
            st.info(
                "Choose a user and click **CLAIM BONUS**. The backend will make the decision "
                "using only claim-time signals."
            )

    st.divider()


elif active_section == "🔗 Cluster Analysis":
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#f0edf4,#f1e9ff);border:1px solid #d8b4fe;border-radius:18px;padding:18px 20px;margin:4px 0 18px 0;">
          <div style="font-size:1.55rem;font-weight:800;color:#0f172a;">🔗 Fraud Cluster Analysis</div>
          <div style="color:#475569;margin-top:4px;">Cluster-level analysis • inspect connected accounts, model evidence, policy and AI explanation.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    default_metrics = metrics.get(
        "metrics_at_default_threshold",
        {}
    )

    precision = default_metrics.get(
        "precision",
        0
    )

    recall = default_metrics.get(
        "recall",
        0
    )

    f1 = default_metrics.get(
        "f1",
        0
    )

    roc_auc = default_metrics.get(
        "roc_auc",
        0
    )


    released = 0
    blocked = 0
    blocked_money = 0.0
    released_money = 0.0

    # Calculate synthetic bonus exposure directly from scored clusters.
    # This is exposure protected by the model, not real money movement.
    if not scores.empty:
        score_df = scores.copy()
        score_df["cluster_id"] = score_df["cluster_id"].astype(str)

        if not features.empty and "total_bonus_claimed" in features.columns:
            bonus_df = features[["cluster_id", "total_bonus_claimed"]].copy()
            bonus_df["cluster_id"] = bonus_df["cluster_id"].astype(str)

            score_df = score_df.merge(
                bonus_df,
                on="cluster_id",
                how="left",
            )

            score_df["total_bonus_claimed"] = pd.to_numeric(
                score_df["total_bonus_claimed"],
                errors="coerce",
            ).fillna(0)

            released_mask = score_df["risk_score"] < 0.30
            blocked_mask = score_df["risk_score"] >= 0.70

            released = int(released_mask.sum())
            blocked = int(blocked_mask.sum())

            released_money = float(
                score_df.loc[released_mask, "total_bonus_claimed"].sum()
            )
            blocked_money = float(
                score_df.loc[blocked_mask, "total_bonus_claimed"].sum()
            )
        else:
            released = int((score_df["risk_score"] < 0.30).sum())
            blocked = int((score_df["risk_score"] >= 0.70).sum())

    else:
        # Fallback to the ledger if scored cluster data is unavailable.
        for record in ledger:
            action = str(record.get("action", "")).upper()

            try:
                amount = float(
                    record.get(
                        "bonus_amount",
                        record.get("amount", 0),
                    )
                    or 0
                )
            except Exception:
                amount = 0.0

            if "BLOCK" in action or "HOLD" in action:
                blocked += 1
                blocked_money += amount
            elif "RELEASE" in action:
                released += 1
                released_money += amount


    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "BONUSES RELEASED",
            f"{released:,}",
        )

    with k2:

        st.metric(
            "BONUSES BLOCKED",
            f"{blocked:,}",
        )

    with k3:

        st.metric(
            "BONUS EXPOSURE PROTECTED",
            money(blocked_money),
        )

    with k4:

        st.metric(
            "MODEL RECALL",
            f"{recall:.1%}",
        )


    st.divider()

    if not scores.empty:

        cluster_ids = (
            scores["cluster_id"]
            .astype(str)
            .tolist()
        )

        default_index = (
            cluster_ids.index("comp_1653")
            if "comp_1653" in cluster_ids
            else (
                cluster_ids.index("comp_0")
                if "comp_0" in cluster_ids
                else 0
            )
        )

        selected_cluster = st.selectbox(
            "Select a cluster to inspect",
            cluster_ids,
            index=default_index,
        )

        # IMPORTANT: risk scores and cluster features live in separate files.
        # Merge them before running verification or generating the AI explanation.
        # Without this merge, missing feature columns silently become 0.0.
        score_view = scores.copy()
        score_view["cluster_id"] = score_view["cluster_id"].astype(str)

        if not features.empty:
            feature_view = features.copy()
            feature_view["cluster_id"] = feature_view["cluster_id"].astype(str)
            feature_view = feature_view.drop(
                columns=["_true_cluster_type", "label_fraud"],
                errors="ignore",
            )
            score_view = score_view.merge(
                feature_view,
                on="cluster_id",
                how="left",
                suffixes=("", "_feature"),
            )

        selected = score_view[
            score_view["cluster_id"].astype(str) == selected_cluster
        ]

        if not selected.empty:

            row = selected.iloc[0]
            score = float(row["risk_score"])

            # ML action
            if score < 0.30:
                initial_action = "RELEASE"
            elif score < 0.70:
                initial_action = "HOLD_FOR_VERIFICATION"
            else:
                initial_action = "BLOCK_BONUS"

            # Deterministic verification for medium-risk cases.
            checks = {}

            def value(column, default=0.0):
                try:
                    return float(row.get(column, default))
                except Exception:
                    return default

            if initial_action == "HOLD_FOR_VERIFICATION":
                checks = {
                    "post_signup_activity": {
                        "value": value("avg_txn_post_signup"),
                        "threshold": 1.0,
                        "passed": value("avg_txn_post_signup") >= 1.0,
                    },
                    "sustained_activity": {
                        "value": value("avg_active_days_post_signup"),
                        "threshold": 2.0,
                        "passed": value("avg_active_days_post_signup") >= 2.0,
                    },
                    "meaningful_transaction_value": {
                        "value": value("avg_txn_value_post_signup"),
                        "threshold": 100.0,
                        "passed": value("avg_txn_value_post_signup") >= 100.0,
                    },
                    "engagement_presence": {
                        "value": 1.0 - value("pct_zero_engagement"),
                        "threshold": 0.5,
                        "passed": (
                            1.0 - value("pct_zero_engagement")
                        ) >= 0.5,
                    },
                    "payment_instrument_diversity": {
                        "value": value("instrument_reuse_ratio"),
                        "threshold": 0.5,
                        "passed": value("instrument_reuse_ratio") <= 0.5,
                    },
                    "device_diversity": {
                        "value": value("device_reuse_ratio"),
                        "threshold": 0.5,
                        "passed": value("device_reuse_ratio") <= 0.5,
                    },
                    "ip_diversity": {
                        "value": value("ip_reuse_ratio"),
                        "threshold": 0.5,
                        "passed": value("ip_reuse_ratio") <= 0.5,
                    },
                }

                checks_passed = sum(
                    1 for check in checks.values() if check["passed"]
                )

                final_action = (
                    "RELEASE"
                    if checks_passed >= 5
                    else "BLOCK_BONUS"
                )
            else:
                checks_passed = None
                final_action = initial_action

            left, middle, right = st.columns([1, 2, 1])

            with left:
                st.metric("CLUSTER", selected_cluster)

            with middle:
                st.metric("RISK SCORE", f"{score:.3f}")

            with right:
                if final_action == "RELEASE":
                    st.success("🟢 RELEASE")
                elif final_action == "HOLD_FOR_VERIFICATION":
                    st.warning("🟡 VERIFY")
                else:
                    st.error("🔴 BLOCK BONUS")

            # Decision pipeline
            st.markdown("### Decision Pipeline")

            p1, p2, p3, p4 = st.columns(4)

            with p1:
                st.info(f"**ML RISK**\n\n{score:.3f}")

            with p2:
                st.warning(
                    f"**MODEL ACTION**\n\n{initial_action}"
                    if initial_action == "HOLD_FOR_VERIFICATION"
                    else f"**MODEL ACTION**\n\n{initial_action}"
                )

            with p3:
                if checks_passed is None:
                    st.info("**VERIFICATION**\n\nNot required")
                elif checks_passed >= 5:
                    st.success(
                        f"**VERIFICATION**\n\n{checks_passed}/7 PASS"
                    )
                else:
                    st.error(
                        f"**VERIFICATION**\n\n{checks_passed}/7 PASS"
                    )

            with p4:
                if final_action == "RELEASE":
                    st.success("**FINAL ACTION**\n\nRELEASE")
                else:
                    st.error("**FINAL ACTION**\n\nBLOCK BONUS")

            # Bonus amount
            bonus_amount = 0.0
            if "total_bonus_claimed" in row.index:
                try:
                    bonus_amount = float(row["total_bonus_claimed"])
                except Exception:
                    bonus_amount = 0.0

            st.metric("BONUS AT STAKE", money(bonus_amount))

            # ========================================================
            # EXPLAINABLE RISK CALCULATION
            # ========================================================
            st.markdown("### 🧠 Why this risk score?")
            st.caption(
                "This is the actual model evidence behind the score — not a generic AI explanation."
            )

            _imp = load_global_feature_importance()
            _top = _imp.head(5).copy() if not _imp.empty else pd.DataFrame()

            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Model", "Gradient Boosting")
                st.caption("200 trees • depth 3 • learning rate 0.08")
            with r2:
                st.metric("Model score", f"{score:.4f}")
                st.caption("Probability returned by the trained classifier")
            with r3:
                if score < 0.30:
                    _band = "LOW"
                elif score < 0.70:
                    _band = "MEDIUM"
                else:
                    _band = "HIGH"
                st.metric("Risk band", _band)
                st.caption("Policy: <0.30 release • 0.30–0.69 verify • ≥0.70 block")

            if not _top.empty:
                _top["Importance"] = _top["Global importance"].map(lambda x: f"{x:.2f}%")
                _reason_rows = []
                for _, _imp_row in _top.iterrows():
                    _name = _imp_row["Parameter"]
                    _value = row.get(_name, "N/A")
                    try:
                        _value = f"{float(_value):.4f}"
                    except Exception:
                        _value = str(_value)
                    _reason_rows.append({
                        "Model-important parameter": _name,
                        "Global importance": _imp_row["Importance"],
                        "This cluster": _value,
                    })
                st.dataframe(
                    pd.DataFrame(_reason_rows),
                    use_container_width=True,
                    hide_index=True,
                )

            st.info(
                "Important: Gradient Boosting does not have a single fixed weight per parameter. "
                "The percentages above are global feature importance across the trained tree ensemble; "
                "the observed values are the real inputs for this cluster."
            )

            # Existing detailed explanation panel.
            render_risk_reasoning(row, score, initial_action)

            # Verification evidence
            if checks:
                st.markdown("### 🤖 Automated Verification Evidence")

                labels = {
                    "post_signup_activity": "Post-signup activity",
                    "sustained_activity": "Sustained activity",
                    "meaningful_transaction_value": "Meaningful transaction value",
                    "engagement_presence": "Engagement presence",
                    "payment_instrument_diversity": "Payment instrument diversity",
                    "device_diversity": "Device diversity",
                    "ip_diversity": "IP diversity",
                }

                for key, item in checks.items():
                    c1, c2, c3 = st.columns([2, 3, 1])

                    with c1:
                        st.write(labels.get(key, key))

                    with c2:
                        val = float(item["value"])
                        threshold = float(item["threshold"])

                        if "diversity" in key or "engagement" in key:
                            display = f"{val:.1%}"
                            progress = min(max(val, 0), 1)
                        else:
                            display = f"{val:.2f}"
                            progress = min(
                                max(val / max(threshold, 1.0), 0),
                                1,
                            )

                        st.progress(
                            progress,
                            text=f"{display} | threshold {threshold:g}",
                        )

                    with c3:
                        if item["passed"]:
                            st.success("PASS")
                        else:
                            st.error("FAIL")

            # Model evidence
            st.markdown("### 🔎 Why the Model Flagged This Cluster")

            explanation_columns = [
                ("instrument_reuse_ratio", "Payment Instrument Reuse"),
                ("cluster_size", "Cluster Size"),
                ("n_referral_edges", "Referral Edges"),
                ("device_reuse_ratio", "Device Reuse"),
            ]

            for column, label in explanation_columns:
                if column in row.index:
                    try:
                        val = float(row[column])
                    except Exception:
                        continue

                    c1, c2 = st.columns([2, 3])

                    with c1:
                        st.write(label)

                    with c2:
                        if "reuse" in column:
                            st.progress(
                                min(max(val, 0), 1),
                                text=f"{val:.1%}",
                            )
                        else:
                            st.progress(
                                min(max(val / 20, 0), 1),
                                text=f"{val:.2f}",
                            )

            # Groq explanation
            st.markdown("### 🧠 Cluster-Level AI Risk Analyst")

            st.caption(
                "Groq explains the existing ML + policy decision. "
                "It does not control the fraud decision. Evidence is taken "
                "from the selected cluster's actual feature row."
            )

            if st.button(
                "Generate AI Explanation",
                type="primary",
                key="generate_groq_explanation",
            ):
                with st.spinner("Generating evidence-based explanation..."):
                    explanation = generate_groq_explanation(
                        row,
                        initial_action,
                        final_action,
                        checks,
                    )

                st.session_state["groq_explanation"] = explanation
                st.session_state["groq_explanation_cluster"] = (
                    selected_cluster
                )

            if (
                st.session_state.get("groq_explanation")
                and st.session_state.get("groq_explanation_cluster")
                == selected_cluster
            ):
                st.info(st.session_state["groq_explanation"])

    else:
        st.warning("No scored clusters found. Run the pipeline first.")
    st.divider()

elif active_section == "🗃️ Data & Referral Graph":
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#e9f6ee,#eaf8f1);border:1px solid #bbf7d0;border-radius:18px;padding:18px 20px;margin:4px 0 18px 0;">
          <div style="font-size:1.55rem;font-weight:800;color:#0f172a;">🗃️ Data & Referral Graph</div>
          <div style="color:#475569;margin-top:4px;">Evidence workspace • inspect datasets, Razorpay test events and the referral network.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.header("🗃️ Evidence Data")
    st.caption(
        "Everything below is read from the project's generated datasets and "
        "Razorpay Test Mode event log — not invented dashboard values."
    )

    # Dataset counts
    count_cols = st.columns(5)

    data_counts = [
        ("Users", len(users)),
        ("Referral edges", len(referrals)),
        ("Payments", len(payments)),
        ("Clusters", len(features)),
        ("Test-set rows", int(metrics.get("metrics_at_default_threshold", {}).get("test_set_size", 0))),
    ]

    for col, (label, count) in zip(count_cols, data_counts):
        with col:
            st.metric(label, f"{count:,}")

    # Two useful tabs: actual transaction records + raw referral evidence.
    data_tab, tx_tab, graph_tab = st.tabs([
        "📦 Dataset",
        "💳 Test Transactions",
        "🕸️ Referral Graph",
    ])

    with data_tab:
        st.markdown("#### Raw generated data")

        dataset_name = st.selectbox(
            "Choose a dataset to inspect",
            [
                "Users",
                "Referrals",
                "Payments",
                "Cluster features",
                "Risk scores",
            ],
            key="dataset_inspector_final",
        )

        dataset_map = {
            "Users": users,
            "Referrals": referrals,
            "Payments": payments,
            "Cluster features": features,
            "Risk scores": scores,
        }

        inspect_df = dataset_map[dataset_name]

        if not inspect_df.empty:
            st.dataframe(
                inspect_df.head(30),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                f"Showing the first 30 rows of {len(inspect_df):,} total rows."
            )
        else:
            st.warning(f"{dataset_name} is not available.")

    with tx_tab:
        st.markdown("#### 💳 Payment / bonus transaction evidence")

        if not payments.empty:
            tx_df = payments.copy()

            # Attach the graph cluster so the transaction can be traced back
            # to the referral graph.
            if not users.empty and not graph_cluster_map.empty:
                cluster_lookup = graph_cluster_map.rename("graph_cluster_id").reset_index()
                cluster_lookup.columns = ["user_id", "graph_cluster_id"]
                tx_df = tx_df.merge(cluster_lookup, on="user_id", how="left")

            show_cols = [
                c for c in [
                    "payment_id",
                    "user_id",
                    "graph_cluster_id",
                    "instrument_id",
                    "amount",
                    "purpose",
                    "created_ts",
                    "method",
                ]
                if c in tx_df.columns
            ]

            st.dataframe(
                tx_df.sort_values("created_ts", ascending=False).head(25)[show_cols],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "These are the project's synthetic payment/bonus transaction records. "
                "They are separate from the live Razorpay Test Mode payment used to prove the webhook path."
            )
        else:
            st.warning("data/payments.csv not found.")

        st.markdown("#### 🔴 Razorpay Test Mode events")

        if webhook_events:
            event_rows = []
            for event in webhook_events[-20:][::-1]:
                event_rows.append({
                    "Event": event.get("event", ""),
                    "Payment ID": event.get("payment_id", ""),
                    "Method": event.get("method", ""),
                    "Received": event.get("received", ""),
                    "Signature verified": event.get("signature_verified", ""),
                })

            st.dataframe(
                pd.DataFrame(event_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No webhook_events.jsonl found yet. The Razorpay Test Mode webhook "
                "section will populate after another payment.captured event."
            )

        if razorpay_mapping:
            st.caption(
                f"Merchant-side demo mapping contains {len(razorpay_mapping)} payment → cluster link(s)."
            )

    with graph_tab:
        st.markdown("#### 🕸️ Complete referral-network graph")
        st.caption(
            "All 6,315 users are shown. Nodes are separated using the dataset's cluster_type: "
            "FRAUD_RING, FAMILY_FRIEND and ORGANIC_SINGLE. Referral edges come from users.csv. "
            "Payment activity and model risk are attached to node hover details."
        )

        fraud_users = int((users.get("cluster_type", pd.Series(dtype=object)) == "FRAUD_RING").sum())
        friend_users = int((users.get("cluster_type", pd.Series(dtype=object)) == "FAMILY_FRIEND").sum())
        organic_users = int((users.get("cluster_type", pd.Series(dtype=object)) == "ORGANIC_SINGLE").sum())

        a, b, c, d = st.columns(4)
        a.metric("All users", f"{len(users):,}")
        b.metric("🚨 Fraudsters", f"{fraud_users:,}")
        c.metric("👥 Friends / Family", f"{friend_users:,}")
        d.metric("👤 Organic", f"{organic_users:,}")

        if not users.empty and referral_graph.number_of_nodes() > 0:
            global_fig = complete_referral_graph_figure(
                users, payments, scores, referral_graph
            )
            if global_fig is not None:
                st.plotly_chart(
                    global_fig,
                    use_container_width=True,
                    key="complete_referral_network_graph",
                )

            st.info(
                "🚨 Red = fraudsters | 👥 Green = friends/family | 👤 Gray = organic users. "
                "Hover any node to inspect its cluster, risk score, referrals, payments, "
                "device, IP, payment instrument and bonus."
            )

            st.markdown("#### 🔍 Zoom into one cluster")
            cluster_options = (
    sorted(
        users["cluster_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    if "cluster_id" in users.columns
    else []
)
            if cluster_options:
                graph_choice = st.selectbox(
                    "Choose a cluster",
                    cluster_options,
                    index=cluster_options.index("comp_1653") if "comp_1653" in cluster_options else 0,
                    key="graph_cluster_selector",
                )
                focused_fig = referral_graph_figure(users, referral_graph, graph_choice)
                if focused_fig is not None:
                    st.plotly_chart(focused_fig, use_container_width=True, key="focused_referral_network_graph")

                members = users[users["cluster_id"].astype(str) == str(graph_choice)].copy()
                if not members.empty:
                    member_cols = [c for c in [
                        "user_id", "cluster_type", "referred_by", "device_id", "signup_ip",
                        "payment_instrument_id", "bonus_amount_claimed", "num_txn_post_signup",
                        "total_txn_value_post_signup", "active_days_post_signup"
                    ] if c in members.columns]
                    st.dataframe(members[member_cols], use_container_width=True, hide_index=True)
        else:
            st.info("users.csv / referral data is not available.")

elif active_section == "🧠 Autonomous Policy":
    # ============================================================
    # POLICY
    # ============================================================

    st.header("🧠 Autonomous Policy")

    p1, p2, p3 = st.columns(3)

    with p1:

        st.success(
            "🟢 LOW RISK"
        )

        st.markdown(
            "**Risk < 0.30**"
        )

        st.write(
            "Automatically release bonus."
        )


    with p2:

        st.warning(
            "🟡 MEDIUM RISK"
        )

        st.markdown(
            "**0.30 ≤ Risk < 0.70**"
        )

        st.write(
            "Run secondary automated verification."
        )


    with p3:

        st.error(
            "🔴 HIGH RISK"
        )

        st.markdown(
            "**Risk ≥ 0.70**"
        )

        st.write(
            "Automatically block bonus."
        )


    st.divider()



elif active_section == "📊 Model Performance":
    # ============================================================
    # MODEL PERFORMANCE
    # ============================================================

    st.header("📊 Held-Out Test Performance")

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            "Precision",
            f"{precision:.3f}",
        )

    with m2:
        st.metric(
            "Recall",
            f"{recall:.3f}",
        )

    with m3:
        st.metric(
            "F1",
            f"{f1:.3f}",
        )

    with m4:
        st.metric(
            "ROC-AUC",
            f"{roc_auc:.3f}",
        )

    st.caption(
        "Metrics are from the held-out synthetic test set."
    )



elif active_section == "📈 Risk Distribution":
    # ============================================================
    # RISK DISTRIBUTION
    # ============================================================

    if not scores.empty:

        st.header("📈 Risk Distribution")

        chart_df = scores.copy()

        chart_df["decision"] = (
            chart_df["risk_score"]
            .apply(risk_label)
        )

        fig = px.histogram(
            chart_df,
            x="risk_score",
            color="decision",
            nbins=30,
            title="Cluster Risk Scores",
        )

        fig.update_layout(
            xaxis_title="Risk Score",
            yaxis_title="Number of Clusters",
            legend_title="Decision",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )



elif active_section == "🔗 Ring Signals":
    # ============================================================
    # FRAUD-RING SIGNALS
    # ============================================================

    if not features.empty:

        st.header("🔗 Referral-Ring Signals")

        graph_cols = [
            "cluster_size",
            "n_referral_edges",
            "device_reuse_ratio",
            "ip_reuse_ratio",
            "instrument_reuse_ratio",
        ]

        available_cols = [
            c
            for c in graph_cols
            if c in features.columns
        ]

        if available_cols:

            signal_df = features[
                available_cols
            ].describe().T

            signal_df = signal_df[
                ["mean", "min", "max"]
            ]

            signal_df.columns = [
                "Average",
                "Minimum",
                "Maximum",
            ]

            st.dataframe(
                signal_df.round(3),
                use_container_width=True,
            )


elif active_section == "📜 Audit Trail":

    # ============================================================
    # RECENT AUDIT TRAIL
    # ============================================================

    st.header("📜 Autonomous Audit Trail")

    if audit:

        audit_rows = []

        _audit_imp = load_global_feature_importance()
        _audit_top = (
            _audit_imp.head(3)["Parameter"].tolist()
            if not _audit_imp.empty else []
        )

        for record in audit[-15:]:
            _cid = str(record.get("cluster_id", ""))
            _risk_raw = record.get("risk_score", "")
            try:
                _risk = float(_risk_raw)
                _risk_text = f"{_risk:.4f}"
            except Exception:
                _risk = None
                _risk_text = str(_risk_raw)

            # Pull the actual feature values for the audited cluster.
            _cluster_row = pd.DataFrame()
            if not features.empty and "cluster_id" in features.columns:
                _cluster_row = features[
                    features["cluster_id"].astype(str) == _cid
                ]

            _factor_parts = []
            if not _cluster_row.empty:
                _rr = _cluster_row.iloc[0]
                for _name in _audit_top:
                    if _name in _rr.index:
                        try:
                            _factor_parts.append(
                                f"{_name}={float(_rr[_name]):.3f}"
                            )
                        except Exception:
                            _factor_parts.append(f"{_name}={_rr[_name]}")

            if _risk is not None:
                if _risk < 0.30:
                    _band = "LOW (<0.30)"
                elif _risk < 0.70:
                    _band = "MEDIUM (0.30–0.69)"
                else:
                    _band = "HIGH (≥0.70)"
                _reason = (
                    f"{_band}; top model signals: "
                    + (", ".join(_factor_parts) if _factor_parts else "feature data unavailable")
                )
            else:
                _reason = "Risk score unavailable; see source audit record."

            audit_rows.append(
                {
                    "Timestamp": record.get("timestamp", ""),
                    "Cluster": _cid,
                    "Action": record.get(
                        "action",
                        record.get("decision", ""),
                    ),
                    "Risk": _risk_text,
                    "Why / key evidence": _reason,
                    "Policy": record.get("policy_version", "1.1-autonomous"),
                }
            )

        audit_df = pd.DataFrame(
            audit_rows
        )

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No audit records available yet."
        )


elif active_section == "💰 Bonus Protection":
    # ============================================================
    # MONEY MOVEMENT
    # ============================================================

    st.header("💰 Bonus Protection")

    _total_bonus_exposure = (
        float(features["total_bonus_claimed"].sum())
        if not features.empty and "total_bonus_claimed" in features.columns
        else 0.0
    )
    _blocked_exposure_pct = (
        blocked_money / _total_bonus_exposure * 100.0
        if _total_bonus_exposure > 0 else 0.0
    )

    # Percentage is deliberately the headline metric for the pitch.
    bp1, bp2, bp3 = st.columns(3)
    with bp1:
        st.metric("BONUS EXPOSURE BLOCKED", money(blocked_money))
    with bp2:
        st.metric("EXPOSURE PROTECTED", f"{_blocked_exposure_pct:.1f}%")
    with bp3:
        st.metric("TOTAL BONUS EXPOSURE", money(_total_bonus_exposure))

    st.caption(
        "The percentage is blocked referral-bonus exposure ÷ total synthetic referral-bonus exposure."
    )

    _illustrative_1cr = 10_000_000 * _blocked_exposure_pct / 100.0
    st.info(
        f"Illustrative scale: if a merchant spent ₹1 crore on referral bonuses, "
        f"the same {_blocked_exposure_pct:.1f}% protection rate would correspond to "
        f"about ₹{_illustrative_1cr:,.0f} of exposure protected. "
        "This is a scenario estimate, not a claim about any real company's spend."
    )

    b1, b2 = st.columns(2)

    with b1:

        st.metric(
            "Bonus Exposure Blocked",
            money(blocked_money),
        )

        st.caption(
            "Synthetic/test-mode exposure prevented "
            "by autonomous policy."
        )

    with b2:

        st.metric(
            "Bonus Released / Simulated",
            money(released_money),
        )

        st.caption(
            "Approved bonus payouts are simulated "
            "because this dashboard is configured for Razorpay Test Mode / dry-run payouts."
        )


    st.caption("Approved payouts are simulated in this demo; no real money moves.")

st.divider()
st.caption("Abuse-Ring Sentinel • Policy 1.1-autonomous • Defense-only • Razorpay Test Mode")
st.caption("No real payment was blocked or transferred by this demo.")
