import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from root .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from app.core.database import Base, engine
from app.models.models import User, Candidate, Skill, CandidateSkill, Experience, Education, JobCriteria, CriteriaSkill, MatchResult, Favorite
from app.api import auth, candidates, skills, jobs, matching, favorites, experiences, educations, match_results
from app.api.chat import router as chat_router
from app.api.export import router as export_router
from app.api.criteria import criteria_router, matching_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        try:
            from ai_module.nlp.profile_generator import ProfileGenerator
            from ai_module.matching.semantic_matcher import SemanticSkillMatcher

            ProfileGenerator.clear_cache()
            SemanticSkillMatcher.release_resources()
        finally:
            engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title="AI Talent Finder",
    version="1.0.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers (Auth must be first)
app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(skills.router)
app.include_router(jobs.router)
app.include_router(criteria_router)
app.include_router(matching.router)
app.include_router(matching_router)
app.include_router(favorites.router)
app.include_router(experiences.router)
app.include_router(educations.router)
app.include_router(match_results.router)
app.include_router(chat_router)
app.include_router(export_router)

# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}
