import json
import re
from decimal import Decimal, InvalidOperation

def evaluate(response: str, parameters: dict) -> tuple[float, str]:
    expected = parameters.get("expected_answer")
    precision = parameters.get("precision", 2)  # Default precision if not specified

    # Strip whitespace and initialize variables
    cleaned_response = response.strip()
    actual = None

    # Check for "**Answer:**" marker
    answer_match = re.search(r'\*\*Answer:\*\*\s*([^\n]*)', cleaned_response, re.IGNORECASE)
    if answer_match:
        actual = answer_match.group(1).strip()
    
    # If no "**Answer:**" marker, check for JSON block
    if actual is None and '```json' in cleaned_response and '```' in cleaned_response:
        try:
            # Extract content between ```json and ```
            start = cleaned_response.index('```json') + len('```json')
            end = cleaned_response.rindex('```')
            json_str = cleaned_response[start:end].strip()
            json_content = json.loads(json_str)
            if isinstance(json_content, dict) and "answer" in json_content:
                actual = json_content["answer"]
        except (ValueError, json.JSONDecodeError):
            # If JSON parsing fails, fall back to other methods
            pass

    # If no valid answer was found, process the entire response
    if actual is None:
        # Remove markdown code fences if present
        if cleaned_response.startswith('```') and cleaned_response.endswith('```'):
            lines = cleaned_response.splitlines()
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned_response = '\n'.join(lines).strip()

        try:
            # Attempt to parse as JSON first
            response_data = json.loads(cleaned_response)
            if isinstance(response_data, dict):
                actual = response_data.get("answer")
                if actual is None:
                    actual = cleaned_response  # Fallback to raw response
            elif isinstance(response_data, (int, float, str)):
                actual = response_data
            else:
                actual = cleaned_response  # Fallback to raw response
        except json.JSONDecodeError:
            # If not JSON, assume the cleaned response string is the answer
            actual = cleaned_response
        except Exception:
            return 0.0, "Error processing response structure."

    if expected is None:
        return 0.0, "Missing 'expected_answer' in evaluation parameters."

    try:
        # Ensure expected and actual are strings before Decimal conversion
        expected_decimal = Decimal(str(expected))
        actual_decimal = Decimal(str(actual))
        
        # Quantize both to the same precision before comparison
        quantizer = Decimal('1e-' + str(precision))
        
        if actual_decimal.quantize(quantizer) == expected_decimal.quantize(quantizer):
            return 1.0, f"Correct. Expected: {expected_decimal}, Got: {actual_decimal}"
        else:
            return 0.0, f"Incorrect. Expected: {expected_decimal}, Got: {actual_decimal}"
    except InvalidOperation:
        # Handle non-numeric cases with string comparison
        if str(actual).strip() == str(expected).strip():
            return 1.0, f"Correct (non-numeric match). Expected: {expected}, Got: {actual}"
        return 0.0, f"Invalid numeric format or non-matching non-numeric. Expected: {expected}, Got: {actual}"
    except Exception as e:
        return 0.0, f"Error during numeric comparison: {str(e)}"