import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import json
import difflib
import re
import glob

def escape_backticks(content: str) -> str:
    """Escape triple backticks in content."""
    return content.replace('\u0060\u0060\u0060', '\\\u0060\\\u0060\\\u0060')

class FileHandler:
    def __init__(self, project_dir: str = os.getcwd()):
        self.project_dir = Path(project_dir).resolve()
        self.current_files = []
        self.contents = {}
        self.original_contents = {}  # Track original contents for change detection
        self.project_json = self.project_dir / "project.json"
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing FileHandler")

    def _setup_logging(self):
        """Set up logging with rotating file handler."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = RotatingFileHandler('file_handler.log', maxBytes=10*1024*1024, backupCount=5)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    def _update_project(self, filename: str, language: str = None, short: str = None, detailed: str = None):
        """Update project.json with a new or modified file, avoiding duplicates."""
        try:
            file_path = (self.project_dir / filename).resolve()
            try:
                relative_path = file_path.relative_to(self.project_dir).as_posix()
            except ValueError:
                self.logger.error(f"File '{filename}' is not in the project directory '{self.project_dir}'")
                print(f"Error: File '{filename}' is not in the project directory '{self.project_dir}'")
                return

            with open(self.project_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            files = data.get("files", [])
            # Check for existing entry by relative path
            file_entry = next((f for f in files if f["name"] == relative_path), None)
            if not file_entry:
                new_entry = {
                    "name": relative_path,
                    "short": short,
                    "detailed": detailed,
                    "language": language
                }
                files.append(new_entry)
                data["files"] = sorted(files, key=lambda x: x["name"])
                with open(self.project_json, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                self.logger.info(f"Added new file to project.json: {relative_path}, language: {language}")
            else:
                # Update existing entry
                if language and file_entry["language"] != language:
                    file_entry["language"] = language
                    with open(self.project_json, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                    self.logger.info(f"Updated language for file: {relative_path} to {language}")
                else:
                    self.logger.info(f"File {relative_path} already in project.json, no update needed")
        except Exception as e:
            self.logger.error(f"Error updating project.json: {e}")
            print(f"Error updating project.json: {e}")

    def load_file(self, paths: str) -> bool:
        """Load one or more files, supporting wildcards by referencing project.json."""
        try:
            path_list = [p.strip() for p in paths.replace(',', ' ').split() if p.strip()]
            success = True
            files_to_load = []

            # Check if any path contains wildcard characters
            has_wildcard = any('*' in p or '?' in p or '[' in p for p in path_list)
            
            if has_wildcard:
                # Load project.json to get file list
                try:
                    with open(self.project_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    project_files = [f["name"] for f in data.get("files", [])]
                except Exception as e:
                    self.logger.error(f"Error reading project.json for wildcard loading: {e}")
                    print(f"Error reading project.json for wildcard loading: {e}")
                    return False

                for pattern in path_list:
                    # Convert pattern to use forward slashes for glob
                    pattern = pattern.replace('\\', '/')
                    matched_files = [f for f in project_files if glob.fnmatch.fnmatch(f, pattern)]
                    if not matched_files:
                        print(f"Warning: No files in project.json match pattern '{pattern}'")
                        success = False
                    files_to_load.extend(matched_files)
            else:
                files_to_load = path_list

            for path in files_to_load:
                file_path = self.project_dir / path
                if not file_path.exists():
                    print(f"Warning: File '{file_path}' does not exist (resolved: {file_path.resolve()}).")
                    success = False
                    continue
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.contents[str(file_path)] = content
                    self.original_contents[str(file_path)] = content
                if str(file_path) not in self.current_files:
                    self.current_files.append(str(file_path))
                self._update_project(path)
            return success
        except Exception as e:
            print(f"Error loading files: {e}")
            self.logger.error(f"Error loading files: {e}")
            return False

    def save_file(self) -> bool:
        """Save only changed file contents to their respective files, creating parent directories."""
        if not self.current_files:
            print("Warning: No files loaded to save.")
            return False
        try:
            changed_files = []
            for file_path in self.current_files:
                current_content = self.contents.get(file_path, '')
                original_content = self.original_contents.get(file_path, '')
                if current_content != original_content:
                    file_obj = Path(file_path)
                    file_obj.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(current_content)
                    self.original_contents[file_path] = current_content
                    changed_files.append(file_path)
                    self._update_project(file_obj.relative_to(self.project_dir).as_posix())
            
            if changed_files:
                self.logger.info(f"Saved {len(changed_files)} changed files: {', '.join(changed_files)}")
                return True
            else:
                self.logger.info("No files changed, nothing to save.")
                print("No files changed, nothing to save.")
                return True
        except Exception as e:
            print(f"Error saving files: {e}")
            self.logger.error(f"Error saving files: {e}")
            return False

    def apply_result(self, result: list[dict]) -> bool:
        """Apply the extracted file-content pairs to the current files, handling JSON format, diffs, and preserving comments."""
        if not result:
            print("Error: No content to apply.")
            return False
        try:
            self.logger.info(f"Applying result with {len(result)} file-content pairs")
            for item in result:
                filename = item.get('filename', '').strip()
                content = item.get('content', '')
                language = item.get('language', '')
                short = item.get('short', None)
                detailed = item.get('detailed', None)
                is_diff = item.get('is_diff', False)
                if not filename:
                    self.logger.warning(f"Skipping content block with empty filename: {item}")
                    print(f"Warning: Skipping content block with empty filename: {item}")
                    continue
                if not content:
                    self.logger.warning(f"Skipping content block with empty content for filename '{filename}': {item}")
                    print(f"Warning: Skipping content block with empty content for filename '{filename}': {item}")
                    continue
                file_path = str(self.project_dir / filename)
                
                if is_diff:
                    if file_path not in self.contents:
                        if Path(file_path).exists():
                            with open(file_path, 'r', encoding='utf-8') as f:
                                self.contents[file_path] = f.read()
                        else:
                            self.contents[file_path] = ''
                    original_content = self.contents[file_path]
                    original_lines = original_content.splitlines()
                    
                    # Parse the diff
                    hunks = []
                    diff_lines = content.splitlines()
                    i = 0
                    while i < len(diff_lines):
                        line = diff_lines[i]
                        if line.startswith('@@'):
                            match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)
                            if match:
                                original_start = int(match.group(1))
                                original_count = int(match.group(2))
                                new_start = int(match.group(3))
                                new_count = int(match.group(4))
                                hunk_lines = []
                                i += 1
                                while i < len(diff_lines) and not diff_lines[i].startswith('@@'):
                                    hunk_lines.append(diff_lines[i])
                                    i += 1
                                hunks.append({
                                    'original_start': original_start,
                                    'original_count': original_count,
                                    'new_start': new_start,
                                    'new_count': new_count,
                                    'lines': hunk_lines
                                })
                            else:
                                i += 1
                        else:
                            i += 1
                    
                    # Apply the hunks
                    new_lines = []
                    pos = 0
                    for hunk in hunks:
                        original_start = hunk['original_start'] - 1
                        while pos < original_start:
                            if pos < len(original_lines):
                                new_lines.append(original_lines[pos])
                                pos += 1
                            else:
                                break
                        hunk_pos = original_start
                        for hunk_line in hunk['lines']:
                            if hunk_line.startswith(' '):
                                if hunk_pos < len(original_lines) and hunk_line[1:] == original_lines[hunk_pos]:
                                    new_lines.append(original_lines[hunk_pos])
                                    hunk_pos += 1
                                else:
                                    raise ValueError(f"Context mismatch at line {hunk_pos + 1}")
                            elif hunk_line.startswith('-'):
                                if hunk_pos < len(original_lines) and hunk_line[1:] == original_lines[hunk_pos]:
                                    hunk_pos += 1
                                else:
                                    raise ValueError(f"Removed line mismatch at line {hunk_pos + 1}")
                            elif hunk_line.startswith('+'):
                                new_lines.append(hunk_line[1:])
                        pos = hunk_pos
                    while pos < len(original_lines):
                        new_lines.append(original_lines[pos])
                        pos += 1
                    self.contents[file_path] = '\n'.join(new_lines)
                else:
                    # Preserve comments if file exists and language is supported
                    existing_comments = []
                    if file_path in self.contents and language in ['python', 'javascript', 'html', 'css']:
                        existing_lines = self.contents[file_path].splitlines()
                        comment_patterns = {
                            'python': r'^\s*#.*$',
                            'javascript': r'^\s*//.*$|^\s*/\*.*\*/\s*$',
                            'html': r'^\s*<!--.*-->\s*$',
                            'css': r'^\s*/\*.*\*/\s*$'
                        }
                        pattern = comment_patterns.get(language)
                        if pattern:
                            for line in existing_lines:
                                if re.match(pattern, line):
                                    existing_comments.append(line)
                    # Combine comments with new content
                    new_content = escape_backticks(content)
                    if existing_comments:
                        comment_block = '\n'.join([c for c in existing_comments if c not in new_content.splitlines()])
                        if comment_block:
                            new_content = comment_block + '\n' + new_content
                    self.contents[file_path] = new_content
                
                if file_path not in self.current_files:
                    self.current_files.append(file_path)
                    self.logger.info(f"Added new file to buffer: {file_path}")
                    print(f"Added new file to buffer: {file_path}")
                self._update_project(filename, language, short, detailed)
            return True
        except Exception as e:
            print(f"Error applying result: {e}")
            self.logger.error(f"Error applying result: {e}")
            return False
    
    def clear(self):
        """Clear all loaded files and their contents."""
        self.current_files = []
        self.contents = {}
        self.original_contents = {}
        print("Buffer cleared.")

    def get_artifacts(self) -> str:
        """Return the contents of all files with backticks escaped."""
        if not self.current_files:
            return "<!-- No files loaded -->"
        artifacts = []
        for file_path in self.current_files:
            content = escape_backticks(self.contents.get(file_path, ''))

            try:
                relpath = str(Path(file_path).relative_to(self.project_dir))
            except Exception:
                relpath = str(Path(file_path))


            artifacts.append(f"{relpath}\n\u0060\u0060\u0060\n{content}\n\u0060\u0060\u0060")
        return '\n\n'.join(artifacts)

    def get_description_path(self, file_path: str) -> str:
        """Return the path to the description file for a given file."""
        file_path = self.project_dir / file_path
        return str(file_path.with_suffix('.desc.md'))

    def get_project(self) -> str:
        """Return the contents of project.json as a formatted string."""
        try:
            if self.project_json.exists():
                with open(self.project_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                project_name = data.get("project_name", "Unnamed Project")
                files = data.get("files", [])
                if not files:
                    return f"No project files listed."
                result = []
                for file in files:
                    name = file.get("name", "Unknown")
                    short = file.get("short", "No short description")
                    detailed = file.get("detailed", "No detailed description")
                    language = file.get("language", "Unknown")
                    result.append(f"- {name}")
                    if short:
                        result.append(f"  Short: {short}")
                    if detailed:
                        result.append(f"  Detailed: {detailed}")
                    if language:
                        result.append(f"  Language: {language}")
                return "\n".join(result)
            return "project.json not found."
        except Exception as e:
            self.logger.error(f"Error reading project.json: {e}")
            return f"Error reading project.json: {e}"