from app.core import rate_limit


def setup_function():
    rate_limit.reset_for_tests()


def test_same_request_retry_only_counts_once():
    identity = "profile|visitor:device-123"

    assert rate_limit.check(identity, "request-1") == (True, 0)
    assert rate_limit.check(identity, "request-1") == (True, 0)
    assert rate_limit.check(identity, "request-1") == (True, 0)
    assert rate_limit.check(identity, "request-2") == (True, 0)
    assert rate_limit.check(identity, "request-3") == (True, 0)

    allowed, retry_after = rate_limit.check(identity, "request-4")
    assert not allowed
    assert retry_after > 0


def test_different_visitors_do_not_share_limit():
    first = "profile|visitor:device-123"
    second = "profile|visitor:device-456"

    for index in range(3):
        assert rate_limit.check(first, f"first-{index}") == (True, 0)

    assert rate_limit.check(second, "second-1") == (True, 0)
