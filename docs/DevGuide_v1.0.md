# Poor AI Programming Tool Developer Guide v1.0

## Overview

The **Poor AI Programming Tool** is a lightweight, console-based Python application designed to assist programmers by leveraging AI models, optimized for systems with limited computational resources. Its modular architecture supports multi-file operations, a flexible template system, and project tracking with markdown-based component descriptions. The tool emphasizes concise prompts, robust file handling, and extensible AI model integration, making it ideal for developers working with constrained AI setups.

### Key Features
- **Console-Based Interface**: Text-based CLI for broad compatibility.
- **Multi-File Support**: Load and manage multiple files simultaneously, with JSON-formatted output for templates.
- **Template System**: Customizable templates with placeholders for file contents, folder structures, project data, and descriptions.
- **Project Tracking**: Manages project files via `project.json`, including file languages and descriptions.
- **Component Descriptions**: Markdown-based descriptions (`short`, `long`, `detailed`) stored in `<file>.desc.md` files.
- **Model Management**: Configurable AI models via `models.json`, supporting providers like Ollama and OpenRouter.
- **File Handling**: Efficient file operations with change detection, directory creation, diff support, and wildcard loading.
- **Response Processing**: Extracts code and diffs from AI responses, prioritizing JSON format with fallback to code blocks and diffs.
- **Logging**: Comprehensive logging with rotating file handlers across all modules.

## Project Structure

```
poor_ai/
├── poor_ai.py              # Main CLI entry point and core logic
├── core/
│   ├── file_handler.py     # File operations and project tracking
│   ├── model_manager.py    # AI model interactions
│   ├── prompt_processor.py # Command parsing and context building
│   ├── response_processor.py # Code and diff extraction from AI responses
│   ├── template_processor.py # Template management and description handling
├── templates/              # Directory for template files, populated from templates_source_folder
├── template_sources/       # Source folder for template files (configurable in config.json)
├── models.json             # AI model configurations
├── config.json             # Application settings for display behavior and template source
├── project.json            # Tracks project files (created dynamically)
├── requirements.txt        # Dependencies
└── README.md               # Project overview
```

## Module Breakdown

### 1. `poor_ai.py`
**Role**: Main CLI entry point, orchestrating core logic.

- **Class**: `PoorAI`
- **Key Methods**:
  - `__init__(project_folder)`: Initializes project folder, logging, and core components (`FileHandler`, `TemplateProcessor`, `PromptProcessor`, `ModelManager`).
  - `_setup_logging()`: Configures rotating file handler (`poor_ai.log`, 10MB, 5 backups).
  - `_validate_project_structure()`: Ensures project folder, `templates/`, `project.json`, and `logs/` exist, creating them with user confirmation.
  - `load_models_config()`: Loads AI model configurations from `models.json`.
  - `initialize_model_manager(model_name)`: Sets up the AI model, defaulting to the first in `models.json`.
  - `_save_request_response(prompt_data, raw_result, token_info, cost)`: Logs AI request-response pairs with metadata.
  - `run()`: Executes the CLI loop, handling commands and initial arguments.
  - `process_command(command)`: Processes commands (`load`, `save`, `gen`, `template`, `desc`, `model`, `test`, etc.).
  - `_update_project_descriptions(descriptions)`: Updates `project.json` with AI-generated descriptions from `descriptions.json`.
- **Features**:
  - Supports commands for file operations, AI generation, template management, description handling, and model selection.
  - Handles multi-file operations and maintains project state (model, template, task, files).
  - Logs operations for debugging and auditing.
- **Dependencies**: `argparse`, `json`, `os`, `sys`, `pathlib`, `logging`, `logging.handlers`, `datetime`, `uuid`, core modules.

### 2. `core/file_handler.py`
**Role**: Manages file operations, project tracking, and change detection.

- **Class**: `FileHandler`
- **Key Methods**:
  - `__init__(project_dir)`: Initializes with project directory, sets up logging (`file_handler.log`, 10MB, 5 backups), and creates `project.json`.
  - `load_file(paths)`: Loads multiple files into memory, supporting wildcard patterns (e.g., `*.py`) from `project.json`, and updates `project.json`.
  - `save_file()`: Saves changed files, creating parent directories (e.g., `src/` for `src/index.html`), and updates `project.json`.
  - `apply_result(result)`: Applies AI-generated content or diffs, preserving comments for non-diff updates and handling JSON format.
  - `clear()`: Clears loaded files and contents.
  - `get_artifacts()`: Returns formatted file contents with escaped backticks.
  - `get_project()`: Lists project files with descriptions from `project.json`.
  - `get_description_path(file_path)`: Returns path to `<file>.desc.md`.
- **Features**:
  - Supports multi-file loading via space-separated paths or wildcards.
  - Handles unified and Git-style diffs with precise hunk application.
  - Preserves existing comments for non-diff content updates, including multi-line and inline comments.
  - Updates `project.json` with file paths and languages, avoiding duplicates.
  - Provides detailed error messages for file operations.
- **Dependencies**: `os`, `pathlib`, `logging`, `json`, `difflib`, `re`, `fnmatch`.

### 3. `core/model_manager.py`
**Role**: Manages interactions with AI models, supporting multiple providers with robust configuration and error handling.

- **Class**: `ModelManager`
- **Key Methods**:
  - `__init__(config_path, app_config_path)`: Loads model configurations from `models.json` and application settings from `config.json`, sets the default model.
  - `_setup_logging()`: Configures logging to `model_manager.log` with rotation (10MB, 5 backups).
  - `_load_models(config_path)`: Loads model configurations, handling errors for missing or invalid `models.json`.
  - `_load_app_config(app_config_path)`: Loads display settings, defaulting to `notepad` (Windows) or `gedit` (Linux).
  - `_set_default_model()`: Sets the first model in `models.json` as default if available.
  - `set_model(model_name)`: Switches to a specified model, validating against `models.json`.
  - `generate(prompt)`: Generates responses using the current model, supporting Ollama (local), OpenRouter (API), or fake (manual input) providers.
  - `_display_request_response(request, response)`: Saves request/response to a temporary file and opens it with the configured app.
  - `get_current_model()`: Returns the current model configuration.
- **Features**:
  - **Provider Support**:
    - **Ollama**: Local model interaction via OpenAI-compatible API, using endpoints like `http://localhost:11434`.
    - **OpenRouter**: Cloud-based API access, requiring `OPENROUTER_API_KEY` environment variable, with custom headers for context.
    - **Fake**: Simulates AI interaction by opening a text editor (e.g., notepad) for manual response input, useful for testing or offline use.
  - **Configuration**: Models defined in `models.json` with fields for `provider`, `name`, `endpoint`, `system_prompt`, `temperature`, `top_k`, `top_p`, `max_tokens`, and `pricing` (input/output token costs).
  - **Error Handling**: Catches and logs `APIError`, `APIConnectionError`, `RateLimitError`, and general exceptions, providing user-friendly messages and stack traces.
  - **Token and Cost Tracking**: Calculates token usage (`prompt_tokens`, `completion_tokens`) and cost based on `pricing` field for non-fake providers.
  - **Response Display**: Optionally displays request/response in a temporary file using the configured app (e.g., notepad), controlled by `config.json`.
  - **Logging**: Detailed logs for model initialization, API calls, errors, and token/cost metrics.
- **Example `models.json`**:
  ```json
  {
    "models": [
      {
        "provider": "ollama",
        "name": "llama3",
        "endpoint": "http://localhost:11434",
        "system_prompt": "Provide concise code with JSON output.",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2000,
        "pricing": {"input_tokens": 0.0, "output_tokens": 0.0}
      },
      {
        "provider": "openrouter",
        "name": "meta-llama/llama-3-8b-instruct",
        "endpoint": "https://openrouter.ai/api/v1",
        "system_prompt": "Return JSON with filename, language, content.",
        "temperature": 0.8,
        "top_p": 0.95,
        "max_tokens": 4000,
        "pricing": {"input_tokens": 0.15, "output_tokens": 0.60}
      },
      {
        "provider": "fake",
        "name": "manual-test",
        "endpoint": "",
        "system_prompt": "Simulate AI response.",
        "pricing": {"input_tokens": 0.0, "output_tokens": 0.0}
      }
    ]
  }
  ```
- **Dependencies**: `json`, `logging`, `os`, `platform`, `subprocess`, `tempfile`, `time`, `pathlib`, `openai`.

### 4. `core/prompt_processor.py`
**Role**: Parses user commands and builds AI context.

- **Class**: `PromptProcessor`
- **Key Methods**:
  - `__init__(template_processor, file_handler)`: Initializes with dependencies.
  - `process_prompt(command, current_file, project_name, template_name)`: Processes commands into structured prompts.
  - `_parse_command(command)`: Identifies `gen` commands and extracts tasks.
  - `_build_context(current_file, project_name, task, template_name)`: Builds context using `TemplateProcessor` or a default format.
- **Features**:
  - Supports `gen <task>` commands for code generation.
  - Integrates with `TemplateProcessor` for context with multi-file support.
- **Dependencies**: `re`, `typing`.

### 5. `core/response_processor.py`
**Role**: Extracts code and diffs from AI responses.

- **Key Functions**:
  - `extract_code(response)`: Parses responses into file-content pairs, prioritizing JSON format (`filename`, `language`, `content`) with fallbacks for code blocks, raw content, and diffs.
- **Features**:
  - Validates JSON responses with file metadata.
  - Supports unified and Git-style diffs, extracting filenames from headers.
  - Handles fenced JSON, code blocks (including four-backtick fences), and raw content with escaped backticks.
  - Supports filenames after triple-backtick fences.
  - Assigns unique `artifact_id` to each extracted pair.
  - Logs parsing details for debugging.
- **Dependencies**: `re`, `logging`, `uuid`, `json`.

### 6. `core/template_processor.py`
**Role**: Manages templates and component descriptions.

- **Class**: `TemplateProcessor`
- **Key Methods**:
  - `__init__(project_dir, templates_dir, file_handler)`: Initializes with project directory, template directory, and `FileHandler`; copies templates from `templates_source_folder` (from `config.json`).
  - `create_template(name, content)`: Creates a new template file.
  - `fill_template(template_name, current_file, project_name, task)`: Fills templates with placeholders.
  - `get_description(file_path, desc_type)`: Retrieves `short`, `long`, or `detailed` descriptions from `<file>.desc.md`.
  - `create_description(file_path)`: Creates `<file>.desc.md` with default markdown.
  - `edit_description(file_path)`: Prompts manual editing of description files.
  - `view_description(file_path, desc_type)`: Views specific description types.
  - `list_templates()`: Lists available `.txt` templates.
  - `_get_json_file_contents()`: Generates JSON-formatted file contents for templates.
- **Placeholders**:
  - `{{project_name}}`: Project name from `project.json`.
  - `{{task}}`: User task.
  - `{{current_file}}`, `{{current_file_name}}`: Loaded file contents/names.
  - `{{file:path}}`: Specific file content.
  - `{{folder_schema:paths}}`: Directory/file structure.
  - `{{files_no_descriptions}}`, `{{files_with_short_descriptions}}`, `{{files_with_detailed_descriptions}}`: Project file lists.
  - `{{file_contents}}`: Loaded file contents.
  - `{{json_file_contents}}`: JSON-formatted file contents.
  - `{{desc_short/long/detailed:path}}`, `{{current_desc_short/long/detailed}}`: File descriptions.
- **Features**:
  - Copies templates from `templates_source_folder` (defined in `config.json`) to `templates` during initialization.
  - Falls back to `default.txt` if a template is missing.
  - Supports multi-file contexts via `FileHandler`.
  - Parses descriptions using regex for precise extraction.
  - Creates directories for description files.
- **Dependencies**: `os`, `pathlib`, `re`, `typing`, `json`, `shutil`.

## Configuration Files

### 1. `templates/default.txt`
- **Purpose**: Default template for context generation, used when no template is specified or the requested template is missing.
- **Structure**: Includes placeholders like `{{folder_schema:./}}`, `{{files_with_short_descriptions}}`, `{{file_contents}}`, and `{{task}}` to provide project structure, file descriptions, file contents, and the user’s task.
- **Usage**: Automatically populated in the `templates` directory, potentially copied from `templates_source_folder` as specified in `config.json`.

### 2. `templates/main.txt`
- **Purpose**: Advanced template requiring JSON-formatted AI responses.
- **Structure**: Includes `{{task}}`, `{{files_with_short_descriptions}}`, `{{json_file_contents}}`, and instructions for JSON output with `descriptions.json`.
- **Usage**: Used for structured AI responses with file metadata.

### 3. `models.json`
- **Purpose**: Configures AI models.
- **Structure**:
  ```json
  {
    "models": [
      {
        "provider": "ollama|openrouter|fake",
        "name": "model_name",
        "endpoint": "url",
        "system_prompt": "Response formatting instructions",
        "mode": "no_thinking",
        "temperature": float,
        "top_k": int,
        "top_p": float,
        "pricing": {"input_tokens": float, "output_tokens": float},
        "max_tokens": int
      }
    ]
  }
  ```
- **Usage**: Loaded by `PoorAI` to configure AI interactions.

### 4. `config.json`
- **Purpose**: Stores application settings, including display behavior and template source folder.
- **Structure**:
  ```json
  {
    "display_app": "notepad|gedit",
    "display_request_response": true,
    "templates_source_folder": "template_sources"
  }
  ```
- **Usage**: Configures request/response display behavior and specifies a source folder for copying template files into `templates`.

### 5. `project.json` (Dynamic)
- **Purpose**: Tracks project files and metadata.
- **Structure**:
  ```json
  {
    "project_name": "name",
    "files": [
      {
        "name": "file1.py",
        "short": null,
        "detailed": null,
        "language": "python"
      }
    ]
  }
  ```
- **Usage**: Updated by `FileHandler` when loading/saving files.

## Component Interactions

### Data Flow
1. **User Input** (`poor_ai.py` CLI): Parses commands (e.g., `gen`, `desc`).
2. **Prompt Processing** (`PromptProcessor`): Builds context using `TemplateProcessor`.
3. **Template Processing** (`TemplateProcessor`): Fills placeholders with data from `FileHandler`.
4. **AI Interaction** (`PoorAI`): Sends prompts to the AI and logs responses.
5. **Response Processing** (`ResponseProcessor`): Extracts file-content pairs and `descriptions.json`.
6. **File Operations** (`FileHandler`): Applies changes, updates `project.json`, and manages descriptions.

### Dependencies
- **PromptProcessor**: Depends on `TemplateProcessor`, `FileHandler`.
- **TemplateProcessor**: Depends on `FileHandler` for file/project data and `config.json` for `templates_source_folder`.
- **ModelManager**: Independent, but uses `models.json` and `config.json`.
- **ResponseProcessor**: Independent, used by `FileHandler`.
- **FileHandler**: Interacts with `TemplateProcessor` for descriptions.

### Control Flow
1. CLI routes commands to `PromptProcessor.process_prompt`.
2. `PromptProcessor` uses `TemplateProcessor.fill_template`.
3. `TemplateProcessor` fetches data from `FileHandler` and copies templates from `templates_source_folder`.
4. `PoorAI` sends prompts to the AI and processes responses via `ResponseProcessor`.
5. `FileHandler.apply_result` applies changes and updates `project.json`.

## Setup Instructions

### Requirements
- **Python**: 3.8+.
- **Dependencies** (assumed, not provided):
  ```plaintext
  openai
  pytest
  ```
  Install via:
  ```bash
  pip install openai pytest
  ```
- **Environment**: Set `OPENROUTER_API_KEY` for OpenRouter models.
- **AI Model**: Supports Ollama (local), OpenRouter (API), or fake provider.

### Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd poor_ai
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies:
   ```bash
   pip install openai pytest
   ```
4. Configure `models.json` and `config.json` (including `templates_source_folder`).
5. Run the tool:
   ```bash
   python poor_ai.py
   ```

## Usage Examples

### 1. Generating Code
```bash
load src/*.py
task "add a utility function"
gen
```
- Loads all Python files from `project.json` matching `src/*.py`, builds context with `main.txt`, generates JSON-formatted AI response, applies changes, and updates `project.json`.

**Expected AI Response**:
```json
[
  {"filename": "core/utils.py", "language": "python", "content": "def util():\n    return True"},
  {"filename": "descriptions.json", "language": "json", "content": "[{\"file\": \"core/utils.py\", \"short\": \"Utility function\", \"detailed\": \"Implements a basic utility function.\"}]"}
]
```

### 2. Managing Descriptions
```bash
desc new src/main.py
desc view src/main.py short
```
- Creates `src/main.py.desc.md` and displays its short description.

### 3. Using a Custom Template
```bash
template use main
gen "create a new API endpoint"
```
- Uses `main.txt` (potentially copied from `templates_source_folder`) to generate JSON-formatted AI responses with file contents and descriptions.

## Notes
- **Context Size**: Use concise descriptions to support weaker AI models.
- **Extensibility**: Add new providers in `models.json` or placeholders in `TemplateProcessor`.
- **Logging**: Check `poor_ai.log`, `file_handler.log`, and `response_processor.log` for debugging.
- **Testing**: Create a `tests/` directory with `pytest` scripts to validate functionality.