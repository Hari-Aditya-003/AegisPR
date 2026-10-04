# Demo Store

This small Python fixture creates the three-minute AegisPR demonstration.

The baseline clamps a coupon discount at zero. Apply `seeded-regression.patch` on a branch to remove the boundary and open a public pull request. Existing tests continue to pass because they cover only a normal discount. AegisPR should hypothesize that the discount can exceed the cart total, generate a boundary test, and produce `BASE PASS + PR FAIL`.

```bash
python -m pytest -q
git switch -c demo/negative-coupon
git apply seeded-regression.patch
git add store/coupon.py
git commit -m "feat: simplify coupon calculation"
git push -u origin demo/negative-coupon
```
