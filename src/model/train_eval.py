"""
train_eval.py

Trains a gradient-boosted classifier to flag fraud-ring clusters, then
reports HONEST metrics on a held-out test set — including the business
cost of false positives (holding a legitimate family/friend group's bonus)
versus false negatives (paying out a bonus to a fraud ring).

This directly targets the buildathon's Track 02 bar: "Honest metrics
including false-positive cost."
"""
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report, precision_recall_curve,
)
import joblib

FEATURE_COLS = [
    "cluster_size", "n_referral_edges", "referral_tree_depth", "graph_density",
    "fan_out_ratio", "signup_span_hours", "signups_per_hour",
    "n_unique_devices", "n_unique_ips", "n_unique_instruments",
    "device_reuse_ratio", "ip_reuse_ratio", "instrument_reuse_ratio",
    "addr_concentration_ratio", "top_instrument_share", "top_device_share",
    "avg_txn_post_signup", "avg_txn_value_post_signup",
    "avg_active_days_post_signup", "pct_zero_engagement",
    "total_bonus_claimed", "avg_bonus_claimed",
]

# ---- business cost assumptions (INR), configurable ----
# Cost of a false positive = friction cost of wrongly holding a genuine
# family/friend group's bonus: support tickets, manual review time, user
# trust/churn risk. Cost of a false negative = the fraud bonus actually
# paid out, uncapped since rings often re-run the same trick.
COST_PER_FALSE_POSITIVE = 150     # ops + goodwill cost per wrongly-held legit cluster
COST_PER_FALSE_NEGATIVE_MULTIPLIER = 1.0  # multiplied by that cluster's total_bonus_claimed


def load_features(path="data/cluster_features.csv"):
    return pd.read_csv(path)


def split(df, test_size=0.25, random_state=42):
    # Only clusters with size > 1 are meaningful referral clusters; pure
    # organic singles (size==1, never fraud) are folded in as negative
    # examples so the model also learns not to flag the ordinary baseline.
    X = df[FEATURE_COLS].fillna(0)
    y = df["label_fraud"]
    return train_test_split(X, y, df, test_size=test_size, random_state=random_state,
                             stratify=y)


def train_model(X_train, y_train):
    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)
    return model


def evaluate(model, X_test, y_test, df_test, threshold=0.5):
    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= threshold).astype(int)

    precision = precision_score(y_test, preds, zero_division=0)
    recall = recall_score(y_test, preds, zero_division=0)
    f1 = f1_score(y_test, preds, zero_division=0)
    auc = roc_auc_score(y_test, proba)
    cm = confusion_matrix(y_test, preds).tolist()  # [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]

    # ---- false-positive cost breakdown, split by WHICH legit group got hit ----
    test_df = df_test.copy()
    test_df["pred"] = preds
    test_df["proba"] = proba

    fp_rows = test_df[(test_df["pred"] == 1) & (test_df["label_fraud"] == 0)]
    fp_family = (fp_rows["_true_cluster_type"] == "FAMILY_FRIEND").sum()
    fp_organic = (fp_rows["_true_cluster_type"] == "ORGANIC_SINGLE").sum()

    fn_rows = test_df[(test_df["pred"] == 0) & (test_df["label_fraud"] == 1)]
    money_missed = fn_rows["total_bonus_claimed"].sum() * COST_PER_FALSE_NEGATIVE_MULTIPLIER
    money_correctly_blocked = test_df[(test_df["pred"] == 1) & (test_df["label_fraud"] == 1)][
        "total_bonus_claimed"].sum()

    total_fp_cost = fp * COST_PER_FALSE_POSITIVE
    total_fn_cost = money_missed
    net_value = money_correctly_blocked - total_fp_cost  # value created by the system

    report = {
        "threshold": threshold,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "false_positive_breakdown": {
            "total_false_positives": int(fp),
            "false_positives_that_were_family_friend_groups": int(fp_family),
            "false_positives_that_were_organic_singles": int(fp_organic),
            "cost_per_false_positive_inr": COST_PER_FALSE_POSITIVE,
            "total_false_positive_cost_inr": round(total_fp_cost, 2),
        },
        "false_negative_breakdown": {
            "total_false_negatives": int(fn),
            "fraud_bonus_money_missed_inr": round(total_fn_cost, 2),
        },
        "value_created": {
            "fraud_bonus_correctly_blocked_inr": round(money_correctly_blocked, 2),
            "net_value_inr": round(net_value, 2),
            "note": "net_value = money correctly blocked from confirmed fraud rings minus "
                    "the operational/goodwill cost of false positives on legit clusters",
        },
        "classification_report": classification_report(y_test, preds, target_names=["legit", "fraud_ring"],
                                                         zero_division=0, output_dict=True),
        "test_set_size": len(y_test),
        "test_set_fraud_ring_count": int(y_test.sum()),
    }
    return report, test_df


def threshold_sweep(model, X_test, y_test, df_test):
    """Show precision/recall/cost across thresholds so the operator can pick
    an operating point that matches their actual risk appetite, rather than
    trusting a single cherry-picked cutoff."""
    proba = model.predict_proba(X_test)[:, 1]
    rows = []
    for t in np.arange(0.1, 0.95, 0.1):
        preds = (proba >= t).astype(int)
        p = precision_score(y_test, preds, zero_division=0)
        r = recall_score(y_test, preds, zero_division=0)
        cm = confusion_matrix(y_test, preds)
        tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
        rows.append({"threshold": round(t, 2), "precision": round(p, 3), "recall": round(r, 3),
                     "false_positives": int(fp), "false_negatives": int(fn),
                     "false_positive_cost_inr": int(fp) * COST_PER_FALSE_POSITIVE})
    return rows


def feature_importance(model):
    importances = model.feature_importances_
    pairs = sorted(zip(FEATURE_COLS, importances), key=lambda x: -x[1])
    return [{"feature": f, "importance": round(float(v), 4)} for f, v in pairs]


def main():
    df = load_features()
    X_train, X_test, y_train, y_test, df_train, df_test = split(df)

    model = train_model(X_train, y_train)
    report, test_df = evaluate(model, X_test, y_test, df_test)
    sweep = threshold_sweep(model, X_test, y_test, df_test)
    importance = feature_importance(model)

    full_report = {
        "model": "GradientBoostingClassifier",
        "features_used": FEATURE_COLS,
        "metrics_at_default_threshold": report,
        "threshold_sweep": sweep,
        "feature_importance": importance,
    }

    import os
    os.makedirs("reports", exist_ok=True)
    with open("reports/metrics.json", "w") as f:
        json.dump(full_report, f, indent=2)

    joblib.dump(model, "reports/fraud_ring_model.joblib")
    test_df.to_csv("reports/test_set_predictions.csv", index=False)

    print(json.dumps(report["confusion_matrix"], indent=2))
    print(f"Precision: {report['precision']}  Recall: {report['recall']}  "
          f"F1: {report['f1']}  ROC-AUC: {report['roc_auc']}")
    print(f"Net value created (test set): INR {report['value_created']['net_value_inr']}")
    print("Full report -> reports/metrics.json")
    print("Model -> reports/fraud_ring_model.joblib")


if __name__ == "__main__":
    main()
