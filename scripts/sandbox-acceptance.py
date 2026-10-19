"""Backward-compatible entry point for the shared credential-free acceptance CLI."""
from app.services.fixture_acceptance import main


if __name__ == "__main__":
    raise SystemExit(main())
