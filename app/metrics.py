from dataclasses import dataclass


@dataclass(frozen=True)
class PRF1:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


def precision_recall_f1(predicted: set[str], expected: set[str]) -> PRF1:
    tp = len(predicted & expected)
    fp = len(predicted - expected)
    fn = len(expected - predicted)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return PRF1(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        tp=tp,
        fp=fp,
        fn=fn,
    )
