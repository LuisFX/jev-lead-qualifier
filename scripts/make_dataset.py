"""Writes the synthetic dataset: data/leads/*.json (one file per lead), data/crm.json, data/gold.json.

Everything is invented. Companies, people and domains do not exist. The texts are authored
(not model-generated) so every lead has a known reason to land where it lands; the gold file
is the reference for the Accuracy panel and the integration tests.

    ./run.sh dataset
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADS = ROOT / "data" / "leads"
CRM = ROOT / "data" / "crm.json"
GOLD = ROOT / "data" / "gold.json"

# --------------------------------------------------------------------------- CRM (existing accounts)

ACCOUNTS = [
    {"id": "acc_hafenblick", "name": "Hafenblick Digital GmbH", "domain": "hafenblick-digital.de", "status": "customer", "owner": "Lena Berg",
     "about": "Performance marketing agency in Hamburg, 14 people; reporting automation live since March 2026",
     "contacts": [{"name": "Jonas Petersen", "title": "Managing Director"}]},
    {"id": "acc_kontornord", "name": "Kontor Nord Creative", "domain": "kontornord.de", "status": "customer", "owner": "Lena Berg",
     "about": "Brand and content agency in Hamburg, 20 people; onboarding automation project running",
     "contacts": [{"name": "Tim Ahrens", "title": "Founder"}]},
    {"id": "acc_brightpath", "name": "Brightpath Coaching Ltd", "domain": "brightpath-coaching.com", "status": "open opportunity", "owner": "Sara Nowak",
     "about": "Executive coaching business in Leeds, 6 people; proposal for applicant follow-up automation pending",
     "contacts": [{"name": "James Whitfield", "title": "Founder"}]},
    {"id": "acc_marlow", "name": "Studio Marlow", "domain": "studiomarlow.co.uk", "status": "churned", "owner": "Lena Berg",
     "about": "Design studio in London; reporting pilot paused in 2025 when the team shrank to 5",
     "contacts": [{"name": "Hugo Marlow", "title": "Founder"}]},
    {"id": "acc_nordwind", "name": "Nordwind Media GmbH", "domain": "nordwind-media.de", "status": "customer", "owner": "Jonas Falk",
     "about": "Video and social agency in Bremen, 12 people; content repurposing automation live",
     "contacts": [{"name": "Kim Nordwind", "title": "Owner"}]},
    {"id": "acc_klarsicht", "name": "Klarsicht PR", "domain": "klarsicht-pr.at", "status": "open opportunity", "owner": "Sara Nowak",
     "about": "PR boutique in Vienna, 9 people; media monitoring report automation being scoped",
     "contacts": [{"name": "Eva Lang", "title": "Managing Partner"}]},
    {"id": "acc_growthloop", "name": "Growthloop Agency", "domain": "growthloop.io", "status": "customer", "owner": "Jonas Falk",
     "about": "Performance marketing agency in Berlin, 28 people; lead follow-up and reporting automations live",
     "contacts": [{"name": "Dana Fischer", "title": "COO"}, {"name": "Leon Gruber", "title": "Founder"}]},
    {"id": "acc_mindful", "name": "Mindful Momentum Coaching", "domain": "mindfulmomentum.de", "status": "customer", "owner": "Lena Berg",
     "about": "Mindset coaching business in Cologne, 4 people; onboarding automation live",
     "contacts": [{"name": "Nadine Roth", "title": "Founder"}]},
    {"id": "acc_pixelwerk", "name": "Pixelwerk Studio AG", "domain": "pixelwerk.ch", "status": "open opportunity", "owner": "Sara Nowak",
     "about": "Web and brand studio in Zurich, 15 people; discovery call done",
     "contacts": [{"name": "Reto Amsler", "title": "CEO"}]},
    {"id": "acc_ostsee", "name": "Ostsee Social", "domain": "ostsee-social.de", "status": "lost", "owner": "Jonas Falk",
     "about": "Social media agency in Rostock, 6 people; chose an in-house solution in 2025",
     "contacts": [{"name": "Finn Larsen", "title": "Founder"}]},
    {"id": "acc_velvet", "name": "Velvet & Vine Branding", "domain": "velvetandvine.nl", "status": "customer", "owner": "Lena Berg",
     "about": "Branding studio in Amsterdam, 11 people; reporting automation live",
     "contacts": [{"name": "Noor de Wit", "title": "Creative Director"}]},
    {"id": "acc_bergblick", "name": "Bergblick Consulting", "domain": "bergblick-consulting.at", "status": "customer", "owner": "Jonas Falk",
     "about": "Business coaching and consulting in Salzburg, 8 people; applicant pipeline automation live",
     "contacts": [{"name": "Markus Bergblick", "title": "Owner"}]},
]

# --------------------------------------------------------------------------- helpers


def P(name, title, company, location=None, bio=None):
    d = {"name": name, "title": title, "company": company}
    if location:
        d["location"] = location
    if bio:
        d["bio"] = bio
    return d


def Co(name, domain, description, location, size=None, services=None, news=None, founded=None):
    d = {"name": name, "domain": domain, "description": description, "location": location}
    if size:
        d["size"] = size
    if services:
        d["services"] = services
    if news:
        d["news"] = news
    if founded:
        d["founded"] = founded
    return d


def M(text, subject=None, from_name=None, from_domain=None, channel=None):
    d = {"text": text}
    if subject:
        d["subject"] = subject
    if from_name:
        d["from_name"] = from_name
    if from_domain:
        d["from_domain"] = from_domain
    if channel:
        d["channel"] = channel
    return d


def L(id, source, day, gold, person=None, company=None, message=None, tags=None, note=None, persona=None, pain="__omit__"):
    h = sum(ord(c) for c in id)  # deterministic pseudo-time of day
    lead = {"id": id, "source": source, "received_at": f"2026-09-{day:02d}T{9 + (h % 8):02d}:{(h * 7) % 60:02d}:00Z",
            "person": person, "company": company, "message": message, "tags": tags or []}
    g = {"tier": gold}
    if persona:
        g["persona"] = persona
    if pain != "__omit__":
        g["primary_pain"] = pain
    if note:
        g["note"] = note
    return lead, g


# --------------------------------------------------------------------------- leads

ROWS = [
    # ===================================================================== HOT
    L("L001", "website_form", 14, "hot", persona="founder_owner", pain="manual_reporting", tags=["demo:vague_hot"],
      note="Vague but hot: no form fields filled, intent and pain live in the sentences",
      person=P("Mara Lindqvist", "Founder & Managing Director", "Lindqvist & Co Performance", "Hamburg, DE"),
      company=Co("Lindqvist & Co Performance", "lindqvist-performance.de", "Paid social and search agency for consumer brands in Germany and Scandinavia.", "Hamburg, DE",
                 services=["paid social", "Google Ads", "creative testing"]),
      message=M("Hi — we're drowning in reporting for 14 clients. Every month my team loses close to a week building decks and pulling numbers from Meta, Google and GA4 into slides. Do you do this? Could we talk this week?",
                subject="quick question", from_name="Mara Lindqvist", from_domain="lindqvist-performance.de")),
    L("L002", "email_reply", 15, "hot", persona="head_of_operations", pain="lead_followup",
      person=P("Tobias Reinhardt", "COO", "Funnelwerk GmbH", "Berlin, DE"),
      company=Co("Funnelwerk GmbH", "funnelwerk.de", "Growth marketing agency running paid acquisition and CRM for B2B software companies. 20 people.", "Berlin, DE", size="11-50",
                 services=["paid acquisition", "HubSpot", "landing pages"]),
      message=M("Thanks for the follow-up. Yes, still relevant: our inbound leads sit for two days before anyone answers, and by then half of them have signed with someone else. We have budget set aside for Q4 and I'd like to see a proposal before the end of the month. When can we do a call?",
                subject="Re: lead follow-up automation", from_name="Tobias Reinhardt", from_domain="funnelwerk.de")),
    L("L003", "linkedin_dm", 16, "hot", persona="founder_owner", pain="onboarding_chaos", tags=["revenue:30k_100k"],
      person=P("Anneke de Vries", "Founder", "Ritmo Business Coaching", "Utrecht, NL"),
      company=Co("Ritmo Business Coaching", "ritmocoaching.nl", "Group and 1:1 business coaching programmes for owners of service businesses.", "Utrecht, NL", size="2-10"),
      message=M("Hi! I run a business coaching programme with about 90 clients a year and a team of five. Onboarding new clients is completely manual — contracts, intake forms, Slack invites, calendar links — and it is eating my assistant alive. We bill around €45k a month so there is room to invest. Can we set up a call next week?",
                from_name="Anneke de Vries", channel="LinkedIn")),
    L("L004", "website_form", 17, "hot", persona="founder_owner", pain="scaling_with_freelancers",
      person=P("Sven Ahlgren", "Managing Director", "Northlight Studios", "Stockholm, SE"),
      company=Co("Northlight Studios", "northlight.se", "Branding and video production studio working with Nordic consumer brands.", "Stockholm, SE", size="11-50",
                 services=["brand identity", "video production", "motion design"]),
      message=M("We are a 30-person branding and video studio. Our delivery runs on about 20 freelancers and every project handover is a mess of Notion pages and WhatsApp threads. I want this fixed before we take on two new retainers in November. Budget is approved. Please send me your availability for a 30-minute call.",
                subject="Freelancer handovers", from_name="Sven Ahlgren", from_domain="northlight.se")),
    L("L005", "instantly_reply", 11, "hot", persona="head_of_delivery", pain="manual_reporting",
      person=P("Priya Nandakumar", "Head of Client Services", "Brightwave Digital", "Manchester, UK"),
      company=Co("Brightwave Digital", "brightwave.co.uk", "Digital marketing agency for retail and hospitality brands across the UK.", "Manchester, UK", size="11-50",
                 services=["SEO", "paid media", "email marketing"]),
      message=M("Your email landed at the right time. Our monthly client reporting takes my three account managers a full week each month, and we are adding four clients in October. I would like a proposal for automating the reporting first — when could you walk us through what you have done for similar agencies?",
                subject="Re: reporting week", from_name="Priya Nandakumar", from_domain="brightwave.co.uk")),
    L("L006", "website_form", 18, "hot", persona="founder_owner", pain="lead_followup", tags=["revenue:10k_30k", "demo:revenue_gate"],
      note="States €22k/month: flips to disqualify when the minimum revenue band is raised to 30k",
      person=P("Lukas Brandstätter", "Founder", "Kraftwerk Social", "Graz, AT"),
      company=Co("Kraftwerk Social", "kraftwerk-social.at", "Paid social agency for regional retail and tourism businesses in Austria.", "Graz, AT", size="2-10"),
      message=M("Hi, we are a paid social agency, 8 people, roughly €22k per month in revenue. Leads from our website and Instagram DMs go unanswered for days because everyone is busy in delivery. I have been quoted €12k by another shop and want to compare. Can we talk this month?",
                from_name="Lukas Brandstätter", from_domain="kraftwerk-social.at")),
    L("L007", "email_reply", 19, "hot", persona="founder_owner", pain="lead_followup",
      person=P("Jana Kowalczyk", "Founder", "Bloom & Grow Coaching", "Munich, DE"),
      company=Co("Bloom & Grow Coaching", "bloomandgrow.de", "Mastermind and group coaching for female founders; cohort launches twice a year.", "Munich, DE", size="2-10"),
      message=M("Yes please. I have 40 people in my mastermind and a launch in six weeks. The applicant follow-up is me, at midnight, in Gmail — people wait days for a reply and some just give up. I want the whole application, call and onboarding flow automated before the launch. What would it cost and how fast can you start?",
                subject="Re: your note", from_name="Jana Kowalczyk", from_domain="bloomandgrow.de")),
    L("L008", "linkedin_dm", 20, "hot", persona="head_of_operations", pain="content_bottleneck",
      person=P("Mikkel Sørensen", "COO", "Fjord Content Agency", "Copenhagen, DK"),
      company=Co("Fjord Content Agency", "fjordcontent.dk", "Content marketing agency producing social, blog and newsletter content for B2B and consumer clients.", "Copenhagen, DK", size="11-50",
                 services=["content production", "social media management", "newsletters"]),
      message=M("Saw your post on agency automations. We produce around 300 pieces of content a month for 18 clients and the repurposing and scheduling is a bottleneck we cannot hire our way out of. We have set aside a budget for this quarter. Could you do a call on Thursday or Friday?",
                from_name="Mikkel Sørensen", channel="LinkedIn")),
    L("L009", "website_form", 21, "hot", persona="founder_owner", pain="manual_reporting", tags=["revenue:30k_100k"],
      person=P("Elena Marchetti", "Owner", "Marchetti Media", "Zurich, CH"),
      company=Co("Marchetti Media", "marchettimedia.ch", "Performance marketing agency for DACH e-commerce brands.", "Zurich, CH", size="11-50",
                 services=["performance marketing", "Shopify apps", "analytics"]),
      message=M("We are 11 people doing performance marketing for DACH e-commerce brands, about €60k a month. Client reporting is manual and my ops lead is leaving in December, so the process has to be automated before she goes. I need someone who can run this as a project starting in October. Proposal please, and a call to discuss.",
                subject="Reporting before December", from_name="Elena Marchetti", from_domain="marchettimedia.ch")),
    L("L010", "referral", 12, "hot", persona="founder_owner", pain="manual_reporting",
      person=P("Daniel Weber", "Founder", "Weber & Söhne Digital", "Cologne, DE"),
      company=Co("Weber & Söhne Digital", "webersoehne.de", "Digital marketing agency for mid-sized manufacturers; 15 people.", "Cologne, DE", size="11-50"),
      message=M("Jonas from Hafenblick gave me your contact. We have the same reporting problem they had — 16 clients, decks built by hand every month — and I would rather not wait. Are you free for a call early next week? Budget is not the issue, time is.",
                subject="Referral from Hafenblick", from_name="Daniel Weber", from_domain="webersoehne.de")),

    # ===================================================================== WARM
    L("L011", "website_form", 3, "warm", persona="founder_owner", pain="manual_reporting",
      person=P("Nina Falk", "Founder", "Falk Social", "Vienna, AT"),
      company=Co("Falk Social", "falksocial.at", "Social media agency for restaurants, hotels and lifestyle brands.", "Vienna, AT", size="2-10"),
      message=M("We are a 6-person social media agency in Vienna. Curious what kind of automations you have built for agencies like ours — reporting takes ages every month. No rush, just exploring.",
                from_name="Nina Falk", from_domain="falksocial.at")),
    L("L012", "linkedin_dm", 4, "warm", persona="head_of_operations", pain="onboarding_chaos",
      person=P("Oliver Bright", "Head of Operations", "Meridian Growth Partners", "London, UK"),
      company=Co("Meridian Growth Partners", "meridiangrowth.co.uk", "Growth marketing agency for scale-ups; 40 people across London and Leeds.", "London, UK", size="11-50"),
      message=M("Interesting profile. We are a 40-person growth agency and our onboarding for new clients is still a 30-tab spreadsheet. Not sure automation is the answer versus hiring a project manager, but happy to hear how you would approach it.",
                from_name="Oliver Bright", channel="LinkedIn")),
    L("L013", "email_reply", 5, "warm", persona="marketing_lead", pain="lead_followup",
      person=P("Sofia Lindgren", "Marketing Manager", "Aurora Coaching Collective", "Malmö, SE"),
      company=Co("Aurora Coaching Collective", "auroracoaching.se", "Collective of leadership coaches running webinars and group programmes for managers.", "Malmö, SE", size="2-10"),
      message=M("Thanks, I am forwarding this to our founder. We do struggle with follow-up on webinar leads — most of them never hear from us again. Could you send a couple of examples of what you have built for coaching businesses so she can have a look?",
                subject="Re: webinar leads", from_name="Sofia Lindgren", from_domain="auroracoaching.se")),
    L("L014", "apollo_export", 2, "nurture", persona="founder_owner", pain=None,
      person=P("Julian Nacht", "Managing Partner", "Studio Nachtblau", "Leipzig, DE"),
      company=Co("Studio Nachtblau", "nachtblau.de", "Branding and web studio for cultural institutions and mid-sized companies.", "Leipzig, DE", size="11-50",
                 services=["brand identity", "web design", "Webflow development"],
                 news="Studio Nachtblau announced three new retainer clients and is hiring two account managers (September 2026).")),
    L("L015", "linkedin_export", 6, "warm", persona="founder_owner", pain="manual_reporting",
      person=P("Katharina Vogel", "Founder & CEO", "Vogel Kommunikation", "Frankfurt, DE",
               bio="Founder of Vogel Kommunikation, a 14-person PR and content agency for B2B tech companies. Currently looking for partners to automate our media monitoring reports and monthly client updates — DM me if that is you. Previously Edelman and Fink & Fuchs."),
      company=Co("Vogel Kommunikation", "vogel-kommunikation.de", "PR and content agency for B2B technology companies.", "Frankfurt, DE", size="11-50")),
    L("L016", "linkedin_export", 7, "warm", persona="head_of_operations", pain="scaling_with_freelancers",
      person=P("Marcus Thalberg", "COO", "Thalberg Creative", "Amsterdam, NL",
               bio="COO at Thalberg Creative (22 people, brand and performance). Building the operating system for a freelancer-heavy delivery model. Actively evaluating automation partners this quarter for briefing and handovers."),
      company=Co("Thalberg Creative", "thalbergcreative.com", "Brand and performance agency working with a network of freelance specialists.", "Amsterdam, NL", size="11-50")),
    L("L017", "website_form", 8, "warm", persona="head_of_delivery", pain="manual_reporting", tags=["geo:outside"],
      person=P("Hannah Ruiz", "Account Director", "Ruiz & Partners", "Barcelona, ES"),
      company=Co("Ruiz & Partners", "ruizpartners.es", "Digital marketing agency for tourism and hospitality brands in Spain.", "Barcelona, ES", size="11-50"),
      message=M("Hola! We are a 12-person agency in Barcelona. Our client reporting is a nightmare every month — could you share your pricing?",
                from_name="Hannah Ruiz", from_domain="ruizpartners.es")),
    L("L018", "instantly_reply", 9, "nurture", persona="founder_owner", pain="lead_followup",
      person=P("Felix Baumann", "Founder", "Baumann Digital", "Stuttgart, DE"),
      company=Co("Baumann Digital", "baumann-digital.de", "Performance marketing agency for regional B2B companies; 9 people.", "Stuttgart, DE", size="2-10"),
      message=M("Not right now — we are in the middle of a rebrand until November. But the follow-up problem you describe is real for us, leads do fall through. Ping me again in December?",
                subject="Re: leads falling through", from_name="Felix Baumann", from_domain="baumann-digital.de")),
    L("L019", "website_form", 10, "warm", persona="marketing_lead", pain="manual_reporting",
      person=P("Isabel Fontaine", "Head of Marketing", "Cadence Studio", "Dublin, IE"),
      company=Co("Cadence Studio", "cadencestudio.ie", "Content and social agency for consumer tech and fintech brands; 18 people.", "Dublin, IE", size="11-50"),
      message=M("Our founders asked me to look into automating our monthly client dashboards — we have 9 retainer clients and it takes two of us three days every month. Could you send over a rough price range and a couple of case studies?",
                from_name="Isabel Fontaine", from_domain="cadencestudio.ie")),
    L("L020", "email_reply", 13, "warm", persona="founder_owner", pain="lead_followup", tags=["revenue:10k_30k", "demo:revenue_gate"],
      person=P("Jón Einarsson", "Owner", "Reykjavik Growth Lab", "Reykjavik, IS"),
      company=Co("Reykjavik Growth Lab", "rvkgrowth.is", "Five-person performance marketing shop for Icelandic tourism and retail businesses.", "Reykjavik, IS", size="2-10"),
      message=M("We are a five-person performance shop, around €15k a month in revenue. Leads from our site get answered when someone remembers. Would be good to understand what a setup like this costs before we talk.",
                subject="Re: follow-up", from_name="Jón Einarsson", from_domain="rvkgrowth.is")),
    L("L021", "linkedin_dm", 14, "warm", persona="founder_owner", pain="content_bottleneck",
      person=P("Charlotte Mbeki", "Founder", "Kinfolk Coaching", "Bristol, UK"),
      company=Co("Kinfolk Coaching", "kinfolkcoaching.co.uk", "Coaching for first-time founders; group cohorts and a paid community.", "Bristol, UK", size="2-10"),
      message=M("I coach about 60 founders a year with a team of four. Content is where I lose most of my time — repurposing every session into posts and emails. Do you have an example of what you have done for coaches? Not urgent.",
                from_name="Charlotte Mbeki", channel="LinkedIn")),
    L("L022", "email_reply", 15, "warm", persona="head_of_delivery", pain="scaling_with_freelancers", tags=["churn"],
      person=P("Rasmus Kjær", "Head of Client Success", "Nordic Peak Agency", "Aarhus, DK"),
      company=Co("Nordic Peak Agency", "nordicpeak.dk", "Full-service digital agency; 35 people, 40 active clients.", "Aarhus, DK", size="11-50"),
      message=M("We have grown to 35 people and 40 clients and the freelancer handovers are killing quality — two clients left last quarter because deliverables were late. I am collecting options for our leadership offsite in October. What would a first project with you look like?",
                subject="Re: handovers", from_name="Rasmus Kjær", from_domain="nordicpeak.dk")),
    L("L023", "website_form", 16, "warm", persona="head_of_operations", pain="onboarding_chaos",
      person=P("Amira Haddad", "Operations Lead", "Sundial Studio", "Rotterdam, NL"),
      company=Co("Sundial Studio", "sundialstudio.nl", "Design and development studio for SaaS companies; 9 people.", "Rotterdam, NL", size="2-10"),
      message=M("Our onboarding is chaos — every new client gets a slightly different kickoff, and nobody knows who owns what. I would want my founder in the conversation before we commit to anything. Could you send me how you would approach a project like this?",
                from_name="Amira Haddad", from_domain="sundialstudio.nl")),
    L("L024", "linkedin_export", 17, "warm", persona="founder_owner", pain="scaling_with_freelancers",
      person=P("Benedikt Hauser", "Founder", "Hauser Studio", "Basel, CH",
               bio="Founder of Hauser Studio, 7 people, brand identity for Swiss SMEs. Looking to modernise how we brief and hand over work to our freelancers — open to talking with automation specialists this autumn."),
      company=Co("Hauser Studio", "hauserstudio.ch", "Brand identity studio for Swiss small and mid-sized companies.", "Basel, CH", size="2-10")),
    L("L025", "website_form", 18, "warm", persona="founder_owner", pain="manual_reporting", tags=["revenue:10k_30k", "demo:revenue_gate"],
      person=P("Lotte Jensen", "Founder", "Jensen Digital", "Odense, DK"),
      company=Co("Jensen Digital", "jensendigital.dk", "Digital marketing agency for local service businesses.", "Odense, DK", size="2-10"),
      message=M("We would like to automate our monthly client reports. Six people, about €18k a month in revenue, 11 clients. What does a project like that usually cost?",
                from_name="Lotte Jensen", from_domain="jensendigital.dk")),
    L("L026", "email_reply", 19, "warm", persona="founder_owner", pain="lead_followup",
      person=P("Paul Ostrowski", "Founder", "Ostrowski Coaching", "Hanover, DE"),
      company=Co("Ostrowski Coaching", "ostrowski-coaching.de", "Sales coaching for B2B teams; workshops and a 12-week programme. 6 people.", "Hanover, DE", size="2-10"),
      message=M("Interested but skeptical — we tried a chatbot for lead follow-up last year and it annoyed people, so leads still fall through today. How is what you do different? Happy to hear more.",
                subject="Re: follow-up", from_name="Paul Ostrowski", from_domain="ostrowski-coaching.de")),
    L("L065", "website_form", 20, "warm", persona="founder_owner", pain="manual_reporting", tags=["dedupe:near_miss"],
      note="Name shares a token with CRM account Kontor Nord; a different company in Munich — Jev should answer none",
      person=P("Sarah Klein", "Founder", "Kontor Süd Agentur", "Munich, DE"),
      company=Co("Kontor Süd Agentur", "kontor-sued.de", "Marketing agency for craft businesses and regional retailers in Bavaria; 10 people.", "Munich, DE", size="2-10"),
      message=M("We are a 10-person agency in Munich and reporting eats our Fridays. Do you have a price sheet you could send?",
                from_name="Sarah Klein", from_domain="kontor-sued.de")),

    # ===================================================================== NURTURE
    L("L027", "website_form", 1, "nurture", persona="founder_owner", pain=None,
      person=P("Greta Holm", "Founder", "Holm Studio", "Gothenburg, SE"),
      company=Co("Holm Studio", "holmstudio.se", "Brand and packaging design studio; 5 people.", "Gothenburg, SE", size="2-10"),
      message=M("Downloaded your agency automation guide — good stuff. Nothing concrete on our side yet, just following along.",
                from_name="Greta Holm", from_domain="holmstudio.se")),
    L("L028", "apollo_export", 2, "nurture", persona="founder_owner", pain=None,
      person=P("Tim Klarwasser", "Managing Director", "Klarwasser Digital", "Düsseldorf, DE"),
      company=Co("Klarwasser Digital", "klarwasser-digital.de", "Performance marketing agency for e-commerce brands.", "Düsseldorf, DE", size="11-50",
                 services=["paid social", "Amazon Ads", "CRO"], news="Klarwasser Digital wins two DACH e-commerce accounts; team grows to 24 (August 2026).")),
    L("L029", "apollo_export", 3, "nurture", persona="founder_owner", pain=None,
      person=P("Amy Cole", "Founder", "Seaside Social", "Brighton, UK"),
      company=Co("Seaside Social", "seaside-social.co.uk", "Social media agency for hospitality and leisure brands on the south coast.", "Brighton, UK", size="2-10",
                 news="Seaside Social launches a TikTok-first offer for hospitality brands.")),
    L("L030", "apollo_export", 4, "nurture", persona="head_of_operations", pain="content_bottleneck",
      person=P("Judith Mahler", "Head of Content Operations", "Wortwerk Content GmbH", "Hamburg, DE"),
      company=Co("Wortwerk Content GmbH", "wortwerk-content.de", "Content marketing agency writing blogs, whitepapers and newsletters for B2B clients.", "Hamburg, DE", size="11-50",
                 news="Wortwerk hires four freelance editors to work through a growing content backlog for its enterprise clients; the team says production, not demand, is the bottleneck.")),
    L("L031", "apollo_export", 5, "nurture", persona="founder_owner", pain=None,
      person=P("Verena Stocker", "Founder", "Alpenglow Coaching", "Innsbruck, AT"),
      company=Co("Alpenglow Coaching", "alpenglow-coaching.at", "Leadership and career coaching for professionals in the Alpine region; retreats and online programmes.", "Innsbruck, AT", size="2-10")),
    L("L032", "apollo_export", 6, "nurture", persona="founder_owner", pain=None,
      person=P("Deniz Aydin", "Managing Partner", "Loft 21 Creative Studio", "Berlin, DE"),
      company=Co("Loft 21 Creative Studio", "loft21.de", "Design and motion studio for tech and media clients.", "Berlin, DE", size="11-50",
                 news="Loft 21 opens a second studio in Hamburg (July 2026).")),
    L("L033", "apollo_export", 7, "nurture", persona="head_of_operations", pain="manual_reporting", tags=["churn"],
      person=P("Aino Virtanen", "COO", "Pinewood Performance", "Helsinki, FI"),
      company=Co("Pinewood Performance", "pinewoodperformance.fi", "Performance marketing agency for Nordic e-commerce and SaaS.", "Helsinki, FI", size="11-50",
                 news="In an interview, Pinewood's COO said monthly client reporting now takes a fifth of team time and that two clients left over late reports; the agency is reviewing tooling.")),
    L("L034", "apollo_export", 8, "nurture", persona="founder_owner", pain=None,
      person=P("Bram Willems", "Founder", "Studio Mondrian", "Eindhoven, NL"),
      company=Co("Studio Mondrian", "studiomondrian.nl", "Web design studio for architects and manufacturers; 6 people.", "Eindhoven, NL", size="2-10")),
    L("L035", "apollo_export", 9, "nurture", persona="marketing_lead", pain=None, tags=["size:outside"],
      person=P("Carla Neumann", "Head of Marketing", "Helios Growth", "Munich, DE"),
      company=Co("Helios Growth", "heliosgrowth.de", "Performance marketing agency for large consumer brands; 80 people in Munich and Hamburg.", "Munich, DE", size="51-200",
                 news="Helios Growth named agency of record for a DAX-listed beverage brand.")),
    L("L036", "linkedin_export", 10, "nurture", persona="head_of_delivery", pain=None,
      person=P("Robin Achterberg", "Account Director", "Waterfront Agency", "Amsterdam, NL",
               bio="Account Director at Waterfront Agency (16 people, integrated campaigns). Ex-Dentsu. I love a good dashboard."),
      company=Co("Waterfront Agency", "waterfront-agency.nl", "Integrated marketing agency for Dutch consumer brands.", "Amsterdam, NL", size="11-50")),
    L("L037", "linkedin_export", 11, "nurture", persona="marketing_lead", pain=None,
      person=P("Ines Castellano", "Head of Marketing", "Lumen Coaching Academy", "Berlin, DE",
               bio="Marketing at Lumen Coaching Academy (cohort-based leadership programmes, about 12 staff). Growing our newsletter to 50k subscribers."),
      company=Co("Lumen Coaching Academy", "lumenacademy.de", "Cohort-based leadership coaching programmes for managers.", "Berlin, DE", size="11-50")),
    L("L038", "linkedin_export", 12, "nurture", persona="founder_owner", pain=None,
      person=P("Henrik Dahl", "Founder", "Dahl & Co", "Oslo, NO", bio="Founder of Dahl & Co — a 9-person brand studio in Oslo. Sailing on weekends."),
      company=Co("Dahl & Co", "dahlco.no", "Brand strategy and identity studio.", "Oslo, NO", size="2-10")),
    L("L039", "linkedin_export", 13, "nurture", persona="head_of_operations", pain="onboarding_chaos",
      person=P("Selin Kaya", "COO", "Meltem Digital", "Hamburg, DE",
               bio="COO at Meltem Digital (paid media, 19 people). Systems person. We just moved client onboarding to ClickUp and it is still a mess of manual steps."),
      company=Co("Meltem Digital", "meltemdigital.de", "Paid media agency for DACH e-commerce and travel brands.", "Hamburg, DE", size="11-50")),
    L("L040", "website_form", 14, "nurture", persona="other", pain=None,
      person=P("Theo Vermeulen", "Junior Account Manager", "Peak & Pine Agency", "Antwerp, BE"),
      company=Co("Peak & Pine Agency", "peakandpine.be", "Digital agency for Belgian retail and food brands; 14 people.", "Antwerp, BE", size="11-50"),
      message=M("Hi, I am a junior account manager at Peak & Pine. My boss asked me to collect names of automation agencies for a comparison sheet. No need to reply in detail, I am just adding names for now.",
                from_name="Theo Vermeulen", from_domain="peakandpine.be")),
    L("L041", "website_form", 15, "nurture", persona="founder_owner", pain=None,
      person=P("Yara Boutros", "Founder", "Boutros Studio", "Berlin, DE"),
      company=Co("Boutros Studio", "boutros.studio", "Small brand studio for founders and restaurants; 4 people.", "Berlin, DE", size="2-10"),
      message=M("Saw your video. We are a small brand studio, 4 people. Everything is manual but honestly it works for now. Would love to be on your newsletter.",
                from_name="Yara Boutros", from_domain="boutros.studio")),
    L("L042", "email_reply", 16, "nurture", persona="founder_owner", pain=None,
      person=P("Malte Petersen", "Founder", "Küstenkind Kreativ", "Kiel, DE"),
      company=Co("Küstenkind Kreativ", "kuestenkind-kreativ.de", "Print, packaging and brand design for regional food producers; 5 people.", "Kiel, DE", size="2-10"),
      message=M("Nice work. We are 5 people, mostly print and packaging design, not much recurring client reporting to speak of. Let us stay in touch.",
                subject="Re: agency automations", from_name="Malte Petersen", from_domain="kuestenkind-kreativ.de")),
    L("L043", "linkedin_dm", 17, "nurture", persona="founder_owner",
      person=P("Emilia Novak", "Co-founder", "Signal Boost Coaching", "Lisbon, PT"),
      company=Co("Signal Boost Coaching", "signalboost.co", "Career coaching for people moving into tech; two coaches and a virtual assistant.", "Lisbon, PT", size="2-10"),
      message=M("Curious: do you also work with coaching businesses? We are two coaches and a VA. Onboarding is a bit messy but manageable for now.",
                from_name="Emilia Novak", channel="LinkedIn")),
    L("L044", "website_form", 18, "nurture", persona="founder_owner", pain=None,
      person=P("Stefan Gruber", "Managing Director", "Gruber Werbeagentur", "Linz, AT"),
      company=Co("Gruber Werbeagentur", "gruber-werbung.at", "Classic full-service advertising agency; print, outdoor, radio; 25 people.", "Linz, AT", size="11-50"),
      message=M("We are a classic full-service ad agency, 25 people. Not sure the AI stuff is for us, but I read your case study. If you ever do a webinar for agency owners, let me know.",
                from_name="Stefan Gruber", from_domain="gruber-werbung.at")),
    L("L045", "linkedin_export", 19, "nurture", persona="head_of_delivery", pain=None,
      person=P("Léa Moreau", "Head of Client Services", "Atelier Nord", "Lille, FR",
               bio="Client services at Atelier Nord (brand and digital, 30 people). Ten years on the agency side."),
      company=Co("Atelier Nord", "ateliernord.fr", "Brand and digital agency for retail and culture clients.", "Lille, FR", size="11-50")),
    L("L046", "apollo_export", 20, "nurture", persona="founder_owner", pain=None, tags=["churn"],
      person=P("Erik Bergström", "CEO", "Bergström Kommunikation", "Stockholm, SE"),
      company=Co("Bergström Kommunikation", "bergstromkomm.se", "Communications and content agency for public-sector and NGO clients.", "Stockholm, SE", size="11-50",
                 news="Bergström Kommunikation reports a record year; the CEO says clients now churn less since the agency introduced a weekly reporting cadence.")),

    # ===================================================================== DISQUALIFY
    L("L047", "email_reply", 8, "disqualify", tags=["demo:vendor"], note="Polished vendor pitch: also reads as a competitor and is outside the region",
      person=P("Jordan Reyes", "VP Partnerships", "ScaleSignal", "Austin, TX, USA"),
      company=Co("ScaleSignal", "scalesignal.io", "AI SDR platform for agencies: automated outbound sequences and lead scoring.", "Austin, TX, USA", size="51-200"),
      message=M("Hi Lanternfield team, loved what you are building. ScaleSignal is the AI SDR platform trusted by 400+ agencies — we would love to explore a partnership where your clients get 20% off and you earn referral revenue on every seat. Can I grab 15 minutes this week?",
                subject="Partnership: ScaleSignal x Lanternfield", from_name="Jordan Reyes", from_domain="scalesignal.io")),
    L("L048", "website_form", 9, "disqualify", tags=["demo:student"], note="Student asking for a thesis interview",
      person=P("Lea Schmitt", "Master's student", "University of Mannheim", "Mannheim, DE"),
      message=M("Hello! I am a master's student writing my thesis on AI adoption in marketing agencies. Would you have 20 minutes for an interview about how you sell automation projects? I can send the questions in advance. Thank you so much!",
                from_name="Lea Schmitt", from_domain="students.uni-mannheim.de")),
    L("L049", "linkedin_dm", 10, "disqualify", note="Competitor proposing white-labelling",
      person=P("Nico Berger", "Founder", "Automata Labs", "Berlin, DE"),
      company=Co("Automata Labs", "automatalabs.de", "We build AI automations and agents for agencies and SMEs, mostly on Make, n8n and OpenAI.", "Berlin, DE", size="2-10"),
      message=M("Hey — we also build AI automations for agencies, mostly Make plus OpenAI. Would you be open to white-labelling some of our workflows or teaming up on bigger projects? Always good to know other shops in the space.",
                from_name="Nico Berger", channel="LinkedIn")),
    L("L050", "email_reply", 11, "disqualify", note="Enterprise procurement",
      person=P("Dr. Sabine Krüger", "Head of Marketing Operations", "Hansa Versicherungsgruppe", "Hamburg, DE"),
      company=Co("Hansa Versicherungsgruppe", "hansa-versicherung.de", "Insurance group with six brands and about 3,000 employees.", "Hamburg, DE", size="200+"),
      message=M("We are evaluating automation vendors for our group marketing department (3,000 employees, six brands). Please complete the attached supplier questionnaire, confirm your ISO 27001 certification and provide three enterprise references.",
                subject="Supplier questionnaire — marketing automation", from_name="Dr. Sabine Krüger", from_domain="hansa-versicherung.de")),
    L("L051", "website_form", 12, "disqualify", tags=["demo:too_small"], note="Pre-revenue coach with a tight budget",
      person=P("Kevin Moser", "Coach (starting out)", "Kevin Moser Coaching", "Bochum, DE"),
      message=M("Hi, I am just starting my coaching business — no clients yet but I want to set everything up right from day one. Budget is tight, is there a starter package or a discount for beginners?",
                from_name="Kevin Moser", from_domain="gmail.com")),
    L("L052", "email_reply", 13, "disqualify", note="SEO spam",
      person=P("Rahul", "SEO Expert", "Top Rank SEO Services"),
      message=M("Dear Sir/Madam, I noticed your website is not ranking on Google first page. We offer guaranteed SEO at $99 per month with 500 backlinks. Reply YES for a free audit. To unsubscribe click here.",
                subject="Your website ranking", from_name="Rahul", from_domain="toprankseo-services.biz")),
    L("L053", "website_form", 14, "disqualify", tags=["revenue:under_10k"], note="Solo freelancer at €6k/month: below the minimum revenue band",
      person=P("Tamara Ilic", "Founder", "Ilic Social", "Nuremberg, DE"),
      company=Co("Ilic Social", "ilicsocial.de", "Solo social media freelancer for local shops and restaurants.", "Nuremberg, DE", size="solo"),
      message=M("Solo social media freelancer here, around €6k a month. Reporting is annoying but I mostly want to know if this is even in reach for someone my size.",
                from_name="Tamara Ilic", from_domain="ilicsocial.de")),
    L("L054", "email_reply", 15, "disqualify", note="Job seeker",
      person=P("Dario Costa", "Automation Engineer", "Freelance", "Porto, PT"),
      message=M("Hi! I am an n8n and Make specialist with three years of agency experience and I am looking for my next role. Are you hiring? CV attached, happy to do a trial project.",
                subject="Automation engineer — open to work", from_name="Dario Costa", from_domain="gmail.com")),
    L("L055", "email_reply", 16, "disqualify", note="Paid podcast placement pitch",
      person=P("Chloe Winters", "Business Development", "Podcast Guest Co", "London, UK"),
      company=Co("Podcast Guest Co", "podcastguest.co", "Paid guest placements on marketing podcasts.", "London, UK", size="2-10"),
      message=M("I would love to feature you on our network of marketing podcasts — paid placement from £1,200 per episode, great for lead generation. Shall I send the media kit?",
                subject="Feature you on 12 marketing podcasts", from_name="Chloe Winters", from_domain="podcastguest.co")),
    L("L056", "apollo_export", 17, "disqualify", note="Enterprise retail group from an export",
      person=P("Marco Lehmann", "Head of Digital Marketing", "Rheinland Retail Group", "Cologne, DE"),
      company=Co("Rheinland Retail Group", "rheinland-retail.de", "Retail group with 4,500 employees, 300 stores and twelve regional marketing teams.", "Cologne, DE", size="200+",
                 news="Rheinland Retail Group consolidates its twelve regional marketing teams into one central unit.")),
    L("L057", "email_reply", 18, "disqualify", note="Phishing: asks for payment details",
      person=P("Domain Registry Services", "Billing", "Domain Registry Services"),
      message=M("Dear customer, your domain lanternfield.de will expire within 24 hours. To avoid suspension confirm your credit card details and a copy of the account holder's ID using the secure link. This is an automated message.",
                subject="URGENT: domain expiration notice", from_name="Domain Registry Services", from_domain="registry-renewals-secure.com")),
    L("L058", "instantly_reply", 19, "disqualify", note="Agency pitching outbound services to Lanternfield Automation",
      person=P("Ben Hartmann", "Co-founder", "Growth Hackers Berlin", "Berlin, DE"),
      company=Co("Growth Hackers Berlin", "growthhackers-berlin.de", "Cold email agency for B2B consultancies.", "Berlin, DE", size="2-10"),
      message=M("Quick one — we help AI consultancies like yours book 20+ qualified calls a month with cold email. Want a free audit of your current outbound?",
                subject="20 calls a month", from_name="Ben Hartmann", from_domain="growthhackers-berlin.de")),
    L("L059", "apollo_export", 20, "disqualify", note="Competitor from an export",
      person=P("Jan Brück", "Founder", "Flowstate Automation GmbH", "Hamburg, DE"),
      company=Co("Flowstate Automation GmbH", "flowstate-automation.de", "We build AI agents and workflow automations for agencies and small businesses.", "Hamburg, DE", size="2-10",
                 services=["AI agents", "Make and n8n automations", "automation consulting"])),

    # ===================================================================== EXISTING ACCOUNT
    L("L060", "website_form", 20, "existing", tags=["demo:duplicate"], note="Existing customer Hafenblick Digital (owner Lena Berg)",
      person=P("Jonas Petersen", "Managing Director", "Hafenblick Digital", "Hamburg, DE"),
      company=Co("Hafenblick Digital", "hafenblick-digital.de", "Performance marketing agency in Hamburg; 15 clients.", "Hamburg, DE", size="11-50"),
      message=M("Hi again — since the reporting automation went live we would like to look at lead follow-up too. Same team, 15 clients now. Can Lena or you call me this week?",
                from_name="Jonas Petersen", from_domain="hafenblick-digital.de")),
    L("L061", "email_reply", 21, "existing", note="Existing customer Kontor Nord, different contact",
      person=P("Marie Stein", "Head of Client Services", "Kontor Nord Creative", "Hamburg, DE"),
      company=Co("Kontor Nord Creative", "kontornord.de", "Brand and content agency in Hamburg.", "Hamburg, DE", size="11-50"),
      message=M("We are already working with you on the onboarding automations — my colleague Tim mentioned we should also look at automating the monthly dashboards. Who should I speak to?",
                subject="Dashboards next?", from_name="Marie Stein", from_domain="kontornord.de")),
    L("L062", "instantly_reply", 21, "existing", note="Open opportunity Brightpath (owner Sara Nowak)",
      person=P("James Whitfield", "Founder", "Brightpath Coaching", "Leeds, UK"),
      company=Co("Brightpath Coaching", "brightpath-coaching.com", "Executive coaching for senior leaders.", "Leeds, UK", size="2-10"),
      message=M("Thanks — we spoke to Sara two weeks ago and I am still waiting on the proposal. Any update on timing?",
                subject="Re: applicant follow-up", from_name="James Whitfield", from_domain="brightpath-coaching.com")),
    L("L063", "linkedin_export", 6, "existing", note="LinkedIn export of an existing customer's COO",
      person=P("Dana Fischer", "COO", "Growthloop Agency", "Berlin, DE", bio="COO at Growthloop (performance marketing, 28 people). Operations, finance and tooling."),
      company=Co("Growthloop Agency", "growthloop.io", "Performance marketing agency for DTC brands.", "Berlin, DE", size="11-50")),
    L("L064", "email_reply", 21, "existing", note="Churned account returning (owner Lena Berg)",
      person=P("Hugo Marlow", "Founder", "Studio Marlow", "London, UK"),
      company=Co("Studio Marlow", "studiomarlow.co.uk", "Design studio for consumer brands; 12 people.", "London, UK", size="11-50"),
      message=M("It has been a year since we paused. We have grown to 12 people and the reporting problem is back with a vengeance. Can we pick up where we left off?",
                subject="Picking things back up", from_name="Hugo Marlow", from_domain="studiomarlow.co.uk")),
]


def main() -> int:
    if LEADS.exists():
        shutil.rmtree(LEADS)
    LEADS.mkdir(parents=True)
    gold: dict[str, dict] = {}
    ids: set[str] = set()
    for lead, g in ROWS:
        assert lead["id"] not in ids, lead["id"]
        ids.add(lead["id"])
        (LEADS / f"{lead['id']}.json").write_text(json.dumps(lead, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        gold[lead["id"]] = g
    CRM.write_text(json.dumps({"accounts": ACCOUNTS}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    GOLD.write_text(json.dumps({"icp": "lanternfield_agencies", "leads": dict(sorted(gold.items()))}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tiers = {}
    for g in gold.values():
        tiers[g["tier"]] = tiers.get(g["tier"], 0) + 1
    print(f"wrote {len(gold)} leads, {len(ACCOUNTS)} CRM accounts; gold tiers: {tiers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
