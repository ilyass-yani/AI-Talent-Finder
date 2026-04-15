"""NER-based Resume Extraction using AventIQ Model"""
import logging
from typing import Dict, List, Any, Optional
import re

from ai_module.nlp.cv_cleaner import CVCleaner
from ai_module.nlp.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class NERExtractor:
    """Extract structured data from resume text using Named Entity Recognition"""

    def __init__(self):
        """Initialize NER pipeline lazily (on first use)"""
        self.ner_pipeline = None
        self._loading = False
        self.skill_extractor = SkillExtractor()

    def _ensure_loaded(self):
        """Load NER pipeline lazily on first use"""
        if self.ner_pipeline is not None or self._loading:
            return
            
        if self._loading:
            logger.warning("NER pipeline is still loading...")
            return
        
        try:
            self._loading = True
            from transformers import pipeline
            
            logger.info("Loading NER Pipeline: AventIQ-AI/Resume-Parsing-NER-AI-Model...")
            self.ner_pipeline = pipeline(
                "ner",
                model="AventIQ-AI/Resume-Parsing-NER-AI-Model",
                aggregation_strategy="simple"
            )
            logger.info("✓ NER Pipeline loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NER model: {e}")
            self.ner_pipeline = None
        finally:
            self._loading = False

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract resume entities using NER model
        
        Args:
            text: Resume text
            
        Returns:
            Dict with extracted entities (name, email, phone, skills, etc.)
        """
        # Try NER extraction if available
        try:
            self._ensure_loaded()
            
            if not self.ner_pipeline:
                logger.warning("NER Pipeline not available, returning empty results")
                return self._empty_result()
            
            # Run NER on the full text
            entities = self.ner_pipeline(text)
            logger.info(f"NER extracted {len(entities)} entity mentions")
            
            # Process and structure entities
            result = self._process_entities(entities, text)
            if self._has_fragmented_output(result):
                logger.info("NER output looks fragmented, using fallback heuristics")
                return self._fallback_extract(text)
            if not result.get("skills") and not result.get("experiences") and not result.get("educations"):
                logger.info("NER model returned sparse output, using fallback heuristics")
                return self._fallback_extract(text)
            return result
            
        except Exception as e:
            logger.warning(f"Error during NER extraction: {e}, using fallback")
            return self._fallback_extract(text)

    def _process_entities(self, entities: List[Dict], text: str) -> Dict[str, Any]:
        """
        Process raw NER outputs into structured format
        
        Entity tags from model:
        - NAME: Person name
        - EMAIL: Email address
        - PHONE: Phone number
        - EDUCATION: Degree/School
        - SKILL: Technical/Soft skills
        - COMPANY: Company name
        - JOB: Job title
        """
        result = {
            "name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experiences": [],
            "educations": [],
            "raw_entities": entities
        }

        # Group entities by type
        grouped = {}
        for entity in entities:
            entity_type = entity.get("entity_group", "O")
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(entity.get("word", "").strip())

        # Extract specific fields
        if "NAME" in grouped and grouped["NAME"]:
            result["name"] = " ".join(grouped["NAME"][:2])  # First two name mentions

        if "EMAIL" in grouped and grouped["EMAIL"]:
            emails = grouped["EMAIL"]
            result["email"] = self._extract_email(text, emails)

        if "PHONE" in grouped and grouped["PHONE"]:
            phones = grouped["PHONE"]
            result["phone"] = self._extract_phone(text, phones)

        if "SKILL" in grouped and grouped["SKILL"]:
            result["skills"] = list(set(grouped["SKILL"]))  # Remove duplicates

        if "COMPANY" in grouped and grouped["COMPANY"]:
            # Create experience entries from companies and job titles
            companies = grouped["COMPANY"]
            jobs = grouped.get("JOB", [])
            result["experiences"] = self._create_experiences(companies, jobs)

        if "EDUCATION" in grouped and grouped["EDUCATION"]:
            # Create education entries
            educations = grouped["EDUCATION"]
            result["educations"] = self._create_educations(educations, text)

        return result

    def _has_fragmented_output(self, result: Dict[str, Any]) -> bool:
        """Detect low-quality outputs made of fragments or single tokens."""
        def is_fragment(value: Optional[str]) -> bool:
            cleaned = (value or "").strip()
            if not cleaned:
                return True
            if cleaned.startswith("##"):
                return True
            if len(cleaned) <= 2:
                return True
            if cleaned.isdigit():
                return True
            if not re.search(r"[A-Za-zÀ-ÿ]", cleaned):
                return True
            return False

        if is_fragment(result.get("name")):
            return True

        skills = result.get("skills") or []
        if len(skills) == 1 and is_fragment(skills[0]):
            return True

        for education in result.get("educations") or []:
            if is_fragment(education.get("degree")) or is_fragment(education.get("institution")):
                return True

        return False

    def _extract_email(self, text: str, email_mentions: List[str]) -> str:
        """Extract full email address from text"""
        # Try to find complete email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            return emails[0]  # Return first found email
        return " ".join(email_mentions) if email_mentions else None

    def _extract_phone(self, text: str, phone_mentions: List[str]) -> str:
        """Extract full phone number from text"""
        # Try to find phone numbers
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}'
        phones = re.findall(phone_pattern, text)
        if phones:
            return phones[0]  # Return first found phone
        return " ".join(phone_mentions) if phone_mentions else None

    def _create_experiences(self, companies: List[str], jobs: List[str]) -> List[Dict]:
        """Create experience entries from companies and job titles"""
        experiences = []
        for i, company in enumerate(companies):
            job_title = jobs[i] if i < len(jobs) else "Position"
            experiences.append({
                "company": company,
                "job_title": job_title,
                "description": f"Worked as {job_title} at {company}"
            })
        return experiences

    def _create_educations(self, educations: List[str], text: str) -> List[Dict]:
        """Create education entries"""
        education_list = []
        for edu in educations:
            cleaned = (edu or "").strip()
            if len(cleaned) <= 2 or cleaned.startswith("##"):
                continue
            education_list.append({
                "institution": cleaned,
                "field_of_study": "Not specified",
                "degree": self._infer_degree(text, cleaned)
            })
        return education_list

    def _infer_degree(self, text: str, education: str) -> str:
        """Try to infer degree level from context"""
        context = text.lower()
        if any(word in context for word in ["bachelor", "licence", "bsc", "ba"]):
            return "Bachelor's Degree"
        elif any(word in context for word in ["master", "msc", "ma", "diploma"]):
            return "Master's Degree"
        elif any(word in context for word in ["phd", "doctorate", "dr."]):
            return "PhD"
        elif any(word in context for word in ["secondary", "high school", "baccalauréat"]):
            return "High School"
        return "Degree"

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            "name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experiences": [],
            "educations": [],
            "raw_entities": []
        }

    def _fallback_extract(self, text: str) -> Dict[str, Any]:
        """Fallback extraction for unknown CVs using regex and section heuristics."""
        cleaned = CVCleaner.clean_text(text)
        sections = CVCleaner.extract_sections(cleaned)

        result = {
            "name": self._extract_name(cleaned),
            "email": self._extract_email(cleaned, []),
            "phone": self._extract_phone(cleaned, []),
            "skills": self._extract_skills(cleaned),
            "experiences": self._extract_experiences(cleaned, sections),
            "educations": self._extract_educations(cleaned, sections),
            "raw_entities": []
        }
        return result

    def _extract_name(self, text: str) -> Optional[str]:
        """Try to infer the candidate name from the first meaningful lines."""
        lines = [line.strip(" •\t-") for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        candidate_line = lines[0]
        if len(candidate_line) > 80 and len(lines) > 1:
            candidate_line = lines[1]

        # Avoid returning contact headers or obvious metadata.
        if re.search(r"@(\w|\.)+", candidate_line, re.IGNORECASE):
            candidate_line = next((line for line in lines[1:4] if not re.search(r"@(\w|\.)+", line)), candidate_line)

        return candidate_line or None

    def _extract_skills(self, text: str) -> List[str]:
        """Extract a de-duplicated list of skills from text."""
        extracted = self.skill_extractor.extract_skills(text)
        skills = []
        seen = set()
        for item in extracted:
            name = item.get("name")
            if name and name.lower() not in seen:
                skills.append(name)
                seen.add(name.lower())

        # Add skills explicitly listed in skill sections if they were missed.
        for section_name in ("skills", "summary"):
            section_text = CVCleaner.extract_sections(text).get(section_name, "")
            for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", section_text):
                lowered = token.lower()
                if len(lowered) > 2 and lowered not in seen:
                    if lowered in {"python", "java", "react", "docker", "sql", "aws", "excel", "office", "figma", "linux"}:
                        skills.append(token)
                        seen.add(lowered)

        return skills

    def _extract_experiences(self, text: str, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """Heuristic extraction of experiences from structured or unstructured CV text."""
        experience_text = sections.get("experience", "") or text
        experiences: List[Dict[str, Any]] = []
        lines = [line.strip(" •\t-") for line in experience_text.splitlines() if line.strip()]

        date_pattern = re.compile(r"(?P<start>(?:19|20)\d{2})(?:\s*[-–/]\s*(?P<end>(?:19|20)\d{2}|present|current))?", re.IGNORECASE)
        for line in lines:
            if not date_pattern.search(line):
                continue

            parts = [part.strip() for part in re.split(r"\s*[|,;]\s*", line) if part.strip()]
            title = parts[0] if parts else "Position"
            company = parts[1] if len(parts) > 1 else "Company"
            duration_months = 12
            match = date_pattern.search(line)
            if match:
                start = int(match.group("start"))
                end_raw = match.group("end")
                if end_raw and end_raw.isdigit():
                    duration_months = max(12, (int(end_raw) - start) * 12)

            experiences.append({
                "job_title": title,
                "company": company,
                "duration_months": duration_months,
                "description": line,
            })

        return experiences[:5]

    def _extract_educations(self, text: str, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """Heuristic extraction of education entries from structured or unstructured CV text."""
        education_text = sections.get("education", "") or text
        educations: List[Dict[str, Any]] = []
        lines = [line.strip(" •\t-") for line in education_text.splitlines() if line.strip()]

        degree_keywords = ["master", "msc", "bachelor", "licence", "bts", "diploma", "phd", "doctorate", "engineer", "engineering", "bac", "college", "collège", "lycee", "lycée", "school", "university", "université"]

        for line in lines:
            lower = line.lower()
            year_match = re.search(r"((?:19|20)\d{2})", line)
            school_match = re.search(r"\b(coll[eè]ge|lyc[ée]e|school|university|universit[ée])\b", lower)
            if not any(keyword in lower for keyword in degree_keywords) and not (year_match and school_match):
                continue

            parts = [part.strip() for part in re.split(r"\s*[|,;]\s*", line) if part.strip()]
            degree = parts[0] if parts else "Degree"
            institution = parts[1] if len(parts) > 1 else "Institution"
            year = int(year_match.group(1)) if year_match else None

            if len(degree) <= 2 and len(institution) <= 2:
                continue

            educations.append({
                "degree": degree,
                "institution": institution,
                "field_of_study": "Not specified",
                "graduation_year": year,
            })

        return educations[:5]
