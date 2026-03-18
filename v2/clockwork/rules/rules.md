# Clockwork Rule Engine — Master Rules

## Safety Rules (Priority 1 — HIGHEST)
- forbid_core_file_deletion: true
- protect_clockwork_directory: true
- block_unverified_code_execution: true
- no_unsafe_file_operations: true

## Architecture Rules (Priority 2)
- enforce_architecture_layers: true
- restrict_cross_layer_access: true
- require_module_boundaries: true

## Dependency Rules (Priority 3)
- new_dependency_must_be_declared: true
- removed_dependency_must_not_be_referenced: true
- no_version_conflicts: true

## Development Rules (Priority 4)
- new_module_requires_test: true
- require_documentation_for_public_api: true

## Context Rules (Priority 5)
- context_must_match_repository: true
- no_stale_memory_allowed: true