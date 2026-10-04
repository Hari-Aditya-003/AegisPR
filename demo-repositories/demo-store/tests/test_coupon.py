from decimal import Decimal

from store.coupon import apply_coupon


def test_applies_normal_coupon() -> None:
    assert apply_coupon(Decimal("100"), Decimal("10")) == Decimal("90")
