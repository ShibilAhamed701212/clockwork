from pathlib import Path
from typing import Dict, List
from collections import defaultdict

EXTENSION_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".rs": "Rust",
    ".go": "Go", ".java": "Java", ".cpp": "C++", ".c": "C",
    ".cs": "CSharp", ".rb": "Ruby", ".php": "PHP",
    ".html": "HTML", ".css": "CSS", ".sql": "SQL",
    ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON", ".md": "Markdown", ".toml": "TOML",
}

FRAMEWORK_SIGNATURES = {
    "flask": ("Python", "backend"),
    "fastapi": ("Python", "api"),
    "django": ("Python", "backend"),
    "react": ("JavaScript", "frontend"),
    "vue": ("JavaScript", "frontend"),
    "express": ("JavaScript", "backend"),
    "sqlalchemy": ("Python", "database"),
    "pytest": ("Python", "testing"),
    "celery": ("Python", "worker"),
}

class LanguageDetector:
    def __init__(self, files: List[Path]):
        self.files = files

    def detect(self) -> Dict:
        freq: Dict[str, int] = defaultdict(int)
        for f in self.files:
            lang = EXTENSION_MAP.get(f.suffix.lower())
            if lang:
                freq[lang] += 1
        primary = max(freq, key=freq.get) if freq else "unknown"
        return {
            "languages": dict(freq),
            "primary": primary,
            "total_files": len(self.files),
        }

    def detect_frameworks(self, dep_names: List[str]) -> Dict[str, List[str]]:
        classified: Dict[str, List[str]] = {
            "backend": [], "frontend": [], "api": [],
            "database": [], "testing": [], "worker": []
        }
        for dep in dep_names:
            key = dep.lower().replace("-", "_")
            if key in FRAMEWORK_SIGNATURES:
                _, category = FRAMEWORK_SIGNATURES[key]
                classified[category].append(dep)
        return {k: v for k, v in classified.items() if v}

    def infer_skills(self, lang_data: dict, framework_data: dict) -> List[str]:
        skills = set()
        skill_map = {
            "Python": "Python Developer", "JavaScript": "JavaScript Developer",
            "TypeScript": "TypeScript Developer", "SQL": "Database Engineer",
            "Rust": "Systems Developer", "Go": "Go Developer",
        }
        for lang in lang_data.get("languages", {}):
            if lang in skill_map:
                skills.add(skill_map[lang])
        for cat, fws in framework_data.items():
            if fws:
                if cat == "frontend":
                    skills.add("Frontend Developer")
                elif cat in ("backend", "api"):
                    skills.add("Backend Developer")
                elif cat == "database":
                    skills.add("Database Engineer")
        return sorted(skills)