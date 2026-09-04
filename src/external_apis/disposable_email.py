"""
disposable_email.py

Checks whether a signup email uses a known disposable/temp-mail domain —
a common tell for fake identities in a referral-farming ring (real friends
and family use their normal Gmail/Outlook/Yahoo addresses).

Rather than depending on a live third-party "disposable email API" (most
require a paid key, and this project must run reliably offline/in CI), we
bundle the free, open-source domain list maintained at:

    https://github.com/disposable-email-domains/disposable-email-domains

(MIT licensed, community-maintained, ~8,700 domains at time of writing).
It lives at reference/disposable_domains.txt (kept OUTSIDE data/, since
data/ is regenerated/wiped by the synthetic pipeline). Refresh it any time
with:

    curl -o reference/disposable_domains.txt \\
      https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf
"""
import os

_DEFAULT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "reference", "disposable_domains.txt"
)

_domain_set_cache = None


def _load_domains(path: str = _DEFAULT_PATH) -> set:
    global _domain_set_cache
    if _domain_set_cache is not None:
        return _domain_set_cache
    try:
        with open(path) as f:
            _domain_set_cache = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
    except FileNotFoundError:
        _domain_set_cache = set()
    return _domain_set_cache


def is_disposable_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain in _load_domains()


def disposable_ratio(emails: list) -> float:
    """Share of a cluster's emails that come from disposable domains."""
    if not emails:
        return 0.0
    flagged = sum(1 for e in emails if is_disposable_email(e))
    return flagged / len(emails)
