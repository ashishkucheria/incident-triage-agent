"""Tests for templating and masking."""
import pytest

from incident_triage.templating import mask, template


def test_lines_differing_only_by_ids_share_a_template():
    a = "Receiving block blk_-160899 src: /10.250.19.102:54106 dest: /10.250.19.102:50010"
    b = "Receiving block blk_750348 src: /10.251.215.16:55695 dest: /10.251.215.16:50010"
    assert template(a) == template(b) == "Receiving block <BLK> src: <IP> dest: <IP>"


@pytest.mark.parametrize("a, b, expected", [
    ("failed after 3.5s", "failed after 42.25s", "failed after <NUM>s"),
    ("waited 200ms", "waited 5ms", "waited <NUM>ms"),
    ("used 64MB", "used 128MB", "used <NUM>MB"),
])
def test_numbers_with_units_share_a_template(a, b, expected):
    assert template(a) == template(b) == expected


def test_unknown_suffix_is_never_half_replaced():
    assert template("speedup 3.5x") == "speedup 3.5x"


def test_uuid_is_replaced_whole():
    text = "conn 550e8400-e29b-41d4-a716-446655440000 closed"
    assert template(text) == "conn <UUID> closed"


# Fake values, shaped like real secrets.
SECRETS = [
    ("Authorization: Bearer eyJhbGciOi.abc.def", "eyJhbGciOi.abc.def"),
    ("Authorization: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
    ('Authorization: Digest username="bob", response="6629fae49393a053"', "6629fae49393a053"),
    ("Authorization: abc123def", "abc123def"),
    ("Proxy-Authorization: Negotiate YIIFzQYGKwYB", "YIIFzQYGKwYB"),
    ("sent bearer abc123def456", "abc123def456"),
    ("jwt eyJhbGciOi.eyJzdWIi.sig rejected", "eyJhbGciOi.eyJzdWIi.sig"),
    ("using key AKIAIOSFODNN7EXAMPLE", "AKIAIOSFODNN7EXAMPLE"),
    ("key sk-" + "a" * 24 + " refused", "sk-" + "a" * 24),
    ("password=hunter2", "hunter2"),
    ('{"password": "hunter2"}', "hunter2"),
    ('{"user":"bob","api_key":"abc123"}', "abc123"),
    ("{'token': 'two words'}", "two words"),
]


@pytest.mark.parametrize("line, secret", SECRETS)
def test_secrets_are_removed_by_mask_and_template(line, secret):
    assert secret not in mask(line)
    assert secret not in template(line)


def test_ordinary_text_is_not_masked():
    line = "bearer authentication failed for block blk_123"
    assert mask(line) == line
