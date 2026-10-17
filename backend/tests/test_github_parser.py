import pytest

from app.github.parser import PullRequestReference, parse_pull_request_url


def test_parses_canonical_public_github_pull_request_url() -> None:
    assert parse_pull_request_url("https://github.com/acme/store/pull/42") == PullRequestReference(
        owner="acme", repository="store", number=42
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/acme/store/pull/42",
        "https://evil.example/acme/store/pull/42",
        "https://github.com/acme/store/issues/42",
        "https://github.com/acme/store/pull/0",
        "file:///etc/passwd",
        "not-a-url",
        "https://github.com/../store/pull/42",
        "https://github.com/acme/../pull/42",
        "https://github.com/acme/store/pull/+42",
        "https://github.com/acme/store/pull/٤٢",
        "https://github.com/acme/store/pull/42?redirect=example.com",
        "https://github.com/acme/store/pull/42#anything",
        "https://github.com/acme%2fother/store/pull/42",
    ],
)
def test_rejects_noncanonical_or_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError, match="public GitHub pull request"):
        parse_pull_request_url(url)

