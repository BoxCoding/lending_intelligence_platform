"""Unit tests for the Firestore REST typed-value encode/decode logic.

Pure functions, no network — the live REST round-trip against the real
project is verified manually (see docs/DEPLOYMENT.md); this covers the
encoding contract itself.
"""

from app.db.store import _decode_fields, _decode_value, _encode_value


class TestEncodeValue:
    def test_none_becomes_null_value(self):
        assert _encode_value(None) == {"nullValue": None}

    def test_bool_becomes_boolean_value(self):
        assert _encode_value(True) == {"booleanValue": True}
        assert _encode_value(False) == {"booleanValue": False}

    def test_bool_checked_before_int(self):
        # bool is an int subclass in Python; must not fall into the int branch
        encoded = _encode_value(True)
        assert "booleanValue" in encoded
        assert "integerValue" not in encoded

    def test_int_becomes_integer_value_as_string(self):
        assert _encode_value(42) == {"integerValue": "42"}

    def test_float_becomes_double_value(self):
        assert _encode_value(3.14) == {"doubleValue": 3.14}

    def test_string_becomes_string_value(self):
        assert _encode_value("HOT") == {"stringValue": "HOT"}

    def test_dict_becomes_map_value(self):
        encoded = _encode_value({"a": 1, "b": "x"})
        assert encoded == {
            "mapValue": {"fields": {"a": {"integerValue": "1"}, "b": {"stringValue": "x"}}}
        }

    def test_list_becomes_array_value(self):
        encoded = _encode_value([1, "x", True])
        assert encoded == {
            "arrayValue": {
                "values": [
                    {"integerValue": "1"},
                    {"stringValue": "x"},
                    {"booleanValue": True},
                ]
            }
        }

    def test_nested_structures(self):
        encoded = _encode_value({"offers": [{"amount": 500000.0, "active": True}]})
        assert encoded["mapValue"]["fields"]["offers"]["arrayValue"]["values"][0] == {
            "mapValue": {
                "fields": {
                    "amount": {"doubleValue": 500000.0},
                    "active": {"booleanValue": True},
                }
            }
        }

    def test_unknown_type_falls_back_to_string(self):
        class Weird:
            def __str__(self):
                return "weird-repr"

        assert _encode_value(Weird()) == {"stringValue": "weird-repr"}


class TestDecodeValue:
    def test_null_value(self):
        assert _decode_value({"nullValue": None}) is None

    def test_boolean_value(self):
        assert _decode_value({"booleanValue": True}) is True

    def test_integer_value(self):
        assert _decode_value({"integerValue": "42"}) == 42
        assert isinstance(_decode_value({"integerValue": "42"}), int)

    def test_double_value(self):
        assert _decode_value({"doubleValue": 3.14}) == 3.14

    def test_string_value(self):
        assert _decode_value({"stringValue": "HOT"}) == "HOT"

    def test_timestamp_value_passthrough(self):
        assert _decode_value({"timestampValue": "2026-07-08T00:00:00Z"}) == "2026-07-08T00:00:00Z"

    def test_map_value(self):
        decoded = _decode_value(
            {"mapValue": {"fields": {"a": {"integerValue": "1"}, "b": {"stringValue": "x"}}}}
        )
        assert decoded == {"a": 1, "b": "x"}

    def test_array_value(self):
        decoded = _decode_value(
            {"arrayValue": {"values": [{"integerValue": "1"}, {"stringValue": "x"}]}}
        )
        assert decoded == [1, "x"]

    def test_empty_map_value(self):
        assert _decode_value({"mapValue": {}}) == {}

    def test_empty_array_value(self):
        assert _decode_value({"arrayValue": {}}) == []

    def test_unrecognised_type_returns_none(self):
        assert _decode_value({"geoPointValue": {"latitude": 1, "longitude": 2}}) is None


class TestDecodeFields:
    def test_empty_fields(self):
        assert _decode_fields({}) == {}

    def test_multiple_fields(self):
        fields = {
            "score": {"doubleValue": 82.8},
            "tier": {"stringValue": "HOT"},
            "active": {"booleanValue": True},
        }
        assert _decode_fields(fields) == {"score": 82.8, "tier": "HOT", "active": True}


class TestRoundTrip:
    def test_encode_then_decode_preserves_value(self):
        original = {
            "customer_id": "CUST00024",
            "score": 82.8,
            "tier": "HOT",
            "active": True,
            "fraud_indicators": [],
            "components": {"intent": 73.2, "risk": 98.0},
            "offers": [{"product": "Personal Loan", "amount": 500000}],
            "note": None,
        }
        encoded = {k: _encode_value(v) for k, v in original.items()}
        decoded = _decode_fields(encoded)
        assert decoded == original
