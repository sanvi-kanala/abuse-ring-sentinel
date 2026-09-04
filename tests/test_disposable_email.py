from src.external_apis.disposable_email import is_disposable_email, disposable_ratio


def test_known_disposable_domain():
    assert is_disposable_email("someone@mailinator.com") is True


def test_normal_domain():
    assert is_disposable_email("someone@gmail.com") is False


def test_case_insensitive():
    assert is_disposable_email("Someone@MAILINATOR.COM") is True


def test_malformed_email():
    assert is_disposable_email("not-an-email") is False
    assert is_disposable_email("") is False


def test_disposable_ratio():
    emails = ["a@gmail.com", "b@mailinator.com", "c@yahoo.com", "d@yopmail.com"]
    assert disposable_ratio(emails) == 0.5
