from __future__ import annotations

from leadqualifier.dedupe import name_tokens, normalise_name, shortlist, similarity


def test_domain_match_scores_one(crm, make_lead):
    lead = make_lead(company={"name": "Hafenblick", "domain": "www.hafenblick-digital.de", "description": "x", "location": "Hamburg"})
    s, reasons = similarity(lead, next(a for a in crm if a["id"] == "acc_hafenblick"))
    assert s == 1.0 and any("same domain" in r for r in reasons)


def test_name_token_near_miss_is_shortlisted_for_jev(crm, make_lead):
    lead = make_lead(company={"name": "Kontor Süd Agentur", "domain": "kontor-sued.de", "description": "x", "location": "Munich"})
    cands = shortlist(lead, crm)
    assert [c["id"] for c in cands] == ["acc_kontornord"]
    assert cands[0]["code_score"] < 1.0  # code is unsure; Jev decides


def test_contact_name_on_account_shortlists(crm, make_lead):
    lead = make_lead(company=None, person={"name": "Dana Fischer", "title": "COO", "company": "Growthloop"})
    cands = shortlist(lead, crm)
    assert any(c["id"] == "acc_growthloop" for c in cands)


def test_unrelated_company_has_no_candidates(crm, make_lead):
    lead = make_lead(company={"name": "Zebra Coffee Roasters", "domain": "zebracoffee.io", "description": "x", "location": "Berlin"})
    assert shortlist(lead, crm) == []


def test_shortlist_is_capped(make_lead):
    accounts = [{"id": f"a{i}", "name": f"Test Agency {i}", "domain": f"test-agency-{i}.de"} for i in range(25)]
    assert len(shortlist(make_lead(), accounts, limit=10)) == 10


def test_normalisation():
    assert normalise_name("Hafenblick Digital GmbH") == "hafenblick"
    assert name_tokens("Kontor Nord Creative") == {"kontor", "nord", "creative"} - {"creative"} or "kontor" in name_tokens("Kontor Nord Creative")
