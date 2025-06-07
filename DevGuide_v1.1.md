# Poor AI Programming Tool Developer Guide v1.1

## Overview

The **Poor AI Programming Tool** is a lightweight, console-based Python application designed to streamline development workflows by integrating AI-driven code generation with robust project management. Optimized for systems with limited resources, it offers a modular architecture, a flexible template system, and seamless project tracking via `project.json`. The tool is ideal for developers seeking efficient, AI-assisted coding with a focus on extensibility and minimal computational overhead. This guide provides a comprehensive blueprint for a new team to rebuild the project from scratch and addressing modern development needs.

### Key Features
- **Console-Based Interface**: A text-based CLI ensures compatibility across platforms, from low-end systems to high-performance setups.
- **Multi-File Operations**: Load, edit, and save multiple files with wildcard support (e.g., `*.py`), tracked in `project.json`.
- **Template System**: Customizable templates with dynamic placeholders for project metadata, file contents, and tasks, enabling structured AI prompts.
- **Project Tracking**: Centralizes file metadata (name, language, short/detailed descriptions) in `project.json` for streamlined management.
- **AI Model Integration**: Supports multiple AI providers (Ollama, OpenRouter, fake) via `models.json`, with enhanced configuration options like the `think` parameter for Ollama.
- **File Handling**: Robust file operations with change detection, directory creation, wildcard loading, and diff application.
- **Response Processing**: Extracts structured JSON responses from AI, including file contents and metadata, with fallbacks for code blocks and diffs.
- **Logging**: Comprehensive logging across modules with rotating file handlers for debugging and auditing.
- **Extensibility**: Modular design allows easy addition of new AI providers, templates, and placeholders.

## Project Structure

```
poor_ai/
├── poor_ai.py              # Main CLI entry point and core logic
├── core/
│   ├── __init__.py           # Makes core a Python package
│   ├── file_handler.py     # File operations and project tracking
│   ├── model_manager.py    # AI model interactions with provider support
│   ├── prompt_processor.py # Command parsing and context building
│   ├── response_processor.py # Code and diff extraction from AI responses
│   ├── template_processor.py # Template management and placeholder processing
├── templates/              # Directory for template files (e.g., main.txt)
├── template_sources/       # Source folder for template files (configurable in config.json)
├── models.json             # AI model configurations
├── config.json             # Application settings (display, template source)
├── project.json            # Tracks project files and metadata (dynamic)
├── requirements.txt        # Python dependencies
├── logs/                   # Log files (poor_ai.log, file_handler.log, etc.)
├── README.md               # Project overview
└── .gitignore              # Git ignore file
```

## Module Breakdown

### 1. `poor_ai.py`
**Role**: The main CLI entry point, orchestrating user commands and coordinating core components.

- **Class**: `PoorAI`
- **Key Methods**:
  - `__init__(project_folder)`: Initializes the project folder, logging, and core components (`FileHandler`, `TemplateProcessor`, `PromptProcessor`, `ModelManager`). The `--project-folder` argument is parsed via `argparse` and used to set the project directory for all operations.
  - `_setup_logging()`: Configures a rotating file handler for `poor_ai.log` (10MB, 5 backups).
  - `_validate_project_structure()`: Ensures the existence of `project.json`, `templates/`, and `logs/`, creating them with user confirmation if missing.
  - `load_models_config()`: Loads AI model configurations from `models.json` in the project directory if present; otherwise, falls back to the script directory.
  - `initialize_model_manager(model_name)`: Sets the active AI model, defaulting to the first in `models.json`.
  - `_save_request_response(prompt_data, raw_result, token_info, cost)`: Logs AI request-response pairs with metadata (model, tokens, cost) to `logs/request_<timestamp>_<uuid>.txt`.
  - `run()`: Runs the CLI loop, processing commands and optional initial arguments.
  - `process_command(command)`: Handles commands like `load`, `save`, `gen`, `task`, `template`, `context`, `desc`, `test`, `model`, `project`, `version`, and `help`.
- **Features**:
  - Supports interactive commands for file operations, code generation, template management, model selection, and project management.
  - Maintains state (current model, template, task, loaded files) for consistent workflows.
  - Integrates with `FileHandler` for file operations, `TemplateProcessor` for context building, and `ModelManager` for AI interactions.
  - Logs all operations for traceability.
  - **CLI Commands**:
    - `load <file_path[,file_path,...]>`: Loads one or more files into the editor buffer, supporting wildcard patterns (e.g., `src/*.py`).
    - `save`: Saves changed contents of loaded files to disk, updating `project.json` with file metadata.
    - `clear`: Clears all loaded files from the in-memory buffer.
    - `gen`: Generates code based on the current task, template, and loaded files, sending the prompt to the AI model and applying the response to the buffer.
    - `task <description>`: Sets the task description for code generation, supporting multiline input ending with `END`.
    - `template <subcommand>`: Manages templates with subcommands: `new <name>`, `edit <name>`, `list`, `use <name>`, `show [name]`.
    - `context show`: Displays the generated AI prompt context based on the current template, task, and files.
    - `test`: Runs automated tests using `pytest` in the `tests/` directory.
    - `model <name|index>|list`: Switches the active AI model or lists available models from `models.json`.
    - `project set-name <name>`: Updates the `project_name` field in `project.json`.
    - `version`: Displays the tool’s version.
    - `help`: Shows the help message with all available commands.
- **Dependencies**: `argparse`, `json`, `os`, `sys`, `pathlib`, `logging`, `logging.handlers`, `datetime`, `uuid`, `shutil`, core modules.

### 2. `core/file_handler.py`
**Role**: Manages file operations, project tracking, and change detection.

- **Class**: `FileHandler`
- **Key Methods**:
  - `__init__(project_dir)`: Initializes with the project directory, assuming `project.json` exists as ensured by `PoorAI._validate_project_structure()`. Sets up logging (`file_handler.log`, 10MB, 5 backups).
  - `load_file(paths)`: Loads multiple files into memory, supporting wildcard patterns (e.g., `*.py`) and updating `project.json` with file metadata.
  - `save_file()`: Saves modified files, creating parent directories as needed, and updates `project.json`.
  - `apply_result(result)`: Applies AI-generated content or diffs, preserving comments for Python, JavaScript, HTML, and CSS in non-diff updates.
  - `clear()`: Clears loaded files and their in-memory contents.
  - `get_artifacts()`: Returns formatted file contents with escaped backticks for template integration.
  - `get_project()`: Retrieves project file list with descriptions from `project.json`.
- **Features**:
  - Supports wildcard file loading (e.g., `load src/*.py`) from `project.json`.
  - Handles unified and Git-style diffs for precise updates.
  - Preserves multi-line and inline comments during non-diff content updates.
  - Updates `project.json` by matching files on their `name` (file path), updating existing entries rather than appending duplicates.
  - Provides detailed error messages for file operations.
- **Dependencies**: `os`, `pathlib`, `logging`, `json`, `difflib`, `re`, `fnmatch`.

### 3. `core/model_manager.py`
**Role**: Manages AI model interactions, supporting multiple providers with robust configuration.

- **Class**: `ModelManager`
- **Key Methods**:
  - `__init__(config_path, app_config_path)`: Loads model configurations (`models.json`) and application settings (`config.json`).
  - `_setup_logging()`: Configures logging to `model_manager.log` (10MB, 5 backups).
  - `_load_models(config_path)`: Parses `models.json`, handling errors for missing or invalid files.
  - `_load_app_config(app_config_path)`: Loads display settings (e.g., `notepad` or `gedit`) from `config.json`.
  - `_set_default_model()`: Sets the first model in `models.json` as default.
  - `set_model(model_name)`: Switches to the specified model, validating against `models.json`.
  - `generate(prompt)`: Sends prompts to the current model (Ollama, OpenRouter, or fake), including the `think` parameter in the payload only for Ollama providers, and processes responses.
  - `_display_request_response(request, response)`: Displays request/response in a temporary file using the configured app.
  - `get_current_model()`: Returns the current model’s configuration.
- **Features**:
  - **Provider Support**:
    - **Ollama**: Interacts with local models via an OpenAI-compatible API (e.g., `http://localhost:11434`), supporting the `think` parameter for enhanced reasoning.
    - **OpenRouter**: Uses cloud-based APIs with `OPENROUTER_API_KEY` read from the environment variable, supporting custom headers and token/cost tracking.
    - **Fake**: Simulates AI responses by opening a text editor for manual input, ideal for testing or offline scenarios.
  - **Ollama API Call with `think` Parameter**:
    - The `think` parameter (boolean) in `models.json` enables advanced reasoning in Ollama’s `/api/chat` endpoint, allowing the model to process prompts more deeply before responding.
    - Example API call:
      ```python
      import requests
      import json

      def call_ollama(endpoint, model, messages, parameters):
          payload = {
              "model": model,
              "messages": messages,
              "options": {},
              "stream": False,
          }
          # Handle special 'think' parameter for Ollama's custom API
          if parameters.get("think", False):
              payload["think"] = True
          
          # Standard OpenAI-compatible parameters go into 'options'
          for key in ["temperature", "top_k", "top_p", "num_predict"]:
              if key in parameters:
                  payload["options"][key] = parameters[key]

          headers = {"Content-Type": "application/json"}
          try:
              response = requests.post(
                  f"{endpoint}/api/chat",
                  headers=headers,
                  data=json.dumps(payload),
                  timeout=1200  # 20 minutes
              )
              response.raise_for_status()
              return response.json()
          except requests.RequestException as e:
              print(f"Error calling Ollama API: {e}")
              return None
      ```
  - **Configuration**: Models defined in `models.json` with fields for `provider`, `name`, `endpoint`, `system_prompt`, `size`, `parameters` (including `think`, `temperature`, `top_k`, `top_p`, `max_tokens`), and `pricing`.
  - **Error Handling**: Catches `APIError`, `APIConnectionError`, `RateLimitError`, and general exceptions, logging detailed errors.
  - **Token and Cost Tracking**: Calculates `prompt_tokens`, `completion_tokens`, and costs based on `pricing` for non-fake providers.
  - **Response Display**: Optionally displays request/response in a temporary file, controlled by `config.json`.
- **Dependencies**: `json`, `logging`, `os`, `platform`, `subprocess`, `tempfile`, `time`, `pathlib`, `openai`, `requests`.

### 4. `core/prompt_processor.py`
**Role**: Parses user commands and constructs AI prompts.

- **Class**: `PromptProcessor`
- **Key Methods**:
  - `__init__(template_processor, file_handler)`: Initializes with `TemplateProcessor` and `FileHandler`.
  - `process_prompt(command, current_file, project_name, template_name)`: Processes commands (e.g., `gen <task>`) into structured prompts.
  - `_parse_command(command)`: Identifies command type and extracts task.
  - `_build_context(current_file, project_name, task, template_name)`: Builds context using `TemplateProcessor`.
- **Features**:
  - Processes `gen` commands for code generation.
  - Integrates with `TemplateProcessor` for dynamic context creation.
- **Dependencies**: `re`, `typing`.

### 5. `core/response_processor.py`
**Role**: Extracts structured data from AI responses.

- **Key Functions**:
  - `extract_code(response)`: Parses AI responses into file-content pairs, prioritizing JSON format (`filename`, `language`, `content`) with fallbacks for code blocks, raw content, and diffs.
- **Features**:
  - Supports JSON responses with file metadata.
  - Handles unified and Git-style diffs, extracting filenames from headers.
  - Processes four-backtick fenced blocks and filenames after triple-backtick fences.
  - Assigns unique `artifact_id` to each extracted pair.
  - Logs parsing details for debugging.
- **Dependencies**: `re`, `logging`, `uuid`, `json`.

### 6. `core/template_processor.py`
**Role**: Manages templates and processes placeholders for AI context.

- **Class**: `TemplateProcessor`
- **Key Methods**:
  - `__init__(project_dir, templates_dir, file_handler)`: Initializes with project and template directories, copies templates from `templates_source_folder` (from `config.json`). If the folder is missing or invalid, logs an error and falls back to an empty `templates/` directory.
  - `create_template(name, content)`: Creates a new `.txt` template file.
  - `fill_template(template_name, current_file, project_name, task)`: Fills templates with dynamic placeholder values.
  - `list_templates()`: Lists available `.txt` templates in `templates/`.
  - `_get_json_file_contents()`: Generates JSON-formatted file contents for templates.
  - `_replace_placeholders(template, current_file, project_name, task)`: Replaces placeholders like `{{project_name}}`, `{{task}}`, etc.
- **Supported Placeholders**:
  - `{{project_name}}`: Project name from `project.json`.
  - `{{task}}`: User-specified task description.
  - `{{current_file}}`: Contents of the currently loaded file(s).
  - `{{current_file_name}}`: Names of loaded file(s).
  - `{{file:path}}`: Contents of a specific file.
  - `{{folder_schema:paths}}`: Directory/file structure for specified paths.
  - `{{files_no_descriptions}}`: List of project files without descriptions.
  - `{{files_with_short_descriptions}}`: Project files with short descriptions from `project.json`.
  - `{{files_with_detailed_descriptions}}`: Project files with detailed descriptions from `project.json`.
  - `{{file_contents}}`: Contents of all loaded files.
  - `{{json_file_contents}}`: JSON-formatted list of loaded files with `filename`, `language`, and `content`.
- **Features**:
  - Copies templates from `templates_source_folder` (defined in `config.json`) during initialization.
  - Falls back to a default template if the specified template is missing.
  - Generates JSON-formatted file contents for structured AI prompts.
  - Supports relative file paths in placeholders for consistency.
- **Dependencies**: `os`, `pathlib`, `re`, `typing`, `json`, `shutil`.

## Configuration Files

### 1. `templates/main.txt`
- **Purpose**: Primary template for structured AI prompts, requiring JSON-formatted responses with file contents and optional descriptions.
- **Content**:
  ```
**[PROJECT NAME]**
{{project_name}}

**[TASK]**
{{task}}

**[PROJECT FILE LIST]**
{{files_with_short_descriptions}}

**[FILE CONTENTS]**
{{json_file_contents}}

**[FORMAT SPEC]**
- You are a code generator tasked with modifying or creating files to implement the specified features.
- Output a structured JSON array:
  ```json
  [
    {
      "filename": "<filename>",
      "language": "<language>",
      "short": "<summary>",
      "detailed": "<longer description>",
      "content": "..."
    }
  ]
  ```
- "content": The file’s complete code as a string, with special characters (e.g., quotes, newlines) properly escaped to ensure valid JSON. 
  ```
- **Usage**: Used by `gen` command to structure AI prompts, ensuring consistent JSON responses.

### 2. `models.json`
- **Purpose**: Configures AI models for `ModelManager`.
- **Structure**:
  ```json
  {
    "models": [
      {
        "provider": "ollama",
        "name": "qwen2:1.5b",
        "endpoint": "http://127.0.0.1:11434",
        "system_prompt": "You are a helpful AI assistant. Provide concise JSON-formatted code and descriptions.",
        "size": 1.5,
        "parameters": {
          "think": true,
          "temperature": 0.6,
          "top_k": 20,
          "top_p": 0.95,
          "max_tokens": 16000
        },
        "pricing": {
          "input_tokens": 0.01,
          "output_tokens": 0.02
        }
      },
      {
        "provider": "fake",
        "name": "fake_model",
        "endpoint": "",
        "system_prompt": "Simulate AI response.",
        "size": 0,
        "parameters": {
          "think": false
        },
        "pricing": {
          "input_tokens": 0.0,
          "output_tokens": 0.0
        }
      }
    ]
  }
  ```
- **New Features**:
  - Added `size` field to indicate model size (e.g., 1.5 for memory requirements).
  - Added `parameters.think` (boolean) for Ollama models to enable advanced reasoning.
  - Updated `parameters` to include `temperature`, `top_k`, `top_p`, and `max_tokens` for fine-grained control.
- **Usage**: Loaded by `PoorAI` to configure AI models, with `think` enabling deeper reasoning for Ollama.

### 3. `config.json`
- **Purpose**: Configures application settings.
- **Structure**:
  ```json
  {
    "display_app": "notepad",
    "display_request_response": true,
    "templates_source_folder": "template_sources"
  }
  ```
- **Usage**: Specifies the display app for `ModelManager`, controls request/response display, and defines the source folder for templates.

### 4. `project.json` (Dynamic)
- **Purpose**: Tracks project files and metadata.
- **Structure**:
  ```json
  {
    "project_name": "My New Project",
    "files": [
      {
        "name": "src/main.py",
        "language": "python",
        "short": "Main game loop",
        "detailed": "Implements core game loop for SimCity-inspired game."
      }
    ]
  }
  ```
- **Usage**: Updated by `FileHandler` during file operations, storing file paths, languages, and descriptions. The `project_name` is set when initializing a new project (e.g., derived from the `--project-folder` basename if not specified) or updated via a `project set-name <name>` command.

## Component Interactions

### Data Flow
1. **User Input** (`poor_ai.py`): Parses CLI commands (e.g., `gen`, `load`).
2. **Prompt Processing** (`PromptProcessor`): Builds AI context using `TemplateProcessor`.
3. **Template Processing** (`TemplateProcessor`): Fills placeholders with data from `FileHandler`.
4. **AI Interaction** (`ModelManager`): Sends prompts to the AI, leveraging `think` for Ollama models.
5. **Response Processing** (`ResponseProcessor`): Extracts JSON-formatted file contents and descriptions.
6. **File Operations** (`FileHandler`): Applies changes, updates `project.json`, and manages file metadata.

### Dependencies
- **PromptProcessor**: Requires `TemplateProcessor`, `FileHandler`.
- **TemplateProcessor**: Uses `FileHandler` for file/project data, `config.json` for `templates_source_folder`.
- **ModelManager**: Uses `models.json`, `config.json`, and `requests` for API calls.
- **ResponseProcessor**: Independent, used by `FileHandler`.
- **FileHandler**: Interacts with `TemplateProcessor` for project metadata.

### Control Flow
1. CLI parses commands and routes to `PromptProcessor.process_prompt`.
2. `PromptProcessor` calls `TemplateProcessor.fill_template(template_name, current_file, project_name, task)` with the current file contents, project name, and task description.
3. `TemplateProcessor` fetches data from `FileHandler` and copies templates from `templates_source_folder`.
4. `ModelManager` sends prompts to the AI, using `think` for Ollama if enabled.
5. `ResponseProcessor.extract_code` processes the response into structured data.
6. `FileHandler.apply_result` applies the extracted content or diffs.

## Setup Instructions

### Requirements
- **Python**: 3.8+.
- **Dependencies**:
  ```plaintext
  openai
  pytest
  requests
  ```
  Install via:
  ```bash
  pip install -r requirements.txt
  ```
- **Environment**: Set `OPENROUTER_API_KEY` for OpenRouter models, read by `ModelManager` for API request headers.
- **AI Model**: Requires Ollama (local) with `think`-capable endpoint, OpenRouter (API), or fake provider.

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
   pip install -r requirements.txt
   ```
4. Configure `models.json` and `config.json` (set `templates_source_folder`).
5. Run the tool:
   ```bash
   python poor_ai.py --project-folder ./my_project
   ```

## Usage Examples

### 1. Setting the Project Name
```bash
project set-name "SimCity Game"
```
- Updates the `project_name` in `project.json` to "SimCity Game".

### 2. Generating Code
```bash
load src/*.py
task "Implement a game loop for SimCity"
template use main
gen
```
- Loads Python files, sets the task, uses `main.txt`, and generates a JSON response:
  ```json
  [
    {
      "filename": "src/main.py",
      "language": "python",
      "short": "Game loop",
      "detailed": "Core loop for SimCity game",
      "content": "def game_loop():\n    print('Running SimCity')"
    }
  ]
  ```

### 3. Managing Project Metadata
```bash
load src/main.py
save
```
- Loads `src/main.py`, saves changes, and updates `project.json` with file metadata.

### 4. Using a Custom Template
```bash
template new custom
template use custom
gen "Add a new feature"
```
- Creates and uses a custom template, generating JSON-formatted AI responses.

## Notes
- **Context Size**: Keep descriptions concise in `project.json` to optimize for weaker AI models.
- **Extensibility**: Add new providers in `models.json`, placeholders in `TemplateProcessor`, or templates in `templates/`.
- **Logging**: Check `poor_ai.log`, `file_handler.log`, and `response_processor.log` for debugging.
- **Testing**: Use `pytest` in a `tests/` directory to validate functionality.
- **Ollama `think` Parameter**: Enable for complex tasks requiring deeper reasoning, but note increased response time.