from app.verification.mutation import changed_python_lines, mutate_python_line


def test_changed_python_lines_only_reports_added_hunk_lines() -> None:
    diff = (
        "diff --git a/coupon.py b/coupon.py\n"
        "--- a/coupon.py\n+++ b/coupon.py\n"
        "@@ -2,2 +2,3 @@\n"
        " context\n-old\n+new\n+other\n"
        "diff --git a/readme.md b/readme.md\n"
        "--- a/readme.md\n+++ b/readme.md\n"
        "@@ -1 +1 @@\n-old\n+new\n"
    )
    assert changed_python_lines(diff) == {"coupon.py": [3, 4]}


def test_mutation_flips_only_operator_on_changed_line_outside_string() -> None:
    source = 'label = "x > y"\nreturn amount > 0\n'
    mutation = mutate_python_line(source, 2)
    assert mutation is not None
    assert mutation.source == 'label = "x > y"\nreturn amount >= 0\n'
    assert mutation.operator == "> to >="
    assert mutate_python_line(source, 1) is None
