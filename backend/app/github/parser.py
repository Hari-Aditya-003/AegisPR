from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class PullRequestReference:
    owner: str
    repository: str
    number: int


def parse_pull_request_url(value: str) -> PullRequestReference:
    message = "A public GitHub pull request URL is required"
    try:
        parsed = urlparse(value.strip())
        parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username
            or parsed.password
            or parsed.port
            or len(parts) != 4
            or parts[2] != "pull"
        ):
            raise ValueError(message)
        number = int(parts[3])
        if number < 1 or not parts[0] or not parts[1]:
            raise ValueError(message)
        return PullRequestReference(owner=parts[0], repository=parts[1], number=number)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc

