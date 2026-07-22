"""Regression tests — run:  ./.venv/bin/python -m pytest -q  (pip install pytest once)."""
import re

import app


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
