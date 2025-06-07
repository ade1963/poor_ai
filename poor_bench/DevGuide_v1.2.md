# Developer Guide for `poor_bench` v1.2

## Overview

`poor_bench` is a Python-based benchmarking framework designed to create, manage, and evaluate tests for Large Language Models (LLMs). It empowers developers to define test classes with customizable prompt templates, generate tests across multiple difficulty levels, and evaluate results using modular evaluation components. The tool supports tailored prompts per LLM, initial test validation, and bulk test execution, with results scored on a 0.0 to 1.0 scale. As a lightweight, console-based solution optimized for constrained systems, it operates as a standalone module within the `poor_ai` ecosystem.

A key focus of `poor_bench` is to catch potential LLM issues early in development, enabling fine-tuning of parameters and system prompts to boost performance and reliability.

### Project Structure
`poor_bench` resides as a subdirectory within `poor_ai`:

```
poor_ai/
├── poor_bench/
│   ├── __init__.py
│   ├── main.py
│   ├── config_manager.py
│   ├── test_runner.py
│   ├── report_generator.py
│   ├── llm_manager.py
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── math_evaluator.py
│   │   ├── sentiment_evaluator.py
│   │   └── python_evaluator.py
│   ├── test_classes.yaml
│   ├── tests.json
│   ├── llms.json
│   └── results.json
└── (other poor_ai files)
```

### Development Environment Setup

1. **Python Version**: Use Python 3.9+ for development
2. **Dependencies**:
   ```
   pip install pyyaml matplotlib numpy pandas pytest requests dash plotly
   ```
3. **Development Tools**:
   - Use `pytest` for unit testing
   - Use `black` for code formatting
   - Use `pylint` for linting

## Data Structures

`poor_bench` uses YAML for test class configurations and JSON for test instances, LLM configurations, and results. Each file includes a version field for tracking changes.

### 1. Test Class Configuration (`test_classes.yaml`)

Defines test classes with prompt templates and evaluation modules.

#### Schema
- `version`: String, schema version (e.g., "1.0").
- `test_classes`: List of test class objects.
  - `id`: Unique string identifier (e.g., "math_problems").
  - `description`: Human-readable description.
  - `system_prompt`: Optional string for LLM system-level instruction.
  - `work_prompt_template`:
    - `default`: String with placeholders (e.g., `{problem}`).
    - `overrides`: Optional dictionary mapping LLM IDs to custom prompts.
  - `evaluation_module`:
    - `name`: String, evaluation module name (e.g., "math_evaluator").
    - `parameters`: Key-value pairs for module settings.

#### Example
```yaml
version: "1.0"
test_classes:
  - id: "math_problems"
    description: "Tests for solving mathematical problems"
    system_prompt: "You are a math expert. Provide clear solutions."
    work_prompt_template:
      default: "Solve this math problem and return your answer in JSON format with key 'answer': {problem}"
      overrides:
        ollama:gemma3:1b-it-qat: "Solve this and return JSON with 'answer': {problem}"
    evaluation_module:
      name: "math_evaluator"
      parameters:
        precision: 2
        expected_format: "json"

  - id: "sentiment_analysis"
    description: "Tests for determining sentiment of texts"
    system_prompt: "You are a sentiment analysis expert."
    work_prompt_template:
      default: "Analyze the sentiment of these texts and return a JSON list of sentiments ['positive', 'negative', 'neutral']: {texts}"
    evaluation_module:
      name: "sentiment_evaluator"
      parameters:
        response_format: "list_of_sentiments"

  - id: "python_coding"
    description: "Tests for writing Python code to solve programming problems"
    system_prompt: "You are an expert Python programmer. Write clean, efficient, and well-documented code."
    work_prompt_template:
      default: "Write a Python function that {task}. Include docstrings and comments where appropriate."
    evaluation_module:
      name: "python_evaluator"
      parameters:
        test_cases: []
```

### 2. Test Instances (`tests.json`)

Stores specific test instances linked to test classes.

#### Schema
- `version`: String, schema version (e.g., "1.0").
- `tests`: List of test objects.
  - `test_id`: Unique string identifier.
  - `class_id`: Links to a test class `id`.
  - `level`: Integer, difficulty level.
  - `text` or `texts`: String or list, test content.
  - `evaluation_module`:
    - `name`: Evaluation module name.
    - `parameters`: Evaluation settings.

#### Example
```json
{
  "version": "1.0",
  "tests": [
    {
      "test_id": "math_problems_level1_001",
      "class_id": "math_problems",
      "level": 1,
      "text": "What is 2 + 2?",
      "evaluation_module": {
        "name": "math_evaluator",
        "parameters": {
          "expected_answer": "4",
          "precision": 0,
          "expected_format": "json"
        }
      }
    },
    {
      "test_id": "sentiment_analysis_level1_001",
      "class_id": "sentiment_analysis",
      "level": 1,
      "texts": [
        "I love this product!",
        "This is the worst experience ever.",
        "It's okay, nothing special."
      ],
      "evaluation_module": {
        "name": "sentiment_evaluator",
        "parameters": {
          "expected_sentiments": ["positive", "negative", "neutral"],
          "response_format": "list_of_sentiments"
        }
      }
    },
    {
      "test_id": "python_coding_level2_001",
      "class_id": "python_coding",
      "level": 2,
      "text": "calculates the factorial of a number",
      "evaluation_module": {
        "name": "python_evaluator",
        "parameters": {
          "test_cases": [
            {"input": 5, "expected_output": 120},
            {"input": 0, "expected_output": 1},
            {"input": 1, "expected_output": 1}
          ],
          "function_name": "factorial",
          "execution_timeout": 2
        }
      }
    }
  ]
}
```

### 3. LLM Configurations (`llms.json`)

Defines LLMs and their parameters.

#### Schema
- `llms`: List of LLM objects.
  - `provider`: String (e.g., "ollama").
  - `name`: String, model name.
  - `endpoint`: String, API endpoint URL.
  - `base_system_prompt`: Optional default system prompt.
  - `size`: Float, model size in billions of parameters.
  - `parameters`: Key-value pairs (e.g., `temperature`, `think`).
    - `think`: Boolean, enables thinking mode for Ollama models (optional, defaults to false).

#### Example
```json
{
  "llms": [
    {
      "provider": "ollama",
      "name": "deepseek-r1:1.5b-qwen-distill-fp16",
      "endpoint": "http://46.29.236.116:8183/v1",
      "base_system_prompt": "You are an AI for structured tasks.",
      "size": 3.6,
      "parameters": {
        "temperature": 1.0,
        "top_k": 64,
        "top_p": 0.95,
        "think": false
      }
    },
    {
      "provider": "openai",
      "name": "gpt-4o",
      "endpoint": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY",
      "size": 4.0,
      "parameters": {
        "temperature": 0.5,
        "max_tokens": 1024
      }
    }
  ]
}
```

### 4. Test Results (`results.json`)

Logs results, organized by LLM ID for easy querying and persistence.

#### Schema
- `version`: String, schema version (e.g., "1.0").
- `results`: Dictionary with LLM IDs as keys and lists of result objects as values.
  - `test_id`: Unique test identifier.
  - `score`: Float, 0.0 to 1.0.
  - `details`: Evaluation feedback.
  - `response`: Raw LLM response.
  - `timestamp`: ISO format timestamp.
  - `execution_time_ms`: Response time in milliseconds.
  - `think`: Boolean, indicates if thinking mode was enabled (optional, included for Ollama models).

#### Example
```json
{
  "version": "1.0",
  "results": {
    "ollama:deepseek-r1:1.5b-qwen-distill-fp16": [
      {
        "test_id": "math_problems_level1_001",
        "score": 1.0,
        "details": "Correctly answered '4'",
        "response": "{\"answer\": 4}",
        "timestamp": "2025-05-25T14:32:15.123456",
        "execution_time_ms": 245,
        "think": false
      }
    ],
    "openai:gpt-4o": [
      {
        "test_id": "sentiment_analysis_level1_001",
        "score": 1.0,
        "details": "Correctly identified all sentiments",
        "response": "[\"positive\", \"negative\", \"neutral\"]",
        "timestamp": "2025-05-25T14:32:18.654321",
        "execution_time_ms": 189,
        "think": false
      }
    ]
  }
}
```

## Dashboard

The `poor_bench` dashboard, implemented in `dashboard.py`, provides an interactive interface to visualize and analyze LLM benchmark results. Built using Dash and Plotly, it enables users to explore test outcomes, compare model performance, and identify potential issues.

### Features
- **Model Selection**: A dropdown menu allows users to select an LLM to filter test results.
- **Score Visualization**: A bar chart displays test scores (0.0 to 1.0) by test ID, color-coded by test category, with rotated x-axis labels for readability.
- **Test Results Table**: Displays test details (Test ID, Score, Test Category, Execution Time, Details, Think) with pagination and markdown support for details.
- **Issues Detection**: Highlights potential issues, such as tests with a score of 0.0 or unexpected response formats (e.g., JSON objects in math or sentiment tests).
- **Model Comparison Table**: Summarizes model performance with columns for Model, Total Tests, Average Score, Pass Rate (%), Average Execution Time (seconds), and Size (B). The table supports interactive sorting by Model, Average Score, and Size.
- **Refresh Button**: Updates the analysis to reflect new data in `results.json`.

### Usage
Run the dashboard with:
```bash
python dashboard.py
```
The dashboard loads data from `benchmark_results.json` and `llms.json`, processes it into a Pandas DataFrame, and serves the interface at `http://127.0.0.1:8050`. Ensure the required dependencies (`dash`, `plotly`, `pandas`) are installed.

### Customization
- **Data Source**: Modify `file_path` in `dashboard.py` to point to a different results file.
- **Styling**: Adjust CSS styles in the `app.layout` for visual customization.
- **Issue Detection**: Extend the `detect_issues` function to include additional checks specific to your use case.

## Evaluation Modules

Evaluation modules score LLM outputs on a 0.0 to 1.0 scale.

### Interface Specification
```python
def evaluate(response: str, parameters: dict) -> tuple[float, str]:
    """
    Evaluates an LLM response.
    Args:
        response: LLM output.
        parameters: Evaluation settings.
    Returns:
        Tuple[float, str]: Score and details.
    """
```

### Example Evaluation Modules

#### 1. `math_evaluator.py`
Handles JSON responses for math problems.

```python
import json
from decimal import Decimal, InvalidOperation

def evaluate(response: str, parameters: dict) -> tuple[float, str]:
    expected = parameters.get("expected_answer")
    precision = parameters.get("precision", 2)
    expected_format = parameters.get("expected_format", "json")
    
    if expected_format == "json":
        try:
            response_data = json.loads(response)
            actual = response_data.get("answer")
            if actual is None:
                return 0.0, "No 'answer' key in JSON response"
        except json.JSONDecodeError:
            return 0.0, "Invalid JSON in response"
    else:
        return 0.0, "Expected JSON format"
    
    try:
        expected_decimal = Decimal(str(expected))
        actual_decimal = Decimal(str(actual))
        if round(actual_decimal, precision) == round(expected_decimal, precision):
            return 1.0, f"Correct answer: {actual}"
        else:
            return 0.0, f"Expected {expected}, got {actual}"
    except InvalidOperation:
        return 0.0, "Invalid numeric format"
```

#### 2. `sentiment_evaluator.py`
Evaluates multiple sentiments from a JSON list.

```python
import json

def evaluate(response: str, parameters: dict) -> tuple[float, str]:
    expected_sentiments = parameters.get("expected_sentiments", [])
    response_format = parameters.get("response_format", "list_of_sentiments")
    
    if response_format == "list_of_sentiments":
        try:
            actual_sentiments = json.loads(response)
            if not isinstance(actual_sentiments, list):
                return 0.0, "Response must be a list"
        except json.JSONDecodeError:
            return 0.0, "Invalid JSON in response"
        
        if len(actual_sentiments) != len(expected_sentiments):
            return 0.0, f"Expected {len(expected_sentiments)} sentiments, got {len(actual_sentiments)}"
        
        correct = sum(1 for a, e in zip(actual_sentiments, expected_sentiments) if a.lower() == e.lower())
        score = correct / len(expected_sentiments)
        return score, f"Correctly identified {correct} out of {len(expected_sentiments)} sentiments"
    else:
        return 0.0, "Expected list_of_sentiments format"
```

#### 3. `python_evaluator.py`
```python
import sys
import io
import traceback
import ast
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, List, Any, Tuple

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
    # Extract code from the response
    code_blocks = extract_code_blocks(response)
    if not code_blocks:
        return 0.0, "No Python code found in the response"
    
    # Use the largest code block (assuming it's the complete solution)
    code = max(code_blocks, key=len)
    
    # Check if the code is syntactically valid
    try:
        ast.parse(code)
    except SyntaxError as e:
        return 0.0, f"Syntax error in code: {str(e)}"
    
    # Extract test cases and other parameters
    test_cases = parameters.get("test_cases", [])
    function_name = parameters.get("function_name", None)
    timeout = parameters.get("execution_timeout", 5)
    
    if not test_cases:
        return 0.5, "No test cases provided, code syntax is valid but functionality not verified"
    
    # Create a safe execution environment
    namespace = {}
    
    # Execute the code in the namespace
    try:
        exec(code, namespace)
    except Exception as e:
        return 0.0, f"Error executing code: {str(e)}"
    
    # Check if the expected function exists
    if function_name and function_name not in namespace:
        return 0.0, f"Function '{function_name}' not found in code"
    
    # If function_name is not specified, try to find a function in the namespace
    if not function_name:
        functions = [name for name, obj in namespace.items() 
                    if callable(obj) and not name.startswith('__')]
        if not functions:
            return 0.0, "No functions defined in code"
        function_name = functions[0]
    
    # Run test cases
    function = namespace[function_name]
    passed_tests = 0
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        input_value = test_case.get("input")
        expected_output = test_case.get("expected_output")
        
        # Capture stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            # Set timeout for execution
            start_time = time.time()
            
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                if isinstance(input_value, list):
                    actual_output = function(*input_value)
                elif isinstance(input_value, dict):
                    actual_output = function(**input_value)
                else:
                    actual_output = function(input_value)
            
            execution_time = time.time() - start_time
            if execution_time > timeout:
                test_results.append(f"Test {i+1}: TIMEOUT after {execution_time:.2f}s")
                continue
                
            # Compare output
            if actual_output == expected_output:
                passed_tests += 1
                test_results.append(f"Test {i+1}: PASS")
            else:
                test_results.append(f"Test {i+1}: FAIL - Expected {expected_output}, got {actual_output}")
                
        except Exception as e:
            test_results.append(f"Test {i+1}: ERROR - {str(e)}")
    
    # Calculate score
    score = passed_tests / len(test_cases)
    details = "\n".join(test_results)
    
    return score, f"Passed {passed_tests}/{len(test_cases)} tests.\n{details}"

def extract_code_blocks(text: str) -> List[str]:
    """Extract Python code blocks from markdown or plain text."""
    # Look for markdown code blocks
    markdown_pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
    import re
    markdown_blocks = re.findall(markdown_pattern, text)
    
    if markdown_blocks:
        return markdown_blocks
    
    # If no markdown blocks found, treat the entire text as code
    # (after removing potential explanations)
    lines = text.split('\n')
    code_lines = []
    in_code = False
    
    for line in lines:
        if line.strip().startswith('def ') or line.strip().startswith('class '):
            in_code = True
        
        if in_code:
            code_lines.append(line)
    
    if code_lines:
        return ['\n'.join(code_lines)]
    
    # Last resort: return the whole text as a potential code block
    return [text]
```

## Implementation Details

### Core Components

#### 1. `config_manager.py`
Updated to handle the new `results.json` structure.

```python
import os
import json
import yaml
from typing import Dict, List, Any, Optional

class ConfigManager:
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
    
    def load_results(self) -> Dict[str, Any]:
        path = os.path.join(self.base_path, "results.json")
        if not os.path.exists(path):
            return {"version": "1.0", "results": {}}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_results(self, results: Dict[str, Any]) -> None:
        path = os.path.join(self.base_path, "results.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
    
    def get_pending_tests(self, llm_id: str, test_ids: Optional[List[str]] = None) -> List[str]:
        results = self.load_results()
        completed_tests = set(result["test_id"] for result in results.get("results", {}).get(llm_id, []))
        all_tests = self.load_tests()
        available_tests = [test["test_id"] for test in all_tests.get("tests", [])]
        if test_ids:
            available_tests = [tid for tid in available_tests if tid in test_ids]
        return [tid for tid in available_tests if tid not in completed_tests]
    
    def load_test_classes(self) -> Dict[str, Any]:
        """Load test classes from YAML configuration."""
        path = os.path.join(self.base_path, "test_classes.yaml")
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_tests(self) -> Dict[str, Any]:
        """Load test instances from JSON configuration."""
        path = os.path.join(self.base_path, "tests.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_llms(self) -> Dict[str, Any]:
        """Load LLM configurations from JSON."""
        path = os.path.join(self.base_path, "llms.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
```

#### 2. `test_runner.py`
Uses provider-specific handlers for LLMs and includes the `think` parameter in results.

```python
import time
import datetime
from typing import Dict, Any

class LLMProvider:
    def generate_response(self, prompt: str, system_prompt: str, parameters: dict) -> str:
        raise NotImplementedError()

class OllamaProvider(LLMProvider):
    def generate_response(self, prompt: str, system_prompt: str, parameters: dict) -> str:
        # Placeholder for Ollama-specific logic
        return "Simulated Ollama response"

class OpenAIProvider(LLMProvider):
    def generate_response(self, prompt: str, system_prompt: str, parameters: dict) -> str:
        # Placeholder for OpenAI-specific logic
        return "Simulated OpenAI response"

class TestRunner:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.llm_providers = {
            "ollama": OllamaProvider(),
            "openai": OpenAIProvider(),
            "llm7": LLMProvider()  # Placeholder for future custom API
        }
    
    def run_test(self, test_id: str, llm_id: str) -> Dict[str, Any]:
        llm_config = next((llm for llm in self.config_manager.load_llms()["llms"] if f"{llm['provider']}:{llm['name']}" == llm_id), None)
        if not llm_config:
            raise ValueError(f"LLM {llm_id} not found")
        
        provider = self.llm_providers.get(llm_config["provider"])
        if not provider:
            raise ValueError(f"Provider {llm_config['provider']} not supported")
        
        test = next((t for t in self.config_manager.load_tests()["tests"] if t["test_id"] == test_id), None)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        # Simplified prompt generation (full logic omitted for brevity)
        prompt = test["class_id"]  # Replace with actual prompt generation
        start_time = time.time()
        response = provider.generate_response(prompt, llm_config.get("base_system_prompt", ""), llm_config.get("parameters", {}))
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Simplified evaluation (full logic in evaluators)
        score, details = 1.0, "Placeholder evaluation"
        
        result = {
            "test_id": test_id,
            "score": score,
            "details": details,
            "response": response,
            "timestamp": datetime.datetime.now().isoformat(),
            "execution_time_ms": execution_time_ms,
            "think": llm_config.get("parameters", {}).get("think", False)
        }
        
        results = self.config_manager.load_results()
        if llm_id not in results["results"]:
            results["results"][llm_id] = []
        results["results"][llm_id].append(result)
        self.config_manager.save_results(results)
        
        return result
```