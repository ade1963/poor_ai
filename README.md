# Poor AI Programming Tool

A lightweight, console-based Python application designed to streamline development workflows by integrating AI-driven code generation with robust project management. Optimized for systems with limited resources, it offers a modular architecture, a flexible template system, and seamless project tracking, making AI-assisted coding accessible and efficient.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **Console-Based Interface**: A universal text-based CLI that runs on virtually any system.
- **Multi-File Operations**: Load, edit, and save multiple files at once with wildcard support (e.g., `load src/*.py`).
- **Advanced Templating**: Use dynamic placeholders (`{{task}}`, `{{file_contents}}`, etc.) to build precise, context-aware prompts for the AI.
- **Smart Project Tracking**: All project files, metadata, and descriptions are tracked in a central `project.json` file.
- **Multi-Provider AI Support**: Seamlessly switch between AI providers like local Ollama models, cloud-based OpenRouter models, or a 'fake' provider for offline work and testing.
- **Robust File Handling**: Includes automatic change detection, directory creation, and the ability to apply AI-generated diff patches.
- **Intelligent Response Parsing**: Automatically extracts structured data (files, code, descriptions) from AI responses, with smart fallbacks for various formats.
- **Comprehensive Logging**: Detailed logs for all major operations, ensuring full traceability and easier debugging.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- An API key for OpenRouter (if used), set as an environment variable: `OPENROUTER_API_KEY`
- A running Ollama instance (if used)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/poor-ai-programming-tool.git
    cd poor-ai-programming-tool
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the tool:**
    -   Copy `models.json.example` to `models.json` and configure your desired AI models.
    -   Copy `config.json.example` to `config.json` and adjust settings like the text editor for viewing requests.

### Running the Tool

To start the application, point it to a project folder. If the folder doesn't exist, the tool will help you create it.

```bash
python poor_ai.py --project-folder /path/to/your/project
```

You will now be in the interactive CLI.

## Usage

The tool operates through a simple set of commands in its interactive console.

### Basic Workflow

1.  **Load files**: Load the files you want the AI to work on.
    ```
    > load src/main.py src/utils.py
    ```
    Or use wildcards:
    ```
    > load src/*.py
    ```

2.  **Define the task**: Describe what you want the AI to do. You can enter multi-line text; type `END` on a new line to finish.
    ```
    > task
    Please add a function to utils.py called 'calculate_sum' that takes a list of numbers and returns their sum. Then, import and call this function in main.py.
    END
    ```

3.  **Generate code**: Run the generation command. The tool will build a prompt, send it to the AI, and apply the response.
    ```
    > gen
    ```

4.  **Save changes**: If you are satisfied with the changes, save them to disk.
    ```
    > save
    ```

### Advanced. Generate project from dev guide.

1.  **Create custom dev guide**: Edit file from 'docs/' folder, let it be `DevGuide_v1.2.md` with new features. 

2.  **Create empty project**:
    ```
    python poor_ai.py --project-folder <new_folder>
    ```

    - Overwrite `<new_folder>/models.json` with your version of `models.json`
    - Copy dev guide into `<new_folder>/DevGuide_v1.2.md`
    
3.  **Generate project**:
    ```
    > project set-name Poor AI Programming Tool v 1.2
    > model list
    > model use 1
    > template use guide
    > load DevGuide_v1.2.md
    > context show
    > gen
    > save 
    ```

3.  **Update project files**:
    ```
    > clear
    > template use main
    > load poor_ai.py core/model_manager.py
    > task Fix error: ....
    > context show
    > gen
    > save 
    ```

### All Commands

| Command                               | Description                                                                 |
| ------------------------------------- | --------------------------------------------------------------------------- |
| `load <files...>`                     | Load one or more files into the context (wildcards supported).              |
| `save`                                | Save changes from the buffer to the actual files.                           |
| `clear`                               | Clear all loaded files from the buffer.                                     |
| `task <description>`                  | Set the task for the AI. Use `task` alone for multi-line input.             |
| `gen`                                 | Generate code based on the current context, files, and task.                |
| `context show`                        | Display the exact prompt that will be sent to the AI.                       |
| `template list/use/show/new/edit`     | Manage prompt templates.                                                    |
| `model list/use <name_or_index>`      | List available AI models or switch the active one.                          |
| `project set-name <new_name>`         | Set the project's name in `project.json`.                                   |
| `test`                                | Run `pytest` in the `tests/` directory.                                     |
| `version`                             | Show the application's version.                                             |
| `help`                                | Show the help message.                                                      |
| `exit` / `quit`                       | Exit the application.                                                       |


## Poor Bench
`poor_bench` is a Python-based benchmarking framework designed to create, manage, and evaluate tests for Large Language Models (LLMs). It allows developers to define test classes with customizable prompt templates, generate tests across multiple difficulty levels, and evaluate results using modular evaluation components. The framework supports tailored prompts per LLM, initial test validation, and bulk test execution, with results scored on a 0.0 to 1.0 scale. Optimized for constrained systems, it operates as a standalone module within the `poor_ai` ecosystem, focusing on catching potential LLM issues early in development.

Check out the sample model comparison chart:
![Model Comparison: Average Score](poor_bench/images/llm_scores.png)


## Contributing

Contributions are welcome! If you have suggestions for improvements or want to add new features, please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/YourFeature`).
5.  Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
