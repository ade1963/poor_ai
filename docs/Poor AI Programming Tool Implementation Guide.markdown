# Poor AI Programming Tool Implementation Guide

## Introduction

This guide provides a detailed plan for implementing the Poor AI Programming Tool in Python, including the new project tracking feature with component descriptions. The tool is designed for efficiency on weaker AI models, with a modular architecture and an MVP achievable in 10 days. The new feature introduces short, long, and detailed descriptions for project components, stored in markdown files and integrated into the template system for enhanced context.

## Prerequisites

- **Python Version**: 3.8+.
- **Dependencies**:
  - `argparse`, `pathlib`, `json`, `re` (standard library).
  - Optional: `pytest` (`pip install pytest`).
- **AI Model**: Lightweight local model (e.g., DistilBERT); mock for MVP.
- **Environment**: Any editor; virtual environment recommended.

## Architecture Overview

The tool’s architecture includes:

1. **Console Interface**: CLI for user interaction.
2. **Prompt Processor**: Parses inputs into tasks.
3. **Model Manager**: Handles AI interactions.
4. **File Handler**: Manages file operations.
5. **Template Processor**: Processes templates and descriptions.
6. **Testing Suite**: Validates functionality.

The Template Processor now integrates component descriptions from `<component>.desc.md` files.

## Directory Structure

```
poor_ai/
├── poor_ai.py
├── core/
│   ├── file_handler.py
│   ├── prompt_processor.py
│   ├── model_manager.py
│   ├── template_processor.py
├── tests/
│   ├── test_file_handler.py
│   ├── test_template_processor.py
│   ├── test_prompt_processor.py
├── templates/
├── models.json
├── requirements.txt
└── README.md
```

Description files are stored in the user’s project directory (e.g., `main.py.desc.md`).

## Implementation Details

### 1. Console Interface (`poor_ai.py`)

The CLI parses commands and manages state, including description commands.

- **Commands**:
  - `load <file>`
  - `gen <task>`
  - `fix <issue>`
  - `save`
  - `template new/edit/list/use <name>`
  - `context show`
  - `desc new/edit/view <file> [short|long|detailed]`
  - `test`
  - `model <name>`

### 2. File Handler (`core/file_handler.py`)

Unchanged, but interacts with Template Processor for descriptions.

- **Functions**:
  - `load_file(path)`
  - `save_file()`
  - `apply_result(result)`

### 3. Template Processor (`core/template_processor.py`)

Manages templates and descriptions.

- **Functions**:
  - `create_template(name)`
  - `fill_template(template_name, current_file, prompt)`
  - `get_description(path, desc_type)`
  - `create_description(file)`
  - `edit_description(file)`
  - `view_description(file, desc_type)`

- **Placeholders**:
  - Existing ones plus:
  - `{{desc_short:path}}`
  - `{{desc_long:path}}`
  - `{{desc_detailed:path}}`
  - `{{current_desc_short}}`, etc.

- **Description Parsing**: Use regex to extract sections from `<file>.desc.md`.

### 4. Prompt Processor (`core/prompt_processor.py`)

Unchanged, benefits from enriched context.

### 5. Model Manager (`core/model_manager.py`)

Manages AI interactions with enhanced context.

### 6. Testing Suite (`tests/`)

Tests include description handling.

## Development Plan

- **Day 1**: Setup.
- **Days 2-3**: Testing suite with description tests.
- **Days 4-5**: Implement core features with descriptions.
- **Days 6-7**: Model integration.
- **Days 8-9**: Integration and testing.
- **Day 10**: Release.

## Notes

- **Description Storage**: In project directories as `<file>.desc.md`.
- **Context Management**: Encourage concise descriptions.
- **Extensibility**: Modular design for future features.