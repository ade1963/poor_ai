import re
import logging
from typing import Optional, Tuple

from core.template_processor import TemplateProcessor
from core.file_handler import FileHandler

log = logging.getLogger(__name__)

class PromptProcessor:
    """Parses user commands and constructs AI prompts."""

    def __init__(self, template_processor: TemplateProcessor, file_handler: FileHandler):
        self.template_processor = template_processor
        self.file_handler = file_handler

    def _parse_command(self, command: str) -> Tuple[str, Optional[str]]:
        """Identifies command type and extracts the task from it."""
        match = re.match(r'^\s*(\w+)\s*(.*)', command, re.DOTALL)
        if match:
            cmd, args = match.groups()
            return cmd.lower(), args or None
        return command.lower(), None

    def process_prompt(self, command: str, task: str, template_name: str) -> Optional[dict]:
        """Processes a 'gen' command into a structured prompt.

        Args:
            command: The user's full command string (e.g., 'gen add a button').
            task: The current task description (can be multi-line).
            template_name: The name of the template to use.

        Returns:
            A dictionary containing the system prompt and the user prompt, or None.
        """
        cmd, args = self._parse_command(command)

        if cmd != 'gen':
            log.debug(f"PromptProcessor received non-gen command: {cmd}. Ignoring.")
            return None
        
        # If 'gen' has arguments, they override the stored task.
        final_task = args if args else task

        if not final_task:
            print("No task has been set. Use 'task <description>' to set one.")
            log.warning("Attempted to generate without a task.")
            return None

        log.info(f"Building prompt with template '{template_name}' for task: {final_task[:100]}...")

        try:
            filled_template = self.template_processor.fill_template(
                template_name=template_name,
                task=final_task
            )
            
            # The filled template becomes the user part of the prompt.
            # The system prompt will be handled by the ModelManager.
            prompt_data = {
                'user_prompt': filled_template,
                'task': final_task
            }
            return prompt_data
        except Exception as e:
            log.error(f"Failed to build context: {e}", exc_info=True)
            print(f"Error building prompt: {e}")
            return None
