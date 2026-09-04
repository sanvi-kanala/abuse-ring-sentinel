import pandas as pd
import networkx as nx
from src.features.build_features import cluster_features


def _mk_users(rows):
    return pd.DataFrame(rows)


def test_fraud_ring_shows_high_device_reuse():
    ts_base = pd.Timestamp("2026-01-01T00:00:00")
    rows = []
    for i in range(6):
        rows.append({
            "user_id": f"u{i}", "signup_ts": ts_base + pd.Timedelta(minutes=i * 5),
            "device_id": "dev_SHARED", "signup_ip": "1.2.3.4",
            "payment_instrument_id": "card_SHARED", "kyc_address_hash": "addr_1",
            "num_txn_post_signup": 0, "total_txn_value_post_signup": 0.0,
            "active_days_post_signup": 0, "bonus_amount_claimed": 100.0,
            "cluster_type": "FRAUD_RING",
        })
    users = _mk_users(rows)
    g = nx.DiGraph()
    g.add_nodes_from(users["user_id"])
    for i in range(1, 6):
        g.add_edge("u0", f"u{i}")

    feats = cluster_features("test_ring", set(users["user_id"]), users, g)
    assert feats["device_reuse_ratio"] > 0.8
    assert feats["instrument_reuse_ratio"] > 0.8
    assert feats["pct_zero_engagement"] == 1.0


def test_family_cluster_shows_low_reuse():
    ts_base = pd.Timestamp("2026-01-01T00:00:00")
    rows = []
    for i in range(4):
        rows.append({
            "user_id": f"u{i}", "signup_ts": ts_base + pd.Timedelta(days=i * 5),
            "device_id": f"dev_{i}", "signup_ip": f"9.9.9.{i}",
            "payment_instrument_id": f"card_{i}", "kyc_address_hash": f"addr_{i}",
            "num_txn_post_signup": 10, "total_txn_value_post_signup": 5000.0,
            "active_days_post_signup": 60, "bonus_amount_claimed": 100.0,
            "cluster_type": "FAMILY_FRIEND",
        })
    users = _mk_users(rows)
    g = nx.DiGraph()
    g.add_nodes_from(users["user_id"])
    for i in range(1, 4):
        g.add_edge("u0", f"u{i}")

    feats = cluster_features("test_fam", set(users["user_id"]), users, g)
    assert feats["device_reuse_ratio"] < 0.2
    assert feats["instrument_reuse_ratio"] < 0.2
    assert feats["pct_zero_engagement"] == 0.0
