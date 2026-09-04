🛡️ Abuse-Ring Sentinel

Autonomous referral-bonus fraud detection that separates coordinated abuse from legitimate friends and family.

Built for the Razorpay AI Buildathon 2026 — Track 02: AI Risk Manager.

Core idea: Don't automatically punish every suspicious-looking referral. Detect coordinated abuse, protect the bonus while evidence is incomplete, observe subsequent behaviour, and resolve the claim autonomously.

🎯 The Problem

Referral programs create a simple economic target for coordinated abuse:

Create many synthetic-looking accounts

Connect them through referrals

Reuse devices, IPs, or payment instruments

Claim referral bonuses

Disappear before creating genuine customer value

The difficult part is that legitimate groups can look similar.

A family at the same gathering may share Wi-Fi and refer one another. A group of friends may sign up within minutes. A detector based on a single rule can therefore create expensive false positives.

Abuse-Ring Sentinel treats this as a network-risk problem rather than a single-account rule problem.

🚀 What Sentinel Does

Sentinel runs an autonomous two-stage protection workflow.

                REFERRAL BONUS CLAIM
                         │
                         ▼
              ┌─────────────────────┐
              │ Claim-time analysis  │
              │                     │
              │ • Device reuse      │
              │ • IP reuse          │
              │ • Instrument reuse  │
              │ • Referral network  │
              └──────────┬──────────┘
                         │
                         ▼
                    RISK SCORE
                  /      |       \
                 /       |        \
             LOW       MEDIUM      HIGH
              │          │          │
              ▼          ▼          ▼
           APPROVE      HOLD      REJECT
                         │
                         ▼
              🤖 AUTONOMOUS OBSERVATION
                         │
                         ▼
              Post-signup behaviour
              • Transactions
              • Transaction value
              • Active days
                         │
                    ┌────┴────┐
                    ▼         ▼
                 APPROVE    REJECT

Why two stages?

The first decision uses only information available when the bonus is claimed.

If the evidence is ambiguous, Sentinel protects the bonus rather than immediately releasing it. A later observation stage can use behavioural evidence to resolve the held claim.

This removes the need for a human to manually inspect every medium-risk claim.

🧠 Detection Signals

No individual signal is treated as proof of fraud.

Signal

Coordinated abuse tends to show

Legitimate groups can show

Referral graph

Dense referral bursts / hub-heavy structures

Natural branching

Signup timing

Highly concentrated creation

Bursty during genuine events

Device reuse

Same devices across many identities

Occasional household overlap

IP reuse

Many accounts from the same IPs

Shared Wi-Fi

Payment instrument reuse

Same instrument across supposedly different identities

Occasional legitimate shared instrument

Post-signup behaviour

Bonus claim followed by weak activity

Continued genuine activity

The model combines these signals rather than relying on a single heuristic.

🏗️ Architecture

Synthetic / merchant event data
            │
            ▼
     Referral graph
     construction
            │
            ├───────────────┐
            ▼               ▼
     Graph features     Identity signals
            │               │
            │               ├── Device reuse
            │               ├── IP reuse
            │               └── Instrument reuse
            │
            └──────────┬────────────┘
                       ▼
              Fraud-ring classifier
                       │
                       ▼
                 Risk score
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
        APPROVE       HOLD        REJECT
                       │
                       ▼
             Autonomous observation
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          APPROVE              REJECT
                       │
                       ▼
             Razorpay Test Mode
             payout integration

AI roles

ML classifier

Produces the initial cluster risk score.

Evaluated on a held-out test set.

Deterministic policy

Converts risk into an operational action.

The policy, not the LLM, owns the final decision.

Groq

Provides a grounded natural-language explanation.

It does not override the risk score or decision.

Explanations are restricted to supplied evidence.

This separation keeps the decision path auditable.

🤖 Autonomous Bonus-Claim Workflow

At claim time, Sentinel builds signals from the user, referrer, and connected accounts.

Example:

User claims ₹308.57
        ↓
Risk score: 0.31
        ↓
MEDIUM RISK
        ↓
BONUS HELD
        ↓
Autonomous observation
        ↓
Behavioural evidence evaluated
        ↓
Final decision

The observation layer currently replays post-signup behavioural activity from the synthetic dataset:

num_txn_post_signup

total_txn_value_post_signup

active_days_post_signup

In a production deployment, these signals would come from the merchant's transaction/event stream.

💳 Razorpay Integration

Razorpay is integrated in Test Mode.

The project includes:

Razorpay Payments API integration

Payment-instrument fingerprint extraction

Razorpay webhooks for payment events

RazorpayX Test Mode payout integration

Autonomous payout gating

Dry-run protection so the demo does not move real money

The current demo can receive a payment.captured webhook and associate the observed payment with the merchant-side risk workflow.

Important: The prototype does not claim that the synthetic behavioural history comes directly from Razorpay. The synthetic dataset is used for reproducible evaluation and demonstration; Razorpay Test Mode demonstrates the payment integration boundary.

📊 Held-Out Evaluation

Results from the project's held-out synthetic benchmark:

Metric

Result

Precision

100%

Recall

95%

F1

97.4%

ROC-AUC

1.00

False positives

0

False negatives

2

Net value created

≈ ₹106,832

These are not production claims.

The benchmark is synthetic and intentionally contains difficult overlapping cases. Real production traffic would require additional calibration, monitoring, and labelled fraud outcomes.

Why false positives matter

A false positive can incorrectly hold a legitimate referral from a real family or friend group.

The evaluation therefore treats false-positive cost as a first-class metric rather than reporting accuracy alone.

🔐 Defense-Only Design

Abuse-Ring Sentinel is designed strictly as a fraud-loss prevention system.

It can:

Detect coordinated referral abuse

Calculate risk

Protect a bonus

Approve an eligible bonus

Reject a high-risk bonus

Record an auditable decision

It does not contain offensive capabilities or mechanisms for attacking, exploiting, or retaliating against users.

📁 Project Structure

abuse-ring-sentinel/
│
├── run_pipeline.py
├── requirements.txt
├── .env.example
├── README.md
│
├── data/
│   ├── users.csv
│   ├── referrals.csv
│   ├── payments.csv
│   └── cluster_features.csv
│
├── reports/
│   ├── metrics.json
│   ├── fraud_ring_model.joblib
│   ├── cluster_risk_scores.csv
│   ├── audit_log.jsonl
│   ├── bonus_ledger_demo.jsonl
│   └── webhook_events.jsonl
│
├── src/
│   ├── data/
│   │   └── generate_synthetic_data.py
│   │
│   ├── features/
│   │   ├── build_features.py
│   │   └── claim_features.py
│   │
│   ├── model/
│   │   └── train_eval.py
│   │
│   ├── pipeline/
│   │   ├── score_cluster.py
│   │   ├── claim_risk.py
│   │   └── claim_observation.py
│   │
│   ├── razorpay_integration/
│   │   ├── client.py
│   │   └── payout_gate.py
│   │
│   └── api/
│       └── main.py
│
└── tests/

⚙️ Local Setup

1. Create a virtual environment

python -m venv venv

Activate it:

Windows

venv\Scripts\activate

macOS / Linux

source venv/bin/activate

2. Install dependencies

pip install -r requirements.txt

3. Configure environment variables

Copy:

.env.example

to:

.env

For Razorpay testing, use Test Mode credentials beginning with:

rzp_test_

Never commit .env or live credentials to GitHub.

▶️ Run the Pipeline

python run_pipeline.py

The pipeline:

Generates the synthetic dataset

Builds referral-network features

Trains the fraud-ring classifier

Evaluates it on a held-out test set

Scores clusters

Generates reports used by the dashboard

🚀 Run the FastAPI Backend

python -m uvicorn src.api.main:app --reload --port 8000

Health check:

GET /health

Important endpoints include:

POST /claim-bonus
POST /claim-observation/{claim_id}/resolve
POST /webhook/razorpay/payment
POST /score-cluster
GET  /clusters/{cluster_id}
GET  /report/summary
GET  /claim-decisions

🖥️ Run the Streamlit Dashboard

The dashboard provides three main workspaces:

🗃️ Data & Graph — referral network and risk context

⚡ Bonus Claim — live claim-time autonomous workflow

🔗 Cluster Analysis — cluster risk, model results, policy and audit evidence

Run:

streamlit run dashboard_section_navigation_autonomous.py

For the claim workflow, the dashboard communicates with the FastAPI backend through:

SENTINEL_API_URL

For local development this defaults to:

http://127.0.0.1:8000

🧪 Testing

Run:

python -m pytest tests/ -v

The core pipeline and model evaluation are designed to work without requiring live external network access.

🔎 Example Decision Paths

Legitimate / low-risk claim

Claim
  ↓
LOW RISK
  ↓
APPROVED
  ↓
Bonus released in demo mode

Ambiguous claim resolved positively

Claim
  ↓
MEDIUM RISK
  ↓
BONUS HELD
  ↓
Autonomous observation
  ↓
Sufficient genuine behaviour
  ↓
APPROVED

Ambiguous claim resolved negatively

Claim
  ↓
MEDIUM RISK
  ↓
BONUS HELD
  ↓
Autonomous observation
  ↓
Insufficient genuine behaviour
  ↓
REJECTED

The important product behaviour is that the medium-risk path does not automatically become a human queue. Sentinel can protect the money while waiting for evidence and then resolve the claim.

🧾 Auditability

Every important decision is designed to retain:

Risk score

Decision/action

Evidence/reasons

User or cluster context

Policy version

Timestamp

Payout state

This makes the system suitable for operator review and post-decision analysis.

⚠️ Evaluation & Production Limitations

This project is a buildathon prototype, not a production fraud engine.

Important limitations:

Training/evaluation data is synthetic.

Production fraud labels would be required for calibration.

Behavioural observation is replayed from the prototype dataset.

Risk thresholds would need to be tuned against real business costs.

Payment-instrument reuse is a strong signal but is not sufficient by itself.

Legitimate households and shared networks can create correlated signals.

Production deployment would require privacy, retention, access-control, monitoring, and model-governance policies.

The goal is to demonstrate the architecture and autonomous decision loop, not to claim production-ready fraud accuracy.

🏆 Why This Fits the AI Risk Manager Track

The system addresses a concrete merchant-loss problem:

Referral bonus abuse.

Instead of simply generating a fraud score, Sentinel connects detection to an operational action:

DETECT
  ↓
PROTECT THE BONUS
  ↓
OBSERVE
  ↓
DECIDE
  ↓
RELEASE OR REJECT

The result is an autonomous risk-management workflow, not just a prediction model.

👥 Data Privacy

All personal information in the prototype dataset is synthetic.

Names, phone numbers, email addresses, addresses, device identifiers, IPs, and payment-instrument identifiers are generated for the project and are not intended to represent real users.

📜 License

This repository is a buildathon project and is provided for evaluation and demonstration purposes.