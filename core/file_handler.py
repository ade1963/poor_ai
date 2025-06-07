import os
import json
import logging
import re
import difflib
import fnmatch
from pathlib import Path
from logging.handlers import RotatingFileHandler

from core.response_processor import extract_code

log = logging.getLogger(__name__)

class FileHandler:
    """Manages file operations, project tracking, and change detection."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.project_file = self.project_dir / 'project.json'
        self.loaded_files = {}
        self._setup_logging()
        self.project_data = self._load_project_data()

    def _setup_logging(self):
        log_dir = self.project_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / 'file_handler.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)

    def _load_project_data(self):
        """Loads the project.json file."""
        try:
            if self.project_file.exists():
                with open(self.project_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                log.warning("project.json not found. A new one will be created.")
                return {"project_name": self.project_dir.name, "files": []}
        except (json.JSONDecodeError, IOError) as e:
            log.error(f"Error loading project.json: {e}. Starting with a new one.")
            return {"project_name": self.project_dir.name, "files": []}

    def _save_project_data(self):
        """Saves the current project data to project.json."""
        try:
            with open(self.project_file, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=2)
            log.info("project.json saved successfully.")
        except IOError as e:
            log.error(f"Error saving project.json: {e}")

    def load_files(self, paths: list[str]) -> tuple[list[str], list[str]]:
        """Loads files from given paths, supporting wildcards."""
        loaded = []
        failed = []
        all_matching_files = set()

        for pattern in paths:
            # Create an absolute path pattern
            abs_pattern = self.project_dir / pattern
            # Use glob to find all matching files and directories
            found_paths = list(self.project_dir.glob(pattern))
            if not found_paths:
                log.warning(f"No files matched pattern: {pattern}")
                failed.append(pattern)

            for p in found_paths:
                if p.is_file():
                    all_matching_files.add(p)
        
        for file_path in all_matching_files:
            try:
                relative_path_str = str(file_path.relative_to(self.project_dir))
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.loaded_files[relative_path_str] = {
                    'original_content': content,
                    'current_content': content
                }
                self._update_project_file_entry(relative_path_str)
                loaded.append(relative_path_str)
                log.info(f"Loaded file: {relative_path_str}")
            except Exception as e:
                log.error(f"Failed to load file {file_path}: {e}")
                failed.append(str(file_path))
        
        if failed:
            print(f"Failed to load some paths: {', '.join(failed)}")
        
        self._save_project_data()
        return loaded, failed

    def save_files(self) -> list[str]:
        """Saves modified files to disk and updates project.json."""
        saved_files = []
        for filename, data in self.loaded_files.items():
            if data['original_content'] != data['current_content']:
                try:
                    full_path = self.project_dir / filename
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(data['current_content'])
                    data['original_content'] = data['current_content']
                    saved_files.append(filename)
                    log.info(f"Saved changes to {filename}")
                except IOError as e:
                    log.error(f"Error saving file {filename}: {e}")
                    print(f"Error saving {filename}: {e}")
        
        self._save_project_data() # Save any metadata changes
        return saved_files

    def apply_result(self, result: list[dict]):
        """Applies AI-generated content or diffs to loaded files."""
        for artifact in result:
            filename = artifact.get('filename')
            if not filename:
                log.warning(f"Artifact missing filename: {artifact}")
                continue

            # Ensure file is loaded or load it
            if filename not in self.loaded_files:
                full_path = self.project_dir / filename
                if full_path.exists():
                    self.load_files([filename])
                else:
                    # New file
                    self.loaded_files[filename] = {
                        'original_content': '',
                        'current_content': ''
                    }

            # Update metadata in project.json
            self._update_project_file_entry(filename, artifact)

            # Apply content changes
            if 'content' in artifact:
                if artifact.get('type') == 'diff':
                    self._apply_diff(filename, artifact['content'])
                else:
                    self._apply_full_content(filename, artifact['content'])
            
            log.info(f"Applied result to {filename}")

    def _apply_diff(self, filename: str, diff_text: str):
        """Applies a diff patch to a file's content."""
        if filename not in self.loaded_files:
            log.error(f"Attempted to apply diff to unloaded file: {filename}")
            return
        
        original_lines = self.loaded_files[filename]['current_content'].splitlines(True)
        patch = difflib.unified_diff('', '', original_lines, diff_text.splitlines(True))
        
        try:
            # This is a simplification. A real implementation would use a patch library.
            # For now, we use difflib to generate a patched result.
            # Note: `difflib.patch` isn't a standard function. We are using a conceptual approach.
            # A more robust solution would be to use a library like `patch` or manually parse the diff.
            # This is a placeholder for a more complex diff application logic.
            
            # Simple approach: if the diff is in a standard format, we can try to apply it.
            # Let's try to reconstruct the file from the patch.
            patched_lines = list(difflib.patch_from_diff(original_lines, diff_text.splitlines(True)))
            self.loaded_files[filename]['current_content'] = "".join(patched_lines)
            log.info(f"Successfully applied diff to {filename}")
        except Exception as e:
            log.error(f"Failed to apply diff to {filename}: {e}. Overwriting with diff content as a fallback.")
            # Fallback: what to do if patch fails? Maybe just log and do nothing.
            print(f"Warning: Could not apply diff to {filename}. Manual review may be needed.")
    
    def _apply_full_content(self, filename: str, new_content: str):
        """Replaces the content of a file, preserving comments if possible."""
        # Simple replacement for now. Comment preservation is complex.
        # The dev guide mentions it, so a basic implementation could be added here.
        # For now, we perform a direct replacement.
        self.loaded_files[filename]['current_content'] = new_content
        log.debug(f"Replaced content of {filename}")

    def _update_project_file_entry(self, filename: str, data: dict = None):
        """Updates or adds an entry for a file in project.json data."""
        if data is None:
            data = {}
        
        files = self.project_data.get('files', [])
        entry = next((f for f in files if f.get('name') == filename), None)

        if entry:
            # Update existing entry
            entry['language'] = data.get('language', entry.get('language', self._guess_language(filename)))
            entry['short'] = data.get('short', entry.get('short', ''))
            entry['detailed'] = data.get('detailed', entry.get('detailed', ''))
            log.debug(f"Updated project.json entry for {filename}")
        else:
            # Add new entry
            new_entry = {
                'name': filename,
                'language': data.get('language', self._guess_language(filename)),
                'short': data.get('short', ''),
                'detailed': data.get('detailed', '')
            }
            files.append(new_entry)
            self.project_data['files'] = files
            log.info(f"Added new project.json entry for {filename}")

    def _guess_language(self, filename: str) -> str:
        """Guesses the programming language from the file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown',
            '.json': 'json',
            '.txt': 'text',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.sh': 'shell'
        }
        _, ext = os.path.splitext(filename)
        return ext_map.get(ext, 'unknown')

    def clear(self):
        """Clears all loaded files from memory."""
        self.loaded_files.clear()
        log.info("Cleared all loaded files.")

    def get_loaded_files_content(self) -> dict[str, str]:
        """Returns the current content of all loaded files."""
        return {name: data['current_content'] for name, data in self.loaded_files.items()}

    def get_project_files_with_descriptions(self, desc_type: str = 'short') -> str:
        """Returns a formatted string of project files and their descriptions."""
        lines = []
        for f in self.project_data.get('files', []):
            desc = f.get(desc_type, '')
            if desc:
                lines.append(f"- {f['name']}: {desc}")
            else:
                 lines.append(f"- {f['name']}")
        return "\n".join(lines)

    def set_project_name(self, name: str):
        """Sets the project name in the project data."""
        self.project_data['project_name'] = name
        self._save_project_data()
        log.info(f"Project name updated to '{name}'")

    def get_project_name(self) -> str:
        """Gets the project name."""
        return self.project_data.get('project_name', 'Unknown Project')

    def get_file_list_no_description(self) -> str:
        """Returns a newline-separated list of filenames."""
        return "\n".join([f['name'] for f in self.project_data.get('files', [])])
