"""Regression tests — run:  ./.venv/bin/python -m pytest -q  (pip install pytest once)."""
import json
import re

import pytest

import app


def test_strip_json_survives_fences_and_trailing_prose():
    # Trigger: a hard input (a card photographed on its blank side) makes the model
    # wrap the JSON in a fence and append a sentence explaining what it couldn't
    # find — which used to fail the whole parse with "Extra data: line 4 column 1".
    body = json.dumps({"givenName": "Mei", "confidence": 40})
    assert app._strip_json(body)["givenName"] == "Mei"
    assert app._strip_json(f"```json\n{body}\n```")["givenName"] == "Mei"
    assert app._strip_json(f"Here is the contact:\n\n{body}")["givenName"] == "Mei"
    assert app._strip_json(
        f"```json\n{body}\n```\n\nNote: no name is visible on this side of the card."
    )["confidence"] == 40
    with pytest.raises(ValueError):
        app._strip_json("I could not find any contact details in this image.")


def test_every_simple_field_has_a_dom_input():
    # A SIMPLE entry without a matching id in the HTML is silently dropped in the
    # browser round-trip (the countryCode bug) — catch that wiring gap here.
    m = re.search(r"const SIMPLE=\[(.*?)\]", app.HTML, re.S)
    fields = re.findall(r"'(\w+)'", m.group(1))
    assert fields, "SIMPLE list not found in HTML"
    for f in fields:
        assert f'id="{f}"' in app.HTML, f"SIMPLE field '{f}' has no input in the HTML"


def test_contact_body_maps_all_fields():
    c = {"honorificPrefix": "Dr.", "givenName": "Mei", "familyName": "Chen",
         "company": "Acme", "jobTitle": "CTO",
         "phones": [{"value": "+86 138 0000 0000", "type": "mobile"},
                    {"value": "", "type": "work"}],
         "emails": [{"value": "mei@acme.cn", "type": "work"}],
         "street": "1 Nanjing Rd", "city": "Shanghai", "region": "",
         "postalCode": "200000", "country": "China", "countryCode": "CN",
         "website": "https://acme.cn",
         "socials": [{"value": "https://linkedin.com/in/mei", "type": "profile"}],
         "notes": "Jul 2026"}
    b = app.contact_body(c)
    assert b["names"] == [{"honorificPrefix": "Dr.", "givenName": "Mei",
                           "familyName": "Chen"}]
    assert b["organizations"] == [{"name": "Acme", "title": "CTO"}]
    assert b["phoneNumbers"] == [{"value": "+86 138 0000 0000", "type": "mobile"}]
    assert b["emailAddresses"] == [{"value": "mei@acme.cn", "type": "work"}]
    assert b["addresses"] == [{"streetAddress": "1 Nanjing Rd", "city": "Shanghai",
                               "region": "", "postalCode": "200000",
                               "country": "China", "countryCode": "CN"}]
    assert b["urls"] == [{"value": "https://acme.cn", "type": "homePage"},
                         {"value": "https://linkedin.com/in/mei", "type": "profile"}]
    assert b["biographies"] == [{"value": "Jul 2026"}]


def test_contact_body_empty_input_gives_empty_body():
    assert app.contact_body({}) == {}


def _png(tag):
    # Minimal bytes with a PNG mimetype — the stubbed parser never decodes them.
    import io
    return (io.BytesIO(b"\x89PNG" + tag.encode()), f"{tag}.png", "image/png")


def test_parse_sends_every_page_in_order(monkeypatch):
    # Trigger: a two-sided card — the second photo used to replace the first,
    # so the back side (often the other-language name) never reached Claude.
    seen = []
    monkeypatch.setattr(app, "claude_parse", lambda blocks: seen.extend(blocks) or {})
    r = app.app.test_client().post("/parse", data={
        "text": "", "image": [_png("front"), _png("back")]})
    assert r.status_code == 200
    imgs = [b for b in seen if b["type"] == "image"]
    assert [app.base64.b64decode(b["source"]["data"])[4:] for b in imgs] == [b"front", b"back"]


def test_parse_rejects_more_than_max_pages(monkeypatch):
    monkeypatch.setattr(app, "claude_parse", lambda blocks: {})
    r = app.app.test_client().post("/parse", data={
        "image": [_png(f"p{i}") for i in range(app.MAX_PAGES + 1)]})
    assert r.status_code == 400
    assert "pages" in r.get_json()["error"]
