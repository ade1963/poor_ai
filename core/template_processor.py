import os
import re
import json
import shutil
import logging
from pathlib import Path
from typing import Optional

from core.file_handler import FileHandler

log = logging.getLogger(__name__)

class TemplateProcessor:
    """Manages templates and processes placeholders for AI context."""

    def __init__(self, project_dir: Path, templates_dir: Path, file_handler: FileHandler, config: dict):
        self.project_dir = project_dir
        self.templates_dir = templates_dir
        self.file_handler = file_handler
        self.config = config
        self._copy_initial_templates()

    def _copy_initial_templates(self):
        """Copies templates from a source folder to the project's templates dir."""
        source_folder_name = self.config.get('templates_source_folder', 'template_sources')
        # Source folder is relative to the script's directory, not the project directory
        script_dir = Path(__file__).parent.parent
        source_path = script_dir / source_folder_name

        if not source_path.is_dir():
            log.warning(f"Template source folder '{source_path}' not found. Skipping initial template copy.")
            return

        self.templates_dir.mkdir(exist_ok=True)

        try:
            for item in source_path.iterdir():
                if item.is_file() and item.suffix == '.txt':
                    dest_file = self.templates_dir / item.name
                    if not dest_file.exists(): # Don't overwrite user changes
                        shutil.copy(item, dest_file)
                        log.info(f"Copied initial template: {item.name}")
        except OSError as e:
            log.error(f"Error copying initial templates: {e}")

    def list_templates(self) -> list[str]:
        """Lists available .txt templates."""
        if not self.templates_dir.exists():
            return []
        return [f.stem for f in self.templates_dir.glob('*.txt')]

    def get_template_content(self, name: str) -> Optional[str]:
        """Gets the content of a specific template."""
        template_path = self.templates_dir / f"{name}.txt"
        if template_path.exists():
            try:
                return template_path.read_text(encoding='utf-8')
            except IOError as e:
                log.error(f"Error reading template {name}: {e}")
                return None
        log.warning(f"Template '{name}' not found.")
        return None

    def create_template(self, name: str, content: str = "") -> bool:
        """Creates a new template file."""
        template_path = self.templates_dir / f"{name}.txt"
        if template_path.exists():
            log.warning(f"Template '{name}' already exists.")
            return False
        try:
            template_path.write_text(content, encoding='utf-8')
            log.info(f"Created new template: {name}")
            return True
        except IOError as e:
            log.error(f"Error creating template {name}: {e}")
            return False

    def fill_template(self, template_name: str, task: str) -> str:
        """Fills a template with dynamic data."""
        template_content = self.get_template_content(template_name)
        if template_content is None:
            log.error(f"Cannot fill template, as '{template_name}' was not found.")
            # Fallback to a very basic prompt
            template_content = "Task: {{task}}\n\nFiles:\n{{file_contents}}"

        return self._replace_placeholders(template_content, task)

    def _replace_placeholders(self, template_content: str, task: str) -> str:
        """Replaces all known placeholders in the template string."""
        # Simple placeholders
        replacements = {
            '{{project_name}}': self.file_handler.get_project_name(),
            '{{task}}': task,
            '{{current_file_name}}': ', '.join(self.file_handler.loaded_files.keys()),
            '{{file_contents}}': self._get_formatted_file_contents(),
            '{{json_file_contents}}': self._get_json_file_contents(),
            '{{files_no_descriptions}}': self.file_handler.get_file_list_no_description(),
            '{{files_with_short_descriptions}}': self.file_handler.get_project_files_with_descriptions('short'),
            '{{files_with_detailed_descriptions}}': self.file_handler.get_project_files_with_descriptions('detailed'),
        }

        for placeholder, value in replacements.items():
            template_content = template_content.replace(placeholder, value)

        # Complex placeholders with arguments
        template_content = re.sub(r'{{file:(.*?)}}', self._file_placeholder, template_content)
        template_content = re.sub(r'{{folder_schema:(.*?)}}', self._folder_schema_placeholder, template_content)
        
        return template_content

    def _get_formatted_file_contents(self) -> str:
        """Gets loaded file contents formatted for a text prompt."""
        parts = []
        for filename, content in self.file_handler.get_loaded_files_content().items():
            parts.append(f"`{filename}`:\n\u0060\u0060\u0060\n{content}\n\u0060\u0060\u0060")
        return "\n\n".join(parts)

    def _get_json_file_contents(self) -> str:
        """Gets loaded file contents formatted as a JSON string."""
        files_data = []
        for filename, content in self.file_handler.get_loaded_files_content().items():
            files_data.append({
                'filename': filename,
                'language': self.file_handler._guess_language(filename),
                'content': content
            })
        return json.dumps(files_data, indent=2)

    def _file_placeholder(self, match: re.Match) -> str:
        """Replaces {{file:path}} with the content of that file."""
        path_str = match.group(1).strip()
        file_path = self.project_dir / path_str
        if file_path.is_file():
            try:
                return file_path.read_text(encoding='utf-8')
            except IOError as e:
                log.error(f"Error reading file for placeholder {path_str}: {e}")
                return f"[Error reading file: {path_str}]"
        return f"[File not found: {path_str}]"

    def _folder_schema_placeholder(self, match: re.Match) -> str:
        """Replaces {{folder_schema:paths}} with a tree-like structure."""
        paths_str = match.group(1).strip()
        paths = [p.strip() for p in paths_str.split(',')]
        schema = []
        for p_str in paths:
            path = self.project_dir / p_str
            if path.is_dir():
                schema.append(f"{p_str}/:")
                for root, dirs, files in os.walk(path):
                    level = root.replace(str(self.project_dir), '').count(os.sep)
                    indent = ' ' * 4 * (level)
                    sub_indent = ' ' * 4 * (level + 1)
                    if Path(root) != path:
                        schema.append(f'{indent}{os.path.basename(root)}/')
                    for f in files:
                        schema.append(f'{sub_indent}{f}')
            elif path.is_file():
                 schema.append(f"[Not a directory: {p_str}]\n")
            else:
                schema.append(f"[Path not found: {p_str}]\n")
        return "\n".join(schema)
