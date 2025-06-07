import json
import logging
import os
import platform
import subprocess
import tempfile
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# Check if openai is available and import it
try:
    import openai
except ImportError:
    openai = None

log = logging.getLogger(__name__)

class ModelManager:
    """Manages AI model interactions, supporting multiple providers."""

    def __init__(self, models_config_path: Path, app_config_path: Path, project_dir: Path):
        self.project_dir = project_dir
        self._setup_logging()

        self.app_config = self._load_app_config(app_config_path)
        self.models = self._load_models(models_config_path)
        self.current_model = None
        self._set_default_model()

        if openai is None:
            log.warning("OpenAI library not found. OpenRouter provider will be unavailable.")

    def _setup_logging(self):
        log_dir = self.project_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / 'model_manager.log',
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)

    def _load_app_config(self, app_config_path: Path) -> dict:
        try:
            with open(app_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.warning(f"Could not load app config at {app_config_path}: {e}. Using defaults.")
            return {
                'display_app': 'notepad' if platform.system() == 'Windows' else 'gedit',
                'display_request_response': False
            }

    def _load_models(self, config_path: Path) -> dict:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Create a dictionary mapping model names to their configs
                return {model['name']: model for model in data.get('models', [])}
        except (FileNotFoundError, json.JSONDecodeError):
            log.error(f"models.json not found or invalid at {config_path}. No models loaded.")
            print(f"Error: 'models.json' is missing or corrupted. Please create one.")
            return {}

    def _set_default_model(self):
        if self.models:
            self.current_model = next(iter(self.models.values()))
            log.info(f"Default model set to: {self.current_model['name']}")
        else:
            log.warning("No models available to set a default.")

    def list_models(self) -> list:
        return list(self.models.keys())

    def set_model(self, model_identifier: str) -> bool:
        # Try to match by index first
        try:
            index = int(model_identifier)
            if 0 <= index < len(self.models):
                model_name = list(self.models.keys())[index]
                self.current_model = self.models[model_name]
                log.info(f"Switched model to '{self.current_model['name']}' by index {index}.")
                return True
        except (ValueError, IndexError):
            pass # Not a valid index, try matching by name
        
        # Match by name
        if model_identifier in self.models:
            self.current_model = self.models[model_identifier]
            log.info(f"Switched model to: {self.current_model['name']}")
            return True
        
        log.warning(f"Model '{model_identifier}' not found in models.json.")
        return False

    def get_current_model(self) -> Optional[Dict[str, Any]]:
        return self.current_model

    def generate(self, prompt: str) -> Optional[tuple[str, dict, float]]:
        if not self.current_model:
            log.error("Cannot generate, no model selected.")
            print("No model is selected. Use 'model list' and 'model use <name>'.")
            return None

        provider = self.current_model.get('provider')
        system_prompt = self.current_model.get('system_prompt', 'You are a helpful assistant.')
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        start_time = time.time()
        try:
            if provider == 'ollama':
                result = self._generate_ollama(messages)
            elif provider == 'openrouter' or provider == 'llm7':
                result = self._generate_openrouter(messages, provider)
            elif provider == 'fake':
                result = self._generate_fake(prompt)
            else:
                log.error(f"Unknown provider: {provider}")
                print(f"Error: Unknown provider '{provider}' for model '{self.current_model['name']}'.")
                return None
        except Exception as e:
            log.error(f"An unexpected error occurred during generation with {provider}: {e}", exc_info=True)
            print(f"An error occurred: {e}")
            return None
        
        end_time = time.time()
        log.info(f"Generation took {end_time - start_time:.2f} seconds.")

        if not result:
            return None
        
        raw_response, token_info, cost = result
        
        if self.app_config.get('display_request_response', False):
            self._display_request_response(prompt, raw_response)

        return raw_response, token_info, cost

    def _generate_ollama(self, messages: list):
        endpoint = self.current_model['endpoint']
        model_name = self.current_model['name']
        parameters = self.current_model.get('parameters', {})
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False # Required for think parameter and proper JSON response
        }

        # Add think parameter if present (specific to some ollama versions)
        if parameters.get('think', False):
            payload['think'] = True
        
        # Add standard OpenAI-compatible parameters to 'options'
        for key in ['temperature', 'top_k', 'top_p']:
            if key in parameters:
                payload[key] = parameters[key]
        if 'max_tokens' in parameters:
            # Ollama uses 'num_predict' for max_tokens
            payload['num_predict'] = parameters['max_tokens']

        log.debug(f"Ollama payload: {json.dumps(payload, indent=2)}")
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(f"{endpoint}/api/chat", json=payload, headers=headers, timeout=1200)

            response.raise_for_status()
            data = response.json()
            
            content = data['message']['content']
            # Token info from Ollama response
            token_info = {
                'prompt_tokens': data.get('prompt_eval_count', 0),
                'completion_tokens': data.get('eval_count', 0)
            }
            cost = self._calculate_cost(token_info)
            return content, token_info, cost

        except requests.RequestException as e:
            log.error(f"Ollama API request failed: {e}")
            print(f"Error connecting to Ollama at {endpoint}: {e}")
            return None

    def _generate_openrouter(self, messages: list, provider: str):
        if openai is None:
            log.error("OpenRouter provider is unavailable because the 'openai' library is not installed.")
            print("Cannot use OpenRouter: Please run 'pip install openai'.")
            return None
        
        if provider == 'openrouter':
            api_key = os.environ.get("OPENROUTER_API_KEY")
        elif provider == 'llm7':
            api_key = 'unused'
        if not api_key:
            log.error("OPENROUTER_API_KEY environment variable not set.")
            print("Error: OPENROUTER_API_KEY is not set.")
            return None

        client = openai.OpenAI(
            base_url=self.current_model['endpoint'],
            api_key=api_key,
        )

        try:
            completion = client.chat.completions.create(
                model=self.current_model['name'],
                messages=messages,
                **self.current_model.get('parameters', {})
            )
            content = completion.choices[0].message.content
            token_usage = getattr(content, 'usage', None)
            token_info = {
                'prompt_tokens': token_usage.prompt_tokens if token_usage else 'N/A',
                'completion_tokens': token_usage.completion_tokens if token_usage else 'N/A'
            }
            cost = self._calculate_cost(token_info)
            return content, token_info, cost
        
        except openai.APIError as e:
            log.error(f"OpenRouter API Error: {e.status_code} - {e.response}")
            print(f"OpenRouter API Error: {e.message}")
            return None
        except Exception as e:
            log.error(f"An unexpected error occurred with OpenRouter: {e}")
            print(f"An error occurred with OpenRouter: {e}")
            return None

    def _generate_fake(self, prompt: str):
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as tf:
                tf_path = tf.name
                tf.write(f"--- PROMPT ---\n{prompt}\n\n--- YOUR RESPONSE BELOW ---\n")
            
            editor = self.app_config.get('display_app', 'notepad')
            print(f"Opening '{editor}' for you to provide the AI response. Save and close the file to continue.")
            subprocess.run([editor, tf_path], check=True)

            with open(tf_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
            
            os.unlink(tf_path)
            response = full_content.split('--- YOUR RESPONSE BELOW ---')[1].strip()
            
            token_info = {'prompt_tokens': 0, 'completion_tokens': 0}
            return response, token_info, 0.0

        except Exception as e:
            log.error(f"Fake generator failed: {e}")
            print(f"Error with fake generator: {e}")
            return None

    def _calculate_cost(self, token_info: dict) -> float:
        pricing = self.current_model.get('pricing', {})
        input_cost = token_info.get('prompt_tokens', 0) * pricing.get('input_tokens', 0)
        output_cost = token_info.get('completion_tokens', 0) * pricing.get('output_tokens', 0)
        return input_cost + output_cost

    def _display_request_response(self, request: str, response: str):
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as tf:
                tf_path = tf.name
                tf.write("--- REQUEST PROMPT ---\n")
                tf.write(request)
                tf.write("\n\n--- AI RESPONSE ---\n")
                tf.write(response)
            
            editor = self.app_config.get('display_app', 'notepad')
            subprocess.Popen([editor, tf_path])
        except Exception as e:
            log.error(f"Failed to display request/response in editor: {e}")
