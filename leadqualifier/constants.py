"""Everything a human should review lives here: model pin, price, the question texts, the
score rubrics and the fixed option sets.

The question set is a *function of the ICP* (industries, personas, pains, disqualifiers are
the client's plain-English profile) plus two lead-specific parts: the sentence ids of the
lead's text (for evidence Choices) and the CRM accounts shortlisted by code (for the
entity-alignment Choice). Nothing here talks to the network.

Design rules applied (docs.typesafe.ai): one atomic judgement per question; Score levels are
concrete situations, never adjectives; every Choice has an `other`/`none` option because
probabilities always sum to 1; anything arithmetic (weights, tiers, thresholds) is in
`scoring.py`, not here. The ICP lives in the *criteria*, not the state, so editing one pain
changes the fingerprint of exactly the questions about that pain.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

MODEL = "jev-1.13.0"  # pinned: aliases (jev-latest) move on release
BASE_URL = "https://api.typesafe.ai"
PRICE_PER_M_INPUT_TOKENS = 0.042  # USD; output tokens are free
SDR_MINUTES_PER_LEAD = 6  # what a human spends reading, looking up and routing one inbound
MAX_CRM_CANDIDATES = 10
MAX_SENTENCES = 40

TEXT_FIELDS_HINT = "`message`, `company.description`, `company.news` and `person.bio`"

# --------------------------------------------------------------------------- fixed rubrics

MATURITY_LEVELS = [
    "Pre-revenue or hobby: an idea, a side project, a student, or a business that says it has no paying clients yet",
    "One person with some paying clients: a freelancer, solo consultant or solo coach working alone",
    "A small team of two to ten people with a steady base of paying clients and recurring revenue",
    "An established company of roughly eleven to fifty people with several teams, structured delivery and a management layer",
    "A large organisation: more than fifty employees, several offices, a corporate group or a listed company",
]

AUTHORITY_LEVELS = [
    "No purchasing authority: a student, intern, junior employee, assistant, or an outsider such as a vendor or journalist",
    "Influences the decision but must ask someone else: a team lead, specialist or manager who would need approval",
    "Decides for their own department or budget line: a head of, director or department owner",
    "Decides for the whole company: founder, owner, CEO or managing director",
]

INTENT_LEVELS = [
    "No buying intent: the text is not about purchasing anything from the recipient (a vendor pitch, a student request, a bare company profile, small talk)",
    "Curious: asks what the recipient does or whether something is possible, without describing a concrete need of their own",
    "Exploring a concrete need: describes a specific problem they want solved but does not ask for next steps",
    "Asking for next steps: asks for a call, a demo, a proposal, a quote or pricing",
    "Ready to buy: asks for a call or proposal and also states a timeline, a budget, or an already approved project",
]

TIMELINE_OPTIONS = {
    "this_month": "Wants to start or decide within the next few weeks: 'this month', 'ASAP', 'this week', or before an imminent date",
    "this_quarter": "Within the next two or three months: 'this quarter', 'before Q4', 'in the autumn'",
    "later": "Later this year, next year, 'eventually', or 'someday'",
    "not_stated": "No timing is stated at all",
}

OBJECTION_OPTIONS = {
    "price": "Raises cost concerns: says the budget is tight, asks whether it is expensive, compares to cheaper options",
    "timing": "Says now is not the right moment: too busy, after a launch, next year",
    "trust": "Doubts whether AI or automation works, worries about quality, data protection, or mentions a bad past experience",
    "none": "No objection is raised",
}

SIZE_BAND_DESCRIPTIONS = {
    "solo": "Exactly one person: 'just me', 'solo', 'freelancer working alone'",
    "2-10": "Two to ten people (a written head count, 'small team of five', 'we are eight')",
    "11-50": "Eleven to fifty people",
    "51-200": "Fifty-one to two hundred people",
    "200+": "More than two hundred people",
}

# --------------------------------------------------------------------------- question builder


MESSAGE_ONLY = ("is_vendor_pitch", "asks_for_meeting", "urgency", "objection_present", "is_spam_or_automated", "contains_pii_request")


def build_questions(icp: dict[str, Any], sentence_ids: list[str] | None = None,
                    crm_candidates: list[dict[str, Any]] | None = None,
                    playbook: dict[str, Any] | None = None, has_message: bool = True) -> dict[str, dict[str, Any]]:
    """The full question map for one lead under one ICP (raw API dicts). Ids are ours.

    Questions that only make sense for a written message (`MESSAGE_ONLY`) are left out for bare
    profiles and bios: asking "is this message spam?" about a null message produces a confident
    yes, which is the literal-reading failure mode the docs warn about.
    """
    q: dict[str, dict[str, Any]] = {}
    sentence_ids = sentence_ids or []
    crm_candidates = crm_candidates or []

    # ---- ICP fit
    q["industry"] = {
        "type": "choice",
        "instructions": {
            "question": "Which industry best describes the company behind this lead?",
            "focus": "Use `company` first (description, services, news). If `company` is null, infer from `person.bio` and from how the sender describes their own business in `message`. Judge what the company does for a living, not what it is asking about.",
        },
        "criteria": {**{k: v for k, v in icp["industries"].items()},
                     "other": "None of the listed industries, or the company's line of business cannot be determined from the text"},
    }
    q["company_maturity"] = {
        "type": "score",
        "instructions": {
            "question": "Which situation best matches the company behind this lead?",
            "focus": f"Judge from {TEXT_FIELDS_HINT}: head count, number of clients, revenue, offices, team structure. A bare profile with no size information is judged by what it says about clients and services.",
        },
        "criteria": MATURITY_LEVELS,
    }
    q["size_band_stated"] = {
        "type": "choice",
        "instructions": {
            "question": "Which team or employee size does the text explicitly state for the company?",
            "focus": f"Only use a head count or team size actually written in `company.size`, {TEXT_FIELDS_HINT}. Do not infer size from revenue, number of clients, tone or job titles. When nothing is written, choose not_stated.",
        },
        "criteria": {**{b: SIZE_BAND_DESCRIPTIONS.get(b, b) for b in icp["size_bands"]},
                     "not_stated": "No head count or team size is written anywhere in the text"},
    }
    q["revenue_band_stated"] = {
        "type": "choice",
        "instructions": {
            "question": "Which revenue band does the text explicitly state for the company?",
            "focus": f"Only use revenue, turnover, MRR or 'we bill X per month' figures actually written in {TEXT_FIELDS_HINT}. Do not infer revenue from team size, client count or tone. When no figure is written, choose not_stated.",
        },
        "criteria": {**{b: icp["revenue_band_labels"].get(b, b) for b in icp["revenue_bands"]},
                     "not_stated": "No revenue or turnover figure is written anywhere in the text"},
    }
    q["geo_fit"] = {
        "type": "noul",
        "instructions": {
            "question": f"Is the company or person located in this region: {icp['geography']}?",
            "focus": "Answer yes when a stated location (`company.location`, `person.location`, or a place named in the text) is inside the region, and also when no location is stated at all. Answer no only when a stated location is clearly outside the region.",
        },
    }
    for dq_id, desc in icp["disqualifiers"].items():
        q[f"dq_{dq_id}"] = {
            "type": "noul",
            "instructions": {"question": f"Does this lead match the following disqualifier: {desc}?",
                             "focus": f"Judge from {TEXT_FIELDS_HINT}. Answer yes only when the text actually shows it."},
            "criteria": {"true": "The text shows this about the lead's company or the sender", "false": "The text does not show it, or shows the opposite"},
        }

    # ---- buyer relevance
    q["persona"] = {
        "type": "choice",
        "instructions": {
            "question": "Which role does the sender or profiled person hold at their company?",
            "focus": "Use `person.title` and `person.bio` first. If `person` is null, use how the sender describes themselves in `message` (signature, 'I run', 'I'm the founder of').",
        },
        "criteria": {**{k: v["description"] for k, v in icp["personas"].items()},
                     "other": "A role not listed: junior staff, intern, assistant, sales representative, student, or the role cannot be determined"},
    }
    q["decision_authority"] = {
        "type": "score",
        "instructions": {"question": "How much purchasing authority does the sender or profiled person have at their company?",
                         "focus": "Judge from title, bio and how they write ('I decide', 'I would need to ask my boss')."},
        "criteria": AUTHORITY_LEVELS,
    }
    q["is_vendor_pitch"] = {
        "type": "noul",
        "instructions": {"question": "Is the sender of `message` trying to sell, pitch or offer their own product, service, partnership, guest post or agency to the recipient?",
                         "focus": "Yes when the sender offers something to the recipient. No when the sender is asking to buy help or asking a question about the recipient's services."},
    }
    q["is_student_or_jobseeker"] = {
        "type": "noul",
        "instructions": "Is the sender a student, researcher, journalist or job seeker asking for an interview, thesis or survey input, an internship, a job, or career advice?",
    }
    q["is_competitor"] = {
        "type": "noul",
        "instructions": {"question": "Does the company or person behind this lead themselves build or sell AI automation, AI agents, automation consulting, workflow automation or no-code implementation services?",
                         "focus": "Judge what they sell, from `company.description`, `company.services`, `person.bio` and `message`. A company that merely wants to buy automation is not a competitor."},
    }

    # ---- pains (one Noul each) and evidence sentences (one Choice each, when there is text)
    for pain_id, pain in icp["pains"].items():
        desc = pain["description"]
        q[f"pain_{pain_id}"] = {
            "type": "noul",
            "instructions": {"question": f"Does the text indicate this problem at the lead's own company: {desc}?",
                             "focus": f"Judge from {TEXT_FIELDS_HINT}. The problem must be theirs, not a problem they solve for others."},
            "criteria": {"true": "The text describes this problem at their company, or asks for help with it, in their own words",
                         "false": "The text does not mention this problem, or only mentions it as a service they offer to others"},
        }
        if sentence_ids:
            q[f"evidence_{pain_id}"] = {
                "type": "choice",
                "instructions": {"question": f"Which entry in `sentences` most directly indicates this problem at the lead's own company: {desc}?",
                                 "focus": "Pick the single most direct sentence. Choose none when no sentence indicates it."},
                "criteria": {**{sid: None for sid in sentence_ids}, "none": "No sentence indicates this problem"},
            }

    # ---- intent
    q["purchase_intent"] = {
        "type": "score",
        "instructions": {"question": "How far along is the sender towards buying help from the recipient?",
                         "focus": "Judge `message` first; if `message` is null, judge only from `company.news` and `person.bio` (a bare profile is usually level 0 or 1)."},
        "criteria": INTENT_LEVELS,
    }
    if sentence_ids:
        q["intent_evidence"] = {
            "type": "choice",
            "instructions": {"question": "Which entry in `sentences` most directly shows that the sender wants to buy or hire help: asks for a call, proposal, demo or pricing, or states a timeline or budget?",
                             "focus": "Pick the single most direct sentence. Choose none when no sentence shows it."},
            "criteria": {**{sid: None for sid in sentence_ids}, "none": "No sentence shows buying intent"},
        }
    q["timeline_stated"] = {
        "type": "choice",
        "instructions": {"question": "What timing does the sender state for starting or deciding?",
                         "focus": "Only use timing actually written in `message` or `company.news`. Choose not_stated when none is written."},
        "criteria": TIMELINE_OPTIONS,
    }
    q["budget_signal"] = {"type": "noul", "instructions": "Does the text mention a budget, an approved spend, a price range they can pay, or that money has been set aside for this?"}
    q["urgency"] = {"type": "noul", "instructions": "Does `message` express urgency about their own situation: 'ASAP', 'drowning', 'urgent', 'cannot keep up', 'before the launch', a deadline?"}
    q["asks_for_meeting"] = {"type": "noul", "instructions": "Does `message` ask for a call, meeting, demo, chat or conversation with the recipient?"}
    q["objection_present"] = {
        "type": "choice",
        "instructions": "Which objection, if any, does the sender raise in `message`?",
        "criteria": OBJECTION_OPTIONS,
    }

    # ---- message quality / safety
    q["is_spam_or_automated"] = {"type": "noul", "instructions": "Is `message` spam, an automated notification, a bulk mailing, an out-of-office reply or gibberish, rather than a person writing to the recipient on purpose?"}
    q["contains_pii_request"] = {"type": "noul", "instructions": "Does `message` ask the recipient to share personal data, credentials, payment details or confidential documents: passwords, bank details, ID copies, client lists, contracts?"}

    # ---- dedupe: entity alignment against the CRM shortlist
    if crm_candidates:
        q["same_account"] = {
            "type": "choice",
            "instructions": {"question": "Is the company behind this lead the same organisation as one of the CRM accounts listed as options?",
                             "focus": "Compare company name, domain, location and what they do. Different spelling or a person's e-mail domain matching the account domain counts as the same organisation. Choose none when it is a different company or when there is not enough information."},
            "criteria": {**{c["id"]: {"name": c["name"], "domain": c.get("domain"), "about": c.get("about")} for c in crm_candidates[:MAX_CRM_CANDIDATES]},
                         "none": "A different company, or not enough information to tell"},
        }

    # ---- next best action from the fixed playbook
    if playbook:
        q["next_best_action"] = {
            "type": "choice",
            "instructions": {"question": "Which playbook action should the recipient take next with this lead?",
                             "focus": "Choose by what the sender asked for and how well they fit; the descriptions say when each action applies."},
            "criteria": {k: v["description"] for k, v in playbook.items()},
        }
    if not has_message:
        for qid in MESSAGE_ONLY:
            q.pop(qid, None)
    return q


# --------------------------------------------------------------------------- grouping & fingerprints

GROUP_ORDER = ["fit", "relevance", "pain", "intent", "quality", "dedupe", "action"]


def group_of(qid: str) -> str:
    if qid in ("industry", "company_maturity", "size_band_stated", "revenue_band_stated", "geo_fit") or qid.startswith("dq_"):
        return "fit"
    if qid in ("persona", "decision_authority", "is_vendor_pitch", "is_student_or_jobseeker", "is_competitor"):
        return "relevance"
    if qid.startswith("pain_") or qid.startswith("evidence_"):
        return "pain"
    if qid in ("purchase_intent", "intent_evidence", "timeline_stated", "budget_signal", "urgency", "asks_for_meeting", "objection_present"):
        return "intent"
    if qid in ("is_spam_or_automated", "contains_pii_request"):
        return "quality"
    if qid == "same_account":
        return "dedupe"
    return "action"


def fingerprint(question: dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(question, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def fingerprints(questions: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {qid: fingerprint(q) for qid, q in questions.items()}


def describe_questions(questions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Read-only view for the UI: id, type, group, one-line text, option count."""
    out = []
    for qid, q in questions.items():
        inst = q.get("instructions")
        text = inst if isinstance(inst, str) else (inst or {}).get("question", json.dumps(inst))
        crit = q.get("criteria")
        n_opts = len(crit) if isinstance(crit, (dict, list)) else 0
        out.append({"id": qid, "type": q["type"], "group": group_of(qid), "text": text, "n_options": n_opts,
                    "options": list(crit) if isinstance(crit, dict) else (crit if isinstance(crit, list) else [])})
    return out
