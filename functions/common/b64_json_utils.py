import base64

import simplejson


def b64_encode_json(obj):
    json_bytes = simplejson.dumps(obj).encode('utf-8')
    json_b64_str = base64.b64encode(json_bytes).decode('ascii')
    return json_b64_str


def b64_decode_json_safe(probably_b64_str):
    if isinstance(probably_b64_str, str):
        json_bytes = base64.b64decode(probably_b64_str)
        obj = simplejson.loads(json_bytes.decode('utf-8'))
        return obj
    return probably_b64_str
