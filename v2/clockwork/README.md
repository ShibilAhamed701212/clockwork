# Clockwork AI OS

A Local-First Intelligent Governance Layer for AI-Assisted Software Development.

## Quick Start

    pip install -r requirements.txt
    python main.py init
    python main.py scan
    python main.py verify
    python main.py status

## Execution Modes

| Mode       | Validation | Speed  | Autonomy   |
|------------|------------|--------|------------|
| safe       | strict     | slow   | restricted |
| balanced   | moderate   | medium | partial    |
| aggressive | relaxed    | fast   | full       |

## Pipeline

scanner -> context -> graph -> brain -> agents -> validation -> recovery