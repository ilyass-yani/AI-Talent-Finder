"""Synthetic data generation for testing and training."""

from typing import List, Dict, Any
import random


SKILLS_POOL = [
    "Python", "JavaScript", "React", "Node.js", "TypeScript",
    "AWS", "Docker", "Kubernetes", "PostgreSQL", "MongoDB",
    "Django", "FastAPI", "REST API", "GraphQL", "CI/CD",
    "Git", "Linux", "Machine Learning", "TensorFlow", "PyTorch",
    "Data Analysis", "Pandas", "SQL", "Java", "C++",
    "Agile", "Scrum", "Problem Solving", "Leadership", "Communication",
]

COMPANIES = [
    "Google", "Amazon", "Microsoft", "Apple", "Meta", "Netflix",
    "Tesla", "SpaceX", "Stripe", "Airbnb", "Uber", "Spotify",
    "GitHub", "GitLab", "Open Source Foundation",
]

LANGUAGES = ["English", "French", "Spanish", "German", "Chinese", "Japanese"]

JOB_TITLES = [
    "Senior React Developer", "Backend Engineer", "Full Stack Developer",
    "Data Scientist", "DevOps Engineer", "ML Engineer", "Product Engineer",
    "Solutions Architect", "Technical Lead", "Software Engineer",
]

LOCATIONS = [
    "San Francisco", "New York", "London", "Paris", "Berlin",
    "Toronto", "Sydney", "Singapore", "Tokyo", "Dubai",
]


def generate_synthetic_candidate(user_id: int = None) -> Dict[str, Any]:
    """Generate a realistic synthetic CV candidate."""
    if user_id is None:
        user_id = random.randint(1000, 9999)

    skills_count = random.randint(4, 12)
    candidate_skills = random.sample(SKILLS_POOL, min(skills_count, len(SKILLS_POOL)))

    years = random.randint(1, 20)
    languages_count = random.randint(1, 3)
    candidate_langs = random.sample(LANGUAGES, min(languages_count, len(LANGUAGES)))

    return {
        "id": user_id,
        "full_name": f"Candidate {user_id}",
        "email": f"candidate{user_id}@example.com",
        "phone": f"+1-555-{random.randint(1000, 9999)}",
        "companies": random.sample(COMPANIES, min(random.randint(1, 3), len(COMPANIES))),
        "normalized_skills": candidate_skills,
        "experience_years": years,
        "education": random.choice(["Bachelor in Computer Science", "Master in AI", "Bootcamp Graduate"]),
        "languages": candidate_langs,
        "location": random.choice(LOCATIONS),
    }


def generate_synthetic_job(job_id: int = None) -> Dict[str, Any]:
    """Generate a realistic synthetic job posting."""
    if job_id is None:
        job_id = random.randint(1000, 9999)

    required_skills_count = random.randint(3, 8)
    required_skills = random.sample(SKILLS_POOL, min(required_skills_count, len(SKILLS_POOL)))

    req_years = random.randint(0, 15)
    req_languages = random.sample(LANGUAGES, min(random.randint(1, 2), len(LANGUAGES)))

    return {
        "id": job_id,
        "title": random.choice(JOB_TITLES),
        "company": random.choice(COMPANIES),
        "required_skills": required_skills,
        "required_years": req_years,
        "education_requirement": random.choice(["Bachelor's degree", "Master's degree", "Bootcamp or equivalent"]),
        "languages_required": req_languages,
        "location": random.choice(LOCATIONS),
        "description": f"We are looking for a {random.choice(JOB_TITLES)} with expertise in {', '.join(required_skills[:3])} and {req_years}+ years of experience.",
    }


def generate_synthetic_dataset(
    n_candidates: int = 50,
    n_jobs: int = 20,
    seed: int = 42,
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate synthetic dataset for testing."""
    random.seed(seed)

    candidates = [generate_synthetic_candidate(i) for i in range(n_candidates)]
    jobs = [generate_synthetic_job(j) for j in range(n_jobs)]

    return {
        "candidates": candidates,
        "jobs": jobs,
    }


__all__ = [
    "generate_synthetic_candidate",
    "generate_synthetic_job",
    "generate_synthetic_dataset",
]


if __name__ == "__main__":
    dataset = generate_synthetic_dataset(n_candidates=5, n_jobs=3)
    print(f"Generated {len(dataset['candidates'])} candidates and {len(dataset['jobs'])} jobs")
    for c in dataset["candidates"][:2]:
        print(f"  Candidate: {c['full_name']} ({c['experience_years']} years, {len(c['normalized_skills'])} skills)")
    for j in dataset["jobs"][:2]:
        print(f"  Job: {j['title']} @ {j['company']} ({j['required_years']} years required)")
