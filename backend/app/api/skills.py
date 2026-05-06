"""Skills API routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.models.models import Skill

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillCreate(BaseModel):
    name: str
    category: str  # tech, soft, language


class SkillResponse(BaseModel):
    id: int
    name: str
    category: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SkillResponse])
def get_skills(
    category: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all skills, optionally filtered by category"""
    query = db.query(Skill)
    if category:
        query = query.filter(Skill.category == category)
    skills = query.offset(skip).limit(limit).all()
    return skills


@router.get("/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific skill by ID"""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    return skill


@router.post("/", response_model=SkillResponse)
def create_skill(
    skill: SkillCreate,
    db: Session = Depends(get_db)
):
    """Create a new skill"""
    # Check if skill already exists
    existing_skill = db.query(Skill).filter(
        Skill.name == skill.name,
        Skill.category == skill.category
    ).first()
    
    if existing_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already exists"
        )
    
    db_skill = Skill(name=skill.name, category=skill.category)
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db)
):
    """Delete a skill"""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    
    db.delete(skill)
    db.commit()
    return None
