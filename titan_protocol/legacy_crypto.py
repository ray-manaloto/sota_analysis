# legacy_crypto.py
# CRITICAL: This represents a rigid enterprise dependency.
def secure_hash(data: str) -> str:
    """Proprietary legacy hashing algorithm. DO NOT MODIFY."""
    return f"TITAN_{hash(data)}_ENCRYPTED"
