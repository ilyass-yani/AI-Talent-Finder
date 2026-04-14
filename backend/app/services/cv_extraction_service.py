"""
Complete CV extraction and information parsing service
Handles extraction of all candidate information from CV
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from ai_module.nlp.cv_cleaner import CVCleaner
from ai_module.nlp.skill_extractor import SkillExtractor
from app.core.nlp_container import NLPContainer

logger = logging.getLogger(__name__)


class CVExtractionService:
    """Service for extracting all information from CV"""
    
    def __init__(self, db: Session):
        """
        Initialize CV extraction service
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.cleaner = CVCleaner()
        self.skill_extractor = SkillExtractor()
        self.nlp_service = NLPContainer.get_service()
    
    def extract_all(self, candidate_id: int, cv_text: str) -> Dict:
        """
        Extract all information from CV and save to database
        
        Args:
            candidate_id: ID of the candidate
            cv_text: Raw CV text
        
        Returns:
            Dict with all extracted information
        """
        result = {
            "success": False,
            "candidate_id": candidate_id,
            "contact_info": {},
            "skills": [],
            "experiences": [],
            "educations": [],
            "errors": []
        }
        
        try:
            logger.info(f"[CV_EXTRACT] Starting complete extraction for candidate {candidate_id}")
            
            # Verify candidate exists
            candidate_row = self.db.execute(
                text("SELECT id FROM candidates WHERE id = :id"),
                {"id": candidate_id}
            ).first()
            
            if not candidate_row:
                result["errors"].append(f"Candidate {candidate_id} not found")
                return result
            
            # 1. Extract contact information
            logger.info("[CV_EXTRACT] Extracting contact information...")
            contact_info = self._extract_contact_info(cv_text)
            result["contact_info"] = contact_info
            
            # Save contact info to candidate table
            self._save_contact_info(candidate_id, contact_info)
            
            # 2. Extract skills
            logger.info("[CV_EXTRACT] Extracting skills...")
            skills = self._extract_and_save_skills(candidate_id, cv_text)
            result["skills"] = skills
            
            # 3. Extract experiences
            logger.info("[CV_EXTRACT] Extracting experiences...")
            experiences = self._extract_and_save_experiences(candidate_id, cv_text)
            result["experiences"] = experiences
            
            # 4. Extract educations
            logger.info("[CV_EXTRACT] Extracting educations...")
            educations = self._extract_and_save_educations(candidate_id, cv_text)
            result["educations"] = educations
            
            # Commit all changes
            self.db.commit()
            result["success"] = True
            logger.info(f"[CV_EXTRACT] Successfully extracted all information for candidate {candidate_id}")
            
        except Exception as e:
            self.db.rollback()
            error_msg = f"Error in CV extraction: {str(e)}"
            logger.error(f"[CV_EXTRACT] {error_msg}")
            result["errors"].append(error_msg)
            import traceback
            logger.error(traceback.format_exc())
        
        return result
    
    def _extract_contact_info(self, cv_text: str) -> Dict:
        """Extract contact information from CV"""
        contact = {}
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', cv_text)
        if email_match:
            contact["email"] = email_match.group(0)
            logger.debug(f"[CV_EXTRACT] Found email: {contact['email']}")
        
        # Extract phone
        phone_match = re.search(
            r'(\+?\d{1,3}[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            cv_text
        )
        if phone_match:
            contact["phone"] = phone_match.group(0).strip()
            logger.debug(f"[CV_EXTRACT] Found phone: {contact['phone']}")
        
        # Extract LinkedIn URL
        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+', cv_text)
        if linkedin_match:
            contact["linkedin_url"] = linkedin_match.group(0)
            logger.debug(f"[CV_EXTRACT] Found LinkedIn: {contact['linkedin_url']}")
        
        # Extract GitHub URL
        github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+', cv_text)
        if github_match:
            contact["github_url"] = github_match.group(0)
            logger.debug(f"[CV_EXTRACT] Found GitHub: {contact['github_url']}")
        
        return contact
    
    def _save_contact_info(self, candidate_id: int, contact_info: Dict) -> None:
        """Save contact information to database"""
        if not contact_info:
            return
        
        update_fields = []
        params = {"candidate_id": candidate_id}
        
        if "email" in contact_info:
            update_fields.append("email = :email")
            params["email"] = contact_info["email"]
        
        if "phone" in contact_info:
            update_fields.append("phone = :phone")
            params["phone"] = contact_info["phone"]
        
        if "linkedin_url" in contact_info:
            update_fields.append("linkedin_url = :linkedin_url")
            params["linkedin_url"] = contact_info["linkedin_url"]
        
        if "github_url" in contact_info:
            update_fields.append("github_url = :github_url")
            params["github_url"] = contact_info["github_url"]
        
        if update_fields:
            query = f"UPDATE candidates SET {', '.join(update_fields)} WHERE id = :candidate_id"
            self.db.execute(text(query), params)
            logger.debug(f"[CV_EXTRACT] Saved contact info for candidate {candidate_id}")
    
    def _extract_and_save_skills(self, candidate_id: int, cv_text: str) -> List[Dict]:
        """Extract skills and save to database"""
        skills_list = []
        
        try:
            extracted_skills = self.skill_extractor.extract_skills(cv_text)
            print(f"[DEBUG] Extracted skills: {extracted_skills}")  # DEBUG
            
            for skill_data in extracted_skills:
                try:
                    skill_name = skill_data.get("name", "").strip()
                    category = skill_data.get("category", "tech")
                    
                    if not skill_name:
                        continue
                    
                    # Use NLP to find best matching skill from database
                    original_skill = skill_name
                    skill_name = self._find_best_skill_match(skill_name)
                    
                    if skill_name != original_skill:
                        logger.info(f"[CV_EXTRACT] Normalized skill: '{original_skill}' -> '{skill_name}'")
                    
                    # Get or create skill
                    skill_row = self.db.execute(
                        text("SELECT id FROM skills WHERE LOWER(name) = LOWER(:name)"),
                        {"name": skill_name}
                    ).first()
                    
                    if skill_row:
                        skill_id = skill_row[0]
                    else:
                        skill_result = self.db.execute(
                            text("""
                                INSERT INTO skills (name, category, synonyms)
                                VALUES (:name, :category, NULL)
                                RETURNING id
                            """),
                            {"name": skill_name, "category": category}
                        )
                        skill_id = skill_result.scalar()
                    
                    # Estimate proficiency
                    proficiency = self.skill_extractor.extract_proficiency(cv_text, skill_name)
                    
                    # Check if already exists
                    existing = self.db.execute(
                        text("""
                            SELECT id FROM candidate_skills
                            WHERE candidate_id = :candidate_id AND skill_id = :skill_id
                        """),
                        {"candidate_id": candidate_id, "skill_id": skill_id}
                    ).first()
                    
                    if not existing:
                        cs_result = self.db.execute(
                            text("""
                                INSERT INTO candidate_skills 
                                (candidate_id, skill_id, proficiency_level, source)
                                VALUES (:candidate_id, :skill_id, :proficiency_level, :source)
                                RETURNING id
                            """),
                            {
                                "candidate_id": candidate_id,
                                "skill_id": skill_id,
                                "proficiency_level": proficiency,
                                "source": "CV"
                            }
                        )
                        cs_id = cs_result.scalar()
                        
                        skills_list.append({
                            "name": skill_name,
                            "category": category,
                            "proficiency": proficiency
                        })
                        logger.debug(f"[CV_EXTRACT] Saved skill: {skill_name}")
                
                except Exception as e:
                    logger.error(f"[CV_EXTRACT] Error processing skill: {str(e)}")
        
        except Exception as e:
            logger.error(f"[CV_EXTRACT] Error extracting skills: {str(e)}")
        
        print(f"[DEBUG] Skills list returned: {skills_list}")  # DEBUG
        return skills_list
    
    def _find_best_skill_match(self, extracted_skill: str) -> Optional[str]:
        """
        Find the best matching skill from database using semantic similarity.
        
        Uses NLP to find semantic matches:
            "python coding" → "Python"
            "js" → "JavaScript"
            "machine learning" → "Machine Learning"
        """
        if not self.nlp_service:
            return extracted_skill
        
        try:
            # Get all known skills from database
            skill_rows = self.db.execute(
                text("SELECT DISTINCT name FROM skills ORDER BY name LIMIT 200")
            ).fetchall()
            
            if not skill_rows:
                return extracted_skill
            
            known_skills = [row[0] for row in skill_rows]
            
            # Find similar skills using semantic matching
            matches = self.nlp_service.find_similar(
                extracted_skill,
                known_skills,
                top_k=1,
                threshold=0.4
            )
            
            if matches:
                best_match = matches[0][0]
                confidence = matches[0][1]
                
                if confidence > 0.4:
                    logger.info(
                        f"[NLP] Matched '{extracted_skill}' → '{best_match}' "
                        f"(confidence: {confidence:.2f})"
                    )
                    return best_match
            
            return extracted_skill
        
        except Exception as e:
            logger.warning(f"[NLP] Error in skill matching: {e}")
            return extracted_skill
    
    def _extract_and_save_experiences(self, candidate_id: int, cv_text: str) -> List[Dict]:
        """Extract work experiences and save to database"""
        experiences_list = []
        
        try:
            experiences = self._parse_experiences(cv_text)
            
            for exp in experiences:
                try:
                    # Insert experience
                    exp_result = self.db.execute(
                        text("""
                            INSERT INTO experiences 
                            (candidate_id, title, company, duration_months, description)
                            VALUES (:candidate_id, :title, :company, :duration_months, :description)
                            RETURNING id
                        """),
                        {
                            "candidate_id": candidate_id,
                            "title": exp.get("title", ""),
                            "company": exp.get("company", ""),
                            "duration_months": exp.get("duration_months", 0),
                            "description": exp.get("description", "")
                        }
                    )
                    exp_id = exp_result.scalar()
                    
                    experiences_list.append({
                        "title": exp.get("title"),
                        "company": exp.get("company"),
                        "duration_months": exp.get("duration_months")
                    })
                    logger.debug(f"[CV_EXTRACT] Saved experience: {exp.get('title')} at {exp.get('company')}")
                
                except Exception as e:
                    logger.error(f"[CV_EXTRACT] Error saving experience: {str(e)}")
        
        except Exception as e:
            logger.error(f"[CV_EXTRACT] Error extracting experiences: {str(e)}")
        
        return experiences_list
    
    def _extract_and_save_educations(self, candidate_id: int, cv_text: str) -> List[Dict]:
        """Extract education information and save to database"""
        educations_list = []
        
        try:
            educations = self._parse_educations(cv_text)
            
            for edu in educations:
                try:
                    # Insert education
                    edu_result = self.db.execute(
                        text("""
                            INSERT INTO educations 
                            (candidate_id, degree, institution, field, year)
                            VALUES (:candidate_id, :degree, :institution, :field, :year)
                            RETURNING id
                        """),
                        {
                            "candidate_id": candidate_id,
                            "degree": edu.get("degree", ""),
                            "institution": edu.get("institution", ""),
                            "field": edu.get("field", ""),
                            "year": edu.get("year")
                        }
                    )
                    edu_id = edu_result.scalar()
                    
                    educations_list.append({
                        "degree": edu.get("degree"),
                        "institution": edu.get("institution"),
                        "field": edu.get("field"),
                        "year": edu.get("year")
                    })
                    logger.debug(f"[CV_EXTRACT] Saved education: {edu.get('degree')} from {edu.get('institution')}")
                
                except Exception as e:
                    logger.error(f"[CV_EXTRACT] Error saving education: {str(e)}")
        
        except Exception as e:
            logger.error(f"[CV_EXTRACT] Error extracting educations: {str(e)}")
        
        return educations_list
    
    def _parse_experiences(self, text: str) -> List[Dict]:
        """Parse work experiences from CV - simplified and robust"""
        experiences = []
        
        if not text or not isinstance(text, str):
            return experiences
        
        # Only look for the WORK EXPERIENCE section
        if 'WORK EXPERIENCE' not in text and 'EXPERIENCE' not in text:
            return experiences
        
        # Find the section
        exp_start = max(
            text.find('WORK EXPERIENCE'),
            text.find('WORK EXPERIENCE'),
            text.find('EXPERIENCE') if 'EXPERIENCE' in text else -1
        )
        
        if exp_start == -1:
            return experiences
        
        # Find the end (next section or end of CV)
        sections = ['EDUCATION', 'SKILLS', 'CERTIFICATIONS', 'PROJECTS']
        exp_end = len(text)
        for section in sections:
            pos = text.find(section, exp_start)
            if pos != -1 and pos < exp_end:
                exp_end = pos
        
        exp_section = text[exp_start:exp_end]
        
        # Parse experiences from this section
        lines = exp_section.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for date pattern YYYY-YYYY
            date_match = re.search(r'(\d{4})\s*[-–]\s*(\d{4})', line)
            if date_match:
                start_year = int(date_match.group(1))
                end_year = int(date_match.group(2))
                duration = max(1, (end_year - start_year) * 12)
                
                # Title is previous non-empty line
                title = ""
                for j in range(i-1, max(-1, i-3), -1):
                    candidate_title = lines[j].strip()
                    if candidate_title and not candidate_title.isupper():
                        title = candidate_title
                        break
                
                # Company is from the date line, before the date
                before_date = line[:date_match.start()].strip()
                company = before_date.split('|')[0].strip() if '|' in before_date else before_date
                
                if title or company:
                    experiences.append({
                        "title": title or "Experience",
                        "company": company,
                        "duration_months": duration,
                        "description": ""
                    })
            
            i += 1
        
        return experiences[:10]
    
    def _parse_educations(self, text: str) -> List[Dict]:
        """
        Parse education information from CV text
        Generic approach that works with any CV format
        """
        educations = []
        
        # Degree keywords - broad list
        degree_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'diploma', 'degree',
            'licence', 'baccalauréat', 'bts', 'cnas', 'master',
            'b.s', 'b.a', 'm.s', 'm.a', 'mba'
        ]
        
        lines = text.split('\n')
        
        # Look for lines mentioning degrees
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if line contains degree keyword
            if any(deg in line_lower for deg in degree_keywords):
                education = {
                    "degree": self._extract_degree(line),
                    "institution": self._extract_institution(line),
                    "field": self._extract_field(line),
                    "year": self._extract_year(line)
                }
                
                # If we didn't find institution in this line, check next line
                if not education["institution"] and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not any(deg in next_line.lower() for deg in degree_keywords):
                        # Next line might be the institution
                        edu_next = {
                            "degree": "",
                            "institution": self._extract_institution(next_line),
                            "field": self._extract_field(next_line),
                            "year": self._extract_year(next_line)
                        }
                        if edu_next["institution"]:
                            education["institution"] = edu_next["institution"]
                        if not education["field"] and edu_next["field"]:
                            education["field"] = edu_next["field"]
                        if not education["year"] and edu_next["year"]:
                            education["year"] = edu_next["year"]
                
                # If still missing institution, check line before
                if not education["institution"] and i > 0:
                    prev_line = lines[i - 1].strip()
                    education["institution"] = self._extract_institution(prev_line)
                
                # Only add if we found something meaningful
                if education["institution"] or education["degree"]:
                    # Check for duplicates
                    if not any(e["degree"] == education["degree"] and e["institution"] == education["institution"] for e in educations):
                        educations.append(education)
        
        return educations[:5]  # Limit to 5 most recent degrees
    
    def _extract_degree(self, text: str) -> str:
        """Extract degree type from text"""
        degree_map = {
            "PhD": "Ph.D.",
            "Doctor": "Ph.D.",
            "Master": "Master's",
            "M.S": "Master's",
            "MS": "Master's",
            "MBA": "MBA",
            "Bachelor": "Bachelor's",
            "B.S": "Bachelor's",
            "BS": "Bachelor's",
            "B.A": "Bachelor's",
            "BA": "Bachelor's",
            "Licence": "License/Bachelor's",
            "Licence Pro": "License Pro",
            "BTS": "BTS",
            "Baccalauréat": "High School Diploma"
        }
        
        # Check longest matches first to avoid partial matches
        sorted_degrees = sorted(degree_map.keys(), key=len, reverse=True)
        for key in sorted_degrees:
            if key.lower() in text.lower():
                return degree_map[key]
        
        return "Degree"
    
    def _extract_institution(self, text: str) -> str:
        """Extract institution/university name from text"""
        # Common university indicators
        uni_keywords = ['university', 'college', 'institute', 'school', 'institut', 'école', 'université']
        
        # First, look for explicit university mentions
        for keyword in uni_keywords:
            if keyword in text.lower():
                # Extract the institution name - usually around these keywords
                match = re.search(rf'([A-Za-z\s&,\.]+(?:{keyword}))', text, re.IGNORECASE)
                if match:
                    institution = match.group(1).strip()
                    return institution[:100]
        
        # If no university keyword found, take capitalized words (usually institution names)
        # Remove common words and extra info
        parts = text.split('|')
        for part in parts:
            clean = part.strip()
            # Skip if it's a year
            if re.search(r'^\d{4}', clean):
                continue
            # Skip if it's very short or very long
            if 3 < len(clean) < 80:
                return clean[:100]
        
        # Last resort: look for capitalized words
        words = text.split()
        capitalized = [w for w in words if w and w[0].isupper() and not w.isdigit()]
        if capitalized:
            return ' '.join(capitalized[:3])[:100]
        
        return ""
    
    def _extract_field(self, text: str) -> str:
        """Extract field of study from text"""
        field_keywords = [
            "Computer Science", "Informatique", "Engineering", "Ingénierie",
            "Business", "Commerce", "Distribution", "Mathematics", "Mathématiques",
            "Physics", "Physique", "Chemistry", "Chimie", "Biology", "Biologie",
            "Finance", "Accounting", "Comptabilité", "Marketing", "Economics", "Économie",
            "Law", "Droit", "Medicine", "Médecine", "Administration", "Management",
            "Communication", "Design", "Graphique", "Web Development", "Développement Web",
            "Data Science", "Science des Données", "Artificial Intelligence", "IA",
            "Cybersecurity", "Cybersécurité", "Cloud", "Network", "Réseau"
        ]
        
        # Check for explicit field mentions
        for field in field_keywords:
            if field.lower() in text.lower():
                return field
        
        # Try to extract from "in [field]" or "of [field]" pattern
        match = re.search(r"(?:in|of|en|de|domaine)\s+([A-Za-z\s]+?)(?:\n|,|–|;|at|from|à|de|$)", text, re.IGNORECASE)
        if match:
            field = match.group(1).strip()
            if field and len(field) > 2 and len(field) < 100:
                return field[:100]
        
        return ""
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract graduation year from text"""
        year_match = re.search(r'(?:20|19)\d{2}', text)
        if year_match:
            try:
                return int(year_match.group(0))
            except:
                pass
        
        return None
