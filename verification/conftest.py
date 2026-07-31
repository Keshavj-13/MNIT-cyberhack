"""Shared pytest setup for the verification suite."""
import os

# Dev secrets are fine for verification; suppresses the JWT warning and keeps
# the crypto/JWT paths on their default keys.
os.environ.setdefault("ALLOW_DEFAULT_SECRETS", "1")
