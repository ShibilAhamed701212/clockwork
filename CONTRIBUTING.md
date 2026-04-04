# Contributing to Clockwork

Thank you for your interest in contributing to Clockwork!

---

## Code of Conduct

Be respectful, collaborative, and constructive. We welcome contributors from all backgrounds.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/ShibilAhamed701212/clockwork.git
cd clockwork

# Install in development mode
pip install -e ".[dev]"

# Verify installation
clockwork doctor
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_security.py -v

# Run with coverage
pytest tests/ --cov=clockwork --cov-report=term-missing
```

---

## Project Structure

```
clockwork/
├── clockwork/              # Main package
│   ├── ai/                # AI providers and manager
│   ├── brain/             # Reasoning engines
│   ├── cli/               # CLI commands
│   ├── pipeline/          # Pipeline execution
│   ├── recovery/          # Self-healing and retry
│   ├── safety/            # Security layer
│   └── ...               # Other modules
├── tests/                 # Test suite
└── docs/                  # Documentation
```

---

## Making Changes

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes
4. **Test** locally with `pytest`
5. **Commit** with clear messages: `git commit -am 'Add feature X'`
6. **Push** to your fork: `git push origin feature/my-feature`
7. **Open** a Pull Request

---

## Coding Standards

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints where possible
- Add docstrings to public functions
- Keep functions small and focused

---

## Testing Guidelines

- Test files go in `tests/`
- Name test files: `test_<module>.py`
- Use pytest fixtures for setup/teardown
- Aim for meaningful assertions

---

## Submitting Changes

When submitting a PR:

1. **Description** — Explain what and why
2. **Tests** — Include new tests for new features
3. **Documentation** — Update docs if needed
4. **No Breaking Changes** — Keep backwards compatibility

---

## Questions?

- Open an issue for bugs or feature requests
- Use discussions for questions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
