"""
Resume NER Extractor - Enhanced Edition
Robust pattern matching for real-world CV extraction
"""

import re
import logging
import unicodedata
from typing import Dict, List, Set, Any

logger = logging.getLogger(__name__)


class ResumeNERExtractor:
    """
    Extract resume entities using advanced pattern matching
    Designed for real CVs with complex formatting
    """
    
    # Comprehensive skill database (100+ tech skills)
    TECH_SKILLS = {
        # Languages
        "python", "java", "javascript", "typescript", "csharp", "c++", "php",
        "ruby", "go", "rust", "kotlin", "swift", "scala", "r", "matlab",
        "perl", "groovy", "c", "cpp", "objective-c", "lua", "shell",
        
        # Web Frontend
        "react", "vue", "angular", "nextjs", "gatsby", "svelte", "ember",
        "backbone", "html", "css", "sass", "less", "bootstrap", "tailwind",
        "webpack", "vite", "rollup", "gulp", "grunt",
        
        # Backend & Frameworks
        "fastapi", "django", "flask", "spring", "springboot", "rails", "laravel",
        "nodejs", "express", "koa", "hapi", "nestjs", "strapi", "graphql",
        
        # Databases
        "sql", "postgresql", "mysql", "mongodb", "redis", "cassandra", "dynamodb",
        "firebase", "elasticsearch", "oracle", "mariadb", "sqlite", "neo4j",
        
        # Cloud & DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "openshift", "terraform",
        "ansible", "jenkins", "gitlab", "github", "circleci", "travisci",
        "heroku", "vercel", "netlify", "cloudinary", "s3", "ec2", "rds",
        
        # Data & AI
        "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
        "keras", "sklearn", "pandas", "numpy", "scipy", "matplotlib", "seaborn",
        "jupyter", "spark", "hadoop", "hive", "pig", "airflow", "etl",
        "data science", "data analysis", "data engineering", "statistics",
        
        # Mobile
        "ios", "android", "swift", "kotlin", "react native", "flutter", "xamarin",
        
        # API & Protocols
        "rest", "restful", "graphql", "grpc", "soap", "websocket", "mqtt",
        "api", "http", "https", "json", "xml", "yaml",
        
        # Version Control
        "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
        
        # Other Tools
        "jira", "confluence", "slack", "discord", "figma", "sketch",
        "vim", "vscode", "intellij",
    }
    
    # Job title keywords
    JOB_KEYWORDS = {
        "senior", "lead", "principal", "architect", "manager", "director",
        "head of", "vp", "chief", "officer", "developer", "engineer",
        "programmer", "coder", "specialist", "analyst", "consultant",
        "full stack", "fullstack", "frontend", "backend", "mobile",
        "data scientist", "ml engineer", "devops", "commercial", "assistant",
        "responsable", "conseiller", "charge", "chargé", "ingenieur", "ingénieur",
        "developpeur", "développeur", "vendeur", "gestionnaire", "stagiaire",
    }
    
    # Company indicators
    COMPANY_SUFFIXES = {
        "inc", "incorporated", "ltd", "limited", "llc", "corp", "corporation",
        "company", "co", "gmbh", "ag", "sa", "bv", "pty", "pte",
    }
    
    # Education keywords
    EDUCATION_KEYWORDS = {
        "bachelor", "master", "phd", "doctorate", "computer science",
        "engineering", "degree", "diploma", "certificate",
        "university", "college", "school", "institute", "academy",
        "mba", "postgraduate", "bsc", "msc", "btech", "mtech",
        "licence", "bts", "dut", "universite", "université",
        "ecole", "école", "esup", "sorbonne",
    }

    EXPERIENCE_HEADERS = {
        "experience", "experiences", "experience professionnelle",
        "experiences professionnelles", "professional experience", "work experience",
        "expérience", "expériences", "stage", "stages",
    }

    EDUCATION_HEADERS = {
        "education", "formation", "formations", "etudes", "études",
        "academic background", "education and training",
    }

    STOP_HEADERS = {
        "skills", "competences", "compétences", "technical skills", "langues",
        "languages", "profil", "profile", "contact", "summary", "resume", "résumé",
        "centres d'interet", "centres d’intérêt", "interets", "intérêts",
        "projects", "projets", "certifications", "hobbies",
    }

    SOFT_SKILLS_HEADERS = {
        "competences", "compétences", "soft skills", "skills",
    }

    INTEREST_HEADERS = {
        "centres d interet", "centres d intérêt", "centres d'interet",
        "interets", "intérêts", "hobbies",
    }

    PROJECT_HEADERS = {
        "projects", "project", "projets", "projet", "realisations", "réalisations",
    }

    CERTIFICATION_HEADERS = {
        "certifications", "certification", "certificats", "certificat", "licenses", "licences",
    }

    PROFILE_HEADERS = {
        "profil", "profile", "summary", "professional summary",
    }

    LANGUAGE_NAMES = {
        "francais", "anglais", "espagnol", "allemand", "italien", "portugais",
        "arabe", "chinois", "japonais", "russe", "portuguese", "english",
        "french", "spanish", "german", "italian",
    }

    EXPERIENCE_DATE_PATTERN = re.compile(
        r"(?:(?:19|20)\d{2})\s*(?:-|–|—|/|to|a|à)\s*(?:(?:19|20)\d{2}|present|current|aujourd hui|aujourdhui|now)|(?:(?:19|20)\d{2})",
        flags=re.IGNORECASE,
    )
    
    def __init__(self):
        """Initialize extractor"""
        self.available = True
        self.model_name = "fallback-enhanced-regex"
        logger.info("✅ Enhanced NER Extractor initialized")
    
    def extract(self, text: str) -> Dict[str, List[str]]:
        """Extract all entities from text"""
        if not text or len(text.strip()) < 20:
            return self._empty_entities()
        
        grouped = self._empty_entities()
        text_lower = text.lower()
        
        # Extract all entity types
        grouped["email"] = self._extract_emails(text)
        grouped["phone"] = self._extract_phones(text)
        grouped["linkedin"] = self._extract_linkedin_urls(text)
        grouped["github"] = self._extract_github_urls(text)
        grouped["portfolio"] = self._extract_portfolio_urls(text)
        grouped["location"] = self._extract_locations(text)
        grouped["name"] = self._extract_names(text)
        grouped["job_title"] = self._extract_job_titles(text, text_lower)
        grouped["company"] = self._extract_companies(text)
        grouped["education"] = self._extract_education(text, text_lower)
        grouped["languages"] = self._extract_languages(text)
        grouped["soft_skills"] = self._extract_soft_skills(text)
        grouped["interests"] = self._extract_interests(text)
        grouped["certifications"] = self._extract_certifications(text)
        grouped["projects"] = self._extract_projects(text)
        grouped["profile_summary"] = self._extract_profile_summary(text)
        grouped["skills"] = self._extract_skills(text_lower)
        
        # Deduplicate and clean
        for key in grouped:
            grouped[key] = list(set(
                s.strip() for s in grouped[key] 
                if s and len(s.strip()) > 0
            ))
        
        return grouped
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        emails = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            text
        )
        return emails[:5]
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers - be strict"""
        patterns = [
            # International format: +33 6 12 34 56 78 (must be on single line)
            r'(\+\d{1,3}\s?[\d\s\-\(\)]{8,})(?:\n|$|[^\d\s\-\(\)])',
            # Common French local format: 06 12 34 56 78
            r'\b(0\d(?:[\s\.\-]?\d{2}){4})\b',
            # Compact local format: 0612345678
            r'\b(0\d{9})\b',
            # Alternative: +33612345678 (no spaces)
            r'(\+\d{10,})',
        ]
        phones = []
        for pattern in patterns:
            found = re.findall(pattern, text)
            for phone in found:
                # Extract just the phone part
                phone_clean = phone.strip()
                # Stop at first newline or special character
                phone_clean = re.sub(r'\n.*$', '', phone_clean, flags=re.DOTALL)
                phone_clean = re.sub(r'[^\d\s\-\(\)\+].*$', '', phone_clean)
                
                # Filter out date-like patterns (YYYY - YYYY)
                if not re.search(r'\d{4}\s*-\s*\d{4}', phone_clean) and len(phone_clean.strip()) >= 10:
                    phones.append(phone_clean.strip())

        if not phones:
            # Fallback for OCR text where separators are inconsistent or split across spaces.
            compact_text = re.sub(r"[^\d+]+", " ", text)
            fallback_patterns = [
                r"\+?\d{1,3}\s?\d{1,3}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}",
                r"\b0\d(?:\s?\d{2}){4}\b",
                r"\b\+?\d{10,14}\b",
            ]
            for pattern in fallback_patterns:
                for match in re.findall(pattern, compact_text):
                    cleaned = re.sub(r"\s+", " ", match).strip()
                    if len(re.sub(r"\D", "", cleaned)) >= 10:
                        phones.append(cleaned)
        
        return list(set(phones))[:3]  # Only unique phones
    
    def _extract_names(self, text: str) -> List[str]:
        """Extract person names - look at very beginning"""
        lines = text.strip().split('\n')
        candidates = []
        email_fallback = None

        emails = self._extract_emails(text)
        if emails:
            email_fallback = self._infer_name_from_email(emails[0])

        for index, raw_line in enumerate(lines[:80]):
            line = raw_line.strip().strip('•*-').strip()
            normalized = self._normalize_for_matching(line)

            if not line or '@' in line or 'http' in normalized or self._is_section_header(normalized):
                continue
            if any(token in normalized for token in ('linkedin', 'github', 'contact', 'profil', 'profile')):
                continue
            if any(char.isdigit() for char in line):
                continue

            words = [word for word in re.split(r'\s+', line) if word]
            if not 2 <= len(words) <= 3:
                continue

            alpha_words = sum(1 for word in words if re.search(r'[A-Za-zÀ-ÿ]', word))
            if alpha_words != len(words):
                continue

            score = 0
            if index < 15:
                score += 3
            if re.fullmatch(r"[A-ZÀ-Ÿ][A-ZÀ-Ÿ'’\-]+(?:\s+[A-ZÀ-Ÿ][A-ZÀ-Ÿ'’\-]+){1,2}", line):
                score += 5
            elif re.fullmatch(r"[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+(?:\s+[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+){1,2}", line):
                score += 4
            else:
                score += 2

            if any(keyword in normalized for keyword in ('experience', 'formation', 'education', 'profil', 'contact')):
                score -= 4

            candidates.append((score, line.title()))

            # Also evaluate segmented fragments when a line contains separators like pipes or dashes.
            for fragment in re.split(r"\s*[|/·•]\s*|\s+-\s+|\s+–\s+|\s+—\s+", line):
                fragment = fragment.strip()
                fragment_normalized = self._normalize_for_matching(fragment)
                if not fragment or fragment == line:
                    continue
                if '@' in fragment or 'http' in fragment_normalized or self._is_section_header(fragment_normalized):
                    continue
                if any(token in fragment_normalized for token in ('linkedin', 'github', 'contact', 'profil', 'profile')):
                    continue
                if any(char.isdigit() for char in fragment):
                    continue
                fragment_words = [word for word in re.split(r'\s+', fragment) if word]
                if not 2 <= len(fragment_words) <= 4:
                    continue
                if not all(re.search(r'[A-Za-zÀ-ÿ]', word) for word in fragment_words):
                    continue
                fragment_score = 2
                if index < 10:
                    fragment_score += 2
                if re.fullmatch(r"[A-ZÀ-Ÿ][A-ZÀ-Ÿ'’\-]+(?:\s+[A-ZÀ-Ÿ][A-ZÀ-Ÿ'’\-]+){1,3}", fragment):
                    fragment_score += 4
                elif re.fullmatch(r"[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+(?:\s+[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'’\-]+){1,3}", fragment):
                    fragment_score += 3
                candidates.append((fragment_score, fragment.title()))

        if not candidates:
            if email_fallback:
                return [email_fallback]
            return []

        candidates.sort(key=lambda item: (-item[0], len(item[1])))
        best_name = candidates[0][1]

        if len(best_name) < 3 and email_fallback:
            return [email_fallback]

        return [best_name]

    def _extract_linkedin_urls(self, text: str) -> List[str]:
        """Extract LinkedIn profile URLs."""
        urls = re.findall(r'((?:https?://)?(?:www\.)?linkedin\.com/[^\s,;]+)', text, flags=re.IGNORECASE)
        cleaned = []
        for url in urls:
            normalized = url.strip().rstrip(').,;')
            if not normalized.lower().startswith("http"):
                normalized = f"https://{normalized}"
            cleaned.append(normalized)
        return list(dict.fromkeys(cleaned))[:3]

    def _extract_github_urls(self, text: str) -> List[str]:
        """Extract GitHub profile/repository URLs."""
        urls = re.findall(r'((?:https?://)?(?:www\.)?github\.com/[^\s,;]+)', text, flags=re.IGNORECASE)
        cleaned = []
        for url in urls:
            normalized = url.strip().rstrip(').,;')
            if not normalized.lower().startswith("http"):
                normalized = f"https://{normalized}"
            cleaned.append(normalized)
        return list(dict.fromkeys(cleaned))[:5]

    def _extract_portfolio_urls(self, text: str) -> List[str]:
        """Extract non-social portfolio websites."""
        urls = re.findall(r'((?:https?://)?(?:www\.)?[a-z0-9][a-z0-9\-\.]+\.[a-z]{2,}(?:/[^\s,;]*)?)', text, flags=re.IGNORECASE)
        blocked_domains = ("linkedin.com", "github.com", "facebook.com", "instagram.com", "twitter.com", "x.com")
        cleaned = []
        for url in urls:
            normalized = url.strip().rstrip(').,;')
            lower = normalized.lower()
            if any(domain in lower for domain in blocked_domains):
                continue
            if "@" in normalized:
                continue
            if not normalized.lower().startswith("http"):
                normalized = f"https://{normalized}"
            cleaned.append(normalized)
        return list(dict.fromkeys(cleaned))[:5]

    def _extract_locations(self, text: str) -> List[str]:
        """Extract likely city/country mentions from contact block."""
        locations = []
        for line in text.split('\n')[:30]:
            cleaned = line.strip()
            if not cleaned:
                continue
            if '@' in cleaned or 'linkedin.com' in cleaned.lower() or re.search(r'\d{2}\s?\d{2}', cleaned):
                continue
            for match in re.findall(r'\b([A-ZÀ-Ÿ][A-Za-zÀ-ÿ\-]+\s*,\s*[A-ZÀ-Ÿ][A-Za-zÀ-ÿ\-]+)\b', cleaned):
                locations.append(match.strip())
        return list(dict.fromkeys(locations))[:3]
    
    def _extract_job_titles(self, text: str, text_lower: str) -> List[str]:
        """Extract job titles - be specific"""
        job_titles = set()

        lines = text.split('\n')
        in_experience_section = False

        for index, raw_line in enumerate(lines):
            line = raw_line.strip().strip('•*-').strip()
            normalized = self._normalize_for_matching(line)

            if not line:
                continue

            if self._is_experience_header(normalized):
                in_experience_section = True
                continue

            if in_experience_section and self._is_section_header(normalized) and not self._is_experience_header(normalized):
                in_experience_section = False
                continue

            if not in_experience_section:
                continue

            if self._looks_like_company_line(line):
                for next_line in lines[index + 1:index + 4]:
                    next_clean = next_line.strip().strip('•*-').strip()
                    next_normalized = self._normalize_for_matching(next_clean)
                    if not next_clean:
                        continue
                    if self._is_section_header(next_normalized) or self._looks_like_company_line(next_clean):
                        break
                    if self._looks_like_job_title(next_clean):
                        job_titles.add(next_clean)
                continue

            if index + 1 < len(lines):
                next_clean = lines[index + 1].strip().strip('•*-').strip()
                if next_clean and self._looks_like_company_line(next_clean) and self._looks_like_job_title(line):
                    job_titles.add(line)

        # Fallback: detect title/company pairs globally when OCR breaks section boundaries.
        for index, raw_line in enumerate(lines):
            line = raw_line.strip().strip('•*-').strip()
            if not line:
                continue
            if self._looks_like_job_title(line) and index + 1 < len(lines):
                next_clean = lines[index + 1].strip().strip('•*-').strip()
                if next_clean and self._looks_like_company_line(next_clean):
                    job_titles.add(line)
        
        return list(job_titles)[:5]
    
    def _extract_companies(self, text: str) -> List[str]:
        """Extract company names"""
        companies = set()
        
        # Known tech companies
        known_companies = {
            "google", "microsoft", "apple", "amazon", "facebook", "meta",
            "netflix", "spotify", "uber", "airbnb", "tesla", "twitter",
            "linkedin", "ibm", "oracle", "salesforce", "adobe", "nvidia",
        }
        
        text_lower = text.lower()

        in_experience_section = False

        for raw_line in text.split('\n'):
            line = raw_line.strip()
            normalized = self._normalize_for_matching(line)

            if not line:
                continue

            if self._is_experience_header(normalized):
                in_experience_section = True
                continue

            if in_experience_section and self._is_section_header(normalized) and not self._is_experience_header(normalized):
                in_experience_section = False
                continue

            if in_experience_section and self._looks_like_company_line(line):
                company = self._extract_company_from_line(line)
                if company:
                    companies.add(company)

        # Fallback: extract company lines globally when section headers are merged.
        for raw_line in text.split('\n'):
            line = raw_line.strip()
            if self._looks_like_company_line(line):
                company = self._extract_company_from_line(line)
                if company:
                    companies.add(company)

        for company in known_companies:
            if company in text_lower and company not in {'linkedin', 'github'}:
                companies.add(company.title())
        
        return list(companies)[:5]
    
    def _extract_education(self, text: str, text_lower: str) -> List[str]:
        """Extract education"""
        education = set()

        lines = text.split('\n')
        in_education_section = False

        for raw_line in lines:
            line = raw_line.strip().strip('•*-').strip()
            normalized = self._normalize_for_matching(line)

            if not line:
                continue

            if self._is_education_header(normalized):
                in_education_section = True
                continue

            if in_education_section and self._is_stop_header(normalized):
                in_education_section = False
                continue

            if not in_education_section:
                continue

            if len(line) < 5 or len(line) > 200:
                continue

            if self._looks_like_education_line(line):
                education.add(line)

        for keyword in self.EDUCATION_KEYWORDS:
            if keyword in text_lower:
                for raw_line in lines:
                    cleaned = raw_line.strip().strip('•*-').strip()
                    normalized = self._normalize_for_matching(cleaned)
                    if keyword in normalized and self._looks_like_education_line(cleaned):
                        education.add(cleaned)
        
        return list(education)[:10]
    
    def _extract_skills(self, text_lower: str) -> List[str]:
        """Extract technical skills"""
        skills = set()

        tokens = set(re.findall(r"[a-zA-Z0-9\+\#\-\.]+", text_lower))

        for skill in self.TECH_SKILLS:
            if " " in skill:
                if re.search(rf"\b{re.escape(skill)}\b", text_lower):
                    skills.add(skill.title())
            else:
                if skill in tokens:
                    skills.add(skill.title())

        if not skills:
            lines = text_lower.split('\n')
            in_section = False
            for raw_line in lines:
                line = raw_line.strip().strip('•*- ').strip()
                normalized = self._normalize_for_matching(line)
                if not line:
                    continue

                if self._line_matches_any_header(normalized, self.SOFT_SKILLS_HEADERS):
                    in_section = True
                    continue

                if in_section and self._is_section_header(normalized) and not self._line_matches_any_header(normalized, self.SOFT_SKILLS_HEADERS):
                    in_section = False
                    continue

                if not in_section:
                    continue

                candidates = [candidate.strip() for candidate in re.split(r"[,;/•|]", line) if candidate.strip()]
                for candidate in candidates:
                    candidate_normalized = self._normalize_for_matching(candidate)
                    if not candidate or len(candidate) < 2 or len(candidate) > 60:
                        continue
                    if candidate_normalized in self.LANGUAGE_NAMES:
                        continue
                    if '@' in candidate or 'http' in candidate_normalized:
                        continue
                    if re.search(r'\b(19|20)\d{2}\b', candidate):
                        continue
                    if self._looks_like_company_line(candidate):
                        continue
                    skills.add(candidate.title())

            if not skills:
                soft_skill_vocabulary = {
                    "sens du contact", "communication", "capacite d adaptation", "capacité d adaptation",
                    "polyvalence", "logique", "rigueur", "autonomie", "leadership", "organisation",
                    "gestion de projet", "travail en équipe", "travail en equipe", "esprit d équipe",
                    "esprit d equipe", "collaboration", "créativité", "creativite", "analyse", "adaptabilité",
                }
                for candidate in re.split(r"[\n,;/•|]+", text_lower):
                    cleaned = candidate.strip()
                    normalized = self._normalize_for_matching(cleaned)
                    if normalized in soft_skill_vocabulary:
                        skills.add(cleaned.title())
        
        return list(skills)[:50]

    def _extract_languages(self, text: str) -> List[str]:
        """Extract spoken languages, especially from LANGUES/LANGUAGES section."""
        languages = set()
        lines = text.split('\n')
        in_language_section = False

        for raw_line in lines:
            line = raw_line.strip().strip('•*-').strip()
            normalized = self._normalize_for_matching(line)
            if not line:
                continue

            if self._line_matches_any_header(normalized, {"langues", "languages", "langue"}):
                in_language_section = True
                continue

            if in_language_section and self._is_section_header(normalized) and not self._line_matches_any_header(normalized, {"langues", "languages", "langue"}):
                in_language_section = False
                continue

            if in_language_section:
                tokens = re.split(r'[,;\s]+', normalized)
                for token in tokens:
                    if token in self.LANGUAGE_NAMES:
                        languages.add(token.capitalize())

        for token in re.findall(r'\b[A-Za-zÀ-ÿ]+\b', self._normalize_for_matching(text)):
            if token in self.LANGUAGE_NAMES:
                languages.add(token.capitalize())

        return list(languages)[:8]

    def _extract_soft_skills(self, text: str) -> List[str]:
        """Extract bullet-point soft skills from COMPÉTENCES section."""
        skills = []
        lines = text.split('\n')
        in_section = False

        for raw_line in lines:
            line = raw_line.strip()
            normalized = self._normalize_for_matching(line)
            if not line:
                continue

            if self._line_matches_any_header(normalized, self.SOFT_SKILLS_HEADERS):
                in_section = True
                continue

            if in_section and self._is_section_header(normalized) and not self._line_matches_any_header(normalized, self.SOFT_SKILLS_HEADERS):
                in_section = False
                continue

            if not in_section:
                continue

            candidate = line.strip('•*- ').strip()
            candidate_normalized = self._normalize_for_matching(candidate)
            if not candidate or len(candidate) < 2 or len(candidate) > 60:
                continue
            if candidate_normalized in self.LANGUAGE_NAMES:
                continue
            if '@' in candidate or 'http' in candidate_normalized:
                continue
            if candidate.endswith('.'):
                continue
            skills.append(candidate)

        if not skills:
            soft_skill_vocabulary = {
                "sens du contact", "communication", "capacite d adaptation", "capacité d adaptation",
                "polyvalence", "logique", "rigueur", "autonomie", "leadership", "organisation",
            }
            for raw_line in lines:
                candidate = raw_line.strip().strip('•*- ').strip()
                normalized = self._normalize_for_matching(candidate)
                if normalized in soft_skill_vocabulary:
                    skills.append(candidate)

        return list(dict.fromkeys(skills))[:20]

    def _extract_interests(self, text: str) -> List[str]:
        """Extract interests/hobbies from dedicated section."""
        interests = []
        lines = text.split('\n')
        in_section = False

        for raw_line in lines:
            line = raw_line.strip()
            normalized = self._normalize_for_matching(line)
            if not line:
                continue

            if self._line_matches_any_header(normalized, self.INTEREST_HEADERS):
                in_section = True
                continue

            if in_section and self._is_section_header(normalized) and not self._line_matches_any_header(normalized, self.INTEREST_HEADERS):
                in_section = False
                continue

            if not in_section:
                continue

            candidate = line.strip('•*- ').strip()
            if not candidate or len(candidate) < 2 or len(candidate) > 80:
                continue
            if '@' in candidate or 'http' in candidate.lower():
                continue
            normalized_candidate = self._normalize_for_matching(candidate)
            if re.search(r'\b(19|20)\d{2}\b', candidate):
                continue
            if any(keyword in normalized_candidate for keyword in self.EDUCATION_KEYWORDS):
                continue
            if self._looks_like_company_line(candidate):
                continue
            interests.append(candidate)

        return list(dict.fromkeys(interests))[:20]

    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications from dedicated sections and inline lines."""
        certifications = []
        lines = text.split('\n')
        in_section = False

        for raw_line in lines:
            line = raw_line.strip()
            normalized = self._normalize_for_matching(line)
            if not line:
                continue

            if self._line_matches_any_header(normalized, self.CERTIFICATION_HEADERS):
                in_section = True
                continue

            if in_section and self._is_section_header(normalized):
                in_section = False
                continue

            candidate = line.strip('•*- ').strip()
            if len(candidate) < 3 or len(candidate) > 140:
                continue

            if in_section:
                certifications.append(candidate)
                continue

            if any(token in normalized for token in ("certification", "certificat", "aws certified", "scrum", "pmp", "itil", "toeic", "toefl")):
                certifications.append(candidate)

        return list(dict.fromkeys(certifications))[:20]

    def _extract_projects(self, text: str) -> List[str]:
        """Extract projects from dedicated sections and project-like bullet lines."""
        projects = []
        lines = text.split('\n')
        in_section = False

        for raw_line in lines:
            line = raw_line.strip()
            normalized = self._normalize_for_matching(line)
            if not line:
                continue

            if self._line_matches_any_header(normalized, self.PROJECT_HEADERS):
                in_section = True
                continue

            if in_section and self._is_section_header(normalized):
                in_section = False
                continue

            candidate = line.strip('•*- ').strip()
            if len(candidate) < 4 or len(candidate) > 160:
                continue
            if '@' in candidate or 'http' in normalized:
                continue

            if in_section:
                projects.append(candidate)
                continue

            if any(token in normalized for token in ("project", "projet", "developed", "implemented", "built", "realise", "réalisé")):
                if not self._looks_like_company_line(candidate):
                    projects.append(candidate)

        return list(dict.fromkeys(projects))[:20]

    def _extract_profile_summary(self, text: str) -> List[str]:
        """Extract summary paragraph from PROFIL/PROFILE section."""
        lines = text.split('\n')
        in_section = False
        collected = []

        for raw_line in lines:
            line = raw_line.strip()
            normalized = self._normalize_for_matching(line)
            if not line:
                continue

            if self._line_matches_any_header(normalized, self.PROFILE_HEADERS):
                in_section = True
                continue

            if in_section and self._is_section_header(normalized) and normalized not in self.PROFILE_HEADERS:
                break

            if in_section:
                candidate = line.strip('•*- ').strip()
                if len(candidate) < 10:
                    continue
                if '@' in candidate or 'linkedin.com' in candidate.lower():
                    continue
                collected.append(candidate)
                if len(" ".join(collected)) > 350:
                    break

        if not collected:
            # OCR fallback: summary can appear before the PROFIL header.
            lines_count = len(lines)
            for i, raw_line in enumerate(lines):
                seed = raw_line.strip().strip('•*- ').strip()
                seed_normalized = self._normalize_for_matching(seed)
                if len(seed) < 20:
                    continue
                if any(token in seed_normalized for token in ("contact", "linkedin", "langues", "competences", "experiences", "formation")):
                    continue
                if not any(keyword in seed_normalized for keyword in ("diplome", "diplômé", "experience", "passion", "relationnel")):
                    continue

                chunk = [seed]
                for j in range(i + 1, min(i + 5, lines_count)):
                    follow = lines[j].strip().strip('•*- ').strip()
                    follow_normalized = self._normalize_for_matching(follow)
                    if not follow or len(follow) < 8:
                        continue
                    if self._is_section_header(follow_normalized):
                        break
                    if any(token in follow_normalized for token in ("contact", "linkedin", "langues", "competences", "experiences", "formation")):
                        break
                    if '@' in follow or re.search(r'\b0\d(?:[\s\.\-]?\d{2}){4}\b', follow):
                        break
                    chunk.append(follow)

                joined_chunk = " ".join(chunk).strip()
                if len(joined_chunk) >= 40:
                    return [joined_chunk]

            # Fallback: pick a substantial sentence likely from the profile paragraph.
            for raw_line in lines:
                candidate = raw_line.strip().strip('•*- ').strip()
                normalized = self._normalize_for_matching(candidate)
                if len(candidate) < 40:
                    continue
                if '@' in candidate or 'linkedin.com' in normalized:
                    continue
                if any(header in normalized for header in ("experience", "formation", "langues", "competences", "centres")):
                    continue
                if any(keyword in normalized for keyword in ("experience", "diplome", "diplômé", "passion", "relationnel")):
                    return [candidate]
            for sentence in re.split(r'[\n\.]+', text):
                candidate = sentence.strip().strip('•*- ').strip()
                normalized = self._normalize_for_matching(candidate)
                if len(candidate) < 40:
                    continue
                if '@' in candidate or 'linkedin.com' in normalized:
                    continue
                if re.search(r'\b0\d(?:[\s\.\-]?\d{2}){4}\b', candidate):
                    continue
                if any(keyword in normalized for keyword in ("je suis", "experience", "diplome", "diplômé", "relationnel")):
                    return [candidate]
            return []

        joined = " ".join(collected)
        if re.search(r'\b0\d(?:[\s\.\-]?\d{2}){4}\b', joined):
            filtered = []
            for part in collected:
                normalized = self._normalize_for_matching(part)
                if '@' in part or 'linkedin.com' in normalized:
                    continue
                if re.search(r'\b0\d(?:[\s\.\-]?\d{2}){4}\b', part):
                    continue
                if len(part) < 20:
                    continue
                filtered.append(part)
            joined = " ".join(filtered)

        if not joined:
            lines_count = len(lines)
            for i, raw_line in enumerate(lines):
                seed = raw_line.strip().strip('•*- ').strip()
                seed_normalized = self._normalize_for_matching(seed)
                if len(seed) < 20:
                    continue
                if any(token in seed_normalized for token in ("contact", "linkedin", "langues", "competences", "experiences", "formation")):
                    continue
                if not any(keyword in seed_normalized for keyword in ("diplome", "diplômé", "experience", "passion", "relationnel")):
                    continue

                chunk = [seed]
                for j in range(i + 1, min(i + 5, lines_count)):
                    follow = lines[j].strip().strip('•*- ').strip()
                    follow_normalized = self._normalize_for_matching(follow)
                    if not follow or len(follow) < 8:
                        continue
                    if self._is_section_header(follow_normalized):
                        break
                    if any(token in follow_normalized for token in ("contact", "linkedin", "langues", "competences", "experiences", "formation")):
                        break
                    if '@' in follow or re.search(r'\b0\d(?:[\s\.\-]?\d{2}){4}\b', follow):
                        break
                    chunk.append(follow)

                joined_chunk = " ".join(chunk).strip()
                if len(joined_chunk) >= 40:
                    joined = joined_chunk
                    break

        return [joined] if joined else []
    
    def _empty_entities(self) -> Dict[str, List[str]]:
        """Return empty structure"""
        return {
            "name": [],
            "email": [],
            "phone": [],
            "linkedin": [],
            "github": [],
            "portfolio": [],
            "location": [],
            "skills": [],
            "languages": [],
            "soft_skills": [],
            "interests": [],
            "certifications": [],
            "projects": [],
            "profile_summary": [],
            "company": [],
            "job_title": [],
            "education": []
        }

    def _infer_name_from_email(self, email: str | None) -> str | None:
        """Infer a human-readable name from an email local part."""
        if not email or "@" not in email:
            return None

        local_part = email.split("@", 1)[0].strip()
        if not local_part:
            return None

        pieces = [piece for piece in re.split(r"[._\-+]+", local_part) if piece]
        if len(pieces) < 2:
            return None

        candidate = " ".join(piece.capitalize() for piece in pieces[:3]).strip()
        if len(candidate) < 4:
            return None

        return candidate

    def _normalize_for_matching(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(char for char in value if not unicodedata.combining(char))
        value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip().lower()

    def _is_experience_header(self, normalized_line: str) -> bool:
        normalized_line = normalized_line.rstrip(':')
        return normalized_line in {self._normalize_for_matching(header) for header in self.EXPERIENCE_HEADERS}

    def _is_education_header(self, normalized_line: str) -> bool:
        normalized_line = normalized_line.rstrip(':')
        return normalized_line in {self._normalize_for_matching(header) for header in self.EDUCATION_HEADERS}

    def _is_stop_header(self, normalized_line: str) -> bool:
        normalized_line = normalized_line.rstrip(':')
        return normalized_line in {self._normalize_for_matching(header) for header in self.STOP_HEADERS}

    def _is_section_header(self, normalized_line: str) -> bool:
        normalized_line = normalized_line.rstrip(':')
        return (
            self._is_experience_header(normalized_line)
            or self._is_education_header(normalized_line)
            or self._is_stop_header(normalized_line)
        )

    def _line_matches_any_header(self, normalized_line: str, headers: Set[str]) -> bool:
        """Return True when a normalized OCR line contains any normalized header phrase."""
        normalized_headers = {self._normalize_for_matching(header) for header in headers}
        parts = [part.strip() for part in normalized_line.split(' ') if part.strip()]
        compact_line = " ".join(parts)
        for header in normalized_headers:
            if not header:
                continue
            header_parts = [part for part in header.split(' ') if part]
            if len(header_parts) == 1:
                if compact_line == header:
                    return True
                continue
            if compact_line == header or compact_line.startswith(f"{header} "):
                return True
        return False

    def _looks_like_company_line(self, line: str) -> bool:
        normalized = self._normalize_for_matching(line)
        if 'linkedin.com' in normalized or 'github.com' in normalized:
            return False
        if any(keyword in normalized for keyword in ('contact', 'profil', 'profile', 'skills', 'competences', 'compétences')):
            return False
        return bool(
            re.search(r"\b\d{4}\b", line)
            or '|' in line
            or re.search(r"\s[-–]\s", line)
        )

    def _extract_company_from_line(self, line: str) -> str:
        candidate = line.split('|', 1)[0].strip()
        candidate = re.split(r"\s*\(\s*\d{4}.*$", candidate)[0].strip()
        candidate = re.split(r"\s*[-–]\s*[A-ZÀ-Ÿ][A-Za-zÀ-ÿ\s&'’.-]{1,40}$", candidate)[0].strip()
        candidate = candidate.split(',', 1)[0].strip()
        candidate = candidate.strip('•*-').strip()

        normalized = self._normalize_for_matching(candidate)
        if len(candidate) < 2 or 'linkedin' in normalized or 'github' in normalized:
            return ''
        if any(keyword in normalized for keyword in ('contact', 'profil', 'profile', 'skills', 'competences', 'compétences')):
            return ''
        if any(keyword in normalized for keyword in ('universite', 'université', 'university', 'ecole', 'école', 'school', 'college', 'institute', 'esup')):
            return ''
        return candidate

    def _looks_like_job_title(self, line: str) -> bool:
        normalized = self._normalize_for_matching(line)
        if self._is_section_header(normalized):
            return False
        if self._looks_like_company_line(line):
            return False
        if any(token in normalized for token in ('linkedin', 'github', 'http', 'www', 'profil', 'profile')):
            return False
        if any(keyword in normalized for keyword in self.EDUCATION_KEYWORDS):
            return False
        if normalized in self.LANGUAGE_NAMES:
            return False
        if line.endswith('.') or line.endswith(':'):
            return False
        if any(token in normalized for token in ('bénévolat', 'randonnée', 'voyage', 'théâtre', 'concerts', 'loisirs', 'interets', 'intérêts')):
            return False

        words = [word for word in re.split(r'\s+', line.strip()) if word]
        if not 1 <= len(words) <= 6:
            return False

        if any(keyword in normalized for keyword in self.JOB_KEYWORDS):
            return True

        if len(words) == 1:
            return len(words[0]) >= 7 and words[0].isalpha()

        if all(re.search(r'[A-Za-zÀ-ÿ]', word) for word in words):
            return True

        return False

    def _looks_like_education_line(self, line: str) -> bool:
        normalized = self._normalize_for_matching(line)
        if self._is_section_header(normalized):
            return False
        if any(token in normalized for token in ('linkedin', 'github', 'http', 'www')):
            return False
        if any(token in normalized for token in ('bénévolat', 'randonnée', 'voyage', 'théâtre', 'concerts')):
            return False

        has_education_keyword = any(keyword in normalized for keyword in self.EDUCATION_KEYWORDS)

        if self._looks_like_company_line(line) and not has_education_keyword:
            return False

        if re.search(r'\b(19|20)\d{2}\b', line):
            return True

        if has_education_keyword:
            return True

        return False

    def _extract_period(self, line: str) -> str:
        """Extract date range/year from a line."""
        match = self.EXPERIENCE_DATE_PATTERN.search(line)
        if not match:
            return ""
        period = re.sub(r"\s+", " ", match.group(0)).strip()
        period = period.replace("aujourd hui", "Present").replace("aujourdhui", "Present")
        return period

    def _strip_period(self, line: str) -> str:
        """Remove date range/year from a line to keep role/company content."""
        return self.EXPERIENCE_DATE_PATTERN.sub("", line, count=1).strip(" |-–—,;()")

    def _is_likely_experience_anchor(self, line: str) -> bool:
        """Detect lines that likely start a new experience entry."""
        if not line or len(line) < 3:
            return False

        normalized = self._normalize_for_matching(line)
        if self._is_section_header(normalized):
            return False
        if any(token in normalized for token in ("education", "formation", "universite", "university", "ecole", "school")):
            return False

        has_period = bool(self.EXPERIENCE_DATE_PATTERN.search(line))
        has_separator = any(sep in line for sep in ("|", " - ", " – ", " — "))
        looks_title = self._looks_like_job_title(line)
        looks_company = self._looks_like_company_line(line)

        return has_period or (has_separator and (looks_title or looks_company))

    def _parse_anchor_line(self, line: str, prev_line: str = "", next_line: str = "") -> Dict[str, Any]:
        """Parse a potential anchor line into title/company/period."""
        period = self._extract_period(line)
        core = self._strip_period(line)
        if not core:
            core = line.strip()

        segments = [part.strip(" |-–—,;") for part in re.split(r"\||\s+-\s+|\s+–\s+|\s+—\s+", core) if part.strip()]

        title = ""
        company = ""
        for segment in segments:
            if not title and self._looks_like_job_title(segment):
                title = segment
                continue
            if not company and self._looks_like_company_line(segment):
                parsed = self._extract_company_from_line(segment)
                company = parsed or segment

        if not company:
            company = self._extract_company_from_line(line)

        if not title and prev_line and self._looks_like_job_title(prev_line):
            title = prev_line
        if not title and next_line and self._looks_like_job_title(next_line):
            title = next_line

        if not company and next_line and self._looks_like_company_line(next_line):
            company = self._extract_company_from_line(next_line)

        if not company and not title:
            return {}

        if company and any(keyword in self._normalize_for_matching(company) for keyword in self.EDUCATION_KEYWORDS):
            return {}

        return {
            "title": title,
            "company": company,
            "period": period or None,
            "responsibilities": [],
        }

    def _extract_experiences(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured professional experiences from varied CV formats."""
        original_lines = text.split('\n')
        cleaned_lines = [line.strip().strip('•*- ').strip() for line in original_lines]

        start_idx = 0
        for idx, line in enumerate(cleaned_lines):
            normalized = self._normalize_for_matching(line)
            if self._line_matches_any_header(normalized, self.EXPERIENCE_HEADERS):
                start_idx = idx + 1
                break

        experiences: List[Dict[str, Any]] = []
        current_exp: Dict[str, Any] = {}

        def flush_current() -> None:
            nonlocal current_exp
            if not current_exp:
                return
            if current_exp.get("company") or current_exp.get("title"):
                current_exp["responsibilities"] = list(dict.fromkeys(current_exp.get("responsibilities", [])))[:10]
                experiences.append(current_exp)
            current_exp = {}

        for idx in range(start_idx, len(cleaned_lines)):
            line = cleaned_lines[idx]
            raw_line = original_lines[idx].strip()
            if not line:
                continue

            normalized = self._normalize_for_matching(line)

            if self._is_section_header(normalized) and not self._line_matches_any_header(normalized, self.EXPERIENCE_HEADERS):
                if experiences and any(token in normalized for token in ("education", "formation", "skills", "competences", "langues", "languages")):
                    break
                continue

            prev_line = cleaned_lines[idx - 1] if idx > 0 else ""
            next_line = cleaned_lines[idx + 1] if idx + 1 < len(cleaned_lines) else ""

            if self._is_likely_experience_anchor(line):
                parsed = self._parse_anchor_line(line, prev_line=prev_line, next_line=next_line)
                if parsed:
                    flush_current()
                    current_exp = parsed
                    continue

            if not current_exp and self._looks_like_job_title(line):
                candidate = {
                    "title": line,
                    "company": "",
                    "period": None,
                    "responsibilities": [],
                }
                if next_line and self._looks_like_company_line(next_line):
                    candidate["company"] = self._extract_company_from_line(next_line)
                if candidate["company"]:
                    current_exp = candidate
                    continue

            if current_exp:
                if normalized in self.LANGUAGE_NAMES:
                    continue
                if '@' in line or 'linkedin.com' in normalized:
                    continue
                if self._looks_like_education_line(line):
                    continue

                if not current_exp.get("title") and self._looks_like_job_title(line):
                    current_exp["title"] = line
                    continue
                if not current_exp.get("company") and self._looks_like_company_line(line):
                    current_exp["company"] = self._extract_company_from_line(line)
                    continue
                if not current_exp.get("period"):
                    period = self._extract_period(line)
                    if period:
                        current_exp["period"] = period

                looks_like_description = (
                    raw_line.startswith("•")
                    or raw_line.startswith("-")
                    or raw_line.startswith("*")
                    or len(line) > 30
                )
                if looks_like_description and not self._is_likely_experience_anchor(line):
                    responsibilities = current_exp.get("responsibilities", [])
                    if responsibilities and not raw_line.startswith(("•", "-", "*")) and not responsibilities[-1].endswith('.'):
                        responsibilities[-1] = f"{responsibilities[-1]} {line}".strip()
                    else:
                        responsibilities.append(line)
                    current_exp["responsibilities"] = responsibilities

        flush_current()

        normalized_seen = set()
        deduped_experiences = []
        for exp in experiences:
            key = (
                self._normalize_for_matching(exp.get("title") or ""),
                self._normalize_for_matching(exp.get("company") or ""),
                (exp.get("period") or "").lower(),
            )
            if key in normalized_seen:
                continue
            normalized_seen.add(key)
            if not exp.get("company") and not exp.get("title"):
                continue
            deduped_experiences.append({
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "period": exp.get("period"),
                "responsibilities": exp.get("responsibilities", [])[:10],
            })

        return deduped_experiences[:12]
    
    def extract_structured_profile(self, text: str) -> Dict:
        """Extract and format for API response"""
        entities = self.extract(text)
        experiences = self._extract_experiences(text)
        
        return {
            "full_name": entities["name"][0] if entities["name"] else None,
            "email": entities["email"][0] if entities["email"] else None,
            "phone": entities["phone"][0] if entities["phone"] else None,
            "linkedin_url": entities["linkedin"][0] if entities["linkedin"] else None,
            "linkedin_urls": entities["linkedin"][:3],
            "github_urls": entities["github"][:5],
            "portfolio_urls": entities["portfolio"][:5],
            "locations": entities["location"][:5],
            "education": entities["education"][:5],
            "skills": list(set(entities["skills"])),
            "languages": entities["languages"][:8],
            "soft_skills": entities["soft_skills"][:20],
            "interests": entities["interests"][:20],
            "certifications": entities["certifications"][:20],
            "projects": entities["projects"][:20],
            "profile_summary": entities["profile_summary"][0] if entities["profile_summary"] else None,
            "companies": entities["company"][:5],
            "job_titles": entities["job_title"][:5],
            "experiences": experiences,
            "extraction_metadata": {
                "model": self.model_name,
                "model_available": self.available,
                "total_entities": sum(len(v) for v in entities.values())
            }
        }
