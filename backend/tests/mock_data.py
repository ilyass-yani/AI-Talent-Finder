"""
Mock data for testing API endpoints without external dependencies
Used for frontend development and manual testing
"""

MOCK_CANDIDATES = [
    {
        "id": 1,
        "full_name": "Ahmed Hassan",
        "email": "ahmed@example.com",
        "phone": "+33612345678",
        "linkedin_url": "https://linkedin.com/in/ahmedhassan",
        "github_url": "https://github.com/ahmedhassan",
        "cv_path": "/uploads/cv_ahmed.pdf",
        "raw_text": "Senior Python Developer with 5 years experience...",
        "created_at": "2026-04-01T10:00:00",
        "skills": [
            {"name": "Python", "category": "tech", "level": "expert"},
            {"name": "FastAPI", "category": "tech", "level": "advanced"},
            {"name": "Docker", "category": "tech", "level": "advanced"},
            {"name": "PostgreSQL", "category": "tech", "level": "advanced"},
            {"name": "AWS", "category": "tech", "level": "intermediate"},
            {"name": "Leadership", "category": "soft", "level": "intermediate"},
            {"name": "English", "category": "language", "level": "advanced"}
        ]
    },
    {
        "id": 2,
        "full_name": "Sofia Rodriguez",
        "email": "sofia@example.com",
        "phone": "+33712345678",
        "linkedin_url": "https://linkedin.com/in/sofiar",
        "github_url": "https://github.com/sofiar",
        "cv_path": "/uploads/cv_sofia.pdf",
        "raw_text": "Full-stack developer with React and Node.js expertise...",
        "created_at": "2026-04-02T11:00:00",
        "skills": [
            {"name": "JavaScript", "category": "tech", "level": "expert"},
            {"name": "React", "category": "tech", "level": "expert"},
            {"name": "Next.js", "category": "tech", "level": "advanced"},
            {"name": "Node.js", "category": "tech", "level": "advanced"},
            {"name": "MongoDB", "category": "tech", "level": "intermediate"},
            {"name": "Communication", "category": "soft", "level": "advanced"},
            {"name": "French", "category": "language", "level": "native"},
            {"name": "English", "category": "language", "level": "advanced"}
        ]
    },
    {
        "id": 3,
        "full_name": "Jean Dupont",
        "email": "jean@example.com",
        "phone": "+33812345678",
        "linkedin_url": "https://linkedin.com/in/jeandupont",
        "github_url": "https://github.com/jeandupont",
        "cv_path": "/uploads/cv_jean.pdf",
        "raw_text": "Data Science specialist with ML expertise...",
        "created_at": "2026-04-03T14:00:00",
        "skills": [
            {"name": "Python", "category": "tech", "level": "expert"},
            {"name": "Pandas", "category": "tech", "level": "expert"},
            {"name": "Scikit-learn", "category": "tech", "level": "advanced"},
            {"name": "TensorFlow", "category": "tech", "level": "intermediate"},
            {"name": "SQL", "category": "tech", "level": "advanced"},
            {"name": "Problem Solving", "category": "soft", "level": "expert"},
            {"name": "English", "category": "language", "level": "intermediate"}
        ]
    }
]

MOCK_JOB_CRITERIA = [
    {
        "id": 1,
        "recruiter_id": 1,
        "title": "Senior Python Developer",
        "description": "We need an experienced Python developer for our backend team",
        "created_at": "2026-04-01T15:00:00",
        "criteria_skills": [
            {"id": 1, "skill_id": 1, "weight": 100},  # Python
            {"id": 2, "skill_id": 14, "weight": 70},  # FastAPI
            {"id": 3, "skill_id": 27, "weight": 60},  # Docker
            {"id": 4, "skill_id": 22, "weight": 50},  # PostgreSQL
        ]
    }
]

MOCK_MATCH_RESULTS = [
    {
        "id": 1,
        "criteria_id": 1,
        "candidate_id": 1,
        "score": 95.5,
        "explanation": "Strong match: Has all required skills at high proficiency",
        "created_at": "2026-04-01T16:00:00"
    },
    {
        "id": 2,
        "criteria_id": 1,
        "candidate_id": 2,
        "score": 45.0,
        "explanation": "Moderate match: Missing Python and FastAPI expertise",
        "created_at": "2026-04-01T16:01:00"
    },
    {
        "id": 3,
        "criteria_id": 1,
        "candidate_id": 3,
        "score": 70.5,
        "explanation": "Good match: Has Python, missing Docker and API expertise",
        "created_at": "2026-04-01T16:02:00"
    }
]

MOCK_FAVORITES = [
    {
        "id": 1,
        "recruiter_id": 1,
        "candidate_id": 1,
        "created_at": "2026-04-01T17:00:00"
    },
    {
        "id": 2,
        "recruiter_id": 1,
        "candidate_id": 3,
        "created_at": "2026-04-01T17:05:00"
    }
]


def get_mock_candidates():
    """Get mock candidates"""
    return MOCK_CANDIDATES


def get_mock_criteria():
    """Get mock job criteria"""
    return MOCK_JOB_CRITERIA


def get_mock_match_results():
    """Get mock match results"""
    return MOCK_MATCH_RESULTS


def get_mock_favorites():
    """Get mock favorites"""
    return MOCK_FAVORITES
