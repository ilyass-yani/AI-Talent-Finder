"""
Service layer for skill extraction and management
Handles all skill-related database operations and NLP processing
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import SkillCategory, ProficiencyLevel
from ai_module.nlp.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class SkillService:
    """Service for managing candidate skills and skill extraction"""
    
    def __init__(self, db: Session):
        """
        Initialize skill service
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.extractor = SkillExtractor()
    
    def extract_and_save_skills(
        self, 
        candidate_id: int, 
        cv_text: str
    ) -> Dict:
        """
        Extract skills from CV text and save to database.
        
        Args:
            candidate_id: ID of the candidate
            cv_text: Raw CV text to extract skills from
        
        Returns:
            Dict with extraction results and any errors
        """
        result = {
            "success": False,
            "skills_extracted": 0,
            "skills_saved": 0,
            "errors": [],
            "details": []
        }
        
        try:
            # Validate inputs
            if not candidate_id or not cv_text:
                result["errors"].append("Missing candidate_id or cv_text")
                return result
            
            # Verify candidate exists using SQL
            candidate_row = self.db.execute(
                text("SELECT id FROM candidates WHERE id = :id"),
                {"id": candidate_id}
            ).first()
            
            if not candidate_row:
                result["errors"].append(f"Candidate {candidate_id} not found")
                return result
            
            logger.info(f"[SKILLS] Starting extraction for candidate {candidate_id}")
            logger.info(f"[SKILLS] CV text length: {len(cv_text)} characters")
            
            # Extract skills using NLP module
            extracted_skills = self.extractor.extract_skills(cv_text)
            result["skills_extracted"] = len(extracted_skills)
            
            if not extracted_skills:
                logger.warning(f"[SKILLS] No skills found for candidate {candidate_id}")
                result["success"] = True
                return result
            
            logger.info(f"[SKILLS] Found {len(extracted_skills)} skills")
            logger.info(f"[SKILLS] Skill names: {[s['name'] for s in extracted_skills]}")
            
            # Process each extracted skill
            for skill_data in extracted_skills:
                try:
                    self._process_skill(candidate_id, skill_data, cv_text, result)
                except Exception as skill_error:
                    error_msg = f"Error processing skill '{skill_data.get('name')}': {str(skill_error)}"
                    logger.error(f"[SKILLS] {error_msg}")
                    result["errors"].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            result["success"] = True
            logger.info(f"[SKILLS] Successfully saved {result['skills_saved']} skills for candidate {candidate_id}")
            
        except Exception as e:
            self.db.rollback()
            error_msg = f"Fatal error in skill extraction: {str(e)}"
            logger.error(f"[SKILLS] {error_msg}")
            result["errors"].append(error_msg)
            import traceback
            logger.error(traceback.format_exc())
        
        return result
    
    def _process_skill(
        self, 
        candidate_id: int, 
        skill_data: Dict, 
        cv_text: str,
        result: Dict
    ) -> None:
        """
        Process a single skill and save to database.
        
        Args:
            candidate_id: ID of the candidate
            skill_data: Extracted skill data dict
            cv_text: Full CV text for proficiency estimation
            result: Result dict to update with details
        """
        skill_name = skill_data.get("name", "").strip()
        skill_category_str = skill_data.get("category", "tech").lower()
        
        if not skill_name:
            raise ValueError("Empty skill name")
        
        logger.debug(f"[SKILLS] Processing skill: {skill_name} ({skill_category_str})")
        
        # Map category to enum value (use string, not enum object in SQL)
        try:
            category_value = SkillCategory(skill_category_str).value
        except ValueError:
            logger.warning(f"[SKILLS] Unknown category '{skill_category_str}', using 'tech'")
            category_value = "tech"
        
        # Get or create skill using SQL
        existing_skill = self.db.execute(
            text("SELECT id FROM skills WHERE LOWER(name) = LOWER(:name)"),
            {"name": skill_name}
        ).first()
        
        if existing_skill:
            skill_id = existing_skill[0]
            logger.debug(f"[SKILLS] Found existing skill in DB: {skill_id}")
        else:
            # Insert new skill
            insert_result = self.db.execute(
                text("""
                    INSERT INTO skills (name, category, synonyms)
                    VALUES (:name, :category, NULL)
                    RETURNING id
                """),
                {"name": skill_name, "category": category_value}
            )
            skill_id = insert_result.scalar()
            logger.debug(f"[SKILLS] Created new skill in DB: {skill_id}")
        
        # Estimate proficiency level from context
        proficiency_str = self.extractor.extract_proficiency(cv_text, skill_name)
        
        # Map proficiency to enum value
        try:
            proficiency_value = ProficiencyLevel(proficiency_str).value
        except ValueError:
            logger.warning(f"[SKILLS] Unknown proficiency '{proficiency_str}', using 'intermediate'")
            proficiency_value = "intermediate"
        
        logger.debug(f"[SKILLS] Estimated proficiency: {proficiency_value}")
        
        # Check if CandidateSkill already exists
        existing_cs = self.db.execute(
            text("""
                SELECT id FROM candidate_skills 
                WHERE candidate_id = :candidate_id AND skill_id = :skill_id
            """),
            {"candidate_id": candidate_id, "skill_id": skill_id}
        ).first()
        
        if existing_cs:
            logger.debug(f"[SKILLS] CandidateSkill already exists, skipping")
            return
        
        # Insert CandidateSkill
        cs_result = self.db.execute(
            text("""
                INSERT INTO candidate_skills (candidate_id, skill_id, proficiency_level, source)
                VALUES (:candidate_id, :skill_id, :proficiency_level, :source)
                RETURNING id
            """),
            {
                "candidate_id": candidate_id,
                "skill_id": skill_id,
                "proficiency_level": proficiency_value,
                "source": "CV"
            }
        )
        cs_id = cs_result.scalar()
        
        result["skills_saved"] += 1
        result["details"].append({
            "skill_name": skill_name,
            "category": category_value,
            "proficiency": proficiency_value
        })
        
        logger.info(f"[SKILLS] Saved skill: {skill_name} (ID: {cs_id})")
    
    def get_candidate_skills(self, candidate_id: int) -> Dict:
        """
        Get all skills for a candidate with their proficiency levels.
        
        Args:
            candidate_id: ID of the candidate
        
        Returns:
            Dict with candidate info and skills list
        """
        try:
            # Use SQL text query to match actual database schema
            from sqlalchemy import text
            
            # First check if candidate exists (use columns that actually exist)
            result = self.db.execute(
                text("SELECT id, filename FROM candidates WHERE id = :id"),
                {"id": candidate_id}
            ).first()
            
            if not result:
                return {"error": f"Candidate {candidate_id} not found", "skills": []}
            
            candidate_id_db, filename = result
            
            # Get candidate skills using SQL to match actual schema
            skills_result = self.db.execute(
                text("""
                    SELECT cs.id, s.name, s.category, cs.proficiency_level, cs.source
                    FROM candidate_skills cs
                    JOIN skills s ON cs.skill_id = s.id
                    WHERE cs.candidate_id = :candidate_id
                """),
                {"candidate_id": candidate_id}
            ).fetchall()
            
            skills_list = []
            for row in skills_result:
                try:
                    cs_id, skill_name, category, proficiency, source = row
                    skills_list.append({
                        "id": cs_id,
                        "name": skill_name,
                        "category": category,
                        "proficiency_level": proficiency,
                        "source": source
                    })
                except Exception as e:
                    logger.error(f"[SKILLS] Error processing skill row: {str(e)}")
                    continue
            
            return {
                "candidate_id": candidate_id,
                "filename": filename,
                "skills_count": len(skills_list),
                "skills": skills_list
            }
        except Exception as e:
            logger.error(f"[SKILLS] Error in get_candidate_skills: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "error": f"Error fetching candidate skills: {str(e)}",
                "skills": []
            }
