import json

def parse_inbound(body: bytes) -> dict:
    return json.loads(body.decode("utf-8") or "{}")
