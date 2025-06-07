#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from core.file_handler import FileHandler
from core.prompt_processor import PromptProcessor
from core.model_manager import ModelManager
from core.template_processor import TemplateProcessor
from core.response_processor import extract_code
from datetime import datetime
import shutil
import uuid

class PoorAI:
    VERSION = "1.0.0"

    def __init__(self, project_folder: str = "."):
        self.project_folder = Path(project_folder).resolve()
        self.project_name = None
        self.file_handler = FileHandler(self.project_folder)
        self.template_processor = TemplateProcessor(project_dir=self.project_folder, templates_dir=self.project_folder / "templates", file_handler=self.file_handler)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing PoorAI")
        self._validate_project_structure()
        self.prompt_processor = PromptProcessor(self.template_processor, self.file_handler)
        self.model_manager = ModelManager()
        self.models_config = self.load_models_config()
        self.current_model = None
        self.current_template = "main"  # Changed from "default" to "main" since default.txt is no longer created
        self.current_task = None

    def _setup_logging(self):
        """Set up logging with rotating file handler."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = RotatingFileHandler(
                'poor_ai.log',
                maxBytes=10*1024*1024,
                backupCount=5
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    def _validate_project_structure(self):
        """Validate project folder structure and create missing components if confirmed."""
        templates_dir = self.project_folder / "templates"
        project_json = self.project_folder / "project.json"
        logs_dir = self.project_folder / "logs"

        if not self.project_folder.exists():
            print(f"Project folder '{self.project_folder}' does not exist.")
            self.project_name = input("Enter project name: ").strip()
            if not self.project_name:
                print("Error: Project name cannot be empty.")
                sys.exit(1)
            if self._confirm_create("Create project folder?"):
                self.project_folder.mkdir(parents=True)
                # Copy all .txt files from template_sources to templates directory
                template_source_dir = Path(__file__).parent / "template_sources"
                if template_source_dir.exists() and template_source_dir.is_dir():
                    templates_dir.mkdir(exist_ok=True)
                    for item in template_source_dir.glob('*.txt'):
                        shutil.copy2(item, templates_dir / item.name)
                        print(f"Copied template: {item.name} to {templates_dir}")
                else:
                    print(f"Warning: template_sources directory '{template_source_dir}' does not exist.")
            else:
                print("Project folder is required. Exiting.")
                sys.exit(1)

        if not templates_dir.exists() or not any(templates_dir.glob("*.txt")):
            print(f"Templates directory '{templates_dir}' is missing or contains no .txt files.")
            if self._confirm_create("Create templates directory and copy templates from template_sources?"):
                templates_dir.mkdir(exist_ok=True)
                template_source_dir = Path(__file__).parent / "template_sources"
                if template_source_dir.exists() and template_source_dir.is_dir():
                    for item in template_source_dir.glob('*.txt'):
                        shutil.copy2(item, templates_dir / item.name)
                        print(f"Copied template: {item.name} to {templates_dir}")
                else:
                    print(f"Warning: template_sources directory '{template_source_dir}' does not exist.")
                    print("Templates directory created but no templates copied.")
            else:
                print("Templates directory with at least one template is required. Exiting.")
                sys.exit(1)

        if not project_json.exists():
            print(f"project.json not found at '{project_json}'.")
            if not self.project_name:
                self.project_name = input("Enter project name: ").strip()
                if not self.project_name:
                    print("Error: Project name cannot be empty.")
                    sys.exit(1)
            with open(project_json, 'w', encoding='utf-8') as f:
                json.dump({
                    "project_name": self.project_name,
                    "files": []
                }, f, indent=2)
            print(f"Created project.json at {project_json}")
        else:
            with open(project_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.project_name = data.get("project_name", "Unnamed Project")  # Fallback, should not be reached

        logs_dir.mkdir(exist_ok=True)

    def _confirm_create(self, message: str) -> bool:
        """Prompt user for confirmation to create missing components."""
        response = input(f"{message} [y/N]: ").strip().lower()
        return response == 'y'

    def load_models_config(self):
        """Load models configuration from models.json."""
        try:
            config_path_script = Path(__file__).parent / "models.json"
            config_path_project = self.project_folder / "models.json"
    
            if config_path_project.exists():
                config_path = config_path_project
            elif config_path_script.exists():
                config_path = config_path_script
            else:
                print(f"Error: models.json not found in {self.project_folder} or {Path(__file__).parent}")
                sys.exit(1)
    
            with open(config_path, "r", encoding='utf-8') as f:
                print(f"Loading models from: {config_path}")
                return json.load(f)["models"]
        except FileNotFoundError:
            print("Error: models.json not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {config_path}.")
            sys.exit(1)
        except KeyError:
            print(f"Error: 'models' key not found in {config_path}.")
            sys.exit(1)

    def initialize_model_manager(self, model_name=None):
        """Initialize ModelManager with the specified model or default."""
        if not self.models_config:
            print("Error: No models configured in models.json.")
            self.models_config = self.load_models_config()
            if not self.models_config:
                sys.exit(1)

        if model_name:
            if not self.model_manager.set_model(model_name):
                print(f"Error: Model '{model_name}' not found or failed to set.")
                if self.current_model:
                    print(f"Keeping previously selected model: {self.current_model}")
                else:
                    print("No model is currently selected.")
                return
        elif not self.current_model:
            if self.models_config:
                default_model_name = self.models_config[0]["name"]
                print(f"No model specified, defaulting to first model: {default_model_name}")
                if not self.model_manager.set_model(default_model_name):
                    print(f"Error: Failed to set default model '{default_model_name}'.")
                    sys.exit(1)
                self.current_model = default_model_name
            else:
                print("Error: Cannot set default model, models_config is empty.")
                sys.exit(1)

        if model_name and self.model_manager.get_current_model() and self.model_manager.get_current_model()['name'] == model_name:
            self.current_model = model_name

        active_model_info = self.model_manager.get_current_model()
        if active_model_info:
            print(f"Using model: {active_model_info['name']}")
        else:
            print("Warning: No model is active after initialization attempt.")

    def _save_request_response(self, prompt_data: dict, raw_result: str, token_info: dict, cost: float):
        """Save request-response pair to logs directory."""
        try:
            logs_dir = self.project_folder / "logs"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = logs_dir / f"request_{timestamp}_{uuid.uuid4().hex[:8]}.txt"
            
            model_info = self.model_manager.get_current_model()
            header = f"""Model: {model_info['name']}
Provider: {model_info['provider']}
Prompt Tokens: {token_info.get('prompt_tokens', 'N/A')}
Completion Tokens: {token_info.get('completion_tokens', 'N/A')}
Total Cost: ${cost:.6f}
System Prompt: {model_info.get('system_prompt', 'None')}
Temperature: {model_info.get('temperature', 'N/A')}
Top P: {model_info.get('top_p', 'N/A')}
Max Tokens: {model_info.get('max_tokens', 'N/A')}
Timestamp: {timestamp}

"""
            header = header + f"""Request:
{prompt_data['context']}

"""
            header = header + f"""Response:
{raw_result}
"""
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(header)
            self.logger.info(f"Saved request-response to {log_file}")
        except Exception as e:
            self.logger.error(f"Error saving request-response: {e}")
            print(f"Error saving request-response: {e}")

    def run(self):
        """Run the CLI loop."""
        parser = argparse.ArgumentParser(description=f"Poor AI Programming Tool v{PoorAI.VERSION}")
        parser.add_argument("initial_command", nargs="*", help="Initial command to execute (optional)")
        parser.add_argument("--project-folder", default=".", help="Path to the project folder")
        args = parser.parse_args()

        self.initialize_model_manager()

        if args.initial_command:
            initial_command_str = " ".join(args.initial_command)
            print(f"Executing initial command: {initial_command_str}")
            self.process_command(initial_command_str)

        print(f"Poor AI Programming Tool v{PoorAI.VERSION}. Type 'help' for commands, 'exit' to quit.")
        while True:
            try:
                current_file_display = ""
                if hasattr(self.file_handler, 'current_files'):
                    current_file_display = f" [{', '.join(Path(f).name for f in self.file_handler.current_files)}]" if self.file_handler.current_files else ""
                else:
                    print("Warning: FileHandler is missing current_files attribute.")
                    current_file_display = ""

                current_model_display = f" ({self.current_model})" if self.current_model else " (No Model)"
                prompt_text = f"{current_file_display}{current_model_display}> "

                command = input(prompt_text).strip()
                if not command:
                    continue
                if command.lower() == 'exit':
                    print("Exiting...")
                    break
                self.process_command(command)
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except EOFError:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                import traceback
                traceback.print_exc()

    def process_command(self, command):
        """Process a single command."""
        parts = command.split(maxsplit=1)
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "load":
            if not args:
                print("Usage: load <file_path[,file_path,...]> (supports wildcards)")
                return
            file_paths = args
            if self.file_handler.load_file(file_paths):
                print(f"Loaded: {', '.join(self.file_handler.current_files)}")
            else:
                print(f"Error: Failed to load some or all files: {file_paths}")

        elif cmd == "save":
            if not hasattr(self.file_handler, 'current_files') or not self.file_handler.current_files:
                print("Error: No files loaded to save.")
                return
            if self.file_handler.save_file():
                print(f"Saved changed files: {', '.join(self.file_handler.current_files)}")
                # Check for any descriptions stored from the last 'gen' command and update project.json
                if hasattr(self, 'last_descriptions') and self.last_descriptions:
                    self._update_project_descriptions(self.last_descriptions)
                    print("Updated project.json with descriptions from last generation.")
            else:
                print("Error: Failed to save files.")

        elif cmd == "clear":
            if hasattr(self.file_handler, 'clear'):
                self.file_handler.clear()
            else:
                print("Error: Clear command not supported by this FileHandler version.")

        elif cmd == "gen":
            self.logger.info(f"Processing command: {cmd}")
            if not self.current_model:
                print("Error: No model selected. Use 'model index|<name>' first.")
                return
            if not self.current_task:
                print("Error: No task set. Use 'task <description>' first.")
                return

            print(f"Processing 'gen' task with template '{self.current_template}'...")

            prompt_data = self.prompt_processor.process_prompt(
                f"gen {self.current_task}",
                None,
                self.project_name,
                self.current_template
            )

            if prompt_data["command_type"] != 'unknown':
                print("Sending request to model...")
                raw_result = self.model_manager.generate(prompt_data["context"])
                if raw_result:
                    self.logger.info("Received raw response from model")
                    self.logger.debug(f"Raw response content:\n{raw_result[:500]}...")
                    print("Processing model response...")
                    processed_result = extract_code(raw_result)
                    self.logger.info(f"Parsed response into {len(processed_result)} file-content pairs")
                    self.logger.debug(f"Processed result: {processed_result}")

                    token_info = {'prompt_tokens': 'N/A', 'completion_tokens': 'N/A'}
                    cost = 0.0
                    if self.model_manager.get_current_model().get('provider') != 'fake':
                        token_info = {'prompt_tokens': len(prompt_data['context'].split()), 'completion_tokens': len(raw_result.split())}
                        if 'pricing' in self.model_manager.get_current_model():
                            pricing = self.model_manager.get_current_model()['pricing']
                            cost = (token_info['prompt_tokens'] * pricing.get('input_tokens', 0) +
                                    token_info['completion_tokens'] * pricing.get('output_tokens', 0)) / 1000000

                    self._save_request_response(prompt_data, raw_result, token_info, cost)

                    descriptions = None
                    filtered_result = []
                    for item in processed_result:
                        if item['filename'] == 'descriptions.json':
                            try:
                                desc_content = json.loads(item['content'])
                                if isinstance(desc_content, list):
                                    descriptions = desc_content
                                else:
                                    print("Warning: descriptions.json content is not a list, skipping.")
                            except json.JSONDecodeError:
                                print("Warning: Invalid JSON in descriptions.json, skipping.")
                                continue
                        else:
                            filtered_result.append(item)

                    # Store descriptions for use in 'save' command
                    self.last_descriptions = descriptions

                    # Only update descriptions if project.json has files
                    project_json = self.project_folder / "project.json"
                    with open(project_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if descriptions and data.get("files", []):
                        self._update_project_descriptions(descriptions)
                        print("Updated descriptions.")

                    if self.file_handler.apply_result(filtered_result):
                        print(f"Task 'gen' completed. Results applied to in-memory buffer.")
                        self.logger.info("Applied processed result to FileHandler buffer")
                        if self.file_handler.current_files:
                            print(f"Modified files: {', '.join(self.file_handler.current_files)}")
                        else:
                            print("No files modified; results stored in buffer.")
                        print("Use 'save' to write changes to disk.")

                    else:
                        print("Error: Could not apply result.")
                else:
                    print(f"Error: Failed to get response from model for 'gen' task.")
            else:
                print(f"Error: Invalid command format for 'gen'.")

        elif cmd == "task":
            if not args:
                print("Usage: task <task description>")
                print("For multiline task, enter task and end with 'END' on a new line.")
                lines = []
                print("Enter task (type 'END' on a new line to finish):")
                while True:
                    line = input()
                    if line.strip().upper() == 'END':
                        break
                    lines.append(line)
                args = '\n'.join(lines)
                if not args.strip():
                    print("Error: Task cannot be empty.")
                    return
            self.current_task = args
            print(f"Task set: {self.current_task}")

        elif cmd == "template":
            if not args:
                print("Usage: template <subcommand> [options]")
                print("Subcommands: new, edit, list, use, show")
                return
            subcmd = args.split()[0].lower()
            t_args = args.split()[1:]

            if subcmd == "new":
                if not t_args:
                    print("Usage: template new <template_name>")
                    return
                template_name = t_args[0]
                if self.template_processor.create_template(template_name):
                    print(f"Template '{template_name}' created at {self.template_processor.templates_dir}. You may want to edit it.")
                else:
                    print(f"Failed to create template '{template_name}'.")

            elif subcmd == "edit":
                if not t_args:
                    print("Usage: template edit <template_name>")
                    return
                template_name = t_args[0]
                self.template_processor.edit_template(template_name)

            elif subcmd == "list":
                templates = self.template_processor.list_templates()
                if templates:
                    print("Available templates:", ", ".join(templates))
                else:
                    print("No templates found in", self.template_processor.templates_dir)

            elif subcmd == "use":
                if not t_args:
                    print("Usage: template use <template_name>")
                    return
                template_name = t_args[0]
                available_templates = self.template_processor.list_templates()
                if template_name in available_templates:
                    self.current_template = template_name
                    print(f"Using template: {template_name}")
                else:
                    print(f"Error: Template '{template_name}' not found in {self.template_processor.templates_dir}.")
                    print(f"Available: {', '.join(available_templates) if available_templates else 'None'}")

            elif subcmd == "show":
                template_to_show = self.current_template
                if t_args:
                    template_to_show = t_args[0]
                template_path = self.template_processor.templates_dir / f"{template_to_show}.txt"
                if template_path.exists():
                    print(f"--- Content of template '{template_to_show}' ---")
                    with open(template_path, 'r', encoding='utf-8') as f:
                        print(f.read())
                    print("--- End of template ---")
                else:
                    print(f"Template '{template_to_show}' not found.")

            else:
                print(f"Unknown template subcommand: {subcmd}. Use 'template list' to see options.")

        elif cmd == "context":
            if args and args.split()[0].lower() == "show":
                if not self.current_template:
                    print("Error: No template selected. Use 'template use <name>'.")
                    return
                if not self.current_task:
                    print("Error: No task set. Use 'task <description>' first.")
                    return

                print(f"--- Context generated using template '{self.current_template}' ---")
                context = self.template_processor.fill_template(
                    self.current_template,
                    None,
                    self.project_name,
                    self.current_task
                )
                print(context)
                print("--- End of context ---")
            else:
                print("Usage: context show")

        elif cmd == "desc":
            if not args:
                print("Usage: desc <subcommand> <file_path> [options]")
                print("Subcommands: new, edit, view")
                return
            subcmd = args.split()[0].lower()
            if len(args.split()) < 2:
                print(f"Usage: desc {subcmd} <file_path> [type]")
                return

            file_path = args.split()[1]
            target_file = self.project_folder / file_path
            if not target_file.exists():
                print(f"Warning: The target file '{file_path}' does not exist. Description commands operate on the .desc.md file.")

            if subcmd == "new":
                self.template_processor.create_description(file_path)

            elif subcmd == "edit":
                self.template_processor.edit_description(file_path)

            elif subcmd == "view":
                if len(args.split()) < 3:
                    print("Usage: desc view <file_path> <short|long|detailed>")
                    return
                desc_type = args.split()[2].lower()
                if desc_type not in ["short", "long", "detailed"]:
                    print("Error: Description type must be one of: short, long, detailed")
                    return

                desc = self.template_processor.view_description(file_path, desc_type)
                if desc is not None:
                    print(f"--- {desc_type.capitalize()} description for '{file_path}' ---")
                    print(desc)
                    print(f"--- End of description ---")

            else:
                print(f"Unknown desc subcommand: {subcmd}. Available: new, edit, view.")

        elif cmd == "test":
            print("Running tests...")
            test_dir = self.project_folder / "tests"
            if not test_dir.exists():
                test_dir = Path("tests")

            if test_dir.exists():
                print(f"Executing pytest in: {test_dir.resolve()}")
                result = os.system(f"{sys.executable} -m pytest {test_dir}")
                if result == 0:
                    print("Tests completed successfully.")
                else:
                    print(f"Tests failed with exit code {result}.")
            else:
                print(f"Error: Test directory not found at expected locations.")

        elif cmd == "model":
            if not args:
                print("Usage: model <model_name | index> | list")
                print(f"Currently selected: {self.current_model if self.current_model else 'None'}")
                return

            subcmd = args.lower()
            if subcmd == "list":
                print("Available Models:")
                if not self.models_config:
                    print(f"  No models loaded. Check models.json.")
                else:
                    for idx, model in enumerate(self.models_config):
                        print(f"  [{idx}] Name:     {model.get('name', 'N/A')}")
                        print(f"      Provider: {model.get('provider', 'N/A')}")
                        print(f"      Endpoint: {model.get('endpoint', 'N/A')}")
                        print("-" * 20)
            else:
                model_identifier = args
                if model_identifier.isdigit():
                    model_index = int(model_identifier)
                    if 0 <= model_index < len(self.models_config):
                        model_name = self.models_config[model_index]['name']
                        self.initialize_model_manager(model_name)
                    else:
                        print(f"Error: Invalid model index '{model_index}'. Use 'model list' to see available models.")
                else:
                    self.initialize_model_manager(model_identifier)

        elif cmd == "version":
            print(f"Poor AI Programming Tool v{PoorAI.VERSION}")

        elif cmd == "help":
            print(f"""
Poor AI Programming Tool v{PoorAI.VERSION} Commands:

File Operations:
  load <file_path[,file_path,...]> Load one or more files into the editor buffer (supports wildcards).
  save                            Save only changed contents to the loaded files.
  clear                           Clear all loaded files from the buffer.

AI Interaction:
  task <task description>        Set the task description to be used for generation (supports multiline with 'END').
  gen                            Generate code based on the stored prompt, using current files and template context.

Template Management:
  template list                   List available templates in the 'templates' directory.
  template use <name>             Set the template to use for 'gen' command.
  template new <name>             Create a new template file.
  template edit <name>            (Simulated) Opens the template file for manual editing.
  template show [name]            Show the content of the current or specified template.

Context & Descriptions:
  context show                    Display the context that would be sent to the AI based on the current files, prompt, and template.
  desc new <file_path>            Create a description file (.desc.md) for the specified file.
  desc edit <file_path>           (Simulated) Opens the description file for manual editing.
  desc view <file> <type>         View the 'short', 'long', or 'detailed' description for a file.

Model Selection:
  model list                      List all models available in models.json with details.
  model index|<name>              Switch the active AI model to the one specified by <name>.

Other:
  test                            Run the project's automated tests using pytest.
  version                         Display the tool version.
  help                            Show this help message.
  exit                            Exit the Poor AI tool.
            """)

        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for a list of commands.")

    def _update_project_descriptions(self, descriptions):
        """Update project.json with descriptions from descriptions.json."""
        try:
            project_json = self.project_folder / "project.json"
            with open(project_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            files = data.get("files", [])
            
            if isinstance(descriptions, list):
                desc_dict = {item['file']: item for item in descriptions if 'file' in item}
            else:
                self.logger.error("Invalid descriptions format: must be a list")
                print("Error: Invalid descriptions format.")
                return

            for file_entry in files:
                file_name = file_entry.get("name")
                if file_name in desc_dict:
                    desc = desc_dict[file_name]
                    file_entry["short"] = desc.get("short", file_entry.get("short", None))
                    file_entry["detailed"] = desc.get("detailed", file_entry.get("detailed", None))
                    file_entry["language"] = desc.get("language", file_entry.get("language", None))
            
            with open(project_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Updated project.json with descriptions and languages")
        except Exception as e:
            print(f"Error updating project.json with descriptions: {e}")
            self.logger.error(f"Error updating project.json with descriptions: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Poor AI Programming Tool v{PoorAI.VERSION}")
    parser.add_argument("--project-folder", default=".", help="Path to the project folder")
    args = parser.parse_args()
    poor_ai = PoorAI(project_folder=args.project_folder)
    poor_ai.run()