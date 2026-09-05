import re
import hashlib

_TIMING_COMMENT = re.compile(rb"<!--\s*cached or not being index\.aspx page\s*-->\s*<!--\s*Elapsed time:.*?-->")

def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalize_for_hash(body: bytes, content_type: str) -> bytes:
    if content_type != "html":
        return body
    return _TIMING_COMMENT.sub(b"", body)
