"""Port of every law in `leadqualifier/workitem.fsx`. A sample is not enough (ts-009).

TEACHING NOTE: when Python and the `.fsx` disagree, the `.fsx` wins. These tests
are the host-language copy of L1–L36, not a second spec.
"""

from __future__ import annotations

from leadqualifier.workitem import (
    ApplyOk,
    Arrive,
    Arrived,
    CsvRow,
    Dismiss,
    Dismissed,
    Err,
    Flag,
    HandOff,
    HandedToCloser,
    HeldForHuman,
    Hidden,
    IcpVersionId,
    ImportId,
    Judged,
    MarkDelivered,
    Nothing,
    Open,
    PersonId,
    Queue,
    QueuedForSequence,
    RecordReply,
    Revealed,
    SearchFilters,
    Unjudged,
    Unreviewed,
    ApolloPerson,
    apply,
    contact_of,
    evolve,
    filters_from_icp,
    NoWrite,
    Pending,
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
    err(Queue(), born(), Unjudged(), "not_judged")


def test_l7_queue_disqualify():
    err(Queue(), born(), judged_dq, "not_sequenceable")


def test_l8_queue_existing():
    err(Queue(), born(), judged_existing, "not_sequenceable")


def test_l9_queue_warm():
    r = ok(Queue(), born(), judged_warm)
    assert isinstance(r.state.disposition, QueuedForSequence)


def test_l10_queue_hot():
    r = ok(Queue(), born(), judged_hot)
    assert isinstance(r.state.disposition, QueuedForSequence)


def test_l11_queue_nurture():
    r = ok(Queue(), born(), judged_nurture)
    assert isinstance(r.state.disposition, QueuedForSequence)


def test_l12_handoff_unjudged():
    err(HandOff(), born(), Unjudged(), "not_judged")


def test_l13_handoff_not_hot():
    err(HandOff(), born(), judged_warm, "not_hot")


def test_l14_handoff_hot_relay():
    r = ok(HandOff(), born(), judged_hot)
    assert isinstance(r.state.disposition, HandedToCloser) and isinstance(r.state.relay, Pending)
    assert [e.kind for e in r.events] == ["handed_off", "relay_pending"]


def test_l15_handoff_twice():
    s14 = ok(HandOff(), born(), judged_hot).state
    err(HandOff(), s14, judged_hot, "already_handed_off")


def test_l16_dismiss_unreviewed():
    r = ok(Dismiss(), born(), judged_warm)
    assert isinstance(r.state.disposition, Dismissed) and isinstance(r.state.relay, NoWrite)


def test_l17_dismiss_twice():
    s16 = ok(Dismiss(), born(), judged_warm).state
    err(Dismiss(), s16, judged_warm, "already_dismissed")


def test_l18_dismiss_queued():
    s9 = ok(Queue(), born(), judged_warm).state
    err(Dismiss(), s9, judged_warm, "not_dismissable")


def test_l19_reply_reopens_dismissed():
    s16 = ok(Dismiss(), born(), judged_warm).state
    r = ok(RecordReply(), s16)
    assert isinstance(r.state.disposition, Unreviewed)


def test_l20_reply_reopens_handed():
    s14 = ok(HandOff(), born(), judged_hot).state
    r = ok(RecordReply(), s14)
    assert isinstance(r.state.disposition, Unreviewed) and isinstance(r.state.relay, Pending)


def test_l21_csv_birth():
    csv = CsvRow(ImportId("imp"), 3)
    r = ok(Arrive(csv), Nothing())
    assert isinstance(r.state, Open) and r.state.arrival == csv
    assert isinstance(r.state.disposition, Unreviewed) and isinstance(r.state.relay, NoWrite)


def test_l22_contact_hidden_unreviewed():
    assert isinstance(contact_of(born()), Hidden)


def test_l23_contact_hidden_dismissed():
    s16 = ok(Dismiss(), born(), judged_warm).state
    assert isinstance(contact_of(s16), Hidden)


def test_l24_contact_revealed_held():
    s4 = ok(Flag(), born(), judged_hot_review).state
    assert isinstance(contact_of(s4), Revealed)


def test_l25_contact_revealed_queued():
    s9 = ok(Queue(), born(), judged_warm).state
    assert isinstance(contact_of(s9), Revealed)


def test_l26_contact_revealed_handed():
    s14 = ok(HandOff(), born(), judged_hot).state
    assert isinstance(contact_of(s14), Revealed)


def test_l27_deliver_not_pending():
    err(MarkDelivered("hs-1"), born(), judged_hot, "relay_not_pending")


def test_l28_deliver_pending():
    s14 = ok(HandOff(), born(), judged_hot).state
    r = ok(MarkDelivered("hs-1"), s14, judged_hot)
    assert isinstance(r.state.relay, Delivered) and r.state.relay.remote_id == "hs-1"


def test_l29_commands_on_nothing():
    err(Flag(), Nothing(), Unjudged(), "not_arrived")
    err(Queue(), Nothing(), judged_warm, "not_arrived")
    err(HandOff(), Nothing(), judged_hot, "not_arrived")


def test_l30_queue_from_held():
    s4 = ok(Flag(), born(), judged_hot_review).state
    r = ok(Queue(), s4, judged_warm)
    assert isinstance(r.state.disposition, QueuedForSequence)


def test_l31_handoff_from_held():
    s4 = ok(Flag(), born(), judged_hot_review).state
    r = ok(HandOff(), s4, judged_hot)
    assert isinstance(r.state.disposition, HandedToCloser) and isinstance(r.state.relay, Pending)


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
