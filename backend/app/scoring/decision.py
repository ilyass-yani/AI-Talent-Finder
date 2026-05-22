import os
from typing import Tuple


def combine_scores(similarity_score: float, ml_score: float, w_sim: float = 0.5, w_ml: float = 0.5) -> float:
    """Combine similarity and ML scores into a single final score (0..100).

    Both inputs expected in 0..100 range.
    """
    final = (w_sim * similarity_score) + (w_ml * ml_score)
    # clip
    if final < 0:
        final = 0.0
    if final > 100:
        final = 100.0
    return float(final)


def decision_from_score(score: float, accept_threshold: float = None, review_threshold: float = None) -> Tuple[str, dict]:
    """Return decision label and metadata.

    The documented business rules are defined on a normalized 0..1 score:
    - accepted if score > 0.8
    - to_review if 0.5 <= score <= 0.8
    - rejected if score < 0.5

    For backward compatibility, percentage scores in 0..100 are also accepted
    and normalized automatically before applying thresholds.
    """
    if accept_threshold is None:
        accept_threshold = float(os.getenv('DECISION_ACCEPT_THR', '0.8'))
    if review_threshold is None:
        review_threshold = float(os.getenv('DECISION_REVIEW_THR', '0.5'))

    normalized_score = float(score)
    if normalized_score > 1.0:
        normalized_score /= 100.0

    if normalized_score > accept_threshold:
        return 'accepted', {'score': score}
    if normalized_score >= review_threshold:
        return 'to_review', {'score': score}
    return 'rejected', {'score': score}
