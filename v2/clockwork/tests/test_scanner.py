import pytest
from pathlib import Path
from scanner.directory_walker import DirectoryWalker
from scanner.language_detector import LanguageDetector
from scanner.dependency_analyzer import DependencyAnalyzer
from scanner.architecture_inferer import ArchitectureInferer
from scanner.relationship_mapper import RelationshipMapper

ROOT = Path(".").resolve()

def test_directory_walker():
    walker = DirectoryWalker(str(ROOT))
    files = walker.walk()
    assert isinstance(files, list)
    assert len(files) > 0

def test_language_detector():
    walker = DirectoryWalker(str(ROOT))
    files = walker.walk()
    detector = LanguageDetector(files)
    result = detector.detect()
    assert "languages" in result
    assert "primary" in result

def test_dependency_analyzer():
    analyzer = DependencyAnalyzer(ROOT)
    result = analyzer.analyze()
    assert "dependencies" in result

def test_architecture_inferer():
    walker = DirectoryWalker(str(ROOT))
    files = walker.walk()
    inferer = ArchitectureInferer(files, ROOT)
    result = inferer.infer()
    assert "type" in result
    assert "components" in result

def test_relationship_mapper():
    walker = DirectoryWalker(str(ROOT))
    files = walker.walk()
    mapper = RelationshipMapper(files, ROOT)
    result = mapper.map()
    assert "graph" in result
    assert "circular_imports" in result