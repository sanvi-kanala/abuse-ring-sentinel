"""
build_features.py

Turns raw users/referrals/payments into one feature row per referral cluster
(a root referrer + everyone they, directly or transitively, brought in).
Singletons with no referrals form their own trivial "cluster" of size 1.

The features are deliberately split into two families:

  1. GRAPH features   - shape of the referral tree itself.
  2. BEHAVIORAL/IDENTITY features - device, IP, payment-instrument reuse,
     KYC address overlap, and post-signup engagement.

None of these features individually prove fraud — a big family WhatsApp
group referring each other in one afternoon can look "bursty" too. The
model has to weigh the combination, which is exactly why this is a
learned classifier rather than a hand-written rule.
"""
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime


def load_raw(data_dir="data"):
    users = pd.read_csv(f"{data_dir}/users.csv")
    users["signup_ts"] = pd.to_datetime(users["signup_ts"], format="mixed")
    referrals = pd.read_csv(f"{data_dir}/referrals.csv") if _has_rows(f"{data_dir}/referrals.csv") else pd.DataFrame(
        columns=["referrer_id", "referee_id", "cluster_id"])
    payments = pd.read_csv(f"{data_dir}/payments.csv")
    return users, referrals, payments


def _has_rows(path):
    import os
    if not os.path.exists(path):
        return False
    with open(path) as f:
        lines = f.readlines()
    return len(lines) > 1


def build_referral_graph(users: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, row in users.iterrows():
        g.add_node(row["user_id"])
    for _, row in users.iterrows():
        if isinstance(row["referred_by"], str) and row["referred_by"]:
            g.add_edge(row["referred_by"], row["user_id"])
    return g


def assign_cluster_ids(users: pd.DataFrame, g: nx.DiGraph) -> pd.DataFrame:
    """Weakly-connected components of the referral graph define our clusters.
    A user with no referral connections at all is their own cluster of 1."""
    ug = g.to_undirected()
    comp_map = {}
    for i, comp in enumerate(nx.connected_components(ug)):
        for node in comp:
            comp_map[node] = f"comp_{i}"
    users = users.copy()
    users["graph_cluster_id"] = users["user_id"].map(comp_map)
    return users


def cluster_features(cluster_id, member_ids, users: pd.DataFrame, g: nx.DiGraph) -> dict:
    sub = users[users["user_id"].isin(member_ids)]
    n = len(sub)
    subg = g.subgraph(member_ids)

    # ---- graph shape ----
    n_edges = subg.number_of_edges()
    depth = 0
    if n > 1:
        roots = [nd for nd in subg.nodes if subg.in_degree(nd) == 0]
        if roots:
            depth = max(
                (max(nx.single_source_shortest_path_length(subg, r).values()) for r in roots),
                default=0,
            )
    density = n_edges / (n * (n - 1)) if n > 1 else 0.0
    max_out_degree = max((d for _, d in subg.out_degree()), default=0)
    fan_out_ratio = max_out_degree / n if n > 0 else 0.0  # one node referring almost everyone

    # ---- timing / burst signal ----
    ts = sub["signup_ts"].sort_values()
    span_hours = (ts.max() - ts.min()).total_seconds() / 3600.0 if n > 1 else 0.0
    signups_per_hour = n / span_hours if span_hours > 0.01 else float(n)  # cap handled below
    signups_per_hour = min(signups_per_hour, 500.0)

    # ---- device / IP / instrument reuse (identity-farming signal) ----
    n_unique_devices = sub["device_id"].nunique()
    n_unique_ips = sub["signup_ip"].nunique()
    n_unique_instruments = sub["payment_instrument_id"].nunique()
    n_unique_addr = sub["kyc_address_hash"].nunique()

    device_reuse_ratio = 1 - (n_unique_devices / n)
    ip_reuse_ratio = 1 - (n_unique_ips / n)
    instrument_reuse_ratio = 1 - (n_unique_instruments / n)
    addr_concentration_ratio = 1 - (n_unique_addr / n)

    # most-shared instrument's share of the cluster (a single card used by
    # everyone is a much stronger tell than two people sharing one)
    top_instrument_share = sub["payment_instrument_id"].value_counts(normalize=True).iloc[0] if n > 0 else 0.0
    top_device_share = sub["device_id"].value_counts(normalize=True).iloc[0] if n > 0 else 0.0

    # ---- post-signup engagement (claim-and-churn signal) ----
    avg_txn_post = sub["num_txn_post_signup"].mean()
    avg_txn_value_post = sub["total_txn_value_post_signup"].mean()
    avg_active_days = sub["active_days_post_signup"].mean()
    pct_zero_engagement = (sub["num_txn_post_signup"] == 0).mean()

    # ---- bonus economics ----
    total_bonus_claimed = sub["bonus_amount_claimed"].sum()
    avg_bonus = sub["bonus_amount_claimed"].mean()

    return {
        "cluster_id": cluster_id,
        "cluster_size": n,
        "n_referral_edges": n_edges,
        "referral_tree_depth": depth,
        "graph_density": density,
        "fan_out_ratio": fan_out_ratio,
        "signup_span_hours": span_hours,
        "signups_per_hour": signups_per_hour,
        "n_unique_devices": n_unique_devices,
        "n_unique_ips": n_unique_ips,
        "n_unique_instruments": n_unique_instruments,
        "device_reuse_ratio": device_reuse_ratio,
        "ip_reuse_ratio": ip_reuse_ratio,
        "instrument_reuse_ratio": instrument_reuse_ratio,
        "addr_concentration_ratio": addr_concentration_ratio,
        "top_instrument_share": top_instrument_share,
        "top_device_share": top_device_share,
        "avg_txn_post_signup": avg_txn_post,
        "avg_txn_value_post_signup": avg_txn_value_post,
        "avg_active_days_post_signup": avg_active_days,
        "pct_zero_engagement": pct_zero_engagement,
        "total_bonus_claimed": total_bonus_claimed,
        "avg_bonus_claimed": avg_bonus,
        # ground truth, kept ONLY for labeling/eval — never fed to the model as a feature
        "_true_cluster_type": sub["cluster_type"].mode().iloc[0],
    }


def inject_measurement_noise(df: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    """Real production signals are never as clean as a synthetic generator's
    ground truth: IP geolocation is fuzzy, device fingerprints collide by
    chance on shared public wifi, engagement logging has gaps. We add
    bounded noise so the classifier faces genuine class overlap rather than
    a suspiciously perfect separation — which is what makes the metrics in
    reports/metrics.json honest instead of a synthetic-data artifact."""
    rng = np.random.default_rng(seed)
    df = df.copy()

    ratio_cols = ["device_reuse_ratio", "ip_reuse_ratio", "instrument_reuse_ratio",
                  "addr_concentration_ratio", "top_instrument_share", "top_device_share",
                  "graph_density", "fan_out_ratio", "pct_zero_engagement"]
    for col in ratio_cols:
        noise = rng.normal(0, 0.16, size=len(df))
        df[col] = (df[col] + noise).clip(0, 1)

    count_noise_cols = ["signups_per_hour", "avg_txn_post_signup", "avg_active_days_post_signup"]
    for col in count_noise_cols:
        mult = rng.lognormal(mean=0, sigma=0.35, size=len(df))
        df[col] = (df[col] * mult).clip(lower=0)

    money_cols = ["total_bonus_claimed", "avg_bonus_claimed", "avg_txn_value_post_signup"]
    for col in money_cols:
        mult = rng.lognormal(mean=0, sigma=0.10, size=len(df))
        df[col] = (df[col] * mult).clip(lower=0)

    return df


def build_cluster_feature_table(data_dir="data") -> pd.DataFrame:
    users, referrals, payments = load_raw(data_dir)
    g = build_referral_graph(users)
    users = assign_cluster_ids(users, g)

    rows = []
    for cluster_id, grp in users.groupby("graph_cluster_id"):
        member_ids = set(grp["user_id"])
        rows.append(cluster_features(cluster_id, member_ids, users, g))

    df = pd.DataFrame(rows)
    df = inject_measurement_noise(df)
    # Binary label: fraud ring vs everything else (family/friend groups AND
    # organic singles are both legitimate — the model must not punish either).
    df["label_fraud"] = (df["_true_cluster_type"] == "FRAUD_RING").astype(int)
    return df


if __name__ == "__main__":
    feats = build_cluster_feature_table()
    feats.to_csv("data/cluster_features.csv", index=False)
    print(feats["_true_cluster_type"].value_counts())
    print(f"\nTotal clusters: {len(feats)}")
    print(f"Saved to data/cluster_features.csv")
