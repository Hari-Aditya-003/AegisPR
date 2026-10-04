from decimal import Decimal


def apply_coupon(total: Decimal, discount: Decimal) -> Decimal:
    """Apply a non-negative discount without producing a negative total."""
    if total < 0 or discount < 0:
        raise ValueError("total and discount must be non-negative")
    return max(total - discount, Decimal("0"))
