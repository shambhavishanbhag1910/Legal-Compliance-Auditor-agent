from app.metrics import precision_recall_f1


def test_precision_recall_f1():
    score = precision_recall_f1({"A", "B", "C"}, {"B", "C", "D"})
    assert score.tp == 2
    assert score.fp == 1
    assert score.fn == 1
    assert score.precision == 0.6667
    assert score.recall == 0.6667
    assert score.f1 == 0.6667
