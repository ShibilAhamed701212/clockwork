# Clockwork Rule Definitions
# ---------------------------
# Add project-specific rules below.
# Rules are evaluated by the Rule Engine during `clockwork verify`.

## Architecture Rules

- Do not bypass the API layer.
- Do not modify database schema without a migration script.
- Do not remove core modules without explicit approval.

## File Protection Rules

- .clockwork/ must not be deleted.
- pyproject.toml must not be modified by automated agents without review.

## Naming Rules

- Python modules must use snake_case.
- Classes must use PascalCase.
