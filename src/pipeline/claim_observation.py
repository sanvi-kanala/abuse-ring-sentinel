from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass
class ObservationResult:
    user_id: str
    risk_score: float
    observation_score: float
    action: str
    reasons: list
    timestamp: str


class ClaimObservationEngine:
    """
    Resolves a previously-held referral bonus claim by replaying
    behavioural evidence that became available after signup.

    IMPORTANT:
    This engine is NOT used for the initial claim-time decision.

    It is only called after the claim has already been placed
    into VERIFY_CLAIM / VERIFICATION_REQUIRED.
    """

    def __init__(self, users_path="data/users.csv"):
        self.users = pd.read_csv(users_path)

        self.users["user_id"] = (
            self.users["user_id"]
            .astype(str)
            .str.strip()
        )

    def _get_user(self, user_id):
        rows = self.users[
            self.users["user_id"] == str(user_id)
        ]

        if rows.empty:
            raise ValueError(
                f"User not found: {user_id}"
            )

        return rows.iloc[0]

    @staticmethod
    def _safe_float(row, column, default=0.0):
        try:
            value = row.get(column, default)

            if pd.isna(value):
                return float(default)

            return float(value)

        except (TypeError, ValueError):
            return float(default)

    def observe(self, user_id):
        """
        Replay post-signup behavioural evidence for a held claim.

        The observation produces an independent resolution signal:

            observation_score < 0.30
                -> APPROVE_BONUS

            0.30 <= observation_score < 0.70
                -> KEEP_HELD

            observation_score >= 0.70
                -> REJECT_BONUS
        """

        user = self._get_user(user_id)

        transactions = self._safe_float(
            user,
            "num_txn_post_signup",
        )

        transaction_value = self._safe_float(
            user,
            "total_txn_value_post_signup",
        )

        active_days = self._safe_float(
            user,
            "active_days_post_signup",
        )

        risk = 0.0
        reasons = []

        # ---------------------------------------------------------
        # 1. Transaction activity
        # ---------------------------------------------------------

        if transactions <= 0:
            risk += 0.25
            reasons.append(
                "No post-signup transactions were observed"
            )

        elif transactions == 1:
            risk += 0.08
            reasons.append(
                "Only one post-signup transaction was observed"
            )

        else:
            reasons.append(
                f"{transactions:.0f} post-signup transactions observed"
            )

        # ---------------------------------------------------------
        # 2. Transaction value
        # ---------------------------------------------------------

        if transaction_value < 100:
            risk += 0.20
            reasons.append(
                f"Low post-signup transaction value "
                f"(₹{transaction_value:,.2f})"
            )

        elif transaction_value < 250:
            risk += 0.08
            reasons.append(
                f"Limited post-signup transaction value "
                f"(₹{transaction_value:,.2f})"
            )

        else:
            reasons.append(
                f"Post-signup transaction value reached "
                f"₹{transaction_value:,.2f}"
            )

        # ---------------------------------------------------------
        # 3. Sustained activity
        # ---------------------------------------------------------

        if active_days <= 0:
            risk += 0.25
            reasons.append(
                "No active days were observed after signup"
            )

        elif active_days < 2:
            risk += 0.15
            reasons.append(
                f"Very limited activity ({active_days:.0f} active day)"
            )

        elif active_days < 5:
            risk += 0.05
            reasons.append(
                f"Limited activity ({active_days:.0f} active days)"
            )

        else:
            reasons.append(
                f"Sustained activity across "
                f"{active_days:.0f} active days"
            )

        # ---------------------------------------------------------
        # 4. Combine signals
        # ---------------------------------------------------------

        risk = min(max(risk, 0.0), 1.0)

        if risk >= 0.70:
            action = "REJECT_BONUS"

        elif risk >= 0.30:
            action = "KEEP_HELD"

        else:
            action = "APPROVE_BONUS"

        # ---------------------------------------------------------
        # 5. Make the evidence useful in the dashboard
        # ---------------------------------------------------------

        if action == "APPROVE_BONUS":
            reasons.append(
                "Observed behaviour provides sufficient evidence "
                "to resolve the held claim"
            )

        elif action == "KEEP_HELD":
            reasons.append(
                "Observed behaviour is still inconclusive; "
                "the bonus remains protected"
            )

        else:
            reasons.append(
                "Observed behaviour provides insufficient evidence "
                "to release the held bonus"
            )

        return ObservationResult(
            user_id=str(user_id),
            risk_score=round(risk, 4),
            observation_score=round(risk, 4),
            action=action,
            reasons=reasons,
            timestamp=datetime.utcnow().isoformat(),
        )