"""Test runner: call pipeline.run directly without starting HTTP server."""
import json
from app.api import pipeline


def main():
    payload = {
        "candidate": {"raw_text": "John Doe\nExperience: 5 years Python, AWS, Docker. Skills: Python, AWS, Docker."},
        "job": {"job_text": "Senior Python developer with AWS experience", "skills": ["Python", "AWS"]},
        "mode": "semantic",
    }

    result = pipeline.run_pipeline(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
