from app.services.explainability_engine import generate_explanation, generate_shortlist_summary


def test_generate_explanation_fallback_is_safe():
    result = generate_explanation(
        candidate_name='John Developer',
        job_title='Senior Python Developer',
        match_score={'match_score': 0.0, 'text_similarity': 0.0, 'skills_match': 0.0},
        matching_skills=[],
        missing_skills=['Python', 'FastAPI', 'Machine Learning'],
        candidate_years_exp=0,
        required_years_exp=5,
    )

    assert result.overall_score == 0.0
    assert result.interpretation in {'🔴 Weak Match', '🟡 Moderate Match', '🟢 Strong Match'}
    assert result.matching_skills == []
    assert 'Under-experienced' in result.experience_alignment or 'Slightly under-experienced' in result.experience_alignment
    assert result.recommendations


def test_generate_shortlist_summary_empty_matches():
    summary = generate_shortlist_summary([], 'Senior Python Developer')
    assert summary['total_candidates_screened'] == 0
    assert summary['strong_matches'] == 0
    assert summary['recommendations']


if __name__ == '__main__':
    test_generate_explanation_fallback_is_safe()
    test_generate_shortlist_summary_empty_matches()
    print('explainability smoke tests: OK')
