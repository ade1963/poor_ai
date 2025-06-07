import sys
import io
import traceback
import ast
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, List, Any, Tuple
import re

def extract_code_blocks(text: str) -> List[str]:
    """Extract Python code blocks from markdown or plain text."""
    # Look for markdown code blocks
    markdown_pattern = r'\u0060\u0060\u0060(?:python)?\s*([\s\S]*?)\s*\u0060\u0060\u0060'
    markdown_blocks = re.findall(markdown_pattern, text)
    
    if markdown_blocks:
        return markdown_blocks
    
    # If no markdown blocks found, try to infer based on common Python keywords
    lines = text.split('\n')
    code_lines = []
    in_code = False
    
    # A simple heuristic: if a line starts with def or class, assume it's code from there
    # This is not foolproof but better than nothing for plain text responses.
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line.startswith('def ') or stripped_line.startswith('class '):
            in_code = True
            code_lines.extend(lines[i:]) # Take this line and all subsequent lines
            break 
        # Heuristic: if it looks like an import statement and we are not in code yet
        if not in_code and (stripped_line.startswith('import ') or stripped_line.startswith('from ')):
            # Tentatively start collecting if it seems like a script beginning
            # This part is tricky without more context; could collect non-code if LLM explains imports first.
            # For now, rely on def/class as stronger signals.
            pass 
            
    if code_lines:
        return ['\n'.join(code_lines)]
    
    # Last resort: return the whole text as a potential code block if it contains common keywords
    # This helps if the LLM just returns code without markdown or clear 'def'/'class' at the start of a block
    if any(kw in text for kw in ['def ', 'class ', 'import ', 'return ', 'for ', 'while ']):
        return [text]
    return []

def evaluate(response: str, parameters: dict) -> tuple[float, str]:
    """
    Evaluates Python code solutions.
    
    Args:
        response: String, LLM's Python code solution.
        parameters: Dict with keys:
            - test_cases: List of dicts with 'input' and 'expected_output' keys
            - function_name: Expected name of the function (optional)
            - execution_timeout: Maximum execution time in seconds (default: 5)
    
    Returns:
        Tuple[float, str]: Score (0.0 to 1.0) and explanation.
    """
    code_blocks = extract_code_blocks(response)
    if not code_blocks:
        return 0.0, "No Python code found in the response."
    
    code = max(code_blocks, key=len) # Use the largest block, assuming it's the main solution
    
    try:
        ast.parse(code)
    except SyntaxError as e:
        return 0.0, f"Syntax error in extracted code: {str(e)}\nCode: {code[:500]}..."
    
    test_cases = parameters.get("test_cases", [])
    function_name_param = parameters.get("function_name")
    timeout = parameters.get("execution_timeout", 5)
    
    if not test_cases:
        return 0.5, "Code syntax is valid, but no test cases provided for functional verification."
    
    namespace = {}
    
    try:
        # Create a restricted global namespace for exec
        # Allow builtins but nothing else from the current global scope
        restricted_globals = {'__builtins__': __builtins__}
        exec(code, restricted_globals, namespace)
    except Exception as e:
        # Capture traceback for more detailed error reporting
        tb_str = traceback.format_exc()
        return 0.0, f"Error executing user code: {str(e)}\nTraceback:\n{tb_str}\nCode: {code[:500]}..."

    # Determine the function to test
    target_function = None
    if function_name_param:
        if function_name_param not in namespace:
            return 0.0, f"Function '{function_name_param}' not found in the executed code."
        target_function = namespace[function_name_param]
    else:
        # Auto-detect function if name not provided
        callable_functions = [obj for name, obj in namespace.items() 
                              if callable(obj) and not name.startswith('__') and hasattr(obj, '__module__') and obj.__module__ == '<string>'] # Check __module__ to prefer user-defined functions
        if not callable_functions:
            return 0.0, "No user-defined functions found in the code."
        if len(callable_functions) > 1:
             # If multiple functions, this could be ambiguous. For now, pick the first one.
             # A better approach might be to require function_name or handle multiple entry points.
            pass # proceed with the first one
        target_function = callable_functions[0]
        function_name_param = target_function.__name__ # Update for reporting

    if not callable(target_function):
        return 0.0, f"'{function_name_param}' is not a callable function."

    passed_tests = 0
    test_results_details = []
    
    for i, tc in enumerate(test_cases):
        input_val = tc.get("input")
        expected_output = tc.get("expected_output")
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        actual_output = None
        error_occurred = False
        
        try:
            start_time = time.perf_counter()
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                if input_val is None: # For functions that take no arguments
                    actual_output = target_function()
                elif isinstance(input_val, list): # Positional arguments
                    actual_output = target_function(*input_val)
                elif isinstance(input_val, dict): # Keyword arguments
                    actual_output = target_function(**input_val)
                else: # Single argument
                    actual_output = target_function(input_val)
            duration = time.perf_counter() - start_time

            if duration > timeout:
                test_results_details.append(f"Test Case {i+1} (Input: {input_val}): TIMEOUT (>{timeout}s)")
                continue

            # Check for errors printed to stderr during execution
            err_output = stderr_capture.getvalue()
            if err_output:
                test_results_details.append(f"Test Case {i+1} (Input: {input_val}): RUNTIME ERROR - Stderr: {err_output.strip()}")
                continue
                
            if actual_output == expected_output:
                passed_tests += 1
                test_results_details.append(f"Test Case {i+1} (Input: {input_val}): PASS")
            else:
                test_results_details.append(f"Test Case {i+1} (Input: {input_val}): FAIL - Expected: {expected_output}, Got: {actual_output}")
        
        except Exception as e:
            tb_str = traceback.format_exc(limit=1) # Keep traceback short
            test_results_details.append(f"Test Case {i+1} (Input: {input_val}): EXECUTION ERROR - {str(e)}\n{tb_str.strip()}")
            error_occurred = True # To mark this test as failed

    score = passed_tests / len(test_cases) if test_cases else 0.0
    summary = f"Function '{function_name_param}': Passed {passed_tests}/{len(test_cases)} test cases."
    full_details = summary + "\n" + "\n".join(test_results_details)
    
    return score, full_details
