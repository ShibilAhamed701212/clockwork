import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

CONFIG_PATH = Path(__file__).parent / "config.yaml"

@dataclass
class ExecutionConfig:
    sandbox: bool = True
    dry_run: bool = False
    max_retries: int = 3
    timeout_seconds: int = 60

@dataclass
class MemoryConfig:
    persist: bool = True
    location: str = ".clockwork/"
    protected: bool = True

@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "logs/"

@dataclass
class SecurityConfig:
    zero_trust: bool = True
    sandbox_all: bool = True
    secrets_scan: bool = True

@dataclass
class PersonalityConfig:
    style: str = "conservative"

@dataclass
class Settings:
    version: str = "2.0"
    mode: str = "safe"
    learning: str = "enabled"
    autonomy: str = "restricted"
    validation: str = "strict"
    personality: PersonalityConfig = field(default_factory=PersonalityConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    @classmethod
    def load(cls, path: Path = CONFIG_PATH):
        if not path.exists():
            print("[Settings] Config not found, using defaults.")
            return cls()
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        cw = raw.get("clockwork", {})
        return cls(
            version=cw.get("version", "2.0"),
            mode=cw.get("mode", "safe"),
            learning=cw.get("learning", "enabled"),
            autonomy=cw.get("autonomy", "restricted"),
            validation=cw.get("validation", "strict"),
            personality=PersonalityConfig(**cw.get("personality", {})),
            execution=ExecutionConfig(**cw.get("execution", {})),
            memory=MemoryConfig(**cw.get("memory", {})),
            logging=LoggingConfig(**cw.get("logging", {})),
            security=SecurityConfig(**cw.get("security", {})),
        )

    def is_safe_mode(self):
        return self.mode == "safe"

    def is_strict_validation(self):
        return self.validation == "strict"

    def is_autonomous(self):
        return self.autonomy == "full"

    def to_dict(self):
        return {
            "version": self.version,
            "mode": self.mode,
            "learning": self.learning,
            "autonomy": self.autonomy,
            "validation": self.validation,
        }