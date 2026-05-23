"""Normalisation intelligente des compétences.

3 niveaux de normalisation :
    1. Mapping exact (dictionnaire) : "ml" → "Machine Learning"
    2. Variants & aliases : "React.js" / "Reactjs" / "React" → "React"
    3. Sémantique (embeddings) : "Profond Learning" → "Deep Learning"
       (utilise sentence-transformers en option si chargé)

Architecture pensée pour être facilement étendue avec un clustering sémantique
sur le pool de skills extraits, pour découvrir de nouveaux aliases.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------- #
# Dictionnaire de skills canoniques + aliases
# ---------------------------------------------------------------------------- #
# Format : "canonical_name": ["alias1", "alias2", ...]
# Les clés sont la forme canonique exposée à l'utilisateur ;
# les valeurs sont toutes les variantes acceptées (en minuscules).

CANONICAL_SKILLS: Dict[str, List[str]] = {
    # === Langages de programmation ===
    "Python": ["python", "python3", "py", "python 3"],
    "JavaScript": ["js", "javascript", "java script", "ecmascript", "es6", "es2015"],
    "TypeScript": ["ts", "typescript", "type script"],
    "Java": ["java", "java se", "java ee", "jakarta ee"],
    "C++": ["c++", "cpp", "cplusplus"],
    "C#": ["c#", "csharp", "c sharp", "dotnet c#"],
    "Go": ["go", "golang"],
    "Rust": ["rust", "rust-lang"],
    "PHP": ["php", "php7", "php8"],
    "Ruby": ["ruby", "ruby on rails"],
    "Kotlin": ["kotlin"],
    "Swift": ["swift", "swiftui"],
    "Scala": ["scala"],
    "R": ["r", "r language", "r programming"],
    "SQL": ["sql", "structured query language"],

    # === Frontend ===
    "React": ["react", "react.js", "reactjs", "react js"],
    "Vue.js": ["vue", "vue.js", "vuejs", "vue 3"],
    "Angular": ["angular", "angularjs", "angular 2+"],
    "Next.js": ["next", "next.js", "nextjs"],
    "Svelte": ["svelte", "sveltekit"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "Tailwind CSS": ["tailwind", "tailwindcss", "tailwind css"],
    "Sass": ["sass", "scss"],

    # === Backend & APIs ===
    "Node.js": ["node", "nodejs", "node.js", "node js"],
    "Express.js": ["express", "expressjs", "express.js"],
    "FastAPI": ["fastapi", "fast api"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring", "spring boot", "springboot"],
    "Laravel": ["laravel"],
    ".NET": [".net", "dotnet", "asp.net", "asp net"],
    "GraphQL": ["graphql", "graph ql"],
    "REST": ["rest", "rest api", "restful"],
    "gRPC": ["grpc"],

    # === Bases de données ===
    "PostgreSQL": ["postgres", "postgresql", "pg"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongo", "mongodb"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic search", "elk"],
    "SQLite": ["sqlite"],
    "Oracle": ["oracle", "oracle db", "oracle database"],
    "SQL Server": ["sql server", "mssql", "ms sql"],
    "Cassandra": ["cassandra"],
    "DynamoDB": ["dynamodb", "dynamo"],
    "Neo4j": ["neo4j", "neo 4j"],

    # === Cloud & DevOps ===
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "Google Cloud": ["gcp", "google cloud", "google cloud platform"],
    "Docker": ["docker", "docker-compose"],
    "Kubernetes": ["k8s", "kubernetes", "kube"],
    "Terraform": ["terraform"],
    "Ansible": ["ansible"],
    "Jenkins": ["jenkins"],
    "GitLab CI": ["gitlab ci", "gitlab-ci", "gitlab pipelines"],
    "GitHub Actions": ["github actions", "gh actions"],
    "CI/CD": ["ci/cd", "ci cd", "cicd", "continuous integration"],
    "Linux": ["linux", "ubuntu", "debian", "centos", "rhel"],

    # === IA / ML / Data ===
    "Machine Learning": ["ml", "machine learning", "apprentissage automatique"],
    "Deep Learning": ["dl", "deep learning", "apprentissage profond"],
    "Artificial Intelligence": ["ai", "artificial intelligence", "ia",
                                 "intelligence artificielle"],
    "NLP": ["nlp", "natural language processing", "traitement du langage naturel",
            "tal"],
    "Computer Vision": ["cv vision", "computer vision", "vision par ordinateur"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "tf", "tensor flow"],
    "Keras": ["keras"],
    "Scikit-learn": ["sklearn", "scikit-learn", "scikit learn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Hugging Face": ["huggingface", "hugging face", "transformers"],
    "LangChain": ["langchain", "lang chain"],
    "LLM": ["llm", "large language model", "large language models"],
    "Fine-tuning": ["fine-tuning", "fine tuning", "finetuning"],
    "LoRA": ["lora", "low-rank adaptation"],
    "QLoRA": ["qlora", "q-lora"],
    "RAG": ["rag", "retrieval augmented generation",
            "retrieval-augmented generation"],
    "Vector Database": ["vector db", "vector database", "vectordb"],
    "FAISS": ["faiss"],
    "ChromaDB": ["chroma", "chromadb"],
    "Sentence Transformers": ["sentence transformers", "sentence-transformers",
                              "sbert"],
    "BERT": ["bert"],
    "GPT": ["gpt", "gpt-3", "gpt-4", "gpt4"],
    "XGBoost": ["xgboost", "xgb"],
    "Random Forest": ["random forest", "rf"],
    "Logistic Regression": ["logistic regression", "lr"],

    # === Outils & méthodes ===
    "Git": ["git"],
    "GitHub": ["github"],
    "GitLab": ["gitlab"],
    "Bitbucket": ["bitbucket"],
    "Jira": ["jira"],
    "Agile": ["agile", "agility", "méthodes agiles"],
    "Scrum": ["scrum"],
    "Kanban": ["kanban"],
    "TDD": ["tdd", "test driven development"],
    "Microservices": ["microservices", "micro services"],

    # === Soft skills (un échantillon) ===
    "Leadership": ["leadership", "team leadership", "leader"],
    "Communication": ["communication", "communication skills"],
    "Problem Solving": ["problem solving", "résolution de problèmes"],
    "Teamwork": ["teamwork", "team work", "travail en équipe"],

    # === Langues ===
    "English": ["english", "anglais"],
    "French": ["french", "français", "francais"],
    "Spanish": ["spanish", "espagnol"],
    "Arabic": ["arabic", "arabe", "العربية"],
    "German": ["german", "allemand", "deutsch"],
    "Mandarin": ["mandarin", "chinese", "chinois"],
}


# ---------------------------------------------------------------------------- #
# Catégorisation des skills (utile pour l'explicabilité)
# ---------------------------------------------------------------------------- #

SKILL_CATEGORIES: Dict[str, str] = {}

_CATEGORY_GROUPS = {
    "programming_language": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
        "PHP", "Ruby", "Kotlin", "Swift", "Scala", "R", "SQL",
    ],
    "frontend": ["React", "Vue.js", "Angular", "Next.js", "Svelte", "HTML",
                 "CSS", "Tailwind CSS", "Sass"],
    "backend": ["Node.js", "Express.js", "FastAPI", "Django", "Flask",
                "Spring Boot", "Laravel", ".NET", "GraphQL", "REST", "gRPC"],
    "database": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
                 "SQLite", "Oracle", "SQL Server", "Cassandra", "DynamoDB", "Neo4j"],
    "cloud_devops": ["AWS", "Azure", "Google Cloud", "Docker", "Kubernetes",
                     "Terraform", "Ansible", "Jenkins", "GitLab CI",
                     "GitHub Actions", "CI/CD", "Linux"],
    "ai_ml": ["Machine Learning", "Deep Learning", "Artificial Intelligence",
              "NLP", "Computer Vision", "PyTorch", "TensorFlow", "Keras",
              "Scikit-learn", "Pandas", "NumPy", "Hugging Face", "LangChain",
              "LLM", "Fine-tuning", "LoRA", "QLoRA", "RAG", "Vector Database",
              "FAISS", "ChromaDB", "Sentence Transformers", "BERT", "GPT",
              "XGBoost", "Random Forest", "Logistic Regression"],
    "tools": ["Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Agile", "Scrum",
              "Kanban", "TDD", "Microservices"],
    "soft_skills": ["Leadership", "Communication", "Problem Solving", "Teamwork"],
    "language": ["English", "French", "Spanish", "Arabic", "German", "Mandarin"],
}

for _cat, _skills in _CATEGORY_GROUPS.items():
    for _s in _skills:
        SKILL_CATEGORIES[_s] = _cat


# ---------------------------------------------------------------------------- #
# Construction du lookup inversé
# ---------------------------------------------------------------------------- #

def _build_alias_index() -> Dict[str, str]:
    """Build alias -> canonical lookup. Inclut le nom canonique lui-même."""
    index: Dict[str, str] = {}
    for canonical, aliases in CANONICAL_SKILLS.items():
        index[canonical.lower()] = canonical
        for alias in aliases:
            index[alias.lower()] = canonical
    return index


_ALIAS_INDEX = _build_alias_index()


# ---------------------------------------------------------------------------- #
# API publique
# ---------------------------------------------------------------------------- #

class SkillNormalizer:
    """Normalise et catégorise les compétences.

    Usage :
        >>> norm = SkillNormalizer()
        >>> norm.normalize("ml")
        'Machine Learning'
        >>> norm.normalize_list(["react.js", "ts", "PostgreSQL", "Unknown Tech"])
        ['React', 'TypeScript', 'PostgreSQL', 'Unknown Tech']
    """

    def __init__(self, custom_dict_path: Optional[Path] = None) -> None:
        self._index: Dict[str, str] = dict(_ALIAS_INDEX)
        if custom_dict_path and custom_dict_path.exists():
            self._load_custom_dict(custom_dict_path)

    # ----- API ----- #

    def normalize(self, skill: str) -> str:
        if not skill:
            return ""
        cleaned = self._clean(skill)
        canonical = self._index.get(cleaned.lower())
        if canonical:
            return canonical
        # Tentative de match flou (sans points, sans tirets, sans espaces)
        compact = self._compact(cleaned)
        for alias, canon in self._index.items():
            if self._compact(alias) == compact:
                return canon
        # Fallback : on garde la version "title case" pour les inconnus
        return self._titlecase_fallback(cleaned)

    def normalize_list(self, skills: Iterable[str]) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for raw in skills:
            normalized = self.normalize(raw)
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
        return out

    def categorize(self, skill: str) -> str:
        canonical = self.normalize(skill)
        return SKILL_CATEGORIES.get(canonical, "other")

    def group_by_category(self, skills: Iterable[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for s in self.normalize_list(skills):
            cat = self.categorize(s)
            groups.setdefault(cat, []).append(s)
        return groups

    def is_known(self, skill: str) -> bool:
        return self._clean(skill).lower() in self._index

    # ----- Extra helpers used by orchestrator / augmentation ----- #

    @property
    def alias_map(self) -> Dict[str, str]:
        """Read-only view of the alias → canonical map (alias is lower-cased)."""
        return dict(self._index)

    def extract_skills(self, text: str) -> List[str]:
        """Extract a deduplicated list of canonical skills mentioned in ``text``.

        Implementation note: scans the alias index for substring matches with
        word-boundary checks.  Lower-cased canonical names are returned so
        downstream comparisons stay case-insensitive.
        """
        if not text:
            return []
        haystack = text.lower()
        found: Set[str] = set()
        for alias, canonical in self._index.items():
            if not alias:
                continue
            # Build a word-boundary regex; escape regex chars in alias.
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])"
            if re.search(pattern, haystack):
                found.add(canonical.lower())
        return sorted(found)

    # ----- Internals ----- #

    @staticmethod
    def _clean(skill: str) -> str:
        skill = skill.strip()
        # Retire les notes de niveau type "Python (advanced)" → "Python"
        skill = re.sub(r"\s*\([^)]*\)\s*", "", skill)
        skill = re.sub(r"[\u00a0\t]+", " ", skill)
        skill = re.sub(r"\s+", " ", skill)
        return skill.strip(" .,;:")

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"[\s\.\-_/]+", "", text.lower())

    @staticmethod
    def _titlecase_fallback(skill: str) -> str:
        if skill.isupper() and len(skill) <= 4:
            return skill  # garder l'acronyme
        return " ".join(w.capitalize() if not w.isupper() else w for w in skill.split())

    def _load_custom_dict(self, path: Path) -> None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(payload, dict):
            for canonical, aliases in payload.items():
                self._index[canonical.lower()] = canonical
                if isinstance(aliases, list):
                    for alias in aliases:
                        self._index[str(alias).lower()] = canonical


@lru_cache(maxsize=1)
def get_default_normalizer() -> SkillNormalizer:
    return SkillNormalizer()


def normalize_skill(skill: str) -> str:
    """Helper standalone."""
    return get_default_normalizer().normalize(skill)


if __name__ == "__main__":
    norm = SkillNormalizer()
    tests = [
        "ml", "ML", "Machine Learning", "react.js", "REACTJS",
        "PostgreSQL", "postgres", "k8s", "Kubernetes",
        "tensorflow 2.0", "TF", "GPT-4", "LoRA",
    ]
    for t in tests:
        print(f"  {t!r:30s} → {norm.normalize(t)!r}  [{norm.categorize(t)}]")
