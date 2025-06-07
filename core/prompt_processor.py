# core/prompt_processor.py
import re
from typing import Dict, Optional

class PromptProcessor:
    def __init__(self, template_processor, file_handler):
        self.template_processor = template_processor
        self.file_handler = file_handler

    def process_prompt(self, command: str, current_file: Optional[str], project_name: str, template_name: str = None) -> Dict[str, str]:
        """Process a user command into a structured prompt for the AI model."""
        command_type, task = self._parse_command(command)
        context = self._build_context(current_file, project_name, task, template_name)
        return {
            'command_type': command_type,
            'task': task,
            'context': context
        }

    def _parse_command(self, command: str) -> tuple[str, str]:
        """Parse the command to determine its type and extract the task."""
        command = command.strip()
        if command.lower().startswith('gen '):
            return 'generate', command[4:].strip()
        else:
            return 'unknown', command

    def _build_context(self, current_file: Optional[str], project_name: str, task: str, template_name: str = None) -> str:
        """Build the context using the template processor."""
        if not template_name:
            # Default context without template
            return f"Task: {task}\nArtifacts:\n{self.file_handler.get_artifacts()}"
        # Pass None for current_file to indicate all files should be used
        return self.template_processor.fill_template(template_name, None, project_name, task)