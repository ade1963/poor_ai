import os
import json
import yaml
from typing import Dict, List, Any, Optional
from .llm_manager import LLMManager # Assuming llm_manager.py is in the same directory

class ConfigManager:
    def __init__(self, base_path: str = None):
        if base_path is None:
            # Default base_path to the directory containing this config_manager.py file
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        else:
            self.base_path = base_path
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.base_path, filename)
        if not os.path.exists(path):
            # For results.json, return an empty structure if it doesn't exist
            if filename == "results.json":
                return {"version": "1.0", "results": {}}
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, filename: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self.base_path, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.base_path, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_results(self) -> Dict[str, Any]:
        return self._load_json("results.json")
    
    def save_results(self, results_data: Dict[str, Any]) -> None:
        self._save_json("results.json", results_data)
    
    def get_pending_tests(self, llm_id_str: str, target_test_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        all_tests_config = self.load_tests()
        all_test_instances = all_tests_config.get("tests", [])
        
        current_results_data = self.load_results()
        llm_results = current_results_data.get("results", {}).get(llm_id_str, [])
        completed_test_ids = {result["test_id"] for result in llm_results}
        
        pending_tests = [] 
        if target_test_ids is not None:
            # Filter by specific test IDs if provided
            for test_instance in all_test_instances:
                if test_instance["test_id"] in target_test_ids and test_instance["test_id"] not in completed_test_ids:
                    pending_tests.append(test_instance)
        else:
            # Otherwise, consider all tests not yet completed
            for test_instance in all_test_instances:
                if test_instance["test_id"] not in completed_test_ids:
                    pending_tests.append(test_instance)
        return pending_tests

    def load_test_classes(self) -> Dict[str, Any]:
        """Load test classes from YAML configuration."""
        return self._load_yaml("test_classes.yaml")
    
    def load_tests(self) -> Dict[str, Any]:
        """Load test instances from JSON configuration."""
        return self._load_json("tests.json")
    
    def get_test_instance_by_id(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single test instance by its ID."""
        all_tests = self.load_tests().get("tests", [])
        for test in all_tests:
            if test["test_id"] == test_id:
                return test
        return None

    def load_llms(self) -> Dict[str, Any]:
        """Load LLM configurations from JSON."""
        return self._load_json("llms.json")

    def get_llm_config_by_id(self, llm_id_str: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single LLM configuration by its ID (provider:name:think)."""
        all_llms = self.load_llms().get("llms", [])
        try:
            #provider, name, think_str = llm_id_str.split(":", 2)
            provider, name, think_str = LLMManager.split_llm_id(llm_id_str)
            think = think_str.lower() == "true"
        except ValueError:
            # Fallback for legacy llm_id_str format (provider:name)
            provider, name = llm_id_str.split(":") if ":" in llm_id_str else (None, llm_id_str)
            think = None  # Allow matching configs without think mode for backward compatibility
        for llm_config in all_llms:
            config_id = f"{llm_config['provider']}:{llm_config['name']}"
            config_think = llm_config.get("parameters", {}).get("think", False)
            if config_id == f"{provider}:{name}" and (think is None or config_think == think):
                return llm_config
        return None

    def get_test_class_by_id(self, class_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single test class configuration by its ID."""
        all_test_classes = self.load_test_classes().get("test_classes", [])
        for tc in all_test_classes:
            if tc["id"] == class_id:
                return tc
        return None
