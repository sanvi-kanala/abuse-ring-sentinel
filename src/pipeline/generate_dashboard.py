"""
generate_dashboard.py

Builds a single self-contained HTML report (reports/dashboard.html):
  1. A sample referral-graph visualization, nodes colored by ground truth
     cluster type, sized/bordered by model risk score.
  2. Precision/recall/threshold-sweep charts.
  3. Headline metrics and false-positive cost breakdown.
"""

import json
import random

import networkx as nx
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pyvis.network import Network

from src.features.build_features import (
    load_raw,
    build_referral_graph,
    assign_cluster_ids,
)


COLOR_MAP = {
    "FRAUD_RING": "#e74c3c",
    "FAMILY_FRIEND": "#2ecc71",
    "ORGANIC_SINGLE": "#95a5a6",
}


def build_sample_graph_html(
    out_path="reports/graph_sample.html",
    n_fraud=10,
    n_family=10,
):
    """Build a sample interactive referral graph."""

    users, referrals, payments = load_raw()

    # Build referral graph
    g = build_referral_graph(users)

    # Assign graph cluster IDs
    users = assign_cluster_ids(users, g)

    # Load risk scores
    risk_df = pd.read_csv(
        "reports/cluster_risk_scores.csv",
        encoding="utf-8",
    )

    # Map cluster ID -> risk score
    risk_map = dict(
        zip(
            risk_df["cluster_id"],
            risk_df["risk_score"],
        )
    )

    # Find fraud and family clusters
    fraud_clusters = users[
        users["cluster_type"] == "FRAUD_RING"
    ]["graph_cluster_id"].unique()

    family_clusters = users[
        users["cluster_type"] == "FAMILY_FRIEND"
    ]["graph_cluster_id"].unique()

    # Reproducible sampling
    random.seed(3)

    fraud_sample = random.sample(
        list(fraud_clusters),
        min(n_fraud, len(fraud_clusters)),
    )

    family_sample = random.sample(
        list(family_clusters),
        min(n_family, len(family_clusters)),
    )

    sample_ids = fraud_sample + family_sample

    # Select users belonging to sampled clusters
    sub_users = users[
        users["graph_cluster_id"].isin(sample_ids)
    ]

    node_ids = set(sub_users["user_id"])

    # Extract corresponding graph
    subg = g.subgraph(node_ids)

    # Create PyVis network
    net = Network(
        height="650px",
        width="100%",
        directed=True,
        bgcolor="#0d1117",
        font_color="white",
    )

    net.barnes_hut(
        gravity=-3000,
        spring_length=120,
    )

    # ---------------------------------------------------------
    # Add nodes
    # ---------------------------------------------------------

    for _, row in sub_users.iterrows():

        risk = risk_map.get(
            row["graph_cluster_id"],
            0.0,
        )

        color = COLOR_MAP.get(
            row["cluster_type"],
            "#3498db",
        )

        title = (
            f"{row['user_id']}<br>"
            f"type: {row['cluster_type']}<br>"
            f"cluster: {row['graph_cluster_id']}<br>"
            f"risk_score: {risk:.2f}"
        )

        size = 10 + risk * 20

        net.add_node(
            row["user_id"],
            label="",
            title=title,
            color=color,
            size=size,
        )

    # ---------------------------------------------------------
    # Add referral edges
    # ---------------------------------------------------------

    for u, v in subg.edges():

        net.add_edge(
            u,
            v,
            color="rgba(255,255,255,0.35)",
        )

    # ---------------------------------------------------------
    # Write PyVis HTML
    # ---------------------------------------------------------

    net.write_html(
        out_path,
        notebook=False,
    )

    # PyVis may reference a local utility file that isn't needed
    # for this standalone visualization.
    #
    # Read explicitly as UTF-8 so Windows does not use cp1252.

    with open(
        out_path,
        "r",
        encoding="utf-8",
    ) as f:
        html = f.read()

    # Remove unnecessary local utility reference
    html = html.replace(
        '<script src="lib/bindings/utils.js"></script>',
        "",
    )

    # Write explicitly as UTF-8
    with open(
        out_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(html)

    return out_path


def build_charts(out_dir="reports"):
    """Build evaluation charts."""

    # ---------------------------------------------------------
    # Load metrics
    # ---------------------------------------------------------

    with open(
        "reports/metrics.json",
        "r",
        encoding="utf-8",
    ) as f:
        metrics = json.load(f)

    sweep = pd.DataFrame(
        metrics["threshold_sweep"]
    )

    # ---------------------------------------------------------
    # Precision / Recall chart
    # ---------------------------------------------------------

    fig, ax1 = plt.subplots(
        figsize=(7, 4.2)
    )

    ax1.plot(
        sweep["threshold"],
        sweep["precision"],
        marker="o",
        label="Precision",
        color="#2ecc71",
    )

    ax1.plot(
        sweep["threshold"],
        sweep["recall"],
        marker="s",
        label="Recall",
        color="#3498db",
    )

    ax1.set_xlabel(
        "Decision threshold"
    )

    ax1.set_ylabel(
        "Score"
    )

    ax1.set_ylim(
        0,
        1.05,
    )

    ax1.legend(
        loc="lower left"
    )

    ax1.set_title(
        "Precision / Recall vs. threshold (held-out test set)"
    )

    fig.tight_layout()

    fig.savefig(
        f"{out_dir}/precision_recall_sweep.png",
        dpi=130,
    )

    plt.close(fig)

    # ---------------------------------------------------------
    # False-positive cost chart
    # ---------------------------------------------------------

    fig2, ax2 = plt.subplots(
        figsize=(7, 4.2)
    )

    ax2.bar(
        sweep["threshold"].astype(str),
        sweep["false_positive_cost_inr"],
        color="#e74c3c",
        alpha=0.85,
    )

    ax2.set_xlabel(
        "Decision threshold"
    )

    ax2.set_ylabel(
        "False-positive cost (INR)"
    )

    ax2.set_title(
        "Cost of false positives at each operating threshold"
    )

    fig2.tight_layout()

    fig2.savefig(
        f"{out_dir}/fp_cost_sweep.png",
        dpi=130,
    )

    plt.close(fig2)

    # ---------------------------------------------------------
    # Feature importance chart
    # ---------------------------------------------------------

    fi = pd.DataFrame(
        metrics["feature_importance"]
    ).head(10)

    fig3, ax3 = plt.subplots(
        figsize=(7, 4.5)
    )

    ax3.barh(
        fi["feature"][::-1],
        fi["importance"][::-1],
        color="#9b59b6",
    )

    ax3.set_title(
        "Top 10 feature importances"
    )

    fig3.tight_layout()

    fig3.savefig(
        f"{out_dir}/feature_importance.png",
        dpi=130,
    )

    plt.close(fig3)

    return metrics


def build_dashboard_html(
    out_path="reports/dashboard.html",
):
    """Build the final dashboard HTML."""

    # ---------------------------------------------------------
    # Build graph
    # ---------------------------------------------------------

    graph_path = build_sample_graph_html()

    # ---------------------------------------------------------
    # Build charts
    # ---------------------------------------------------------

    metrics = build_charts()

    # ---------------------------------------------------------
    # Extract metrics
    # ---------------------------------------------------------

    m = metrics[
        "metrics_at_default_threshold"
    ]

    fp = m[
        "false_positive_breakdown"
    ]

    fn = m[
        "false_negative_breakdown"
    ]

    vc = m[
        "value_created"
    ]

    # Handle Windows paths safely
    graph_filename = graph_path.replace(
        "\\",
        "/",
    ).split("/")[-1]

    # ---------------------------------------------------------
    # Dashboard HTML
    # ---------------------------------------------------------

    html = f"""<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>
Abuse-Ring Sentinel — Dashboard
</title>

<style>

body {{
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Roboto,
        sans-serif;

    background: #0d1117;
    color: #e6edf3;

    margin: 0;
    padding: 32px;
}}

h1 {{
    font-size: 26px;
    margin-bottom: 4px;
}}

h2 {{
    font-size: 18px;

    margin-top: 40px;

    border-bottom:
        1px solid #30363d;

    padding-bottom: 8px;
}}

.subtitle {{
    color: #8b949e;
    margin-bottom: 24px;
}}

.metrics-grid {{
    display: flex;

    gap: 16px;

    flex-wrap: wrap;

    margin: 20px 0;
}}

.metric-card {{
    background: #161b22;

    border:
        1px solid #30363d;

    border-radius: 10px;

    padding:
        18px 24px;

    min-width: 150px;
}}

.metric-card .value {{
    font-size: 28px;
    font-weight: 700;
}}

.metric-card .label {{
    color: #8b949e;

    font-size: 13px;

    margin-top: 4px;
}}

.legend span {{
    display: inline-block;
    margin-right: 18px;
}}

.dot {{
    display: inline-block;

    width: 10px;
    height: 10px;

    border-radius: 50%;

    margin-right: 6px;
}}

img {{
    max-width: 100%;

    border-radius: 8px;

    border:
        1px solid #30363d;

    margin: 8px 0;
}}

.charts {{
    display: flex;

    gap: 16px;

    flex-wrap: wrap;
}}

.charts img {{
    max-width: 48%;
}}

.graph-wrap {{
    background: #0d1117;

    border:
        1px solid #30363d;

    border-radius: 10px;

    overflow: hidden;
}}

code {{
    background: #161b22;

    padding:
        2px 6px;

    border-radius: 4px;
}}

</style>

</head>

<body>

<h1>
🛡️ Abuse-Ring Sentinel
</h1>

<div class="subtitle">

Referral-bonus fraud detection —
Razorpay AI Buildathon,
Track 02: AI Risk Manager

</div>


<div class="metrics-grid">

<div class="metric-card">

<div class="value">
{m['precision'] * 100:.1f}%
</div>

<div class="label">
Precision
</div>

</div>


<div class="metric-card">

<div class="value">
{m['recall'] * 100:.1f}%
</div>

<div class="label">
Recall
</div>

</div>


<div class="metric-card">

<div class="value">
{m['f1'] * 100:.1f}%
</div>

<div class="label">
F1
</div>

</div>


<div class="metric-card">

<div class="value">
{m['roc_auc']:.3f}
</div>

<div class="label">
ROC-AUC
</div>

</div>


<div class="metric-card">

<div class="value">
₹{vc['net_value_inr']:,.0f}
</div>

<div class="label">
Net value created (test set)
</div>

</div>

</div>


<h2>
Honest cost accounting
</h2>


<div class="metrics-grid">


<div class="metric-card">

<div class="value">
{fp['total_false_positives']}
</div>

<div class="label">

False positives
(₹{fp['total_false_positive_cost_inr']:,.0f}
friction cost)

</div>

</div>


<div class="metric-card">

<div class="value">
{fp['false_positives_that_were_family_friend_groups']}
</div>

<div class="label">

...of which were genuine
family/friend groups

</div>

</div>


<div class="metric-card">

<div class="value">
{fn['total_false_negatives']}
</div>

<div class="label">

False negatives
(₹{fn['fraud_bonus_money_missed_inr']:,.0f}
missed)

</div>

</div>


<div class="metric-card">

<div class="value">

₹{vc['fraud_bonus_correctly_blocked_inr']:,.0f}

</div>

<div class="label">

Fraud bonus correctly blocked

</div>

</div>


</div>


<h2>
Precision / Recall across thresholds
</h2>


<div class="charts">

<img src="precision_recall_sweep.png">

<img src="fp_cost_sweep.png">

</div>


<h2>
What the model actually keys off
</h2>


<img
    src="feature_importance.png"
    style="max-width:600px;"
>


<h2>
Sample referral graph —
fraud rings vs. genuine family/friend clusters
</h2>


<div class="legend">

<span>

<span
    class="dot"
    style="background:#e74c3c"
></span>

Fraud ring

</span>


<span>

<span
    class="dot"
    style="background:#2ecc71"
></span>

Family / friend group

</span>

</div>


<p style="color:#8b949e">

Node size scales with the model's risk score.
Hover a node for details.

Notice the fraud rings render as tight
star/burst shapes around 1-2 hubs,
while family trees sprawl with looser,
more organic branching.

</p>


<div class="graph-wrap">

<iframe
    src="{graph_filename}"
    width="100%"
    height="670"
    style="border:none; display:block;"
></iframe>

</div>


</body>

</html>
"""

    # ---------------------------------------------------------
    # IMPORTANT WINDOWS FIX
    # ---------------------------------------------------------
    #
    # Always explicitly use UTF-8.
    # The HTML contains Unicode characters such as:
    #   🛡️
    #   ₹
    #
    # Windows otherwise defaults to cp1252, which causes:
    # UnicodeEncodeError: 'charmap' codec can't encode characters

    with open(
        out_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(html)

    return out_path


if __name__ == "__main__":

    path = build_dashboard_html()

    print(
        f"Dashboard written to {path}"
    )