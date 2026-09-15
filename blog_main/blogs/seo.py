import json

from django.core.serializers.json import DjangoJSONEncoder


JSON_SCRIPT_ESCAPES = {
    ord('>'): r'\u003E',
    ord('<'): r'\u003C',
    ord('&'): r'\u0026',
    ord('\u2028'): r'\u2028',
    ord('\u2029'): r'\u2029',
}


def serialize_json_ld(value):
    """Serialize JSON-LD while preventing user text from ending a script tag."""
    return json.dumps(
        value,
        cls=DjangoJSONEncoder,
        ensure_ascii=True,
        separators=(',', ':'),
    ).translate(JSON_SCRIPT_ESCAPES)
