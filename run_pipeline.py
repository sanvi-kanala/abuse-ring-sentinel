import os
import subprocess
import sys


# Always run from the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

PYTHON = sys.executable

STEPS = [
    (
        "Generating synthetic referral ecosystem",
        [
            PYTHON,
            "src/data/generate_synthetic_data.py",
        ],
    ),
    (
        "Building cluster features",
        [
            PYTHON,
            "src/features/build_features.py",
        ],
    ),
    (
        "Training + evaluating the fraud-ring classifier",
        [
            PYTHON,
            "src/model/train_eval.py",
        ],
    ),
    (
        "Scoring all clusters (risk + audit trail)",
        [
            PYTHON,
            "-m",
            "src.pipeline.score_cluster",
        ],
    ),
    (
        "Building the dashboard",
        [
            PYTHON,
            "-m",
            "src.pipeline.generate_dashboard",
        ],
    ),
]


def run_step(name, command):
    print()
    print("=" * 70)
    print(name)
    print("=" * 70)
    print("Running:", " ".join(command))
    print()

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": PROJECT_ROOT,
        },
    )

    if result.returncode != 0:
        print()
        print(f"ERROR: {name} failed.")
        sys.exit(result.returncode)


def main():
    print("=" * 70)
    print("ABUSE-RING SENTINEL")
    print("Razorpay AI Buildathon — Track 02")
    print("=" * 70)

    print()
    print("Project root:")
    print(PROJECT_ROOT)

    for name, command in STEPS:
        run_step(name, command)

    print()
    print("=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print()
    print("Dashboard:")
    print(
        os.path.join(
            PROJECT_ROOT,
            "reports",
            "dashboard.html",
        )
    )


if __name__ == "__main__":
    main()