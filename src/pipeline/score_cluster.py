"""
score_cluster.py

Autonomous end-to-end decision pipeline for Abuse-Ring Sentinel.

Flow:
    engineered features
        ↓
    ML fraud-ring probability
        ↓
    bounded policy engine
        ↓
    RELEASE / HOLD_FOR_VERIFICATION / BLOCK_BONUS
        ↓
    explainable audit trail

The system is strictly defense-only.

Actions:
    RELEASE
        Low-risk referral. Bonus can be released automatically.

    HOLD_FOR_VERIFICATION
        Ambiguous risk. Bonus is automatically held while the system
        performs additional verification checks. No human approval is
        required in the normal workflow.

    BLOCK_BONUS
        High-confidence abuse-ring risk. The referral bonus is
        automatically blocked according to the configured policy.

All decisions are reversible through the audit trail and are logged
with the model score, reasons, policy version, and bonus value.
"""

import json
import os
import time
from dataclasses import dataclass, asdict

import joblib
import numpy as np
import pandas as pd

from src.model.train_eval import FEATURE_COLS


# ============================================================
# Configuration
# ============================================================

AUDIT_LOG_PATH = "reports/audit_log.jsonl"

POLICY_VERSION = "1.0-autonomous"

# Bounded decision thresholds.
#
# LOW:
#     risk < 0.30
#     Automatically release the referral bonus.
#
# MEDIUM:
#     0.30 <= risk < 0.70
#     Automatically hold and verify.
#
# HIGH:
#     risk >= 0.70
#     Automatically block the bonus.

LOW_RISK_THRESHOLD = 0.30
HIGH_RISK_THRESHOLD = 0.70


# ============================================================
# Result object
# ============================================================

@dataclass
class ScoringResult:
    cluster_id: str
    risk_score: float

    # RELEASE | HOLD_FOR_VERIFICATION | BLOCK_BONUS
    action: str

    # Human-readable explanation of why the model considers
    # the cluster risky.
    top_reasons: list

    cluster_size: int
    total_bonus_at_stake: float

    # Records exactly which policy produced the decision.
    policy_version: str

    # Timestamp for the immutable audit event.
    timestamp: float


# ============================================================
# Autonomous cluster scorer
# ============================================================

class ClusterScorer:

    def __init__(
        self,
        model_path: str = "reports/fraud_ring_model.joblib",
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No trained model at {model_path}. "
                "Run `python src/model/train_eval.py` first."
            )

        self.model = joblib.load(model_path)

    # --------------------------------------------------------
    # Explainability
    # --------------------------------------------------------

    def _top_reasons(
        self,
        feature_row: pd.Series,
        n: int = 4,
    ) -> list:
        """
        Produce a lightweight explanation using the trained
        model's global feature importances.

        This intentionally avoids introducing SHAP or another
        dependency at this stage.
        """

        importances = dict(
            zip(
                FEATURE_COLS,
                self.model.feature_importances_,
            )
        )

        reasons = []

        for col in FEATURE_COLS:
            value = feature_row.get(col, 0)

            if pd.isna(value):
                value = 0

            weight = importances.get(col, 0)

            reasons.append(
                (
                    col,
                    value,
                    weight,
                )
            )

        # Highest model importance first.
        reasons.sort(
            key=lambda x: -x[2]
        )

        top = reasons[:n]

        return [
            {
                "feature": feature,
                "value": round(float(value), 3),
                "model_importance": round(
                    float(importance),
                    4,
                ),
            }
            for feature, value, importance in top
        ]

    # --------------------------------------------------------
    # Autonomous policy engine
    # --------------------------------------------------------

    def _decide_action(
        self,
        risk: float,
    ) -> str:
        """
        Convert the ML probability into a bounded autonomous
        business action.

        IMPORTANT:
        The model predicts risk.
        The policy engine decides what the system is allowed
        to do with that prediction.

        This separation makes the system easier to audit.
        """

        if risk >= HIGH_RISK_THRESHOLD:
            return "BLOCK_BONUS"

        if risk >= LOW_RISK_THRESHOLD:
            return "HOLD_FOR_VERIFICATION"

        return "RELEASE"

    # --------------------------------------------------------
    # Main scoring function
    # --------------------------------------------------------

    def score(
        self,
        cluster_row: pd.Series,
    ) -> ScoringResult:

        # Explicitly fill missing values before constructing
        # the model input. This also avoids the pandas warning
        # produced by the previous implementation.
        feature_values = (
            cluster_row[FEATURE_COLS]
            .copy()
            .fillna(0)
        )

        X = feature_values.to_frame().T

        # ML probability that this cluster is a fraud ring.
        risk = float(
            self.model.predict_proba(X)[0, 1]
        )

        # Autonomous policy decision.
        action = self._decide_action(risk)

        result = ScoringResult(
            cluster_id=str(
                cluster_row.get(
                    "cluster_id",
                    "unknown",
                )
            ),

            risk_score=round(
                risk,
                4,
            ),

            action=action,

            top_reasons=self._top_reasons(
                cluster_row
            ),

            cluster_size=int(
                cluster_row.get(
                    "cluster_size",
                    0,
                )
            ),

            total_bonus_at_stake=float(
                cluster_row.get(
                    "total_bonus_claimed",
                    0,
                )
            ),

            policy_version=POLICY_VERSION,

            timestamp=time.time(),
        )

        # Every autonomous decision is audited.
        self._log_audit(result)

        return result

    # --------------------------------------------------------
    # Append-only audit trail
    # --------------------------------------------------------

    def _log_audit(
        self,
        result: ScoringResult,
    ):
        os.makedirs(
            os.path.dirname(
                AUDIT_LOG_PATH
            ),
            exist_ok=True,
        )

        with open(
            AUDIT_LOG_PATH,
            "a",
            encoding="utf-8",
        ) as f:

            f.write(
                json.dumps(
                    asdict(result),
                    ensure_ascii=False,
                )
                + "\n"
            )


# ============================================================
# Score every cluster
# ============================================================

def score_all_clusters(
    features_path: str = "data/cluster_features.csv",
) -> pd.DataFrame:

    df = pd.read_csv(
        features_path
    )

    scorer = ClusterScorer()

    results = [
        scorer.score(row)
        for _, row in df.iterrows()
    ]

    return pd.DataFrame(
        [
            asdict(result)
            for result in results
        ]
    )


# ============================================================
# CLI entry point
# ============================================================

if __name__ == "__main__":

    results = score_all_clusters()

    action_counts = (
        results["action"]
        .value_counts()
    )

    print(
        "\nAutonomous decision distribution:"
    )

    print(action_counts)

    # Anything other than RELEASE means the system
    # prevented immediate bonus release.
    held_value = (
        results[
            results["action"] != "RELEASE"
        ]["total_bonus_at_stake"]
        .sum()
    )

    blocked_value = (
        results[
            results["action"] == "BLOCK_BONUS"
        ]["total_bonus_at_stake"]
        .sum()
    )

    verification_value = (
        results[
            results["action"]
            == "HOLD_FOR_VERIFICATION"
        ]["total_bonus_at_stake"]
        .sum()
    )

    released_value = (
        results[
            results["action"] == "RELEASE"
        ]["total_bonus_at_stake"]
        .sum()
    )

    print(
        f"\nBonus released automatically: "
        f"INR {released_value:,.2f}"
    )

    print(
        f"Bonus held automatically: "
        f"INR {held_value:,.2f}"
    )

    print(
        f"  - Verification holds: "
        f"INR {verification_value:,.2f}"
    )

    print(
        f"  - Fraud blocks: "
        f"INR {blocked_value:,.2f}"
    )

    print(
        "\nFull scores -> "
        "reports/cluster_risk_scores.csv"
    )

    results.to_csv(
        "reports/cluster_risk_scores.csv",
        index=False,
        encoding="utf-8",
    )

    print(
        "Audit trail -> "
        "reports/audit_log.jsonl"
    )

    print(
        "\nAUTONOMOUS POLICY:"
    )

    print(
        f"  risk < {LOW_RISK_THRESHOLD:.2f}"
        "  -> RELEASE"
    )

    print(
        f"  {LOW_RISK_THRESHOLD:.2f} <= risk < "
        f"{HIGH_RISK_THRESHOLD:.2f}"
        " -> HOLD_FOR_VERIFICATION"
    )

    print(
        f"  risk >= {HIGH_RISK_THRESHOLD:.2f}"
        " -> BLOCK_BONUS"
    )