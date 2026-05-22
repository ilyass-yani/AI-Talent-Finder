#!/usr/bin/env python3
"""Simple scoring runner: reads extracted jsonl, computes final decision using dummy similarity and ML scores.

This script is a placeholder to demonstrate `combine_scores` usage. In practice,
`similarity_score` should come from matching (cosine) and `ml_score` from trained model.
"""
import argparse
import json
from pathlib import Path

from app.scoring.decision import combine_scores, decision_from_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    p = Path(args.input)
    rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    out = []
    for r in rows:
        # placeholder: similarity from quality_score, ml_score from heuristic
        sim = float(r.get('quality_score', 0))
        ml = min(100.0, float(len(r.get('raw_text','')) / 10.0))
        final = combine_scores(sim, ml)
        decision, meta = decision_from_score(final)
        record = {**r, 'final_score': final, 'decision': decision}
        out.append(record)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text('\n'.join(json.dumps(o, ensure_ascii=False) for o in out), encoding='utf-8')
    print(f'Wrote decisions to {outp}')


if __name__ == '__main__':
    main()
