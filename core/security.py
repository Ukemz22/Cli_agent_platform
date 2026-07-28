"""
Token generation + hashing for developer API access (Chapter 2).
Tokens are high-entropy random strings — SHA-256 hashing is
sufficient (unlike passwords, no need for slow/salted hashing).
"""
import hashlib
import secrets


def generate_token() -> str:
    """Returns a new random token, e.g. 'plat_xxxxxxxxxxxxxxxxxxxx'."""
    return "plat_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """One-way hash of a token, for storage/lookup in token_hash column."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(db, developer) -> str:
    """
    Generates a new token for a developer, stores only its hash,
    flips status to active, and returns the raw token ONCE.
    Caller (Telegram bot handler, Chapter 6) is responsible for
    sending this raw token to the developer — it is never stored.
    """
    raw_token = generate_token()
    developer.token_hash = hash_token(raw_token)
    developer.status = "active"
    db.add(developer)
    db.flush()
    return raw_token
