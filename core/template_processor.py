# core/template_processor.py
import os
from pathlib import Path
import re
from typing import Optional, List
import json

class TemplateProcessor:
    def __init__(self, project_dir: str, templates_dir: str = 'templates', file_handler=None):
        self.templates_dir = Path(project_dir) / templates_dir
        self.project_dir = Path(project_dir)
        self.file_handler = file_handler  # Inject FileHandler for artifacts

    def create_template(self, name: str, content: str = "") -> bool:
        """Create a new template file."""
        try:
            template_path = self.templates_dir / f"{name}.txt"
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content or self._default_template())
            return True
        except Exception as e:
            print(f"Error creating template: {e}")
            return False

    def _default_template(self) -> str:
        """Return a default template content."""
        return """Project structure:
{{folder_schema:./}}

Project files:
{{files_with_short_descriptions}}

Artifacts:
{{file_contents}}

Description:
{<!-- No short descriptions available -->}

Task: {{task}}"""

    def fill_template(self, template_name: str, current_file: Optional[str], project_name: str, task: str) -> str:
        """Fill a template with actual content."""
        template_path = self.templates_dir / f"{template_name}.txt"
        if not template_path.exists():
            print(f"Template {template_name} not found.")
            return f"Task: {task}\nArtifacts:\n{self._get_artifacts()}"

        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # Replace placeholders
        template = self._replace_placeholders(template, current_file, project_name, task)
        return template

    def _replace_placeholders(self, template: str, current_file: Optional[str], project_name: str, task: str) -> str:
        """Replace all placeholders in the template."""

        def placeholder_replacer(match):
            full_placeholder = match.group(0)
            inner = match.group(1)
            if inner == "project_name":
                return project_name
            if inner == "task":
                return task
            if inner == "current_file":
                if current_file:
                    current_file_path = Path(current_file)
                    return self._read_file(current_file_path) or ''
                else:
                    if self.file_handler and self.file_handler.current_files:
                        return self._get_artifacts()
                    else:
                        return '<!-- No files loaded -->'
            if inner == "current_file_name":
                if current_file:
                    return Path(current_file).name
                elif self.file_handler and self.file_handler.current_files:
                    return ', '.join(Path(f).name for f in self.file_handler.current_files)
                else:
                    return '<!-- No files loaded -->'
            if inner == "files_no_descriptions":
                return self._get_files_no_descriptions()
            if inner == "files_with_short_descriptions":
                return self._get_files_with_short_descriptions()
            if inner == "files_with_detailed_descriptions":
                return self._get_files_with_detailed_descriptions()
            if inner == "file_contents":
                return self._get_artifacts()
            if inner == "json_file_contents":
                return self._get_json_file_contents()

            # {{file:something}}
            if inner.startswith("file:"):
                file_path_str = inner[5:]
                path = (self.project_dir / file_path_str.strip()).resolve()
                return self._read_file(path) or f'<!-- File not found: {file_path_str} -->'
            # {{folder_schema:something}}
            if inner.startswith("folder_schema:"):
                paths = inner[14:]
                return self._get_folder_schema(paths.strip())
            # {{desc_{desc_type}:{file_path}}}
            m = re.match(r'desc_(short|long|detailed):(.*)', inner)
            if m:
                desc_type, file_path_str = m.groups()
                desc = self.get_description(file_path_str.strip(), desc_type) or f'<!-- No {desc_type} description for {file_path_str} -->'
                return desc
            # {current_desc_*}
            m = re.match(r'current_desc_(short|long|detailed)', inner)
            if m:
                desc_type = m.group(1)
                if current_file:
                    desc = self.get_description(current_file, desc_type) or f'<!-- No {desc_type} description for current file -->'
                    return desc
                elif self.file_handler and self.file_handler.current_files:
                    descs = []
                    for f in self.file_handler.current_files:
                        desc = self.get_description(f, desc_type)
                        if desc:
                            descs.append(f"File: {Path(f).name}\n{desc}")
                    desc_content = '\n\n'.join(descs) if descs else f'<!-- No {desc_type} descriptions available -->'
                    return desc_content
                else:
                    return '<!-- No files loaded -->'

            # Unknown placeholder: leave unchanged
            return full_placeholder

        # replace all {{...}} placeholders via regex in one sweep
        result = re.sub(r'\{\{([^\}]+)\}\}', placeholder_replacer, template)
        return result

    def _get_json_file_contents(self) -> str:
        """Generate JSON-formatted file contents for loaded files."""
        if not self.file_handler or not self.file_handler.current_files:
            return '[]'
        
        file_objects = []
        for file_path in self.file_handler.current_files:
            content = self.file_handler.contents.get(file_path, '')
            # Use filename with project-relative path for 'filename', not just basename
            try:
                relpath = str(Path(file_path).relative_to(self.project_dir))
            except Exception:
                relpath = str(Path(file_path))
            # Determine language based on file extension
            extension = Path(file_path).suffix.lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.html': 'html',
                '.css': 'css',
                '.json': 'json',
                '.md': 'markdown',
                '.txt': 'text'
            }
            language = language_map.get(extension, '')
            # Escape content to handle backticks
            escaped_content = content.replace('\\u0060\\u0060\\u0060', '\\\u0060\\\u0060\\\u0060')
            
            file_objects.append({
                'filename': relpath,
                'language': language,
                'content': escaped_content
            })
        
        return json.dumps(file_objects, indent=2)

    def _read_file(self, path: Path) -> Optional[str]:
        """Read the content of a file."""
        try:
            path = path.resolve()
            if path.exists() and path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            return None

    def _get_folder_schema(self, paths: str) -> str:
        """Generate a folder schema for the specified paths."""
        schema = []
        base_path = self.project_dir
        for path_str in paths.split(','):
            path = (base_path / path_str.strip()).resolve()
            try:
                if path.is_file():
                    schema.append(f"- {path.relative_to(base_path)}")
                elif path.is_dir():
                    schema.append(f"+ {path.relative_to(base_path)}/")
                    for item in sorted(path.rglob('*')):
                        if item.is_file():
                            relative_item_path = item.relative_to(path)
                            indent = "  " * (len(relative_item_path.parts) - 1)
                            schema.append(f"  {indent}- {item.relative_to(base_path)}")
            except FileNotFoundError:
                schema.append(f"[Path not found: {path_str.strip()}]")
            except Exception as e:
                schema.append(f"[Error processing path {path_str.strip()}: {e}]")

        return '\n'.join(schema) if schema else 'No files or directories found for specified paths.'

    def _get_artifacts(self) -> str:
        """Retrieve the contents of all loaded files from FileHandler."""
        if self.file_handler:
            return self.file_handler.get_artifacts()
        return "<!-- FileHandler not available or no files loaded -->"

    def _get_files_no_descriptions(self) -> str:
        """Retrieve the list of project files without descriptions from FileHandler."""
        if self.file_handler:
            try:
                if self.file_handler.project_json.exists():
                    with open(self.file_handler.project_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    files = data.get("files", [])
                    if not files:
                        return "No project files listed."
                    return "\n".join(f"- {file['name']}" for file in files)
                return "project.json not found."
            except Exception as e:
                return f"Error reading project.json: {e}"
        return "No project files available."

    def _get_files_with_short_descriptions(self) -> str:
        """Retrieve the list of project files with short descriptions from FileHandler."""
        if self.file_handler:
            try:
                if self.file_handler.project_json.exists():
                    with open(self.file_handler.project_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    files = data.get("files", [])
                    if not files:
                        return "No project files listed."
                    result = []
                    for file in files:
                        name = file.get("name", "Unknown")
                        short = file.get("short", "No short description")
                        result.append(f"- {name}")
                        if short:
                            result.append(f"  Short: {short}")
                    return "\n".join(result)
                return "project.json not found."
            except Exception as e:
                return f"Error reading project.json: {e}"
        return "No project files available."

    def _get_files_with_detailed_descriptions(self) -> str:
        """Retrieve the list of project files with detailed descriptions from FileHandler."""
        if self.file_handler:
            try:
                if self.file_handler.project_json.exists():
                    with open(self.file_handler.project_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    files = data.get("files", [])
                    if not files:
                        return "No project files listed."
                    result = []
                    for file in files:
                        name = file.get("name", "Unknown")
                        detailed = file.get("detailed", "No detailed description")
                        result.append(f"- {name}")
                        if detailed:
                            result.append(f"  Detailed: {detailed}")
                    return "\n".join(result)
                return "project.json not found."
            except Exception as e:
                return f"Error reading project.json: {e}"
        return "No project files available."

    def get_description(self, file_path: str, desc_type: str) -> str:
        """Retrieve a specific description type from a description file."""
        try:
            abs_path = (self.project_dir / file_path).resolve()
            desc_file = abs_path.with_suffix('.desc.md')
            if not desc_file.exists():
                return ""
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._parse_description(content, desc_type)
        except Exception as e:
            print(f"Error getting description for {file_path}: {e}")
            return ""

    def _parse_description(self, content: str, desc_type: str) -> str:
        """Parse the requested description type from markdown content."""
        desc_type_upper = desc_type.upper()
        pattern = re.compile(rf'<!--\s*{re.escape(desc_type_upper)}\s*-->(.*?)(?=<!--|\Z)', re.DOTALL | re.IGNORECASE)
        match = pattern.search(content)
        return match.group(1).strip() if match else ""

    def create_description(self, file_path: str) -> bool:
        """Create a new description file with default content."""
        try:
            abs_path = (self.project_dir / file_path).resolve()
            desc_file = abs_path.with_suffix('.desc.md')
            if desc_file.exists():
                print(f"Description file {desc_file} already exists.")
                return False
            content = """<!-- SHORT -->
Short description here.

<!-- LONG -->
Long description here.

<!-- DETAILED -->
Detailed description here.
"""
            desc_file.parent.mkdir(parents=True, exist_ok=True)
            with open(desc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created description file: {desc_file.relative_to(self.project_dir)}")
            return True
        except Exception as e:
            print(f"Error creating description for {file_path}: {e}")
            return False

    def edit_description(self, file_path: str) -> bool:
        """Open the description file for editing (simulated)."""
        abs_path = (self.project_dir / file_path).resolve()
        desc_file = abs_path.with_suffix('.desc.md')
        if not desc_file.exists():
            print(f"Description file {desc_file} does not exist. Creating it first.")
            created = self.create_description(file_path)
            if not created:
                return False
        print(f"Please manually edit the description file: {desc_file.relative_to(self.project_dir)}")
        return True

    def view_description(self, file_path: str, desc_type: str) -> Optional[str]:
        """View a specific description type."""
        desc = self.get_description(file_path, desc_type)
        if desc:
            return desc
        abs_path = (self.project_dir / file_path).resolve()
        desc_file = abs_path.with_suffix('.desc.md')
        if not desc_file.exists():
            print(f"Description file not found: {desc_file.relative_to(self.project_dir)}")
        else:
            print(f"No '{desc_type}' description found in {desc_file.relative_to(self.project_dir)}")
        return None

    def list_templates(self) -> List[str]:
        """List available template files."""
        try:
            templates = [f.stem for f in self.templates_dir.glob('*.txt')]
            return templates
        except Exception as e:
            print(f"Error listing templates: {e}")
            return []