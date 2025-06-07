# Poor AI Programming Tool Documentation

## Introduction

The "Poor AI Programming Tool" is a lightweight, console-based solution designed for programmers to leverage artificial intelligence, even on systems with weaker AI models. Named "poor" to reflect its compatibility with less powerful setups, it is developed using advanced AI models to ensure intelligence and efficiency. The tool delivers practical programming assistance without requiring high-end computational resources, making it accessible to a wide range of users.

It features a text-based interface that processes concise prompts to minimize context size, critical for weaker models. The tool focuses on single-file operations but introduces a **template system** to gather multi-file context, enhancing AI interactions. Additionally, it now includes a **project tracking feature** that allows users to associate short, long, and detailed descriptions with project components (code and artifacts), stored in markdown files and integrated into the template system for richer context. With a smart testing framework and a minimum viable product (MVP) achievable in days, this documentation provides a comprehensive guide to its development and use.

## Features

The Poor AI Programming Tool offers the following key features, designed for efficiency and adaptability:

- **Console Mode (Phase 1)**: A text-based application operable via terminal or command prompt, ensuring simplicity and broad compatibility.
- **Short Prompts**: Uses brief, focused prompts to reduce context size, enabling faster processing on weaker AI models.
- **Model-Specific Prompt Tuning**: Includes a dynamic testing suite that adjusts prompts for local AI models, supported by a database of models and optimized prompts.
- **Single-File Focus**: Processes one file at a time for streamlined operations, integrating easily into existing workflows.
- **Template System**: Allows users to create and use customizable templates to gather project context, including file contents, folder structures, user prompts, and now component descriptions, for richer AI interactions.
- **Project Tracking with Component Descriptions**: Enables users to add short, long, and detailed descriptions to project components, stored in markdown files, to provide clear context for both human and AI coders.
- **Compact and Rapid Deployment**: Maintains a lean codebase to deliver an MVP within days, balancing functionality with speed.
- **Smart Testing Framework**: Validates functionality and refines prompts using a scoring mechanism, ensuring optimal performance across diverse models.

## Architecture

The tool’s modular, resource-efficient architecture is tailored for limited systems. Its key components are:

- **Console Interface**: A command-line interface (CLI) built with lightweight libraries, accepting short prompts and displaying results in real-time.
- **Prompt Processor**: Interprets concise user inputs and converts them into actionable tasks (e.g., code generation, debugging), incorporating a natural language parser.
- **Model Manager**: Manages interactions with local AI models via a configuration file or lightweight database, mapping models to tuned prompts.
- **File Handler**: Handles file operations—loading, editing, and saving—optimized for single-file workflows with minimal memory overhead.
- **Template Processor**: Manages template creation, editing, and filling, replacing placeholders (e.g., file contents, folder structures, component descriptions) to generate context.
- **Testing Suite**: An embedded framework that runs predefined tests, adapts prompts dynamically, and scores prompt effectiveness per model.

This modular design supports independent development and testing of components, accelerating the MVP timeline and enabling scalability.

## Template System

The template system enhances the tool by allowing users to define structured context for projects, particularly those with multiple files. Templates are editable text files that combine placeholders, constant strings, user prompts, and now component descriptions to create a cohesive context for AI interactions.

### Key Features

- **Customizable Templates**: Users can create and edit templates to define how context is gathered.
- **Placeholders**: Support for:
  - `{{file:path}}`: Inserts the contents of a specified file (e.g., `./main.py`).
  - `{{folder_schema:paths}}`: Lists files or directory contents for specified paths (e.g., `./env,./main.py`).
  - `{{prompt}}`: Inserts the user’s command or task (e.g., “add a function”).
  - `{{current_file}}`: Inserts the contents of the currently loaded file.
  - `{{current_file_name}}`: Inserts the name of the currently loaded file.
  - `{{desc_short:path}}`: Inserts the short description of the file at `path`.
  - `{{desc_long:path}}`: Inserts the long description of the file at `path`.
  - `{{desc_detailed:path}}`: Inserts the detailed description of the file at `path`.
  - `{{current_desc_short}}`: Inserts the short description of the current file.
  - `{{current_desc_long}}`: Inserts the long description of the current file.
  - `{{current_desc_detailed}}`: Inserts the detailed description of the current file.
- **Context Generation**: A “Fill context” action replaces placeholders with actual content, including descriptions, creating a complete context for AI use or external sharing.
- **Integration**: Templates enhance commands like `gen <task>` by providing multi-file context and descriptive metadata while maintaining single-file operations.

### Example Template

```
Project structure:
{{folder_schema:./}}

Main file:
{{file:./main.py}}

Description:
{{desc_short:./main.py}}

Task: {{prompt}}
```

When filled with a project containing `./main.py` and `./env/config.txt`, a description file `./main.py.desc.md`, and a prompt “add a function,” the output might be:

```
Project structure:
- ./main.py
- ./env/config.txt

Main file:
```python
def hello():
    print("Hello, world!")
```

Description:
This is the main entry point of the application.

Task: add a function
```

## Component Descriptions

Component descriptions provide additional context for project components, making the project clearer for both human and AI coders. Each component (e.g., a code file) can have an associated description file named `<component>.desc.md`, containing short, long, and detailed descriptions.

### Format

Description files are markdown files with the following structure:

```markdown
<!-- SHORT -->
Short description here.

<!-- LONG -->
Long description here.

<!-- DETAILED -->
Detailed description here.
```

For example, for `main.py`:

```markdown
<!-- SHORT -->
This is the main entry point of the application.

<!-- LONG -->
This file contains the main function that initializes the application and handles user input.

<!-- DETAILED -->
The main function sets up the environment, parses command-line arguments, and calls appropriate handlers based on user input.
```

### Usage

- **Manage Descriptions**:
  - `desc new <file>`: Create a new description file for `<file>`.
  - `desc edit <file>`: Edit the description file for `<file>`.
  - `desc view <file> [short|long|detailed]`: View the specified description for `<file>`.
- **Integration with Templates**: Use placeholders like `{{desc_short:path}}` in templates to include descriptions in the context.

## Testing

Testing ensures reliability and model-specific optimization. The strategy includes:

- **Functional Testing**: Validates core features, including description handling and template processing.
- **Model Compatibility Testing**: Evaluates performance across local AI models.
- **Prompt Optimization**: Tests prompt variations, scoring them for accuracy and speed.
- **Description Testing**: Verifies correct parsing and inclusion of descriptions in templates.
- **Performance Benchmarking**: Measures response times and resource usage.
- **Stress Testing**: Simulates edge cases, such as missing description files.

The testing framework should be developed early to guide prompt tuning and validate functionality, including the new description features.

## Development Plan

The MVP, including the new description feature, is achievable in 10 days:

1. **Day 1: Project Setup**
   - Initialize repository and environment.
   - Outline CLI and template storage.
2. **Days 2-3: Testing Framework**
   - Build testing suite with description-focused tests.
   - Create prompt scoring system.
3. **Days 4-5: Core Features**
   - Implement Prompt Processor, File Handler, and Template Processor with description support.
4. **Days 6-7: Model Integration**
   - Code Model Manager with mock AI.
   - Set up model-prompt database.
5. **Days 8-9: Polish and Test**
   - Integrate components and run tests.
   - Finalize documentation.
6. **Day 10: MVP Release**
   - Conduct final review and distribute.

## Usage

### Installation
- Download and install dependencies (`pip install -r requirements.txt`).

### Configuration
- Run: `./poor_ai`.
- Select a local AI model.

### Commands
- **File Operations**:
  - `load <file>`: Open a file.
  - `save`: Save changes.
- **AI Tasks**:
  - `gen <task>`: Generate code with template context.
  - `fix <issue>`: Debug code.
- **Template Management**:
  - `template new <name>`: Create template.
  - `template edit <name>`: Edit template.
  - `template list`: List templates.
  - `template use <name>`: Select template.
  - `context show`: Display filled context.
- **Description Management**:
  - `desc new <file>`: Create description file.
  - `desc edit <file>`: Edit description file.
  - `desc view <file> [short|long|detailed]`: View description.
- **Testing**:
  - `test`: Run tests.
- **Utility**:
  - `model <name>`: Switch models.
  - `help`: View commands.

### Tips
- Use short descriptions for quick tasks, detailed for complex ones.
- Keep descriptions concise to manage context size.
- Verify context with `context show` before AI commands.

## Future Enhancements

- **Directory Descriptions**: Extend descriptions to folders.
- **GUI Option**: Add a lightweight interface.
- **Multi-File Support**: Handle small projects natively.
- **Prompt Auto-Learning**: Improve prompts from feedback.
- **API Integration**: Connect to external AI services.
- **Plugins**: Enable custom features.