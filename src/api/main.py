import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from src.pipeline.score_cluster import ClusterScorer
from src.features.claim_features import ClaimFeatureBuilder
from src.pipeline.claim_risk import ClaimRiskScorer
from src.pipeline.claim_observation import ClaimObservationEngine
from src.razorpay_integration.client import RazorpayTestClient


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

REPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

load_dotenv(
    PROJECT_ROOT / ".env"
)


# ============================================================
# REPORT FILES
# ============================================================

CLAIM_DECISIONS_FILE = (
    REPORTS_DIR / "claim_decisions.jsonl"
)

WEBHOOK_EVENTS_FILE = (
    REPORTS_DIR / "webhook_events.jsonl"
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Abuse-Ring Sentinel",
    description=(
        "Autonomous referral bonus abuse detection "
        "and prevention system"
    ),
    version="1.2.0",
)


# ============================================================
# ENGINES
# ============================================================

cluster_scorer = ClusterScorer(
    model_path=str(
        REPORTS_DIR / "fraud_ring_model.joblib"
    )
)

claim_feature_builder = ClaimFeatureBuilder(
    users_path=str(
        DATA_DIR / "users.csv"
    ),
    referrals_path=str(
        DATA_DIR / "referrals.csv"
    ),
)

claim_risk_scorer = ClaimRiskScorer()

claim_observation_engine = ClaimObservationEngine(
    users_path=str(
        DATA_DIR / "users.csv"
    )
)

razorpay_client = RazorpayTestClient()


# ============================================================
# HELPERS
# ============================================================

def append_jsonl(
    path: Path,
    payload: dict,
):
    """
    Append one JSON object to a JSONL file.
    """

    with open(
        path,
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            json.dumps(
                payload,
                default=str,
            )
        )

        f.write("\n")


def read_jsonl(
    path: Path,
):
    """
    Read a JSONL file safely.
    """

    if not path.exists():
        return []

    rows = []

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                rows.append(
                    json.loads(line)
                )

            except json.JSONDecodeError:
                continue

    return rows


def find_latest_claim(
    claim_id: str,
):
    """
    Find the latest state of a claim.
    """

    rows = read_jsonl(
        CLAIM_DECISIONS_FILE
    )

    matches = [
        row
        for row in rows
        if str(
            row.get("claim_id", "")
        )
        == str(claim_id)
    ]

    if not matches:
        return None

    return matches[-1]


def find_claims_for_user(
    user_id: str,
):
    """
    Find all recorded claim states
    for a particular user.
    """

    rows = read_jsonl(
        CLAIM_DECISIONS_FILE
    )

    return [
        row
        for row in rows
        if str(
            row.get("user_id", "")
        )
        == str(user_id)
    ]


# ============================================================
# REQUEST MODELS
# ============================================================

class ClusterScoreRequest(BaseModel):

    cluster_id: str


class BonusClaimRequest(BaseModel):

    user_id: str

    referrer_id: str | None = None

    bonus_amount: float = Field(
        gt=0
    )

    payment_id: str | None = None


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "abuse-ring-sentinel",
        "policy": "1.2-autonomous-observation",
        "razorpay_configured": (
            razorpay_client.is_configured()
        ),
    }


# ============================================================
# CLUSTER SCORING
# ============================================================

@app.post("/score-cluster")
def score_cluster(
    payload: ClusterScoreRequest,
):

    cluster_id = str(
        payload.cluster_id
    )

    features_path = (
        DATA_DIR / "cluster_features.csv"
    )

    if not features_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "cluster_features.csv not found"
            ),
        )

    import pandas as pd

    df = pd.read_csv(
        features_path
    )

    rows = df[
        df["cluster_id"]
        .astype(str)
        == cluster_id
    ]

    if rows.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Cluster not found: {cluster_id}"
            ),
        )

    result = cluster_scorer.score(
        rows.iloc[0]
    )

    return {
        "cluster_id": result.cluster_id,
        "risk_score": result.risk_score,
        "action": result.action,
        "top_reasons": result.top_reasons,
        "cluster_size": result.cluster_size,
        "total_bonus_at_stake": (
            result.total_bonus_at_stake
        ),
        "policy_version": (
            result.policy_version
        ),
        "timestamp": result.timestamp,
    }


# ============================================================
# GET CLUSTER
# ============================================================

@app.get("/clusters/{cluster_id}")
def get_cluster(
    cluster_id: str,
):

    import pandas as pd

    features_path = (
        DATA_DIR / "cluster_features.csv"
    )

    if not features_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "cluster_features.csv not found"
            ),
        )

    df = pd.read_csv(
        features_path
    )

    rows = df[
        df["cluster_id"]
        .astype(str)
        == str(cluster_id)
    ]

    if rows.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Cluster not found: {cluster_id}"
            ),
        )

    row = rows.iloc[0].to_dict()

    # Ground-truth fields are evaluation-only.
    # Never expose them as decision inputs.
    row.pop(
        "label_fraud",
        None,
    )

    row.pop(
        "_true_cluster_type",
        None,
    )

    return row


# ============================================================
# CLAIM BONUS
# ============================================================

@app.post("/claim-bonus")
def claim_bonus(
    payload: BonusClaimRequest,
):

    user_id = str(
        payload.user_id
    )

    # --------------------------------------------------------
    # STEP 1 — BUILD CLAIM-TIME FEATURES
    # --------------------------------------------------------

    try:

        features = (
            claim_feature_builder.build(
                user_id=user_id,
                referrer_id=payload.referrer_id,
            )
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    # --------------------------------------------------------
    # STEP 2 — AUTONOMOUS CLAIM-TIME RISK
    # --------------------------------------------------------

    risk_result = (
        claim_risk_scorer.score(
            features
        )
    )

    # --------------------------------------------------------
    # STEP 3 — CREATE CLAIM ID
    # --------------------------------------------------------

    claim_id = (
        f"claim_"
        f"{user_id}_"
        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    )

    # --------------------------------------------------------
    # STEP 4 — MAP ENGINE ACTION TO BUSINESS DECISION
    # --------------------------------------------------------

    if (
        risk_result.action
        == "APPROVE_BONUS"
    ):

        decision = "APPROVED"

        bonus_status = (
            "RELEASED_SIMULATED"
        )

        observation_status = (
            "NOT_REQUIRED"
        )

    elif (
        risk_result.action
        == "VERIFY_CLAIM"
    ):

        decision = (
            "VERIFICATION_REQUIRED"
        )

        bonus_status = "HELD"

        observation_status = "PENDING"

    else:

        decision = "REJECTED"

        bonus_status = (
            "NOT_RELEASED"
        )

        observation_status = (
            "NOT_REQUIRED"
        )

    # --------------------------------------------------------
    # STEP 5 — PERSIST DECISION
    # --------------------------------------------------------

    record = {

        "claim_id": claim_id,

        "user_id": user_id,

        "referrer_id": (
            risk_result.referrer_id
        ),

        "bonus_amount": float(
            payload.bonus_amount
        ),

        "payment_id": (
            payload.payment_id
        ),

        "risk_score": (
            risk_result.risk_score
        ),

        "risk_level": (
            risk_result.risk_level
        ),

        "engine_action": (
            risk_result.action
        ),

        "decision": decision,

        "bonus_status": bonus_status,

        "reasons": (
            risk_result.reasons
        ),

        # These are the only features
        # available to the claim-time engine.
        "claim_time_features": features,

        "observation_status": (
            observation_status
        ),

        "observation_source": (
            "not_started"
            if observation_status
            == "PENDING"
            else None
        ),

        "policy": {

            "low_action": (
                "APPROVE_BONUS"
            ),

            "medium_action": (
                "HOLD_AND_OBSERVE"
            ),

            "high_action": (
                "REJECT_BONUS"
            ),

            "policy_version": (
                "1.2-autonomous-observation"
            ),
        },

        # Safety:
        # no real payout happens from this demo endpoint.
        "dry_run": True,

        "money_moved": False,

        "created_at": (
            datetime.utcnow()
            .isoformat()
        ),

        "timestamp": (
            datetime.utcnow()
            .isoformat()
        ),
    }

    append_jsonl(
        CLAIM_DECISIONS_FILE,
        record,
    )

    return record


# ============================================================
# AUTONOMOUS CLAIM OBSERVATION
# ============================================================

@app.post(
    "/claim-observation/{claim_id}/resolve"
)
def resolve_claim(
    claim_id: str,
):

    # --------------------------------------------------------
    # STEP 1 — FIND CLAIM
    # --------------------------------------------------------

    claim = find_latest_claim(
        claim_id
    )

    if claim is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Claim not found: {claim_id}"
            ),
        )

    # --------------------------------------------------------
    # STEP 2 — ONLY OBSERVE HELD CLAIMS
    # --------------------------------------------------------

    if (
        claim.get("decision")
        != "VERIFICATION_REQUIRED"
    ):

        return {

            "claim_id": claim_id,

            "status": "NOT_APPLICABLE",

            "decision": (
                claim.get(
                    "decision"
                )
            ),

            "bonus_status": (
                claim.get(
                    "bonus_status"
                )
            ),

            "message": (
                "Autonomous observation "
                "is only required for "
                "claims initially placed "
                "on hold."
            ),
        }

    user_id = str(
        claim["user_id"]
    )

    # --------------------------------------------------------
    # STEP 3 — REPLAY POST-SIGNUP BEHAVIOUR
    # --------------------------------------------------------

    try:

        observation = (
            claim_observation_engine.observe(
                user_id=user_id
            )
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    # --------------------------------------------------------
    # STEP 4 — AUTONOMOUS RESOLUTION
    # --------------------------------------------------------

    if (
        observation.action
        == "APPROVE_BONUS"
    ):

        final_decision = (
            "APPROVED"
        )

        final_bonus_status = (
            "RELEASED_SIMULATED"
        )

        observation_status = (
            "RESOLVED"
        )

    elif (
        observation.action
        == "KEEP_HELD"
    ):

        final_decision = (
            "VERIFICATION_REQUIRED"
        )

        final_bonus_status = (
            "HELD"
        )

        observation_status = (
            "STILL_HELD"
        )

    else:

        final_decision = (
            "REJECTED"
        )

        final_bonus_status = (
            "NOT_RELEASED"
        )

        observation_status = (
            "RESOLVED"
        )

    # --------------------------------------------------------
    # STEP 5 — PERSIST RESOLUTION
    # --------------------------------------------------------

    resolution = {

        "claim_id": claim_id,

        "user_id": user_id,

        "referrer_id": (
            claim.get(
                "referrer_id"
            )
        ),

        "bonus_amount": (
            claim.get(
                "bonus_amount"
            )
        ),

        "payment_id": (
            claim.get(
                "payment_id"
            )
        ),

        # Original decision
        "initial_decision": (
            claim.get(
                "decision"
            )
        ),

        "initial_risk_score": (
            claim.get(
                "risk_score"
            )
        ),

        # Behavioural observation
        "behavior_score": (
            observation.observation_score
        ),

        "observation_score": (
            observation.observation_score
        ),

        "observation_action": (
            observation.action
        ),

        "observation_evidence": (
            observation.reasons
        ),

        # Final decision
        "decision": final_decision,

        "final_decision": (
            final_decision
        ),

        "bonus_status": (
            final_bonus_status
        ),

        "observation_status": (
            observation_status
        ),

        "observation_source": (
            "post_signup_behavior_replay"
        ),

        "reasons": (
            observation.reasons
        ),

        "policy": {

            "initial_medium_action": (
                "HOLD_AND_OBSERVE"
            ),

            "observation_low_action": (
                "APPROVE_BONUS"
            ),

            "observation_medium_action": (
                "KEEP_HELD"
            ),

            "observation_high_action": (
                "REJECT_BONUS"
            ),

            "policy_version": (
                "1.2-autonomous-observation"
            ),
        },

        # No real money is moved in this demo.
        "dry_run": True,

        "money_moved": False,

        "resolved_at": (
            datetime.utcnow()
            .isoformat()
        ),

        "timestamp": (
            datetime.utcnow()
            .isoformat()
        ),
    }

    append_jsonl(
        CLAIM_DECISIONS_FILE,
        resolution,
    )

    return resolution


# ============================================================
# CLAIM DECISION HISTORY
# ============================================================

@app.get("/claim-decisions")
def claim_decisions(
    user_id: str | None = None,
    claim_id: str | None = None,
):

    # --------------------------------------------------------
    # Specific claim
    # --------------------------------------------------------

    if claim_id:

        claim = find_latest_claim(
            claim_id
        )

        if claim is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Claim not found: {claim_id}"
                ),
            )

        return {

            "claims": [claim],

            "count": 1,
        }

    # --------------------------------------------------------
    # Specific user
    # --------------------------------------------------------

    if user_id:

        rows = find_claims_for_user(
            user_id
        )

    # --------------------------------------------------------
    # Everything
    # --------------------------------------------------------

    else:

        rows = read_jsonl(
            CLAIM_DECISIONS_FILE
        )

    return {

        "claims": rows,

        "count": len(rows),
    }


# ============================================================
# RAZORPAY WEBHOOK
# ============================================================

@app.post(
    "/webhook/razorpay/payment"
)
async def razorpay_payment_webhook(
    request: Request,
):

    body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    webhook_secret = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET"
    )

    # --------------------------------------------------------
    # VERIFY WEBHOOK SIGNATURE
    # --------------------------------------------------------

    if (
        webhook_secret
        and signature
    ):

        import hashlib
        import hmac

        expected_signature = (
            hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256,
            )
            .hexdigest()
        )

        if not hmac.compare_digest(
            expected_signature,
            signature,
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid webhook signature"
                ),
            )

    # --------------------------------------------------------
    # PARSE EVENT
    # --------------------------------------------------------

    try:

        event = json.loads(
            body.decode(
                "utf-8"
            )
        )

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid JSON payload"
            ),
        )

    event_name = event.get(
        "event",
        "unknown",
    )

    payment_entity = (
        event
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    payment_id = (
        payment_entity.get(
            "id"
        )
    )

    method = (
        payment_entity.get(
            "method"
        )
    )

    event_id = (
        event.get("account_id")
        or payment_id
        or (
            f"event_"
            f"{datetime.utcnow().timestamp()}"
        )
    )

    # --------------------------------------------------------
    # LOG WEBHOOK
    # --------------------------------------------------------

    record = {

        "event_id": str(
            event_id
        ),

        "event": event_name,

        "payment_id": payment_id,

        "method": method,

        "received": True,

        "timestamp": (
            datetime.utcnow()
            .isoformat()
        ),
    }

    append_jsonl(
        WEBHOOK_EVENTS_FILE,
        record,
    )

    return {

        "received": True,

        "event": event_name,

        "payment_id": payment_id,
    }


# ============================================================
# REPORT SUMMARY
# ============================================================

@app.get("/report/summary")
def report_summary():

    summary = {}

    metrics_file = (
        REPORTS_DIR / "metrics.json"
    )

    if metrics_file.exists():

        try:

            with open(
                metrics_file,
                "r",
                encoding="utf-8",
            ) as f:

                summary["metrics"] = (
                    json.load(f)
                )

        except Exception:

            summary["metrics"] = {}

    else:

        summary["metrics"] = {}

    # --------------------------------------------------------
    # CLAIM SUMMARY
    # --------------------------------------------------------

    claims = read_jsonl(
        CLAIM_DECISIONS_FILE
    )

    summary["claim_decisions"] = {

        "total": len(claims),

        "approved": sum(
            1
            for x in claims
            if x.get("decision")
            == "APPROVED"
        ),

        "verification_required": sum(
            1
            for x in claims
            if x.get("decision")
            == "VERIFICATION_REQUIRED"
        ),

        "rejected": sum(
            1
            for x in claims
            if x.get("decision")
            == "REJECTED"
        ),
    }

    return summary


# ============================================================
# RAZORPAY TEST ORDER
# ============================================================

@app.post(
    "/razorpay/test-order"
)
def create_test_order():

    amount_paise = 1000

    try:

        order = (
            razorpay_client.create_order(
                amount_paise=amount_paise,
                currency="INR",
            )
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return order


# ============================================================
# DEMO CLUSTER PROCESSING
# ============================================================

@app.get(
    "/demo/process-cluster"
)
def process_demo_cluster(
    cluster_id: str,
):

    import pandas as pd

    features_path = (
        DATA_DIR / "cluster_features.csv"
    )

    if not features_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "cluster_features.csv not found"
            ),
        )

    df = pd.read_csv(
        features_path
    )

    rows = df[
        df["cluster_id"]
        .astype(str)
        == str(cluster_id)
    ]

    if rows.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Cluster not found: {cluster_id}"
            ),
        )

    cluster_row = rows.iloc[0]

    scoring = cluster_scorer.score(
        cluster_row
    )

    return {

        "cluster_id": (
            scoring.cluster_id
        ),

        "risk_score": (
            scoring.risk_score
        ),

        "model_action": (
            scoring.action
        ),

        "top_reasons": (
            scoring.top_reasons
        ),

        "cluster_size": (
            scoring.cluster_size
        ),

        "total_bonus_at_stake": (
            scoring.total_bonus_at_stake
        ),

        "policy_version": (
            scoring.policy_version
        ),

        "dry_run": True,

        "money_moved": False,

        "message": (
            "Cluster scored successfully. "
            "Existing payout-gate logic remains "
            "responsible for payout execution."
        ),
    }


# ============================================================
# RAZORPAY EVENT DEMO
# ============================================================

@app.get(
    "/demo/razorpay-event"
)
def process_demo_razorpay_event(
    payment_id: str,
    cluster_id: str,
):

    return {

        "payment_id": payment_id,

        "cluster_id": cluster_id,

        "status": "OBSERVED",

        "message": (
            "Razorpay Test Mode payment observed. "
            "Merchant-side cluster mapping is used "
            "for the fraud-risk demo."
        ),

        "dry_run": True,

        "money_moved": False,
    }