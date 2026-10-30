from types import SimpleNamespace

from app.services import review as review_service


def _business():
    return SimpleNamespace(
        id=1,
        business_name="Dentistry by Gupta Dental",
        business_desc="Dental clinic",
        seo_keyword=["dentist"],
    )


def test_variants_fall_back_when_provider_raises(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(review_service._provider, "generate", fail)

    reviews = review_service.generate_review_variants(_business(), rating=5, count=5)

    assert len(reviews) == 5
    assert all(reviews)
    assert len(set(reviews)) == 5


def test_variants_fall_back_when_worker_pool_cannot_start(monkeypatch):
    class BrokenPool:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("can't start new thread")

    monkeypatch.setattr(review_service, "ThreadPoolExecutor", BrokenPool)

    reviews = review_service.generate_review_variants(_business(), rating=4, count=5)

    assert len(reviews) == 5
    assert all(reviews)
