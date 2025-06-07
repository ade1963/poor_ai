import json
import re

def evaluate(response: str, parameters: dict) -> tuple[float, str]:
    expected_sentiments = parameters.get("expected_sentiments", [])
    # response_format is from test_classes.yaml, typically 'list_of_sentiments'
    
    if not expected_sentiments:
        return 0.0, "No 'expected_sentiments' provided in parameters."

    try:
        actual_sentiments = extract_json_from_response(response)
        if not isinstance(actual_sentiments, list):
            return 0.0, f"Response must be a JSON list. Got: {type(actual_sentiments)}"
    except json.JSONDecodeError:
        return 0.0, f"Invalid JSON in response: {response[:100]}..."
    except Exception as e:
        return 0.0, f"Error parsing response: {str(e)}"
    
    if len(actual_sentiments) != len(expected_sentiments):
        return 0.0, f"Expected {len(expected_sentiments)} sentiments, got {len(actual_sentiments)}."
    
    correct_count = 0
    details = []
    for i, (actual, expected) in enumerate(zip(actual_sentiments, expected_sentiments)):
        if str(actual).strip().lower() == str(expected).strip().lower():
            correct_count += 1
            details.append(f"Item {i+1}: Correct ('{expected}')")
        else:
            details.append(f"Item {i+1}: Incorrect. Expected: '{expected}', Got: '{actual}'")
            
    if not expected_sentiments: # Should be caught earlier, but defensive
        score = 0.0
    else:
        score = float(correct_count) / len(expected_sentiments)
        
    detail_str = f"Correctly identified {correct_count} out of {len(expected_sentiments)} sentiments. Details:\n" + "\n".join(details)
    return score, detail_str


def extract_json_from_response(response: str):
    response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

# Pattern matches ```json\n[...] or {...}\n``` or ```\n[...] or {...}\n```
    json_block_pattern = re.compile(
        r'(?:```json|```)\s*(\[.*?\]|\{.*?\})\s*```',  # Match arrays or objects
        re.DOTALL
    )
    match = json_block_pattern.match(response)
    if not match:
        # Try JSON block at the end
        json_block_pattern_end = re.compile(
            r'(?:```json|```)\s*({.*?})\s*```$',  # JSON block at the end
            re.DOTALL
        )
        match = json_block_pattern_end.search(response)

    if match:
        try:
            json_str = match.group(1).strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    return None  # or raise an error if preferred

"""
def extract_json_from_response(response: str):
    response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Pattern matches ```json\n{...}\n``` or ```\n{...}\n``` at start or end
    json_block_pattern = re.compile(
        r'^(?:```json|```)\s*({.*?})\s*```',      # JSON block at the start
        re.DOTALL
    )
    match = json_block_pattern.match(response)
    if not match:
        # Try JSON block at the end
        json_block_pattern_end = re.compile(
            r'(?:```json|```)\s*({.*?})\s*```$',  # JSON block at the end
            re.DOTALL
        )
        match = json_block_pattern_end.search(response)

    if match:
        try:
            json_str = match.group(1).strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    return None  #

"""