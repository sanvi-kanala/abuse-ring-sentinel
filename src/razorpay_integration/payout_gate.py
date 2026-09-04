"""
payout_gate.py

Autonomous referral-bonus payout gate.

Decision flow:

    Cluster features
          â†“
    ML risk scoring
          â†“
    Autonomous policy
          â†“
    RELEASE / HOLD_FOR_VERIFICATION / BLOCK_BONUS
          â†“
    Secondary verification for ambiguous cases
          â†“
    Bonus action

Safety:
- Ground-truth fields are never used for decisions.
- BLOCK_BONUS never calls the payout API.
- DRY_RUN_PAYOUTS=true prevents external payout creation.
- DRY_RUN_PAYOUTS defaults to true.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from src.pipeline.score_cluster import ClusterScorer
from src.razorpay_integration.client import RazorpayTestClient


logger = logging.getLogger(
    "abuse_ring_sentinel.payout_gate"
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

POLICY_VERSION = "1.1-autonomous"

# Safety-first default.
#
# true  -> simulate approved payouts
# false -> allow RazorpayX TEST MODE payout creation
#
# Keep this TRUE while testing.
DRY_RUN_PAYOUTS = (
    os.getenv(
        "DRY_RUN_PAYOUTS",
        "true",
    ).lower()
    == "true"
)


RELEASE_THRESHOLD = 0.30
BLOCK_THRESHOLD = 0.70


VERIFICATION_THRESHOLDS = {
    "post_signup_activity": 1.0,
    "sustained_activity": 2.0,
    "meaningful_transaction_value": 100.0,
    "engagement_presence": 0.50,
    "payment_instrument_diversity": 0.50,
    "device_diversity": 0.50,
    "ip_diversity": 0.50,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    """Return current UTC time as ISO-8601."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def _append_jsonl(
    path: Path,
    record: Dict[str, Any],
) -> None:
    """Append one JSON object to a JSONL file."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            )
            + "\n"
        )


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Safely convert a value to float."""

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


# ---------------------------------------------------------------------------
# Payout Gate
# ---------------------------------------------------------------------------

class PayoutGate:
    """
    Autonomous referral-bonus decision and payout controller.

    Uses the existing ClusterScorer.score() method.

    Policy:

        risk < 0.30
            RELEASE

        0.30 <= risk < 0.70
            HOLD_FOR_VERIFICATION

        risk >= 0.70
            BLOCK_BONUS
    """

    def __init__(
        self,
        reports_dir: str = "reports",
        scorer: Optional[ClusterScorer] = None,
        razorpay_client: Optional[
            RazorpayTestClient
        ] = None,
    ):

        self.reports_dir = Path(
            reports_dir
        )

        self.reports_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.scorer = (
            scorer
            if scorer is not None
            else ClusterScorer()
        )

        self.razorpay = (
            razorpay_client
            if razorpay_client is not None
            else RazorpayTestClient()
        )

        self.bonus_ledger_path = (
            self.reports_dir
            / "bonus_ledger.jsonl"
        )

        self.held_payouts_path = (
            self.reports_dir
            / "held_payouts.jsonl"
        )

    # -----------------------------------------------------------------------
    # Main processing
    # -----------------------------------------------------------------------

    def process(
        self,
        cluster_row: pd.Series,
        account_number: Optional[str] = None,
        fund_account_id: Optional[str] = None,
        narration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Score one cluster and execute the autonomous policy.
        """

        cluster = cluster_row.copy()

        cluster_id = str(
            cluster.get(
                "cluster_id",
                "unknown_cluster",
            )
        )

        bonus_amount = _safe_float(
            cluster.get(
                "total_bonus_claimed",
                0.0,
            )
        )

        # Never allow evaluation-only fields to affect
        # the live decision.
        decision_row = cluster.drop(
            labels=[
                "_true_cluster_type",
                "label_fraud",
            ],
            errors="ignore",
        )

        # -------------------------------------------------------------------
        # 1. Existing fraud scorer
        # -------------------------------------------------------------------

        # IMPORTANT:
        # ClusterScorer exposes .score(), not .score_cluster().
        score_result = self.scorer.score(
            decision_row
        )

        risk_score = self._extract_risk_score(
            score_result
        )

        # Preserve the model's own action when possible.
        model_action = getattr(
            score_result,
            "action",
            None,
        )

        # -------------------------------------------------------------------
        # 2. Autonomous policy
        # -------------------------------------------------------------------

        if risk_score < RELEASE_THRESHOLD:

            decision = {
                "cluster_id": cluster_id,
                "risk_score": risk_score,
                "model_action": model_action,
                "initial_action": "RELEASE",
                "final_action": "RELEASE",
                "bonus_amount": bonus_amount,
                "verification": None,
                "top_reasons": getattr(
                    score_result,
                    "top_reasons",
                    [],
                ),
                "policy_version": POLICY_VERSION,
            }

            return self._release_bonus(
                cluster=cluster,
                decision=decision,
                account_number=account_number,
                fund_account_id=fund_account_id,
                narration=narration,
            )

        if risk_score >= BLOCK_THRESHOLD:

            decision = {
                "cluster_id": cluster_id,
                "risk_score": risk_score,
                "model_action": model_action,
                "initial_action": "BLOCK_BONUS",
                "final_action": "BLOCK_BONUS",
                "bonus_amount": bonus_amount,
                "verification": None,
                "top_reasons": getattr(
                    score_result,
                    "top_reasons",
                    [],
                ),
                "policy_version": POLICY_VERSION,
            }

            return self._block_bonus(
                cluster=cluster,
                decision=decision,
            )

        # -------------------------------------------------------------------
        # 3. Ambiguous case
        # -------------------------------------------------------------------

        verification = self._verify_cluster(
            cluster
        )

        if verification["passed"]:

            decision = {
                "cluster_id": cluster_id,
                "risk_score": risk_score,
                "model_action": model_action,
                "initial_action": (
                    "HOLD_FOR_VERIFICATION"
                ),
                "final_action": "RELEASE",
                "bonus_amount": bonus_amount,
                "verification": verification,
                "top_reasons": getattr(
                    score_result,
                    "top_reasons",
                    [],
                ),
                "policy_version": POLICY_VERSION,
            }

            return self._release_bonus(
                cluster=cluster,
                decision=decision,
                account_number=account_number,
                fund_account_id=fund_account_id,
                narration=narration,
            )

        decision = {
            "cluster_id": cluster_id,
            "risk_score": risk_score,
            "model_action": model_action,
            "initial_action": (
                "HOLD_FOR_VERIFICATION"
            ),
            "final_action": (
                "HOLD_FOR_VERIFICATION"
            ),
            "bonus_amount": bonus_amount,
            "verification": verification,
            "top_reasons": getattr(
                score_result,
                "top_reasons",
                [],
            ),
            "policy_version": POLICY_VERSION,
        }

        return self._hold_bonus(
            cluster=cluster,
            decision=decision,
        )

    # -----------------------------------------------------------------------
    # Risk extraction
    # -----------------------------------------------------------------------

    def _extract_risk_score(
        self,
        result: Any,
    ) -> float:
        """
        Extract risk score from the existing ScoringResult.

        ClusterScorer.score() returns an object with:
            result.risk_score
        """

        if hasattr(
            result,
            "risk_score",
        ):

            return max(
                0.0,
                min(
                    1.0,
                    float(
                        result.risk_score
                    ),
                ),
            )

        if isinstance(
            result,
            dict,
        ):

            return max(
                0.0,
                min(
                    1.0,
                    _safe_float(
                        result.get(
                            "risk_score",
                            0.0,
                        )
                    ),
                ),
            )

        raise ValueError(
            "Could not extract risk score "
            "from ClusterScorer output."
        )

    # -----------------------------------------------------------------------
    # Secondary verification
    # -----------------------------------------------------------------------

    def _verify_cluster(
        self,
        cluster: pd.Series,
    ) -> Dict[str, Any]:
        """
        Autonomous secondary verification.

        Passes if at least 5 of 7 checks pass.
        """

        checks: Dict[str, Dict[str, Any]] = {}

        # 1. Post-signup activity
        activity = _safe_float(
            cluster.get(
                "avg_txn_post_signup"
            )
        )

        checks[
            "post_signup_activity"
        ] = {
            "value": activity,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "post_signup_activity"
                ]
            ),
            "passed": (
                activity
                >= VERIFICATION_THRESHOLDS[
                    "post_signup_activity"
                ]
            ),
        }

        # 2. Sustained activity
        active_days = _safe_float(
            cluster.get(
                "avg_active_days_post_signup"
            )
        )

        checks[
            "sustained_activity"
        ] = {
            "value": active_days,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "sustained_activity"
                ]
            ),
            "passed": (
                active_days
                >= VERIFICATION_THRESHOLDS[
                    "sustained_activity"
                ]
            ),
        }

        # 3. Meaningful transaction value
        transaction_value = _safe_float(
            cluster.get(
                "avg_txn_value_post_signup"
            )
        )

        checks[
            "meaningful_transaction_value"
        ] = {
            "value": transaction_value,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "meaningful_transaction_value"
                ]
            ),
            "passed": (
                transaction_value
                >= VERIFICATION_THRESHOLDS[
                    "meaningful_transaction_value"
                ]
            ),
        }

        # 4. Engagement presence
        zero_engagement = _safe_float(
            cluster.get(
                "pct_zero_engagement"
            ),
            default=1.0,
        )

        engagement = (
            1.0
            - zero_engagement
        )

        checks[
            "engagement_presence"
        ] = {
            "value": engagement,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "engagement_presence"
                ]
            ),
            "passed": (
                engagement
                >= VERIFICATION_THRESHOLDS[
                    "engagement_presence"
                ]
            ),
        }

        # 5. Payment instrument diversity
        instrument_reuse = _safe_float(
            cluster.get(
                "instrument_reuse_ratio"
            ),
            default=1.0,
        )

        checks[
            "payment_instrument_diversity"
        ] = {
            "value": instrument_reuse,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "payment_instrument_diversity"
                ]
            ),
            "passed": (
                instrument_reuse
                <= VERIFICATION_THRESHOLDS[
                    "payment_instrument_diversity"
                ]
            ),
        }

        # 6. Device diversity
        device_reuse = _safe_float(
            cluster.get(
                "device_reuse_ratio"
            ),
            default=1.0,
        )

        checks[
            "device_diversity"
        ] = {
            "value": device_reuse,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "device_diversity"
                ]
            ),
            "passed": (
                device_reuse
                <= VERIFICATION_THRESHOLDS[
                    "device_diversity"
                ]
            ),
        }

        # 7. IP diversity
        ip_reuse = _safe_float(
            cluster.get(
                "ip_reuse_ratio"
            ),
            default=1.0,
        )

        checks[
            "ip_diversity"
        ] = {
            "value": ip_reuse,
            "threshold": (
                VERIFICATION_THRESHOLDS[
                    "ip_diversity"
                ]
            ),
            "passed": (
                ip_reuse
                <= VERIFICATION_THRESHOLDS[
                    "ip_diversity"
                ]
            ),
        }

        passed_count = sum(
            1
            for check in checks.values()
            if check["passed"]
        )

        total_checks = len(
            checks
        )

        return {
            "passed": (
                passed_count >= 5
            ),
            "checks_passed": passed_count,
            "checks_total": total_checks,
            "checks": checks,
        }

    # -----------------------------------------------------------------------
    # RELEASE
    # -----------------------------------------------------------------------

    def _release_bonus(
        self,
        cluster: pd.Series,
        decision: Dict[str, Any],
        account_number: Optional[str],
        fund_account_id: Optional[str],
        narration: Optional[str],
    ) -> Dict[str, Any]:
        """
        Release or safely simulate the bonus.
        """

        cluster_id = decision[
            "cluster_id"
        ]

        bonus_amount = decision[
            "bonus_amount"
        ]

        amount_paise = int(
            round(
                bonus_amount * 100
            )
        )

        # ================================================================
        # SAFE DRY RUN
        # ================================================================

        if DRY_RUN_PAYOUTS:

            decision.update(
                {
                    "payout_status": (
                        "payout_simulated_dry_run"
                    ),
                    "payout_created": False,
                    "money_moved": False,
                }
            )

            ledger_record = {
                "timestamp": _utc_now(),
                "cluster_id": cluster_id,
                "action": (
                    "BONUS_RELEASE_SIMULATED"
                ),
                "risk_score": decision[
                    "risk_score"
                ],
                "bonus_amount_inr": bonus_amount,
                "amount_paise": amount_paise,
                "payout_status": (
                    "payout_simulated_dry_run"
                ),
                "money_moved": False,
                "policy_version": (
                    POLICY_VERSION
                ),
            }

            _append_jsonl(
                self.bonus_ledger_path,
                ledger_record,
            )

            logger.info(
                "DRY RUN: bonus release "
                "simulated for %s "
                "(INR %.2f)",
                cluster_id,
                bonus_amount,
            )

            return decision

        # ================================================================
        # Missing payout information
        # ================================================================

        if (
            not account_number
            or not fund_account_id
        ):

            decision.update(
                {
                    "payout_status": (
                        "payout_not_created_"
                        "missing_account_data"
                    ),
                    "payout_created": False,
                    "money_moved": False,
                }
            )

            ledger_record = {
                "timestamp": _utc_now(),
                "cluster_id": cluster_id,
                "action": (
                    "BONUS_RELEASE_SIMULATED"
                ),
                "risk_score": decision[
                    "risk_score"
                ],
                "bonus_amount_inr": bonus_amount,
                "amount_paise": amount_paise,
                "payout_status": (
                    "payout_not_created_"
                    "missing_account_data"
                ),
                "money_moved": False,
                "policy_version": (
                    POLICY_VERSION
                ),
            }

            _append_jsonl(
                self.bonus_ledger_path,
                ledger_record,
            )

            return decision

        # ================================================================
        # Razorpay not configured
        # ================================================================

        if not self.razorpay.is_configured():

            decision.update(
                {
                    "payout_status": (
                        "payout_simulated_"
                        "razorpay_not_configured"
                    ),
                    "payout_created": False,
                    "money_moved": False,
                }
            )

            ledger_record = {
                "timestamp": _utc_now(),
                "cluster_id": cluster_id,
                "action": (
                    "BONUS_RELEASE_SIMULATED"
                ),
                "risk_score": decision[
                    "risk_score"
                ],
                "bonus_amount_inr": bonus_amount,
                "amount_paise": amount_paise,
                "payout_status": (
                    "payout_simulated_"
                    "razorpay_not_configured"
                ),
                "money_moved": False,
                "policy_version": (
                    POLICY_VERSION
                ),
            }

            _append_jsonl(
                self.bonus_ledger_path,
                ledger_record,
            )

            return decision

        # ================================================================
        # RazorpayX TEST MODE payout
        # ================================================================

        try:

            payout_response = (
                self.razorpay.create_bonus_payout(
                    account_number=account_number,
                    fund_account_id=fund_account_id,
                    amount_paise=amount_paise,
                    narration=(
                        narration
                        or (
                            f"Referral bonus - "
                            f"{cluster_id}"
                        )
                    ),
                    mode="UPI",
                    queue_if_low_balance=True,
                )
            )

            decision.update(
                {
                    "payout_status": (
                        "payout_created_test_mode"
                    ),
                    "payout_created": True,
                    "money_moved": False,
                    "payout": payout_response,
                }
            )

            ledger_record = {
                "timestamp": _utc_now(),
                "cluster_id": cluster_id,
                "action": (
                    "BONUS_RELEASED_TEST_MODE"
                ),
                "risk_score": decision[
                    "risk_score"
                ],
                "bonus_amount_inr": bonus_amount,
                "amount_paise": amount_paise,
                "payout_status": (
                    "payout_created_test_mode"
                ),
                "money_moved": False,
                "payout_id": (
                    payout_response.get(
                        "id"
                    )
                ),
                "policy_version": (
                    POLICY_VERSION
                ),
            }

            _append_jsonl(
                self.bonus_ledger_path,
                ledger_record,
            )

            return decision

        except Exception as exc:

            logger.exception(
                "RazorpayX payout creation "
                "failed for %s",
                cluster_id,
            )

            decision.update(
                {
                    "payout_status": (
                        "payout_creation_failed"
                    ),
                    "payout_created": False,
                    "money_moved": False,
                    "error": str(exc),
                }
            )

            ledger_record = {
                "timestamp": _utc_now(),
                "cluster_id": cluster_id,
                "action": (
                    "BONUS_RELEASE_FAILED"
                ),
                "risk_score": decision[
                    "risk_score"
                ],
                "bonus_amount_inr": bonus_amount,
                "amount_paise": amount_paise,
                "payout_status": (
                    "payout_creation_failed"
                ),
                "money_moved": False,
                "error": str(exc),
                "policy_version": (
                    POLICY_VERSION
                ),
            }

            _append_jsonl(
                self.bonus_ledger_path,
                ledger_record,
            )

            return decision

    # -----------------------------------------------------------------------
    # HOLD
    # -----------------------------------------------------------------------

    def _hold_bonus(
        self,
        cluster: pd.Series,
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Automatically hold the bonus after failed verification.
        """

        cluster_id = decision[
            "cluster_id"
        ]

        bonus_amount = decision[
            "bonus_amount"
        ]

        decision.update(
            {
                "payout_status": "bonus_held",
                "payout_created": False,
                "money_moved": False,
            }
        )

        record = {
            "timestamp": _utc_now(),
            "cluster_id": cluster_id,
            "action": (
                "HOLD_FOR_VERIFICATION"
            ),
            "risk_score": decision[
                "risk_score"
            ],
            "bonus_amount_inr": bonus_amount,
            "money_moved": False,
            "verification": decision[
                "verification"
            ],
            "policy_version": (
                POLICY_VERSION
            ),
        }

        _append_jsonl(
            self.held_payouts_path,
            record,
        )

        _append_jsonl(
            self.bonus_ledger_path,
            record,
        )

        return decision

    # -----------------------------------------------------------------------
    # BLOCK
    # -----------------------------------------------------------------------

    def _block_bonus(
        self,
        cluster: pd.Series,
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Automatically block a high-risk bonus.

        This method NEVER calls the payout API.
        """

        cluster_id = decision[
            "cluster_id"
        ]

        bonus_amount = decision[
            "bonus_amount"
        ]

        decision.update(
            {
                "payout_status": "bonus_blocked",
                "payout_created": False,
                "money_moved": False,
            }
        )

        record = {
            "timestamp": _utc_now(),
            "cluster_id": cluster_id,
            "action": "BLOCK_BONUS",
            "risk_score": decision[
                "risk_score"
            ],
            "bonus_amount_inr": bonus_amount,
            "money_moved": False,
            "policy_version": (
                POLICY_VERSION
            ),
        }

        _append_jsonl(
            self.held_payouts_path,
            record,
        )

        _append_jsonl(
            self.bonus_ledger_path,
            record,
        )

        return decision


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def process_bonus(
    cluster_row: pd.Series,
    account_number: Optional[str] = None,
    fund_account_id: Optional[str] = None,
    narration: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper for processing one cluster.
    """

    gate = PayoutGate()

    return gate.process(
        cluster_row=cluster_row,
        account_number=account_number,
        fund_account_id=fund_account_id,
        narration=narration,
    )


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print(
        "=" * 70
    )

    print(
        "ABUSE-RING SENTINEL â€” "
        "AUTONOMOUS PAYOUT GATE"
    )

    print(
        "=" * 70
    )

    print()
    print("Policy:")
    print(
        f"  risk < {RELEASE_THRESHOLD:.2f}"
        "  -> RELEASE"
    )

    print(
        f"  {RELEASE_THRESHOLD:.2f} <= risk < "
        f"{BLOCK_THRESHOLD:.2f}"
        " -> HOLD_FOR_VERIFICATION"
    )

    print(
        f"  risk >= {BLOCK_THRESHOLD:.2f}"
        " -> BLOCK_BONUS"
    )

    print()
    print(
        f"Policy version: "
        f"{POLICY_VERSION}"
    )

    print(
        f"DRY_RUN_PAYOUTS: "
        f"{DRY_RUN_PAYOUTS}"
    )

    if DRY_RUN_PAYOUTS:

        print()
        print(
            "SAFE MODE ENABLED: approved "
            "payouts are simulated."
        )

        print(
            "NO RazorpayX payout API "
            "will be called."
        )

    print(
        "=" * 70
    )
