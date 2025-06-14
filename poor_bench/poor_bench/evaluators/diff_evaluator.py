import re
from typing import Tuple

def evaluate(response: str, parameters: dict) -> Tuple[float, str]:
    """
    Evaluates a unified diff response for correctness.
    
    Args:
        response: String, the LLM-generated unified diff, possibly wrapped in markdown code blocks.
        parameters: Dict with 'expected_diff' key containing the correct diff.
    
    Returns:
        Tuple[float, str]: Score (0.0 to 1.0) and evaluation details.
    """
    expected_diff = parameters.get("expected_diff")
    if not expected_diff:
        return 0.0, "No 'expected_diff' provided in parameters."

    # Preprocess response to strip markdown code blocks (```diff or ```)
    response = response.strip()
    markdown_pattern = re.compile(
        r'^```(?:diff)?\s*\n([\s\S]*?)\n```$', re.MULTILINE
    )
    match = markdown_pattern.match(response)
    if match:
        response = match.group(1).strip()

    # Normalize response and expected_diff (strip whitespace, ensure consistent newlines)
    response = response.replace('\r\n', '\n')
    expected_diff = expected_diff.strip().replace('\r\n', '\n')

    # Check if response is empty
    if not response:
        return 0.0, "Empty diff response."

    # Validate unified diff format
    diff_pattern = re.compile(
        r'^--- [^\n]+\n\+\+\+ [^\n]+\n@@ -[0-9]+,[0-9]+ \+[0-9]+,[0-9]+ @@.*?\n',
        re.MULTILINE | re.DOTALL
    )
    if not diff_pattern.search(response):
        return 0.0, "Invalid unified diff format: Missing or incorrect headers/hunk markers."

    # Split into lines for comparison
    response_lines = response.splitlines()
    expected_lines = expected_diff.splitlines()

    # Check headers (--- and +++)
    if len(response_lines) < 2 or not (response_lines[0].startswith('---') and response_lines[1].startswith('+++')):
        return 0.0, "Invalid diff headers."

    # Check if headers match expected
    if response_lines[0] != expected_lines[0] or response_lines[1] != expected_lines[1]:
        return 0.0, f"Header mismatch. Expected:\n{expected_lines[0]}\n{expected_lines[1]}\nGot:\n{response_lines[0]}\n{response_lines[1]}"

    # Extract hunks
    response_hunks = []
    expected_hunks = []
    current_hunk = []
    for line in response_lines[2:]:
        if line.startswith('@@'):
            if current_hunk:
                response_hunks.append(current_hunk)
            current_hunk = [line]
        else:
            current_hunk.append(line)
    if current_hunk:
        response_hunks.append(current_hunk)

    current_hunk = []
    for line in expected_lines[2:]:
        if line.startswith('@@'):
            if current_hunk:
                expected_hunks.append(current_hunk)
            current_hunk = [line]
        else:
            current_hunk.append(line)
    if current_hunk:
        expected_hunks.append(current_hunk)

    # Check number of hunks
    if len(response_hunks) != len(expected_hunks):
        return 0.0, f"Expected {len(expected_hunks)} hunks, got {len(response_hunks)}."

    # Compare hunks
    correct_lines = 0
    total_lines = 0
    details = []
    for i, (resp_hunk, exp_hunk) in enumerate(zip(response_hunks, expected_hunks)):
        if resp_hunk[0] != exp_hunk[0]:
            details.append(f"Hunk {i+1}: Range mismatch. Expected: {exp_hunk[0]}, Got: {resp_hunk[0]}")
            continue

        # Compare lines in hunk
        for j, (resp_line, exp_line) in enumerate(zip(resp_hunk[1:], exp_hunk[1:])):
            total_lines += 1
            if resp_line == exp_line:
                correct_lines += 1
            else:
                details.append(f"Hunk {i+1}, Line {j+1}: Expected '{exp_line}', Got '{resp_line}'")

    if total_lines == 0:
        return 0.0, "No diff content to evaluate."

    score = correct_lines / total_lines
    detail_str = f"Correctly matched {correct_lines}/{total_lines} lines.\n" + "\n".join(details)
    return score, detail_str