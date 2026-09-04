from dataclasses import dataclass
from datetime import datetime


@dataclass
class ClaimRiskResult:
    user_id: str
    referrer_id: str
    risk_score: float
    risk_level: str
    action: str
    reasons: list
    timestamp: str


class ClaimRiskScorer:
    """
    Autonomous risk scorer for referral-bonus claims.

    This operates only on signals available at claim time.
    """

    def score(self, features: dict) -> ClaimRiskResult:

        risk = 0.0
        reasons = []

        # --------------------------------------------------
        # 1. DEVICE REUSE
        # --------------------------------------------------

        device_matches = features.get("device_match_count", 0)

        if device_matches >= 3:
            risk += 0.18
            reasons.append(
                f"Device linked to {device_matches} other accounts"
            )
        elif device_matches >= 1:
            risk += 0.05

        # --------------------------------------------------
        # 2. IP REUSE
        # --------------------------------------------------

        ip_matches = features.get("ip_match_count", 0)

        if ip_matches >= 5:
            risk += 0.20
            reasons.append(
                f"IP linked to {ip_matches} other accounts"
            )
        elif ip_matches >= 2:
            risk += 0.08

        # --------------------------------------------------
        # 3. PAYMENT INSTRUMENT REUSE
        # --------------------------------------------------

        instrument_matches = features.get(
            "instrument_match_count", 0
        )

        if instrument_matches >= 3:
            risk += 0.22
            reasons.append(
                f"Payment instrument linked to "
                f"{instrument_matches} other accounts"
            )
        elif instrument_matches >= 1:
            risk += 0.07

        # --------------------------------------------------
        # 4. CONNECTED NETWORK
        # --------------------------------------------------

        connected_users = features.get(
            "connected_user_count", 0
        )

        if connected_users >= 8:
            risk += 0.15
            reasons.append(
                f"Connected to {connected_users} other accounts"
            )
        elif connected_users >= 4:
            risk += 0.08

        # --------------------------------------------------
        # 5. REFERRAL CONCENTRATION
        # --------------------------------------------------

        referral_count = features.get(
            "referral_count", 0
        )

        if referral_count >= 10:
            risk += 0.15
            reasons.append(
                f"Referrer has {referral_count} referrals"
            )
        elif referral_count >= 5:
            risk += 0.06

        # --------------------------------------------------
        # 6. MULTI-SIGNAL OVERLAP
        # --------------------------------------------------

        multi_signal = features.get(
            "multi_signal_overlap", 0
        )

        if multi_signal >= 3:
            risk += 0.25
            reasons.append(
                "Device, IP and payment instrument "
                "are all reused"
            )

        elif multi_signal == 2:
            risk += 0.10
            reasons.append(
                "Multiple identity signals are reused"
            )

        # --------------------------------------------------
        # 7. STRONG COMBINATION
        # --------------------------------------------------

        if features.get("strong_overlap", 0) == 1:
            risk += 0.12
            reasons.append(
                "Device and IP overlap simultaneously"
            )

        # --------------------------------------------------
        # 8. VERY STRONG COMBINATION
        # --------------------------------------------------

        if features.get("very_strong_overlap", 0) == 1:
            risk += 0.18
            reasons.append(
                "Device, IP and payment instrument "
                "overlap simultaneously"
            )

        # --------------------------------------------------
        # CAP SCORE
        # --------------------------------------------------

        risk = min(risk, 1.0)

        # --------------------------------------------------
        # AUTONOMOUS DECISION
        # --------------------------------------------------

        if risk >= 0.70:

            risk_level = "HIGH"
            action = "REJECT_BONUS"

        elif risk >= 0.30:

            risk_level = "MEDIUM"
            action = "VERIFY_CLAIM"

        else:

            risk_level = "LOW"
            action = "APPROVE_BONUS"

        # Fallback explanation
        if not reasons:
            reasons.append(
                "No significant coordinated-abuse signals detected"
            )

        return ClaimRiskResult(
            user_id=str(features.get("user_id", "")),
            referrer_id=str(features.get("referrer_id", "")),
            risk_score=round(risk, 4),
            risk_level=risk_level,
            action=action,
            reasons=reasons,
            timestamp=datetime.utcnow().isoformat(),
        )