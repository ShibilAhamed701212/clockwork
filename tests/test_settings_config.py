from __future__ import annotations

from pathlib import Path

import yaml

from clockwork.config.settings import load_settings


def test_load_settings_reads_flat_keys(tmp_path: Path):
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "mode": "balanced",
                "autonomy": "partial",
                "validation": "moderate",
                "auto_generate_ide_files": True,
                "ide_formats": ["claude-md", "cursorrules"],
            }
        ),
        encoding="utf-8",
    )

    s = load_settings(tmp_path)
    assert s.mode == "balanced"
    assert s.autonomy == "partial"
    assert s.validation == "moderate"
    assert s.auto_generate_ide_files is True
    assert s.ide_formats == ("claude-md", "cursorrules")


def test_load_settings_reads_runtime_block(tmp_path: Path):
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "runtime": {
                    "mode": "safe",
                    "autonomy": "restricted",
                    "validation": "strict",
                },
                "integration_output_dir": ".clockwork/integrations",
                "legacy_root_integrations": "true",
            }
        ),
        encoding="utf-8",
    )

    s = load_settings(tmp_path)
    assert s.mode == "safe"
    assert s.autonomy == "restricted"
    assert s.validation == "strict"
    assert s.integration_output_dir == ".clockwork/integrations"
    assert s.legacy_root_integrations is True

