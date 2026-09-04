
"""
client.py

Thin wrapper around the official Razorpay Python SDK, scoped to TEST MODE
ONLY.

This client provides:

1. PAYMENT INSTRUMENT FINGERPRINTING
2. RAZORPAYX PAYOUT CREATION AFTER AUTONOMOUS APPROVAL

IMPORTANT:
- Only Razorpay TEST MODE keys are accepted.
- Live keys beginning with `rzp_live_` are rejected.
- Payouts are only attempted after the autonomous payout gate approves.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

import razorpay
from dotenv import load_dotenv


# ======================================================================
# LOAD ENVIRONMENT VARIABLES
# ======================================================================

# Loads variables from .env in the project root.
load_dotenv()


logger = logging.getLogger(
    "abuse_ring_sentinel.razorpay"
)


# ======================================================================
# PAYMENT INSTRUMENT FINGERPRINT
# ======================================================================


@dataclass
class InstrumentFingerprint:

    payment_id: str

    method: str
    # card | upi | wallet | netbanking

    instrument_id: str
    # Stable/tokenized instrument identifier

    contact: Optional[str]

    email: Optional[str]


# ======================================================================
# RAZORPAY TEST CLIENT
# ======================================================================


class RazorpayTestClient:

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ):

        # --------------------------------------------------------------
        # Read credentials
        # --------------------------------------------------------------

        self.key_id = (
            key_id
            or os.getenv(
                "RAZORPAY_KEY_ID",
                "",
            )
        )

        self.key_secret = (
            key_secret
            or os.getenv(
                "RAZORPAY_KEY_SECRET",
                "",
            )
        )

        # --------------------------------------------------------------
        # SECURITY CHECK
        # --------------------------------------------------------------

        if self.key_id:

            if not self.key_id.startswith(
                "rzp_test_"
            ):

                raise RuntimeError(
                    "Refusing to initialize: this project "
                    "is scoped to Razorpay TEST MODE only. "
                    "Expected a key starting with "
                    "'rzp_test_'."
                )

        # --------------------------------------------------------------
        # Initialize SDK
        # --------------------------------------------------------------

        if self.key_id and self.key_secret:

            self._client = razorpay.Client(
                auth=(
                    self.key_id,
                    self.key_secret,
                )
            )

        else:

            self._client = None

    # ==================================================================
    # PAYMENT INSTRUMENT FINGERPRINTING
    # ==================================================================

    def extract_fingerprint(
        self,
        payment: dict,
    ) -> InstrumentFingerprint:

        """
        Extract a stable payment-instrument identifier from a
        Razorpay payment object or webhook payload.
        """

        method = payment.get(
            "method",
            "unknown",
        )

        # --------------------------------------------------------------
        # CARD
        # --------------------------------------------------------------

        if method == "card":

            card = (
                payment.get("card")
                or {}
            )

            instrument_id = (
                card.get("id")
                or payment.get("card_id")
                or "unknown_card"
            )

        # --------------------------------------------------------------
        # UPI
        # --------------------------------------------------------------

        elif method == "upi":

            instrument_id = (
                payment.get("vpa")
                or "unknown_vpa"
            )

        # --------------------------------------------------------------
        # WALLET
        # --------------------------------------------------------------

        elif method == "wallet":

            instrument_id = (
                f"wallet_"
                f"{payment.get('wallet', 'unknown')}_"
                f"{payment.get('contact', '')}"
            )

        # --------------------------------------------------------------
        # NETBANKING / OTHER
        # --------------------------------------------------------------

        else:

            instrument_id = (
                payment.get("bank")
                or "unknown_instrument"
            )

        return InstrumentFingerprint(
            payment_id=payment.get(
                "id",
                "",
            ),

            method=method,

            instrument_id=instrument_id,

            contact=payment.get(
                "contact"
            ),

            email=payment.get(
                "email"
            ),
        )

    # ==================================================================
    # FETCH PAYMENT
    # ==================================================================

    def fetch_payment(
        self,
        payment_id: str,
    ) -> dict:

        """
        Fetch a payment from Razorpay using TEST MODE credentials.
        """

        if not self._client:

            raise RuntimeError(
                "Razorpay client not configured. "
                "Set RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET in .env."
            )

        return self._client.payment.fetch(
            payment_id
        )

    # ==================================================================
    # CREATE BONUS PAYOUT
    # ==================================================================

    def create_bonus_payout(
        self,
        account_number: str,
        fund_account_id: str,
        amount_paise: int,
        narration: str,
        mode: str = "UPI",
        queue_if_low_balance: bool = True,
    ) -> dict:

        """
        Create a RazorpayX payout.

        IMPORTANT:
        This function is only called AFTER the autonomous payout
        gate approves the bonus.

        High-risk BLOCK_BONUS decisions never reach this function.
        """

        if not self._client:

            raise RuntimeError(
                "Razorpay client not configured. "
                "Set RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET in .env."
            )

        if amount_paise <= 0:

            raise ValueError(
                "Payout amount must be greater than zero."
            )

        return self._client.payout.create(
            {
                "account_number": account_number,

                "fund_account_id": fund_account_id,

                "amount": amount_paise,

                "currency": "INR",

                "mode": mode,

                "purpose": "referral_bonus",

                "queue_if_low_balance": (
                    queue_if_low_balance
                ),

                "narration": narration,
            }
        )

    # ==================================================================
    # CONFIGURATION STATUS
    # ==================================================================

    def is_configured(self) -> bool:

        """
        Returns True only when both Razorpay TEST MODE credentials
        are available.
        """

        return (
            self._client is not None
        )

