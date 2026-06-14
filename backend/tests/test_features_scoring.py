import json
from pathlib import Path
from app.scoring.decision import combine_scores, decision_from_score


def test_combine_scores():
    assert combine_scores(80, 60, 0.6, 0.4) ==  (0.6*80 + 0.4*60)


def test_decision_labels():
    label, _ = decision_from_score(85)
    assert label == 'accept'
    label, _ = decision_from_score(50)
    assert label == 'review'
    label, _ = decision_from_score(10)
    assert label == 'reject'
