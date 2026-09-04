🛡️ Abuse-Ring Sentinel

Autonomous referral-bonus fraud detection that separates coordinated abuse rings from legitimate friends and family — and gates payouts before money moves.

Built for the Razorpay AI Buildathon — Track 2: AI Risk Manager.

Goal: stop referral-bonus leakage without punishing genuine users.

Design principle: automate the repetitive risk decision, keep ambiguous cases explainable and auditable, and never move real money in this demo.

Why this matters

Referral programs are easy to abuse: one operator can create or control many identities, connect them through referrals, reuse devices/IPs/payment instruments, claim bonuses, and disappear.

The difficult part is that the same signals can appear in legitimate situations. A real family or group of friends may sign up around the same event, share Wi-Fi, or even share a payment instrument.

Abuse-Ring Sentinel therefore does not rely on a single rule. It combines:

Referral-graph structure — connected components, density, depth and fan-out

Identity reuse — device, IP and payment-instrument overlap

Signup behavior — burstiness and signup span

Post-signup behavior — transactions, transaction value, active days and engagement

Razorpay payment signals — test-mode payment fingerprints where available

Deterministic policy — converts risk into an autonomous payout action

Groq explanations — explains the decision; it does not control the decision

Architecture



End-to-end flow

Signup / referral / payment events
              │
              ▼
     Referral graph construction
              │
              ▼
       Feature engineering
       ├── graph signals
       ├── identity reuse
       ├── timing signals
       └── behavioral signals
              │
              ▼
     Fraud-ring risk scoring
              │
       ┌──────┼─────────┐
       ▼      ▼         ▼
     LOW    MEDIUM     HIGH
       │      │         │
       ▼      ▼         ▼
    APPROVE  HOLD     REJECT
              │
              ▼
     Autonomous observation
     for held claims
              │
       ┌──────┴───────┐
       ▼              ▼
    RELEASE         REJECT
       │
       ▼
 Razorpay payout gate

Important: the claim-time decision is made using signals available at claim time. Future behavioral activity is not used to make the initial claim decision. Held claims can optionally enter a second-stage observation flow using synthetic historical post-signup activity in this prototype.

What makes it autonomous?

Most fraud dashboards only tell an operator “this looks risky.” Sentinel goes one step further.

Stage 1 — Claim-time decision

When a user requests a referral bonus, the system immediately builds claim-time features and produces:

Risk

Decision

Outcome

< 0.30

APPROVE_BONUS

Release payout

0.30 – < 0.70

VERIFY_CLAIM

Hold payout

≥ 0.70

REJECT_BONUS

Do not release payout

The decision is deterministic and auditable.

Stage 2 — Autonomous observation

A held claim can be observed against post-signup activity.

The observation engine considers:

transaction count

transaction value

active days

evidence of genuine engagement

It can convert a held claim into:

HELD → APPROVE_BONUS

or

HELD → REJECT_BONUS

without requiring a person to manually perform the same checks.

For the demo, this behavioral activity is replayed from the synthetic dataset. In production, the same interface can consume a merchant's transaction/event stream or webhook events.

Key signals

Signal

Why it matters

Referral connections

Reveals coordinated referral structures

Device reuse

Many identities controlled from a small device set

IP reuse

Detects shared infrastructure across accounts

Payment-instrument reuse

Strong evidence that apparently different users may share a financial source

Connected-user count

Measures the size of the local abuse network

Multi-signal overlap

Stronger than any single reused attribute

Referral count

Helps identify unusually aggressive referrers

Transaction activity

Helps distinguish bonus farming from genuine users

Active days

Genuine users tend to show continued activity

Transaction value

Helps identify claims with little/no genuine economic activity

AI / ML roles

The system deliberately separates decisioning from explanation.

Machine learning

The cluster-level detector uses a trained classifier over graph, identity and behavioral features.

It is evaluated on a held-out synthetic test set rather than reporting training performance.

Graph analysis

NetworkX is used to construct the referral graph and identify connected components that become candidate clusters.

Groq

Groq is used for human-readable explanations of deterministic decisions.

The LLM receives the computed decision and supporting facts and explains why the system reached that decision.

The LLM is not the payout authority and cannot override the risk policy.

Razorpay integration

The repository includes a Razorpay Test Mode integration.

Payments

The Razorpay client can extract a payment fingerprint from supported payment methods, including:

card identifiers

UPI VPA information

wallet/other method identifiers where available

These fingerprints become identity-linking signals rather than being treated as standalone proof of fraud.

Webhooks

The FastAPI service exposes:

POST /webhook/razorpay/payment

The webhook path is observation-oriented: it records payment events and fingerprints for downstream risk analysis.

Payout gate

Approved decisions can pass through the payout gate.

For this buildathon demo:

DRY_RUN_PAYOUTS=true

so no real money moves.

The integration is therefore safe to demonstrate using Razorpay Test Mode credentials.

Evaluation

The current benchmark uses a synthetically generated dataset containing fraud-ring clusters, family/friend clusters and organic users.

Held-out test results

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

These numbers are intentionally presented as synthetic benchmark results, not production claims.

The test set contains difficult variants including stealthier fraud rings and legitimate bursty family/friend behavior.

False-positive cost

False positives matter because wrongly holding a genuine user's reward creates:

manual-review cost

support overhead

user friction

goodwill/reputation risk

The pipeline therefore tracks false-positive cost separately rather than treating every error as equivalent.

Demo scenarios

🟢 Genuine user

LOW RISK
   ↓
APPROVE_BONUS
   ↓
RELEASED_SIMULATED

No suspicious network overlap → bonus can be released.

🟠 Ambiguous friend/family case

MEDIUM RISK
   ↓
VERIFY_CLAIM
   ↓
HELD
   ↓
AUTONOMOUS OBSERVATION
   ↓
APPROVED / REJECTED

The system avoids immediately penalizing a user when the evidence is ambiguous.

🔴 Coordinated abuse

HIGH RISK
   ↓
REJECT_BONUS
   ↓
NOT_RELEASED

Multiple overlapping identity signals and a connected referral network can push the claim into the high-risk band.

API

Start the backend with:

uvicorn src.api.main:app --reload --port 8000

Core endpoints

Endpoint

Purpose

GET /health

Service and policy health

POST /claim-bonus

Evaluate a bonus claim

GET /claim-decisions

Inspect claim decisions

POST /claim-observation/{claim_id}/resolve

Run autonomous observation on a held claim

POST /score-cluster

Score a referral cluster

GET /clusters/{cluster_id}

Inspect a cluster

POST /webhook/razorpay/payment

Receive Razorpay payment events

GET /report/summary

Read evaluation/report summary

Interactive API documentation is available through FastAPI at:

http://localhost:8000/docs

Dashboard

The Streamlit dashboard provides:

cluster risk overview

fraud-ring/network visualization

risk scores and contributing signals

claim-level decisions

autonomous observation for held claims

payout-gate status

Groq-generated explanations

audit-oriented decision history

Run:

streamlit run dashboard.py

Project structure

abuse-ring-sentinel/
├── dashboard.py
├── run_pipeline.py
├── requirements.txt
├── .env.example
├── reference/
│   └── disposable_domains.txt
├── src/
│   ├── api/
│   │   └── main.py
│   ├── external_apis/
│   │   ├── disposable_email.py
│   │   └── ip_geolocation.py
│   ├── features/
│   │   ├── build_features.py
│   │   └── claim_features.py
│   ├── model/
│   │   └── train_eval.py
│   ├── pipeline/
│   │   ├── claim_observation.py
│   │   ├── claim_risk.py
│   │   ├── generate_dashboard.py
│   │   └── score_cluster.py
│   └── razorpay_integration/
│       ├── client.py
│       ├── payout_gate.py
│       └── run_autonomous_demo.py
└── tests/

Generated datasets and reports are intentionally excluded from Git.

Quick start

1. Clone

git clone https://github.com/<your-username>/abuse-ring-sentinel.git
cd abuse-ring-sentinel

2. Create an environment

Windows PowerShell

python -m venv .venv
.venv\Scripts\Activate.ps1

macOS / Linux

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Configure environment variables

copy .env.example .env

Then add your test-mode credentials if you want to exercise the Razorpay integration.

Never commit .env.

5. Run the pipeline

python run_pipeline.py

This generates the synthetic data, engineers features, trains/evaluates the model and produces the reports used by the dashboard.

6. Start the API

uvicorn src.api.main:app --reload --port 8000

7. Start the dashboard

In another terminal:

streamlit run dashboard.py

8. Run tests

python -m pytest tests/ -v

Auditability

Every decision is designed to be inspectable.

A claim decision records:

claim/user identifier

risk score

decision

supporting signals

policy version

timestamp

payout outcome

observation outcome where applicable

This makes the system easier to debug, evaluate and explain to a risk/operations team.

Defense-only scope

This project is intentionally built as a defensive risk-management system.

It does not:

generate fraud techniques

help bypass fraud detection

attack external systems

retaliate against users

automatically ban accounts

move real money in the demo

Its purpose is to reduce fraudulent bonus payouts while minimizing unnecessary friction for legitimate users.

Limitations & production path

This is a buildathon prototype, not a production fraud platform.

Current limitations

Evaluation data is synthetic.

Real-world fraud patterns will be noisier and more adaptive.

Payment-instrument reuse is powerful but not universally available.

Production thresholds require calibration against labeled incidents.

The autonomous observation stage currently replays synthetic historical behavior.

Production evolution

A production implementation could add:

real-time signup/referral/payment event ingestion

streaming graph updates

stronger entity-resolution signals

online threshold calibration

merchant-specific fraud policies

human-review feedback loops

model monitoring and drift detection

cloud deployment and persistent audit storage

Why this approach?

The objective is not simply to predict “fraud / not fraud.”

The useful question for a payout system is:

“Can we safely release this bonus right now, or should the system take another action?”

Abuse-Ring Sentinel turns that question into an autonomous, explainable workflow:

DETECT → SCORE → DECIDE → OBSERVE IF NEEDED → GATE PAYOUT

That is the core idea behind the project: remove repetitive risk-review work while keeping decisions measurable, explainable and safe.

License

MIT