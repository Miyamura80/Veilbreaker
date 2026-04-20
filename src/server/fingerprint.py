from hashlib import sha256


def fingerprint_secret(secret: str, *, salt: str = "", length: int = 12) -> str:
    """Create a stable short fingerprint for a secret."""
    if not secret:
        raise ValueError("secret must be non-empty")
    if length <= 0:
        raise ValueError("length must be positive")

    material = f"{salt}:{secret}" if salt else secret
    return sha256(material.encode("utf-8")).hexdigest()[:length]
