# Poor AI Programming Tool

## Introduction

The "Poor AI Programming Tool" is a lightweight, console-based Python application designed to help programmers leverage AI models, particularly local or less powerful ones, for coding tasks. It focuses on single-file operations but uses a flexible **template system** and **component descriptions** to provide richer context to the AI, improving the quality of generated code and fixes.

Developed with efficiency in mind, it aims to be a practical assistant without requiring high-end hardware.

## Features

*   **Console Interface**: Simple, text-based operation via terminal.
*   **AI Interaction**: Generate code (`gen`) or apply fixes (`fix`) using configured AI models.
*   **Model Agnostic**: Supports multiple AI model providers (Ollama, OpenRouter) via `models.json`.
*   **Single-File Focus**: Operates on one file at a time, keeping interactions simple.
*   **Template System**: Define custom templates (`templates/*.txt`) to structure the context sent to the AI, including:
    *   File contents (`{{file:path}}`)
    *   Folder structures (`{{folder_schema:paths}}`)
    *   Current file content (`{{current_file}}`) and name (`{{current_file_name}}`)
    *   Component descriptions (`{{desc_short:path}}`, `{{current_desc_long}}`, etc.)
    *   User prompts (`{{prompt}}`)
*   **Component Descriptions**: Associate short, long, and detailed descriptions with files (`<filename>.desc.md`) to provide deeper context within templates.
*   **Context Preview**: View the exact context that will be sent to the AI (`context show`).
*   **Model Management**: List available models and switch between them (`model list`, `model <name>`).
*   **Testing**: Includes a command to run integrated tests (`test`).
*   **Request/Response Display**: Optionally display the full request and response in a configured editor for debugging (`config.json`).

## Getting Started

### Prerequisites

*   Python 3.8+
*   Access to an AI model endpoint (e.g., a running Ollama instance or an OpenRouter API key).
*   Git (for cloning)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd poor-ai-programming-tool
    ```

2.  **Install dependencies:**
    *   Create a `requirements.txt` file with the following content:
        ```
        openai
        pytest
        ```
    *   Install using pip:
        ```bash
        pip install -r requirements.txt
        ```

3.  **Configure Models:**
    *   Edit `models.json` to define the AI models you want to use.
    *   Ensure the `endpoint` is correct for your setup (e.g., `http://127.0.0.1:11434/v1` for local Ollama).
    *   For providers like OpenRouter, add `"api_key_env_var": "YOUR_ENV_VAR_NAME"` to the model definition and set the corresponding environment variable:
        ```bash
        # Linux/macOS
        export YOUR_ENV_VAR_NAME='your_api_key_here'
        # Windows CMD
        set YOUR_ENV_VAR_NAME=your_api_key_here
        # Windows PowerShell
        $env:YOUR_ENV_VAR_NAME="your_api_key_here"
        ```

4.  **Configure Application (Optional):**
    *   Edit `config.json` in the root directory to customize behavior:
        ```json
        {
          "display_app": "code", // Editor to show request/response (e.g., "notepad", "gedit", "code")
          "display_request_response": true // Set to true to automatically show API calls in the editor
        }
        ```
        *(If `config.json` doesn't exist, defaults will be used, and request/response won't be displayed automatically)*

### Running the Tool

```bash
python poor_ai.py
```

This will start the interactive console. Logs are stored in the `logs/` directory.

## Usage

The tool operates via commands entered at its prompt: `[current_file] (Current Model)>`

**Basic Workflow:**

1.  **Select a model:** `model <model_name>` (e.g., `model gemma3:1b-it-qat`)
2.  **Load a file:** `load path/to/your/code.py`
3.  **(Optional) Select a template:** `template use <template_name>` (defaults to `default`)
4.  **(Optional) Create/Edit descriptions:** `desc new path/to/your/code.py`, then `desc edit path/to/your/code.py`
5.  **Generate or fix code:**
    *   `gen write a function that adds two numbers`
    *   `fix the loop condition is wrong`
6.  **Review changes:** The modified code is held in memory.
7.  **Save changes:** `save`

**Key Commands:**

*   `load <file_path>`: Load a file.
*   `save`: Save changes to the loaded file.
*   `gen <task>`: Generate code based on the task.
*   `fix <issue>`: Fix an issue in the code.
*   `template list | use <name> | new <name> | edit <name> | show [name]`: Manage templates.
*   `context show`: Preview the context sent to the AI.
*   `desc new <file> | edit <file> | view <file> <type>`: Manage descriptions (`type` is `short`, `long`, or `detailed`).
*   `model list | <name>`: List or switch AI models.
*   `test`: Run project tests using pytest.
*   `help`: Show available commands.
*   `exit`: Quit the tool.

## Templates

Templates are stored in the `templates/` directory as `.txt` files. They use `{{placeholder}}` syntax to build context. See `docs/Poor AI Programming Tool Documentation.markdown` for details on placeholders.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

*(Specify License Here - e.g., MIT License)* - Currently unlicensed.
