import pandas as pd
import numpy as np


class ClaimFeatureBuilder:
    """
    Builds fraud signals that are available at the moment
    a user attempts to claim a referral bonus.

    IMPORTANT:
    These features intentionally do NOT use future behavioral
    information such as transactions after signup.
    """

    def __init__(
        self,
        users_path="data/users.csv",
        referrals_path="data/referrals.csv",
    ):
        self.users = pd.read_csv(users_path)
        self.referrals = pd.read_csv(referrals_path)

        # Make sure IDs are treated consistently as strings
        self.users["user_id"] = self.users["user_id"].astype(str)

        if "referred_by" in self.users.columns:
            self.users["referred_by"] = self.users["referred_by"].fillna("").astype(str)

        self.referrals["referrer_id"] = self.referrals["referrer_id"].astype(str)
        self.referrals["referee_id"] = self.referrals["referee_id"].astype(str)

    def _get_user(self, user_id):
        rows = self.users[self.users["user_id"] == str(user_id)]

        if rows.empty:
            raise ValueError(f"User not found: {user_id}")

        return rows.iloc[0]

    def _connected_users(self, user_id):
        """
        Find users connected through:
        - same device
        - same IP
        - same payment instrument
        """

        user = self._get_user(user_id)

        connected = set()

        device_id = user.get("device_id")
        signup_ip = user.get("signup_ip")
        instrument_id = user.get("payment_instrument_id")

        if pd.notna(device_id):
            matches = self.users[
                self.users["device_id"] == device_id
            ]["user_id"].tolist()

            connected.update(matches)

        if pd.notna(signup_ip):
            matches = self.users[
                self.users["signup_ip"] == signup_ip
            ]["user_id"].tolist()

            connected.update(matches)

        if pd.notna(instrument_id):
            matches = self.users[
                self.users["payment_instrument_id"] == instrument_id
            ]["user_id"].tolist()

            connected.update(matches)

        connected.discard(str(user_id))

        return connected

    def _referrer_stats(self, referrer_id):
        """
        Calculate referral-network signals for the referrer.
        """

        referrer_id = str(referrer_id)

        outgoing = self.referrals[
            self.referrals["referrer_id"] == referrer_id
        ]

        referral_count = len(outgoing)

        # Users referred by this referrer
        referred_ids = outgoing["referee_id"].astype(str).tolist()

        # How many of those users share device/IP/instrument
        # with each other or the referrer?
        referrer_rows = self.users[
            self.users["user_id"] == referrer_id
        ]

        shared_device_count = 0
        shared_ip_count = 0
        shared_instrument_count = 0

        if not referrer_rows.empty:

            referrer = referrer_rows.iloc[0]

            if pd.notna(referrer.get("device_id")):
                shared_device_count = self.users[
                    self.users["device_id"] == referrer["device_id"]
                ].shape[0] - 1

            if pd.notna(referrer.get("signup_ip")):
                shared_ip_count = self.users[
                    self.users["signup_ip"] == referrer["signup_ip"]
                ].shape[0] - 1

            if pd.notna(referrer.get("payment_instrument_id")):
                shared_instrument_count = self.users[
                    self.users["payment_instrument_id"]
                    == referrer["payment_instrument_id"]
                ].shape[0] - 1

        return {
            "referral_count": referral_count,
            "referrer_shared_device_count": max(shared_device_count, 0),
            "referrer_shared_ip_count": max(shared_ip_count, 0),
            "referrer_shared_instrument_count": max(
                shared_instrument_count, 0
            ),
        }

    def build(self, user_id, referrer_id=None):
        """
        Build all claim-time signals for a user.

        Returns:
            dict containing only information available
            at bonus-claim time.
        """

        user = self._get_user(user_id)

        if referrer_id is None:
            referrer_id = user.get("referred_by", "")

        referrer_id = str(referrer_id) if pd.notna(referrer_id) else ""

        connected_users = self._connected_users(user_id)

        # Direct signal counts
        device_matches = 0
        ip_matches = 0
        instrument_matches = 0

        if pd.notna(user.get("device_id")):
            device_matches = self.users[
                self.users["device_id"] == user["device_id"]
            ].shape[0] - 1

        if pd.notna(user.get("signup_ip")):
            ip_matches = self.users[
                self.users["signup_ip"] == user["signup_ip"]
            ].shape[0] - 1

        if pd.notna(user.get("payment_instrument_id")):
            instrument_matches = self.users[
                self.users["payment_instrument_id"]
                == user["payment_instrument_id"]
            ].shape[0] - 1

        # Referrer statistics
        referrer_stats = self._referrer_stats(referrer_id)

        # How many signals overlap with the referrer specifically?
        referrer = None

        if referrer_id:
            referrer_rows = self.users[
                self.users["user_id"] == referrer_id
            ]

            if not referrer_rows.empty:
                referrer = referrer_rows.iloc[0]

        shared_with_referrer = 0

        if referrer is not None:

            if (
                pd.notna(user.get("device_id"))
                and pd.notna(referrer.get("device_id"))
                and user["device_id"] == referrer["device_id"]
            ):
                shared_with_referrer += 1

            if (
                pd.notna(user.get("signup_ip"))
                and pd.notna(referrer.get("signup_ip"))
                and user["signup_ip"] == referrer["signup_ip"]
            ):
                shared_with_referrer += 1

            if (
                pd.notna(user.get("payment_instrument_id"))
                and pd.notna(referrer.get("payment_instrument_id"))
                and user["payment_instrument_id"]
                == referrer["payment_instrument_id"]
            ):
                shared_with_referrer += 1

        # Combined-signal indicators
        multi_signal_overlap = (
            int(device_matches > 0)
            + int(ip_matches > 0)
            + int(instrument_matches > 0)
        )

        strong_overlap = int(
            device_matches > 0
            and ip_matches > 0
        )

        very_strong_overlap = int(
            device_matches > 0
            and ip_matches > 0
            and instrument_matches > 0
        )

        features = {
            "user_id": str(user_id),
            "referrer_id": referrer_id,

            # Direct identity/network reuse
            "device_match_count": int(max(device_matches, 0)),
            "ip_match_count": int(max(ip_matches, 0)),
            "instrument_match_count": int(max(instrument_matches, 0)),

            # Network size
            "connected_user_count": int(len(connected_users)),

            # Relationship to referrer
            "shared_signals_with_referrer": int(shared_with_referrer),

            # Referrer behavior/network
            **referrer_stats,

            # Combined indicators
            "multi_signal_overlap": int(multi_signal_overlap),
            "strong_overlap": int(strong_overlap),
            "very_strong_overlap": int(very_strong_overlap),
        }

        return features