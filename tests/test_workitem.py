"""Port of every law in `leadqualifier/workitem.fsx`. A sample is not enough (ts-009).

TEACHING NOTE: when Python and the `.fsx` disagree, the `.fsx` wins. These tests
are the host-language copy of L1–L56, not a second spec.
"""

from __future__ import annotations

from leadqualifier.workitem import (
    ApplyOk,
    Arrive,
    Arrived,
    Awaiting,
    Calendar,
    CaseStudy,
    Copy,
    CsvRow,
    DeclineDraft,
    Dismiss,
    Dismissed,
    Dispatched,
    Draft,
    Email,
    Err,
    Flag,
    Form,
    HandOff,
    HandedToCloser,
    HeldForHuman,
    Hidden,
    IcpVersionId,
    ImportId,
    Judged,
    LinkedIn,
    MarkDelivered,
    MarkDispatched,
    MarkDispatchFailed,
    NoSend,
    NoWrite,
    Nothing,
    Open,
    OutboundPending,
    Pending,
    PersonId,
    QualifyingQuestion,
    Queue,
    Queued,
    QueuedForSequence,
    RecordReply,
    Revealed,
    RinglessVoicemail,
    SearchFilters,
    SendFailed,
    Sms,
    Unjudged,
    Unreviewed,
    Voice,
    ApolloPerson,
    apply,
    calendar_draft,
    contact_of,
    decline_draft,
    email_draft,
    evolve,
    filters_from_icp,
    voice_draft,
    Delivered,
)


def _v() -> IcpVersionId:
    return IcpVersionId("v1")


def judged(tier: str, needs: bool = False) -> Judged:
    return Judged(_v(), tier, needs)  # type: ignore[arg-type]


birth = ApolloPerson(PersonId("p1"))
judged_hot = judged("hot")
judged_hot_review = judged("hot", True)
judged_warm = judged("warm")
judged_nurture = judged("nurture")
judged_dq = judged("disqualify")
judged_existing = judged("existing")


def born() -> Open:
    r = apply(Arrive(birth), Nothing(), Unjudged())
    assert isinstance(r, ApplyOk) and isinstance(r.state, Open)
    return r.state


def ok(cmd, state, judgement=None):
    r = apply(cmd, state, judgement if judgement is not None else Unjudged())
    assert isinstance(r, ApplyOk), getattr(r, "error", r)
    return r


def err(cmd, state, judgement, expected: str):
    r = apply(cmd, state, judgement)
    assert isinstance(r, Err) and r.error.kind == expected, r


def test_l1_arrive_unreviewed():
    r = ok(Arrive(birth), Nothing())
    assert isinstance(r.state, Open)
    assert isinstance(r.state.disposition, Unreviewed) and isinstance(r.state.relay, NoWrite)
    assert isinstance(r.state.outbound, NoSend)
    assert r.events == (Arrived(birth),)


def test_l2_arrive_twice():
    err(Arrive(birth), born(), Unjudged(), "already_arrived")


def test_l3_flag_unjudged():
    err(Flag(), born(), Unjudged(), "not_judged")


def test_l4_flag_held():
    r = ok(Flag(), born(), judged_hot_review)
    assert isinstance(r.state.disposition, HeldForHuman)


def test_l5_flag_not_held():
    err(Flag(), born(), judged_hot, "not_held")


def test_l6_queue_unjudged():
    err(Queue(email_draft()), born(), Unjudged(), "not_judged")


def test_l7_queue_disqualify():
    err(Queue(email_draft()), born(), judged_dq, "not_sequenceable")


def test_l8_queue_existing():
    err(Queue(email_draft()), born(), judged_existing, "not_sequenceable")


def test_l9_queue_warm():
    d = email_draft()
    r = ok(Queue(d), born(), judged_warm)
    assert isinstance(r.state.disposition, QueuedForSequence)
    assert isinstance(r.state.outbound, Awaiting) and r.state.outbound.draft == d
    assert [e.kind for e in r.events] == ["queued", "outbound_pending"]


def test_l10_queue_hot():
    r = ok(Queue(email_draft()), born(), judged_hot)
    assert isinstance(r.state.disposition, QueuedForSequence)
    assert isinstance(r.state.outbound, Awaiting)


def test_l11_queue_nurture():
    r = ok(Queue(email_draft()), born(), judged_nurture)
    assert isinstance(r.state.disposition, QueuedForSequence)
    assert isinstance(r.state.outbound, NoSend)
    assert r.events == (Queued(),)


def test_l12_handoff_unjudged():
    err(HandOff(voice_draft()), born(), Unjudged(), "not_judged")


def test_l13_handoff_not_hot():
    err(HandOff(voice_draft()), born(), judged_warm, "not_hot")


def test_l14_handoff_hot_relay():
    d = voice_draft()
    r = ok(HandOff(d), born(), judged_hot)
    assert isinstance(r.state.disposition, HandedToCloser) and isinstance(r.state.relay, Pending)
    assert isinstance(r.state.outbound, Awaiting) and r.state.outbound.draft == d
    assert [e.kind for e in r.events] == ["handed_off", "relay_pending", "outbound_pending"]


def test_l15_handoff_twice():
    s14 = ok(HandOff(voice_draft()), born(), judged_hot).state
    err(HandOff(voice_draft()), s14, judged_hot, "already_handed_off")


def test_l16_dismiss_unreviewed():
    r = ok(Dismiss(), born(), judged_warm)
    assert isinstance(r.state.disposition, Dismissed) and isinstance(r.state.relay, NoWrite)
    assert isinstance(r.state.outbound, NoSend)


def test_l17_dismiss_twice():
    s16 = ok(Dismiss(), born(), judged_warm).state
    err(Dismiss(), s16, judged_warm, "already_dismissed")


def test_l18_dismiss_queued():
    s9 = ok(Queue(email_draft()), born(), judged_warm).state
    err(Dismiss(), s9, judged_warm, "not_dismissable")


def test_l19_reply_reopens_dismissed():
    s16 = ok(Dismiss(), born(), judged_warm).state
    r = ok(RecordReply("ping"), s16)
    assert isinstance(r.state.disposition, Unreviewed)


def test_l20_reply_reopens_handed():
    s14 = ok(HandOff(voice_draft()), born(), judged_hot).state
    r = ok(RecordReply("Tuesday works"), s14)
    assert isinstance(r.state.disposition, Unreviewed) and isinstance(r.state.relay, Pending)
    assert isinstance(r.state.outbound, Awaiting)


def test_l21_csv_birth():
    csv = CsvRow(ImportId("imp"), 3)
    r = ok(Arrive(csv), Nothing())
    assert isinstance(r.state, Open) and r.state.arrival == csv
    assert isinstance(r.state.disposition, Unreviewed) and isinstance(r.state.relay, NoWrite)
    assert isinstance(r.state.outbound, NoSend)


def test_l22_contact_hidden_unreviewed():
    assert isinstance(contact_of(born()), Hidden)


def test_l23_contact_hidden_dismissed():
    s16 = ok(Dismiss(), born(), judged_warm).state
    assert isinstance(contact_of(s16), Hidden)


def test_l24_contact_revealed_held():
    s4 = ok(Flag(), born(), judged_hot_review).state
    assert isinstance(contact_of(s4), Revealed)


def test_l25_contact_revealed_queued():
    s9 = ok(Queue(email_draft()), born(), judged_warm).state
    assert isinstance(contact_of(s9), Revealed)


def test_l26_contact_revealed_handed():
    s14 = ok(HandOff(voice_draft()), born(), judged_hot).state
    assert isinstance(contact_of(s14), Revealed)


def test_l27_deliver_not_pending():
    err(MarkDelivered("hs-1"), born(), judged_hot, "relay_not_pending")


def test_l28_deliver_pending():
    s14 = ok(HandOff(voice_draft()), born(), judged_hot).state
    r = ok(MarkDelivered("hs-1"), s14, judged_hot)
    assert isinstance(r.state.relay, Delivered) and r.state.relay.remote_id == "hs-1"


def test_l29_commands_on_nothing():
    err(Flag(), Nothing(), Unjudged(), "not_arrived")
    err(Queue(email_draft()), Nothing(), judged_warm, "not_arrived")
    err(HandOff(voice_draft()), Nothing(), judged_hot, "not_arrived")


def test_l30_queue_from_held():
    s4 = ok(Flag(), born(), judged_hot_review).state
    r = ok(Queue(email_draft()), s4, judged_warm)
    assert isinstance(r.state.disposition, QueuedForSequence)
    assert isinstance(r.state.outbound, Awaiting)


def test_l31_handoff_from_held():
    s4 = ok(Flag(), born(), judged_hot_review).state
    r = ok(HandOff(voice_draft()), s4, judged_hot)
    assert isinstance(r.state.disposition, HandedToCloser) and isinstance(r.state.relay, Pending)
    assert isinstance(r.state.outbound, Awaiting)


def test_l32_evolve_refuses():
    s1 = born()
    r = evolve(s1, Arrived(birth))
    assert isinstance(r, Err) and r.error.kind == "not_arrived"


def test_l33_state_has_no_judgement():
    s = born()
    assert isinstance(s, Open)
    assert not hasattr(s, "judgement")


def test_sf1_empty_titles_still_valid():
    f = filters_from_icp([], "anywhere")
    assert f == SearchFilters(titles=(), locations=(), employee_ranges=(), keywords=())


def test_sf2_geography_anywhere_means_no_location():
    f = filters_from_icp(["Founder"], "anywhere")
    assert f.locations == ()


def test_sf3_persona_titles_are_copied():
    f = filters_from_icp(["Founder / Owner", "Head of Growth"], "Hamburg")
    assert f.titles == ("Founder / Owner", "Head of Growth") and f.locations == ("Hamburg",)


def test_l37_queue_twice():
    s9 = ok(Queue(email_draft()), born(), judged_warm).state
    err(Queue(email_draft()), s9, judged_warm, "not_queueable")


def test_l38_reply_empty():
    s16 = ok(Dismiss(), born(), judged_warm).state
    err(RecordReply(""), s16, Unjudged(), "empty_reply")
    err(RecordReply("   "), s16, Unjudged(), "empty_reply")


def test_l39_reply_carries_body():
    s16 = ok(Dismiss(), born(), judged_warm).state
    r = ok(RecordReply("thanks"), s16)
    assert [e.kind for e in r.events] == ["reply_arrived"]
    assert r.events[0].body == "thanks"


def test_l40_queue_empty_draft():
    err(Queue(email_draft("")), born(), judged_warm, "empty_draft")


def test_l41_dispatch_not_pending():
    err(MarkDispatched("seq-1"), born(), judged_warm, "outbound_not_pending")


def test_l42_dispatch_pending():
    s9 = ok(Queue(email_draft()), born(), judged_warm).state
    r = ok(MarkDispatched("seq-1"), s9, judged_warm)
    assert isinstance(r.state.outbound, Dispatched) and r.state.outbound.remote_id == "seq-1"


def test_l43_dispatch_failed():
    s9 = ok(Queue(email_draft()), born(), judged_warm).state
    r = ok(MarkDispatchFailed("no_address"), s9, judged_warm)
    assert isinstance(r.state.outbound, SendFailed) and r.state.outbound.reason == "no_address"


def test_l44_disqualify_stays_nosend():
    assert isinstance(born().outbound, NoSend)


def test_l45_contact_hidden_after_reply():
    s14 = ok(HandOff(voice_draft()), born(), judged_hot).state
    s20 = ok(RecordReply("Tuesday works"), s14).state
    assert isinstance(contact_of(s20), Hidden)


def test_l46_handoff_empty_draft():
    err(HandOff(calendar_draft(())), born(), judged_hot, "empty_draft")


def test_l47_fail_not_pending():
    err(MarkDispatchFailed("x"), born(), judged_warm, "outbound_not_pending")


def test_queue_draft_turns_voice_into_email():
    from leadqualifier.workitem import draft_for_handoff, draft_for_queue

    result = {"next_action": {"id": "book_call", "text": "Tue or Thu"}}
    q = draft_for_queue(result)
    h = draft_for_handoff(result)
    assert isinstance(q.channel, Email) and isinstance(q.offer, Copy) and q.offer.text == "Tue or Thu"
    assert isinstance(h, Draft) and isinstance(h.channel, Voice) and isinstance(h.offer, Calendar)
    assert h.offer.slots == ("Tuesday 11:00 CET", "Thursday 15:00 CET")


def test_l48_queue_linkedin():
    d = Draft(LinkedIn(), Copy("Hi — case study"))
    r = ok(Queue(d), born(), judged_warm)
    assert isinstance(r.state.outbound, Awaiting) and r.state.outbound.draft.channel == LinkedIn()
    assert isinstance(r.events[1], OutboundPending)


def test_l49_sms_queue_warm():
    d = Draft(Sms(), Copy("hi"))
    r = ok(Queue(d), born(), judged_warm)
    assert isinstance(r.state.outbound, Awaiting) and r.state.outbound.draft == d


def test_l50_rvm_queue_warm():
    d = Draft(RinglessVoicemail(), Copy("hi"))
    r = ok(Queue(d), born(), judged_warm)
    assert isinstance(r.state.outbound, Awaiting) and r.state.outbound.draft == d


def test_l51_calendar_empty():
    err(Queue(Draft(Voice(), Calendar(()))), born(), judged_warm, "empty_draft")


def test_l52_casestudy_blank():
    err(Queue(Draft(Email(), CaseStudy(""))), born(), judged_warm, "empty_draft")


def test_l53_form_blank():
    err(Queue(Draft(Email(), Form("   "))), born(), judged_warm, "empty_draft")


def test_l54_question_blank():
    err(Queue(Draft(Email(), QualifyingQuestion(""))), born(), judged_warm, "empty_draft")


def test_l55_decline_blank():
    err(Queue(Draft(Email(), DeclineDraft(""))), born(), judged_warm, "empty_draft")


def test_l56_decline_not_sent():
    err(Queue(decline_draft()), born(), judged_warm, "not_sendable")
    err(HandOff(decline_draft()), born(), judged_hot, "not_sendable")


def test_offer_for_action_uses_playbook_ids():
    from leadqualifier.workitem import offer_for_action

    assert isinstance(offer_for_action({"id": "send_case_study_agency", "text": "Hi"}), Copy)
    assert isinstance(offer_for_action({"id": "ask_qualifying_question_pain", "text": "Q?"}), QualifyingQuestion)
    assert isinstance(offer_for_action({"id": "book_call", "text": "slots"}), Copy)
