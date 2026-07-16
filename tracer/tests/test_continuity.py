from tracer.continuity import ChainRecorder, PlayChain, Segment, PathPoint, new_chain_id


def test_recorder_lifecycle():
    r = ChainRecorder()
    assert not r.active
    r.extend(1, 1, 0.1)          # extend before start: ignored
    assert r.points == []
    r.start(0, 0, 0.0)
    r.extend(1, 2, 0.1)
    r.extend(3, 4, 0.2)
    pts = r.finish()
    assert [(p.x, p.y) for p in pts] == [(0, 0), (1, 2), (3, 4)]
    assert not r.active and r.points == []


def test_chain_ids_unique():
    assert new_chain_id() != new_chain_id()


def test_segment_time_window():
    seg = Segment(action="CARRY", points=[PathPoint(0, 0, 1.5), PathPoint(5, 0, 2.5)])
    assert seg.start_t == 1.5 and seg.end_t == 2.5


def test_chain_t0():
    chain = PlayChain(chain_id="c", team="home", start_minute=3.0)
    assert chain.t0 is None
    chain.segments.append(Segment(action="CARRY", points=[PathPoint(0, 0, 9.0)]))
    assert chain.t0 == 9.0
