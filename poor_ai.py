import argparse
import logging
import os
import sys
import shutil
import subprocess
import json # Added missing import
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from logging.handlers import RotatingFileHandler

# Add core directory to Python path
current_dir = Path(__file__).parent
core_dir = current_dir / 'core'
sys.path.append(str(current_dir))
sys.path.append(str(core_dir)) # Ensure core directory is added correctly

from core.file_handler import FileHandler
from core.model_manager import ModelManager
from core.prompt_processor import PromptProcessor
from core.response_processor import extract_code
from core.template_processor import TemplateProcessor

VERSION = "1.1.0"

class PoorAI:
    """Main application class for the Poor AI Programming Tool."""

    def __init__(self, project_folder: str, initial_command: list[str] = None):
        self.project_dir = Path(project_folder).resolve()
        self.initial_command = ' '.join(initial_command) if initial_command else None
        self.should_exit = False
        
        self._setup_logging()
        self._validate_project_structure()

        # Initialize components
        self.config = self._load_config()
        self.file_handler = FileHandler(self.project_dir)
        self.template_processor = TemplateProcessor(
            project_dir=self.project_dir,
            templates_dir=self.project_dir / 'templates',
            file_handler=self.file_handler,
            config=self.config
        )
        self.prompt_processor = PromptProcessor(self.template_processor, self.file_handler)
        self.model_manager = self._initialize_model_manager()

        # Application state
        self.current_task = ""
        self.current_template = "main"

    def _setup_logging(self):
        log_dir = self.project_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Main app log handler
        main_handler = RotatingFileHandler(
            log_dir / 'poor_ai.log', maxBytes=10*1024*1024, backupCount=5
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        main_handler.setFormatter(formatter)
        root_logger.addHandler(main_handler)

        # Console handler for user feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO) # Only show INFO and above to user
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        # We will use print() for direct user interaction instead of logging to console
        logging.getLogger().info(f"Logging initialized. Log file at {log_dir / 'poor_ai.log'}")

    def _validate_project_structure(self):
        """Ensures required directories and files exist, creating them if necessary."""
        if not self.project_dir.exists():
            print(f"Project directory '{self.project_dir}' does not exist.")
            confirm = input("Do you want to create it? (y/n): ").lower()
            if confirm == 'y':
                self.project_dir.mkdir(parents=True)
                print(f"Created project directory.")
            else:
                print("Exiting.")
                sys.exit(1)

        # Create default config files from examples if they don't exist
        for filename in ['config.json']:
            project_file = self.project_dir / filename
            script_file = current_dir / filename
            if not project_file.exists() and script_file.exists():
                shutil.copy(script_file, project_file)
                logging.info(f"Copied default {filename} to project directory.")

        # Create project.json if it doesn't exist
        project_json_path = self.project_dir / 'project.json'
        if not project_json_path.exists():
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump({'project_name': self.project_dir.name, 'files': []}, f, indent=2)
            logging.info("Created new project.json")

        (self.project_dir / 'templates').mkdir(exist_ok=True)
        (self.project_dir / 'logs').mkdir(exist_ok=True)

    def _load_config(self) -> dict:
        config_path = self.project_dir / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _initialize_model_manager(self) -> ModelManager:
        models_path = current_dir / 'models.json'
        config_path = self.project_dir / 'config.json'
        return ModelManager(models_path, config_path, self.project_dir)

    def _save_request_response(self, prompt_data, raw_result, token_info, cost):
        log_dir = self.project_dir / 'logs'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid4().hex[:8]
        filename = log_dir / f"request_{timestamp}_{unique_id}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"--- METADATA ---\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Model: {self.model_manager.get_current_model()['name']}\n")
                f.write(f"Tokens: {token_info}\n")
                f.write(f"Cost: ${cost:.6f}\n")
                f.write("\n--- PROMPT ---\n")
                f.write(prompt_data['user_prompt'])
                f.write("\n\n--- RESPONSE ---\n")
                f.write(raw_result)
            logging.info(f"Saved request/response log to {filename}")
        except Exception as e:
            logging.error(f"Failed to save request/response log: {e}")

    def run(self):
        """Runs the main CLI loop."""
        print(f"Poor AI Programming Tool v{VERSION}")
        print(f"Project: {self.file_handler.get_project_name()} ({self.project_dir})")
        print("Type 'help' for a list of commands.")

        if self.initial_command:
            print(f"Executing initial command: {self.initial_command}")
            self.process_command(self.initial_command)

        while not self.should_exit:
            try:
                model_name = self.model_manager.get_current_model()['name'] if self.model_manager.get_current_model() else 'None'
                prompt_str = f"[{model_name}]> "
                command = input(prompt_str).strip()
                if command:
                    self.process_command(command)
            except KeyboardInterrupt:
                print("\nUse 'exit' or 'quit' to leave.")
            except EOFError:
                self.should_exit = True
                print("\nExiting.")

    def process_command(self, command: str):
        """Processes a single user command."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ['exit', 'quit']:
            self.should_exit = True
            print("Exiting.")
        elif cmd == 'help':
            self._print_help()
        elif cmd == 'version':
            print(f"Version {VERSION}")
        elif cmd == 'load':
            if not args:
                print("Usage: load <file_path> [file_path...]")
            else:
                loaded, failed = self.file_handler.load_files(args)
                if loaded:
                    print(f"Loaded: {', '.join(loaded)}")
        elif cmd == 'save':
            saved = self.file_handler.save_files()
            if saved:
                print(f"Saved changes to: {', '.join(saved)}")
            else:
                print("No changes to save.")
        elif cmd == 'clear':
            self.file_handler.clear()
            print("Cleared loaded files.")
        elif cmd == 'task':
            if args:
                self.current_task = ' '.join(args)
                print(f"Task set to: {self.current_task}")
            else:
                print("Enter multi-line task description (end with 'END' on a new line):")
                lines = []
                while True:
                    line = input()
                    if line == 'END':
                        break
                    lines.append(line)
                self.current_task = "\n".join(lines)
                print("Task set.")
        elif cmd == 'gen':
            self._handle_gen(command)
        elif cmd == 'context':
            if args and args[0] == 'show':
                self._show_context()
            else:
                print("Usage: context show")
        elif cmd == 'template':
            self._handle_template(args)
        elif cmd == 'model':
            self._handle_model(args)
        elif cmd == 'project':
            self._handle_project(args)
        elif cmd == 'test':
            self._run_tests()
        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for a list.")

    def _handle_gen(self, command_str):
        print("Generating... (this may take a while)")
        prompt_data = self.prompt_processor.process_prompt(command_str, self.current_task, self.current_template)
        if not prompt_data:
            return
        
        result = self.model_manager.generate(prompt_data['user_prompt'])
        if result:
            raw_result, token_info, cost = result
            print(f"Generation complete. Tokens: {token_info}. Est. Cost: ${cost:.6f}")
            self._save_request_response(prompt_data, raw_result, token_info, cost)

            extracted_data = extract_code(raw_result)
            if not extracted_data:
                print("Could not extract any code/data from the response.")
                return
            
            self.file_handler.apply_result(extracted_data)
            print("AI response applied to buffer. Use 'save' to write changes to disk.")
            for item in extracted_data:
                print(f"- Modified/created: {item.get('filename')}")
        else:
            print("Generation failed.")

    def _handle_template(self, args):
        if not args:
            print("Usage: template <list|use|show|new|edit> [name]")
            return
        sub_cmd = args[0]
        name = args[1] if len(args) > 1 else None

        if sub_cmd == 'list':
            print("Available templates:", ', '.join(self.template_processor.list_templates()))
        elif sub_cmd == 'use':
            if name and name in self.template_processor.list_templates():
                self.current_template = name
                print(f"Switched to template: {name}")
            else:
                print(f"Template '{name}' not found.")
        elif sub_cmd == 'show':
            template_to_show = name or self.current_template
            content = self.template_processor.get_template_content(template_to_show)
            if content:
                print(f"--- Content of template '{template_to_show}' ---\n{content}")
            else:
                print(f"Template '{template_to_show}' not found.")
        elif sub_cmd == 'new':
            if name:
                if self.template_processor.create_template(name):
                    print(f"Created empty template '{name}'. Use 'template edit {name}' to add content.")
                else:
                    print(f"Failed to create template '{name}'. It may already exist.")
            else:
                print("Usage: template new <name>")
        elif sub_cmd == 'edit':
            # This is a planned feature - requires editor integration for templates.
            print("Editing templates is a planned feature.")
        else:
            print(f"Unknown template command: {sub_cmd}")

    def _handle_model(self, args):
        if not args or args[0] == 'list':
            print("Available models:")
            for i, name in enumerate(self.model_manager.list_models()):
                print(f"  [{i}] {name}")
        elif args[0] in ['use', 'switch'] and len(args) > 1:
            if self.model_manager.set_model(' '.join(args[1:])):
                model_name = self.model_manager.get_current_model()['name']
                print(f"Switched model to: {model_name}")
            else:
                print(f"Model '{' '.join(args[1:])}' not found.")
        else:
            print("Usage: model [list|use <name_or_index>]")

    def _handle_project(self, args):
        if len(args) >= 2 and args[0] == 'set-name':
            new_name = ' '.join(args[1:])
            self.file_handler.set_project_name(new_name)
            print(f"Project name set to: '{new_name}'")
        else:
            print("Usage: project set-name <name>")

    def _show_context(self):
        print("--- Generating prompt context preview ---")
        prompt_data = self.prompt_processor.process_prompt("gen", self.current_task, self.current_template)
        if prompt_data:
            print(prompt_data['user_prompt'])
        else:
            print("Could not generate context. Is a task set?")

    def _run_tests(self):
        test_dir = self.project_dir / 'tests'
        if not test_dir.is_dir():
            print("No 'tests' directory found in the project.")
            return
        print("Running pytest...")
        try:
            subprocess.run([sys.executable, '-m', 'pytest', str(test_dir)], check=True)
        except subprocess.CalledProcessError:
            print("Pytest returned a non-zero exit code. Some tests failed.")
        except FileNotFoundError:
            print("Error: 'pytest' command not found. Is it installed?")

    def _print_help(self):
        help_text = """
Poor AI Programming Tool Commands:

  File Operations:
    load <path> [<path>...]   Load file(s) into buffer. Wildcards (*) are supported.
    save                      Save changes in buffer to disk.
    clear                     Clear all loaded files from the buffer.

  AI Interaction:
    task [<desc>]             Set the task for the AI. No args for multi-line input (end with 'END').
    gen                       Generate code based on current context, task, and files.
    context show              Show the prompt that will be sent to the AI.

  Management:
    template list             List available prompt templates.
    template use <name>       Switch to a different template.
    template show [<name>]    Show the content of a template.
    template new <name>       Create a new empty template.
    model list                List available AI models from models.json.
    model use <name|index>    Switch the active AI model.
    project set-name <name>   Set the project name in project.json.

  Other:
    test                      Run pytest in the 'tests/' directory.
    version                   Display the application version.
    help                      Show this help message.
    exit, quit                Exit the application.
"""
        print(help_text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A poor AI programming tool.")
    parser.add_argument('--project-folder', type=str, required=True, help='The root directory of the project.')
    parser.add_argument('initial_command', nargs='*', help='An initial command to run on startup.')
    
    args = parser.parse_args()

    app = PoorAI(args.project_folder, args.initial_command)
    app.run()
