import re
import logging
import uuid
import json

logger = logging.getLogger(__name__)

def escape_backticks(content: str) -> str:
    """Escape triple backticks in content."""
    return content.replace('\u0060\u0060\u0060', '\\u0060\\u0060\\u0060')

def extract_code(response: str) -> list[dict]:
    """
    Extracts multiple file-content pairs from a response string.
    Validates JSON object format with filename, language, and content fields.
    Falls back to handling filename + code block, filename + raw content, fenced diffs, unified diff format, and Git diff format.
    """
    if not response or not response.strip():
        logger.warning("Empty or whitespace-only response received")
        return []

    results = []

    # Handle JSON inside triple backticks
    try:
        json_data = json.loads(response.strip())
        if isinstance(json_data, list):
            logger.info("Processing response as JSON array")
            for item in json_data:
                if not isinstance(item, dict):
                    logger.warning(f"Skipping invalid JSON item (not a dict): {item}")
                    continue
                filename = item.get('filename', '').strip()
                language = item.get('language', '').strip()
                content = item.get('content', '')
                if not filename or not content:
                    logger.warning(f"Skipping JSON item with empty fields: {item}")
                    continue
                results.append({
                    'filename': filename,
                    'content': escape_backticks(content),
                    'language': language,
                    'artifact_id': str(uuid.uuid4()),
                    'is_diff': False
                })
            if results:
                logger.info(f"Extracted {len(results)} file-content pairs from JSON response")
                return results
    except json.JSONDecodeError as e:
        logger.info(f"Response is not valid JSON (error: {e}), checking for fenced JSON")

    # Fenced JSON in triple backticks
    fence_pattern = re.compile(r'\u0060\u0060\u0060(?:json)?\n([\s\S]*?)\n\u0060\u0060\u0060', re.MULTILINE)
    for match in fence_pattern.finditer(response):
        block = match.group(1).strip()
        try:
            json_data = json.loads(block)
            if isinstance(json_data, list):
                logger.info("Processing fenced content as JSON array")
                for item in json_data:
                    if not isinstance(item, dict):
                        continue
                    filename = item.get('filename', '').strip()
                    language = item.get('language', '').strip().lower()
                    content = item.get('content', '')
                    short = item.get('short', '')
                    detailed = item.get('detailed', '')
                    if not filename or not content:
                        continue
                    results.append({
                        'filename': filename,
                        'content': escape_backticks(content),
                        'language': language,
                        'short': short,
                        'detailed': detailed,
                        'artifact_id': str(uuid.uuid4()),
                        'is_diff': False
                    })
                if results:
                    return results
        except json.JSONDecodeError:
            continue

    # Raw content (no fences or diff markers)
    if not results and '\u0060\u0060\u0060' not in response and not response.startswith(('diff', '---')):
        lines = response.splitlines()
        if len(lines) == 1:
            return [{
                'filename': '',
                'content': escape_backticks(response.strip()),
                'language': '',
                'artifact_id': str(uuid.uuid4()),
                'is_diff': False
            }]
        first = lines[0].strip()
        if ' ' not in first and ('.' in first or '/' in first):
            filename = first
            content = escape_backticks('\n'.join(lines[1:]).rstrip())
            return [{
                'filename': filename,
                'content': content,
                'language': '',
                'artifact_id': str(uuid.uuid4()),
                'is_diff': False
            }]
        return [{
            'filename': '',
            'content': escape_backticks(response.strip()),
            'language': '',
            'artifact_id': str(uuid.uuid4()),
            'is_diff': False
        }]

    # Four backtick fenced blocks
    four_fence_pattern = re.compile(r'\u0060\u0060\u0060\u0060([^\n]*)\n?([\s\S]*?)\u0060\u0060\u0060\u0060', re.MULTILINE)
    for match in four_fence_pattern.finditer(response):
        lang_line = match.group(1).strip()
        block = match.group(2).strip()
        start = match.start()
        pre = response[:start].rstrip('\n')
        lines = pre.split('\n') if pre else []
        filename = ''
        if lines:
            last = lines[-1].strip()
            if last and not last.startswith(('```', 'diff', '----', '````')):
                filename = last
        if '.' in lang_line or '/' in lang_line:
            filename = lang_line
            language = ''
        else:
            language = lang_line
        is_diff = False
        if language == 'diff':
            diff_lines = block.splitlines()
            for line in diff_lines:
                if line.startswith('--- a/'):
                    filename = line[6:].strip()
                    break
                elif line.startswith('diff --git a/'):
                    filename = line.split(' a/')[1].split(' b/')[0].strip()
                    break
            is_diff = True
        content = escape_backticks(block)
        results.append({
            'filename': filename,
            'content': content,
            'language': language,
            'artifact_id': str(uuid.uuid4()),
            'is_diff': is_diff
        })

    # Triple backtick fenced blocks
    fence_pattern = re.compile(r'\u0060\u0060\u0060([^\n]*)\n([\s\S]*?)\n\u0060\u0060\u0060', re.MULTILINE)
    for match in fence_pattern.finditer(response):
        lang_line = match.group(1).strip()
        block = match.group(2).strip()
        start = match.start()
        pre = response[:start].rstrip('\n')
        lines = pre.split('\n') if pre else []
        filename = ''
        if lines:
            last = lines[-1].strip()
            if last and not last.startswith(('```', 'diff', '----', '````')):
                filename = last
        if '.' in lang_line or '/' in lang_line:
            filename = lang_line
            language = ''
        else:
            language = lang_line
        is_diff = False
        if language == 'diff':
            diff_lines = block.splitlines()
            for line in diff_lines:
                if line.startswith('--- a/'):
                    filename = line[6:].strip()
                    break
                elif line.startswith('diff --git a/'):
                    filename = line.split(' a/')[1].split(' b/')[0].strip()
                    break
            is_diff = True
        content = escape_backticks(block)
        if filename and content:
            results.append({
                'filename': filename,
                'content': content,
                'language': language,
                'artifact_id': str(uuid.uuid4()),
                'is_diff': is_diff
            })

    # Unified diffs
    unified_diff_pattern = re.compile(r'--- a/(?P<file>.+?)\n\+{3} b/.+?\n(?P<body>[\s\S]*?)(?=(?:--- a/|$))', re.MULTILINE)
    for match in unified_diff_pattern.finditer(response):
        filename = match.group('file').strip()
        body = match.group('body').strip()
        results.append({
            'filename': filename,
            'content': escape_backticks(body),
            'language': 'diff',
            'artifact_id': str(uuid.uuid4()),
            'is_diff': True
        })

    # Git-style diffs
    git_diff_pattern = re.compile(r'diff --git a/(?P<file>.+?) b/.+?\n(?:--- a/.+?\n\+{3} b/.+?\n)(?P<body>[\s\S]*?)(?=(?:diff --git|$))', re.MULTILINE)
    for match in git_diff_pattern.finditer(response):
        filename = match.group('file').strip()
        body = match.group('body').strip()
        results.append({
            'filename': filename,
            'content': escape_backticks(body),
            'language': 'diff',
            'artifact_id': str(uuid.uuid4()),
            'is_diff': True
        })

    logger.info(f"Extracted {len(results)} file-content pairs from response")
    return results
