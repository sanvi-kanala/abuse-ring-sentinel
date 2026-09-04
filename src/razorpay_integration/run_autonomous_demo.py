"""
run_autonomous_demo.py

Judge-friendly demonstration of the complete autonomous bonus decision flow.

Flow:

    cluster_features.csv
            ↓
       ML risk scorer
            ↓
    initial policy decision
            ↓
    autonomous secondary verification
            ↓
    final bonus action
            ↓
       clean ledger

No real money is moved unless Razorpay TEST MODE credentials are configured.
"""

import os
import json
import time
import pandas as pd

from src.razorpay_integration.payout_gate import PayoutGate


FEATURES_PATH = "data/cluster_features.csv"
LEDGER_PATH = "reports/bonus_ledger_demo.jsonl"


def money(value):
    return f"INR {value:,.2f}"


def main():

    print("=" * 74)
    print("ABUSE-RING SENTINEL")
    print("AUTONOMOUS REFERRAL BONUS DECISION DEMO")
    print("=" * 74)

    if not os.path.exists(FEATURES_PATH):
        raise FileNotFoundError(
            f"Missing {FEATURES_PATH}. Run the pipeline first."
        )

    df = pd.read_csv(FEATURES_PATH)

    gate = PayoutGate()

    # ---------------------------------------------------------------
    # INITIAL ML POLICY DISTRIBUTION
    # ---------------------------------------------------------------

    print("\n" + "-" * 74)
    print("1. INITIAL ML POLICY DECISIONS")
    print("-" * 74)

    initial_results = []

    for _, row in df.iterrows():

        score = gate.scorer.score(row)

        initial_results.append({
            "cluster_id": row["cluster_id"],
            "risk_score": score.risk_score,
            "initial_decision": score.action,
            "bonus": float(row["total_bonus_claimed"]),
        })

    initial_df = pd.DataFrame(initial_results)

    initial_counts = (
        initial_df["initial_decision"]
        .value_counts()
    )

    print(
        initial_counts.to_string()
    )

    # ---------------------------------------------------------------
    # AUTONOMOUS PROCESSING
    # ---------------------------------------------------------------

    print("\n" + "-" * 74)
    print("2. AUTONOMOUS BONUS PROCESSING")
    print("-" * 74)

    # Clean demo ledger.
    if os.path.exists(LEDGER_PATH):
        os.remove(LEDGER_PATH)

    final_results = []

    verification_results = []

    for _, row in df.iterrows():

        initial_decision = initial_df.loc[
            initial_df["cluster_id"] == row["cluster_id"],
            "initial_decision",
        ].iloc[0]

        result = gate.process(
            cluster_row=row,
            account_number="demo_account",
            fund_account_id="demo_fund_account",
            narration="Abuse-Ring Sentinel referral bonus",
        )

        final_decision = result["decision"]

        verification = result.get("verification")

        if initial_decision == "HOLD_FOR_VERIFICATION":

            verification_results.append({
                "cluster_id": row["cluster_id"],
                "risk_score": result["risk_score"],
                "bonus": float(row["total_bonus_claimed"]),
                "verification": verification,
                "final_decision": final_decision,
            })

        final_results.append({
            "cluster_id": row["cluster_id"],
            "risk_score": result["risk_score"],
            "initial_decision": initial_decision,
            "final_decision": final_decision,
            "action_taken": result["action_taken"],
            "bonus": float(row["total_bonus_claimed"]),
        })

    final_df = pd.DataFrame(final_results)

    # ---------------------------------------------------------------
    # SECONDARY VERIFICATION REPORT
    # ---------------------------------------------------------------

    print("\n" + "-" * 74)
    print("3. SECONDARY VERIFICATION")
    print("-" * 74)

    if not verification_results:

        print("No ambiguous clusters required secondary verification.")

    else:

        for item in verification_results:

            verification = item["verification"]

            print(
                f"\nCluster: {item['cluster_id']}"
            )

            print(
                f"Risk score: {item['risk_score']:.4f}"
            )

            print(
                f"Bonus at stake: {money(item['bonus'])}"
            )

            print(
                f"Verification: "
                f"{'PASSED' if verification['passed'] else 'FAILED'}"
            )

            print(
                f"Checks passed: "
                f"{verification['passed_checks']}/"
                f"{verification['total_checks']}"
            )

            for check in verification["checks"]:

                status = "PASS" if check["passed"] else "FAIL"

                print(
                    f"  [{status}] "
                    f"{check['check']}: "
                    f"{check['value']} "
                    f"(threshold {check['threshold']})"
                )

            print(
                f"Final action: {item['final_decision']}"
            )

    # ---------------------------------------------------------------
    # FINANCIAL TOTALS
    # ---------------------------------------------------------------

    released = final_df[
        final_df["action_taken"].isin(
            [
                "BONUS_RELEASED",
                "BONUS_RELEASE_SIMULATED",
            ]
        )
    ]["bonus"].sum()

    blocked = final_df[
        final_df["action_taken"] == "BONUS_BLOCKED"
    ]["bonus"].sum()

    held = final_df[
        final_df["action_taken"] == "BONUS_HELD"
    ]["bonus"].sum()

    # ---------------------------------------------------------------
    # FINAL DECISION DISTRIBUTION
    # ---------------------------------------------------------------

    print("\n" + "=" * 74)
    print("4. FINAL AUTONOMOUS DECISION")
    print("=" * 74)

    print(
        final_df["final_decision"]
        .value_counts()
        .to_string()
    )

    print("\nBonus action totals:")

    print(
        f"  Released/simulated : {money(released)}"
    )

    print(
        f"  Blocked            : {money(blocked)}"
    )

    print(
        f"  Held               : {money(held)}"
    )

    # ---------------------------------------------------------------
    # DECISION TRANSITION
    # ---------------------------------------------------------------

    initially_held = initial_df[
        initial_df["initial_decision"] == "HOLD_FOR_VERIFICATION"
    ]

    verification_released = final_df[
        (final_df["initial_decision"] == "HOLD_FOR_VERIFICATION")
        & (
            final_df["final_decision"] == "RELEASE"
        )
    ]

    verification_held = final_df[
        (final_df["initial_decision"] == "HOLD_FOR_VERIFICATION")
        & (
            final_df["final_decision"] == "HOLD_FOR_VERIFICATION"
        )
    ]

    print("\nAutonomous verification transitions:")

    print(
        f"  Initially ambiguous : {len(initially_held)}"
    )

    print(
        f"  Automatically released after verification : "
        f"{len(verification_released)}"
    )

    print(
        f"  Remained held : "
        f"{len(verification_held)}"
    )

    # ---------------------------------------------------------------
    # SAFETY SUMMARY
    # ---------------------------------------------------------------

    print("\n" + "-" * 74)
    print("5. SAFETY / MONEY MOVEMENT")
    print("-" * 74)

    if gate.client.is_configured():

        print(
            "Razorpay TEST MODE credentials detected."
        )

        print(
            "Approved RELEASE decisions may create TEST MODE payouts."
        )

    else:

        print(
            "Razorpay credentials not configured."
        )

        print(
            "No external payout was created."
        )

        print(
            "Approved payouts were safely simulated."
        )

    print(
        "\nBLOCK_BONUS decisions never call the payout API."
    )

    print(
        "No account suspension or punitive action is performed."
    )

    # ---------------------------------------------------------------
    # SAVE DEMO LEDGER
    # ---------------------------------------------------------------

    os.makedirs(
        os.path.dirname(LEDGER_PATH),
        exist_ok=True,
    )

    with open(
        LEDGER_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        for record in final_results:

            f.write(
                json.dumps(
                    {
                        **record,
                        "policy_version": "1.1-autonomous",
                        "processed_at": time.time(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    # ---------------------------------------------------------------
    # COMPLETE
    # ---------------------------------------------------------------

    print("\n" + "=" * 74)
    print("AUTONOMOUS DEMO COMPLETE")
    print("=" * 74)

    print(
        f"\nDemo ledger -> {LEDGER_PATH}"
    )

    print(
        "Every cluster was processed without human intervention."
    )


if __name__ == "__main__":
    main()