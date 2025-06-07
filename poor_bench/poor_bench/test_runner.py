import time
import datetime
import importlib
import json
import re
from typing import Dict, Any, Tuple, Optional

from .config_manager import ConfigManager
from .llm_manager import LLMManager # Assuming llm_manager.py is in the same directory

class TestRunner:
    def __init__(self, config_manager: ConfigManager, llm_manager: LLMManager):
        self.config_manager = config_manager
        self.llm_manager = llm_manager

    def _get_prompt_template(self, test_class_config: Dict[str, Any], llm_id_str: str) -> str:
        template_config = test_class_config.get("work_prompt_template", {})
        # Strip think mode from llm_id_str for prompt overrides (only provider:name needed)
        llm_id_base = ":".join(llm_id_str.split(":")[:2])  # e.g., ollama:deepseek-r1:1.5b-qwen-distill-fp16
        if llm_id_base in template_config.get("overrides", {}):
            return template_config["overrides"][llm_id_base]
        return template_config.get("default", "")

    def _format_prompt(self, template: str, test_instance: Dict[str, Any]) -> str:
        # Simple substitution based on available keys in test_instance
        # More sophisticated logic might be needed if placeholders are complex
        data_to_format = {}
        if "text" in test_instance:
            data_to_format["text"] = test_instance["text"]
            # Try common placeholders if 'text' is the key
            # This is heuristic; ideally, tests.json keys match template placeholders
            placeholders = re.findall(r'\{([^}]+)\}', template)
            if len(placeholders) == 1:
                # If single placeholder like {problem} or {task}, map 'text' to it
                if placeholders[0] not in ["texts"]: # Avoid overwriting if {texts} is explicitly used
                    data_to_format[placeholders[0]] = test_instance["text"]
        
        if "texts" in test_instance:
            # Ensure texts are passed as a string representation (e.g., JSON string) if template expects a single string placeholder
            # Or, if the template is designed to iterate or handle a list, this might need adjustment.
            # For now, assume {texts} expects a string (e.g. json.dumps(test_instance["texts"]))
            # The current example for sentiment_analysis expects {texts} to be a string of a list
            data_to_format["texts"] = json.dumps(test_instance["texts"])

        try:
            return template.format(**data_to_format)
        except KeyError as e:
            # Fallback if specific keys like {problem} or {task} are missing but {text} might work
            if 'text' in data_to_format and 'text' not in str(e):
                 try: 
                     return template.format(text=data_to_format['text']) 
                 except Exception:
                     pass # If this also fails, original error is more informative
            raise ValueError(f"Failed to format prompt. Missing key: {e}. Template: '{template}', Data: {data_to_format}")
        except Exception as e:
            raise ValueError(f"Error formatting prompt: {e}. Template: '{template}', Data: {data_to_format}")

    def run_test(self, test_id: str, llm_id_str: str) -> Dict[str, Any]:
        test_instance = self.config_manager.get_test_instance_by_id(test_id)
        if not test_instance:
            raise ValueError(f"Test instance '{test_id}' not found.")

        llm_config = self.config_manager.get_llm_config_by_id(llm_id_str)
        if not llm_config:
            raise ValueError(f"LLM configuration for '{llm_id_str}' not found.")

        test_class_config = self.config_manager.get_test_class_by_id(test_instance["class_id"])
        if not test_class_config:
            raise ValueError(f"Test class '{test_instance['class_id']}' not found.")

        # Prepare prompt
        system_prompt = test_class_config.get("system_prompt")
        # LLM's base_system_prompt is handled by LLMManager if test-specific one isn't provided
        
        work_prompt_template_str = self._get_prompt_template(test_class_config, llm_id_str)
        if not work_prompt_template_str:
             raise ValueError(f"No work prompt template found for test class '{test_class_config['id']}' and LLM '{llm_id_str}'.")
        
        work_prompt = self._format_prompt(work_prompt_template_str, test_instance)

        # Get LLM response
        response_text, execution_time_ms = self.llm_manager.run(
            llm_config=llm_config,
            prompt=work_prompt,
            system_prompt=system_prompt
        )

        # Evaluate response
        # Merge parameters: instance overrides class defaults
        eval_module_class_config = test_class_config.get("evaluation_module", {})
        eval_module_instance_config = test_instance.get("evaluation_module", {})
        
        eval_module_name = eval_module_instance_config.get("name") or eval_module_class_config.get("name")
        if not eval_module_name:
            raise ValueError(f"Evaluation module name not specified for test '{test_id}'.")

        eval_parameters = dict(eval_module_class_config.get("parameters", {}))
        eval_parameters.update(eval_module_instance_config.get("parameters", {}))

        score = 0.0
        eval_details = "Evaluation skipped: Error loading/running evaluator."
        try:
            # Dynamically import the evaluator module
            # Assumes evaluators are in poor_bench.evaluators package
            evaluator_module_path = f"poor_bench.evaluators.{eval_module_name}"
            module = importlib.import_module(evaluator_module_path)
            score, eval_details = module.evaluate(response_text, eval_parameters)
        except ImportError:
            eval_details = f"Evaluation module '{evaluator_module_path}' not found."
            print(f"ERROR: {eval_details}")
        except AttributeError:
            eval_details = f"'evaluate' function not found in module '{evaluator_module_path}'."
            print(f"ERROR: {eval_details}")
        except Exception as e:
            eval_details = f"Error during evaluation with '{eval_module_name}': {str(e)}"
            print(f"ERROR: {eval_details}")

        # Construct and save result
        result_entry = {
            "test_id": test_id,
            "score": float(score),
            "details": eval_details,
            "response": response_text,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "execution_time_ms": execution_time_ms,
            "think": llm_config.get("parameters", {}).get("think", False)
        }

        results_data = self.config_manager.load_results()
        if llm_id_str not in results_data["results"]:
            results_data["results"][llm_id_str] = []
        
        # Remove any previous result for this specific test_id and llm_id_str before appending new one
        results_data["results"][llm_id_str] = [
            r for r in results_data["results"][llm_id_str] if r["test_id"] != test_id
        ]
        results_data["results"][llm_id_str].append(result_entry)
        self.config_manager.save_results(results_data)

        return result_entry