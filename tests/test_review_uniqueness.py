from app.db.models import UserBusiness
from app.services import review as review_service
from app.services.review import _is_too_similar


def test_identical_review_is_rejected_despite_case_and_punctuation():
    existing = ["The staff were kind, professional, and explained everything clearly."]
    candidate = "The STAFF were kind professional and explained everything clearly!"

    assert _is_too_similar(candidate, existing)


def test_clearly_different_review_is_allowed():
    existing = ["The staff were kind and explained everything clearly."]
    candidate = "Booking was simple, and the waiting area was clean and comfortable."

    assert not _is_too_similar(candidate, existing)


def test_single_review_retries_when_provider_repeats_profile_history(monkeypatch):
    outputs = iter([
        "The staff were kind and explained everything clearly.",
        "Booking felt simple, and the waiting area was calm and comfortable.",
    ])

    class FakeProvider:
        def generate(self, prompt, max_tokens=200, temperature=0.8):
            return next(outputs)

    monkeypatch.setattr(review_service, "_provider", FakeProvider())
    business = UserBusiness(
        id=1,
        name="Owner",
        user_name="test-business",
        business_name="Test Business",
        email="owner@example.com",
        seo_keyword=[],
        mobile_no="",
        review_link="",
        business_desc="A local business",
    )

    result = review_service.generate_review_text(
        business=business,
        rating=5,
        excluded_reviews=["The staff were kind and explained everything clearly."],
    )

    assert result == "Booking felt simple, and the waiting area was calm and comfortable."
