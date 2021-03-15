import base64

import simplejson


def b64_encode_json(obj):
    json_bytes = simplejson.dumps(obj).encode('utf-8')
    b64_str = base64.b64encode(json_bytes).decode('ascii')
    return b64_str


def b64_decode_json(b64_str):
    if b64_str is None:
        return None
    json_bytes = base64.b64decode(b64_str)
    obj = simplejson.loads(json_bytes.decode('utf-8'))
    return obj


def b64_decode_json_safe(probably_b64_str):
    if isinstance(probably_b64_str, str):
        # TODO oleksandr: also check if probably_b64_str actually contains base64-encoded data ?
        return b64_encode_json(probably_b64_str)
    return probably_b64_str
