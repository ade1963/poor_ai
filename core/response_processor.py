import re
import logging
import uuid
import json

log = logging.getLogger(__name__)

def extract_code(response: str) -> list[dict]:
    """Parses AI responses to extract file content and metadata.

    It tries various strategies in order:
    1. Parse the entire response as a JSON object.
    2. Find a JSON code block (\u0060\u0060\u0060json ... \u0060\u0060\u0060) and parse it.
    3. Find diff blocks and extract filenames and content.
    4. Find regular code blocks with filenames and extract content.
    5. Treat the entire response as a single code block for an unknown file.

    Args:
        response: The raw string response from the AI model.

    Returns:
        A list of dictionaries, where each dictionary represents a file
        and contains keys like 'filename', 'content', 'language', etc.
    """
    if not response:
        log.warning("Received empty response.")
        return []

    log.debug(f"Starting code extraction from response: {response[:500]}...")

    # Strategy 1: Try to parse the whole response as JSON
    try:
        # Clean up the response string: remove leading/trailing whitespace and backticks
        cleaned_response = response.strip().strip('`')
        if cleaned_response.lower().startswith('json'):
            cleaned_response = cleaned_response[4:].strip()

        data = json.loads(cleaned_response)
        if isinstance(data, list):
            log.info(f"Successfully parsed response as a JSON list of {len(data)} items.")
            # Ensure each item has a unique artifact_id
            for item in data:
                item.setdefault('artifact_id', str(uuid.uuid4()))
            return data
    except json.JSONDecodeError:
        log.debug("Response is not a single valid JSON object. Trying other methods.")

    # Strategy 2: Find JSON code blocks
    json_blocks = re.findall(r'\u0060\u0060\u0060json\n(.*?)\n\u0060\u0060\u0060', response, re.DOTALL)
    if json_blocks:
        try:
            data = json.loads(json_blocks[0])
            if isinstance(data, list):
                log.info(f"Successfully parsed a JSON code block with {len(data)} items.")
                for item in data:
                    item.setdefault('artifact_id', str(uuid.uuid4()))
                return data
        except json.JSONDecodeError as e:
            log.warning(f"Could not parse JSON from code block: {e}")

    artifacts = []
    # Strategy 3: Find diff blocks (unified or git-style)
    # Regex for --- a/file.py and +++ b/file.py
    diff_pattern = re.compile(r'diff --git a/(?P<filename_a>.*?) b/(?P<filename_b>.*?)\n.*?---\s*a/(?P=filename_a)\n\+\+\+\s*b/(?P=filename_b)\n(?P<content>.*?(?=\ndiff --git a/|$))', re.DOTALL)
    diffs = diff_pattern.finditer(response)
    for match in diffs:
        data = match.groupdict()
        filename = data['filename_b']
        content = f"--- a/{data['filename_a']}\n+++ b/{filename}\n{data['content']}"
        log.info(f"Extracted diff for file: {filename}")
        artifacts.append({
            'artifact_id': str(uuid.uuid4()),
            'filename': filename,
            'content': content.strip(),
            'type': 'diff'
        })
    if artifacts:
        return artifacts

    # Strategy 4: Find regular code blocks with optional language and filename
    # Pattern for \u0060\u0060\u0060lang filename.ext ... \u0060\u0060\u0060 or \u0060\u0060\u0060`lang\nfilename.ext\n...\u0060\u0060\u0060`
    code_block_pattern = re.compile(r'\u0060\u0060\u0060`?(?:(?P<language>\w+)?(?:\s*(?P<filename>[\w\./-]+))?\n)?(?P<content>.+?)\n\u0060\u0060\u0060`?', re.DOTALL)
    code_blocks = code_block_pattern.finditer(response)

    for match in code_blocks:
        data = match.groupdict()
        filename = data.get('filename')
        content = data.get('content', '').strip()
        language = data.get('language')

        if content:
            log.info(f"Extracted code block for file: {filename or 'unknown'}")
            artifacts.append({
                'artifact_id': str(uuid.uuid4()),
                'filename': filename or f"unknown_{uuid.uuid4().hex[:6]}.txt",
                'language': language,
                'content': content,
                'type': 'code'
            })

    if artifacts:
        return artifacts

    # Strategy 5: If no other structure is found, treat the whole response as one file
    log.info("No structured data found. Treating the entire response as a single artifact.")
    return [{
        'artifact_id': str(uuid.uuid4()),
        'filename': f"generated_file_{uuid.uuid4().hex[:6]}.txt",
        'content': response.strip(),
        'language': 'unknown',
        'type': 'raw'
    }]
