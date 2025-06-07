import json
import logging
import os
import platform
import subprocess
import tempfile
import time
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional
from pathlib import Path
from openai import OpenAI
#from openai.error import APIError, APIConnectionError, RateLimitError
from openai._exceptions import APIError, APIConnectionError, RateLimitError

class ModelManager:
    def __init__(self, config_path: str = 'models.json', app_config_path: str = 'config.json'):
        # Initialize logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ModelManager")

        # Load configurations
        self.models = self._load_models(config_path)
        self.app_config = self._load_app_config(app_config_path)
        self.current_model = None
        self._set_default_model()

    def _setup_logging(self):
        """Set up logging with rotating file handler."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:  # Avoid adding handlers multiple times
            logger.setLevel(logging.INFO)
            handler = RotatingFileHandler(
                'model_manager.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    def _load_models(self, config_path: str) -> Dict:
        """Load model configurations from models.json."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                models = json.load(f)['models']
                self.logger.info(f"Loaded models from {config_path}")
                return models
        except Exception as e:
            self.logger.error(f"Error loading models from {config_path}: {e}")
            return []

    def _load_app_config(self, config_path: str) -> Dict:
        """Load application configuration from config.json."""
        default_config = {'display_app': 'notepad' if platform.system() == 'Windows' else 'gedit'}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.info(f"Loaded app config from {config_path}")
                return config
        except FileNotFoundError:
            self.logger.warning(f"App config file {config_path} not found, using default")
            return default_config
        except Exception as e:
            self.logger.error(f"Error loading app config from {config_path}: {e}")
            return default_config

    def _set_default_model(self):
        """Set the default model (first in the list)."""
        if self.models:
            self.current_model = self.models[0]
            self.logger.info(f"Set default model: {self.current_model['name']}")
        else:
            self.logger.warning("No models available to set as default")

    def set_model(self, model_name: str) -> bool:
        """Set the current model by name."""
        for model in self.models:
            if model['name'] == model_name:
                self.current_model = model
                self.logger.info(f"Switched to model: {model_name}")
                return True
        self.logger.error(f"Model {model_name} not found")
        print(f"Model {model_name} not found.")
        return False

    def generate(self, prompt: str) -> Optional[str]:
        """Generate a response from the current model."""
        if not self.current_model:
            self.logger.error("No model selected")
            print("No model selected.")
            return None
    
        try:
            self.logger.info(f"Processing with provider {self.current_model['provider']} for model {self.current_model['name']}")
            self.logger.info(f"Generating response for prompt: {prompt[:50]}...")
    
            messages = [
                {"role": "system", "content": self.current_model['system_prompt']}
            ] if self.current_model.get('system_prompt') else []
            messages.append({"role": "user", "content": prompt})
    
            start_time = time.time()
    
            if self.current_model['provider'] == "ollama":
                client = OpenAI(
                    base_url=self.current_model['endpoint'],
                    api_key='ollama'
                )
                response = client.chat.completions.create(
                    model=self.current_model['name'],
                    messages=messages,
                    temperature=self.current_model.get('temperature', None),
                    top_p=self.current_model.get('top_p', None),
                    max_tokens=self.current_model.get('max_tokens', None)
                )
                result = response.choices[0].message.content
                duration = time.time() - start_time
                token_usage = getattr(response, 'usage', None)
                token_info = {
                    'prompt_tokens': token_usage.prompt_tokens if token_usage else 'N/A',
                    'completion_tokens': token_usage.completion_tokens if token_usage else 'N/A'
                }
                # Calculate cost
                cost = 0
                if token_usage and 'pricing' in self.current_model:
                    input_cost = token_usage.prompt_tokens * self.current_model['pricing']['input_tokens'] / 1000000
                    output_cost = token_usage.completion_tokens * self.current_model['pricing']['output_tokens'] / 1000000
                    cost = input_cost + output_cost
                self.logger.info(
                    f"Response received successfully from ollama. "
                    f"Duration: {duration:.2f}s, "
                    f"Prompt Tokens: {token_info['prompt_tokens']}, "
                    f"Completion Tokens: {token_info['completion_tokens']}, "
                    f"Cost: ${cost:.6f}"
                )
    
            elif self.current_model['provider'] == "openrouter":
                api_key = os.getenv("OPENROUTER_API_KEY")
                if not api_key:
                    self.logger.error("OPENROUTER_API_KEY environment variable not set")
                    print("OPENROUTER_API_KEY environment variable not set")
                    return None
                client = OpenAI(
                    base_url=self.current_model['endpoint'],
                    api_key=api_key,
                    default_headers={
                        "HTTP-Referer": "http://localhost",
                        "X-Title": "ModelManager"
                    }
                )
                try:
                    response = client.chat.completions.create(
                        model=self.current_model['name'],
                        messages=messages,
                        temperature=self.current_model.get('temperature', None),
                        top_p=self.current_model.get('top_p', None),
                        max_tokens=self.current_model.get('max_tokens', None)
                    )
                    if not response or not hasattr(response, 'choices') or not response.choices:
                        error_msg = "Invalid response from OpenRouter API: Empty or malformed response"
                        self.logger.error(error_msg)
                        if hasattr(response, 'headers'):
                            self.logger.error(f"Response headers: {response.headers}")
                        print(error_msg)
                        print("Response may be empty or lack expected 'choices' structure.")
                        return None
                    result = response.choices[0].message.content
                    duration = time.time() - start_time
                    token_usage = getattr(response, 'usage', None)
                    token_info = {
                        'prompt_tokens': token_usage.prompt_tokens if token_usage else 'N/A',
                        'completion_tokens': token_usage.completion_tokens if token_usage else 'N/A'
                    }
                    # Calculate cost
                    cost = 0
                    if token_usage and 'pricing' in self.current_model:
                        input_cost = token_usage.prompt_tokens * self.current_model['pricing']['input_tokens'] / 1000000
                        output_cost = token_usage.completion_tokens * self.current_model['pricing']['output_tokens'] / 1000000
                        cost = input_cost + output_cost
                    self.logger.info(
                        f"Response received successfully from openrouter. "
                        f"Duration: {duration:.2f}s, "
                        f"Prompt Tokens: {token_info['prompt_tokens']}, "
                        f"Completion Tokens: {token_info['completion_tokens']}, "
                        f"Cost: ${cost:.6f}"
                    )
                except APIError as api_error:
                    error_msg = (
                        f"OpenRouter API error: {str(api_error)}\n"
                        f"Error code: {api_error.code if hasattr(api_error, 'code') else 'N/A'}\n"
                        f"Error type: {api_error.type if hasattr(api_error, 'type') else 'N/A'}\n"
                        f"Response body: {api_error.body if hasattr(api_error, 'body') else 'N/A'}"
                    )
                    self.logger.error(error_msg)
                    print("OpenRouter API call failed:")
                    print(f"Error: {str(api_error)}")
                    print(f"Error code: {api_error.code if hasattr(api_error, 'code') else 'N/A'}")
                    print(f"Error type: {api_error.type if hasattr(api_error, 'type') else 'N/A'}")
                    print(f"Response body: {api_error.body if hasattr(api_error, 'body') else 'N/A'}")
                    return None
                except APIConnectionError as conn_error:
                    error_msg = f"OpenRouter connection error: {str(conn_error)}"
                    self.logger.error(error_msg)
                    print("OpenRouter connection error:")
                    print(f"Error: {str(conn_error)}")
                    print("Check network connectivity or endpoint configuration.")
                    return None
                except RateLimitError as rate_error:
                    error_msg = f"OpenRouter rate limit exceeded: {str(rate_error)}"
                    self.logger.error(error_msg)
                    print("OpenRouter rate limit exceeded:")
                    print(f"Error: {str(rate_error)}")
                    print("Please wait and try again later or check your API quota.")
                    return None
                except Exception as e:
                    error_msg = f"Unexpected error during OpenRouter API call: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)  # Include stack trace in logs
                    print("Unexpected error during OpenRouter API call:")
                    print(f"Error: {str(e)}")
                    print("Check logs for detailed stack trace.")
                    return None
    
            elif self.current_model['provider'] == "fake":
                # Create temp file with request content
                content = f"Request:\n{json.dumps(messages, indent=2)}\n\nResponse:\n(Enter your response here)"
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name

                self.logger.info(f"Opening temp file {temp_file_path} in notepad for fake provider")
                try:
                    # Open notepad and wait for it to close
                    subprocess.run(['notepad', temp_file_path], check=True)
                    # Read the modified content
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        modified_content = f.read()
                    # Extract response (assume everything after "Response:\n" is the response)
                    response_start = modified_content.find("Response:\n") + len("Response:\n")
                    result = modified_content[response_start:].strip()
                    duration = time.time() - start_time
                    # Fake token usage for consistency
                    token_info = {
                        'prompt_tokens': len(prompt.split()),
                        'completion_tokens': len(result.split())
                    }
                    # Calculate cost
                    cost = 0
                    if 'pricing' in self.current_model:
                        input_cost = token_info['prompt_tokens'] * self.current_model['pricing']['input_tokens'] / 1000000
                        output_cost = token_info['completion_tokens'] * self.current_model['pricing']['output_tokens'] / 1000000
                        cost = input_cost + output_cost
                    self.logger.info(
                        f"Response received from fake provider. "
                        f"Duration: {duration:.2f}s, "
                        f"Prompt Tokens: {token_info['prompt_tokens']}, "
                        f"Completion Tokens: {token_info['completion_tokens']}, "
                        f"Cost: ${cost:.6f}"
                    )
                    # Clean up temp file
                    Path(temp_file_path).unlink(missing_ok=True)
                except Exception as e:
                    self.logger.error(f"Error processing fake provider: {e}")
                    print(f"Error processing fake provider: {e}")
                    Path(temp_file_path).unlink(missing_ok=True)
                    return None
    
            else:
                self.logger.error(f"Unsupported provider: {self.current_model['provider']}")
                print(f"Unsupported provider: {self.current_model['provider']}")
                return None
    
            # Display request and response
            self._display_request_response(messages, result)
            return result
    
        except Exception as e:
            self.logger.error(f"Error generating response: {e}", exc_info=True)
            print(f"Error generating response: {e}")
            print("Check logs for detailed stack trace.")
            return None

    def _display_request_response(self, request: list, response: str):
        """Save request and response to a temp file and open with configured app."""
        if not self.app_config.get('display_request_response', True):
            self.logger.info("Request/response display disabled in config")
            return
        try:
            content = f"Request:\n{json.dumps(request, indent=2)}\n\nResponse:\n{response}"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            display_app = self.app_config.get('display_app', 'notepad' if platform.system() == 'Windows' else 'gedit')
            self.logger.info(f"Displaying request/response using {display_app}")

            if platform.system() == 'Windows':
                subprocess.run([display_app, temp_file_path], check=True)
            else:
                subprocess.run([display_app, temp_file_path], check=True)

            # Optionally, clean up the temp file after display (can be commented out for debugging)
            Path(temp_file_path).unlink(missing_ok=True)
        except Exception as e:
            self.logger.error(f"Error displaying request/response: {e}")
            print(f"Error displaying request/response: {e}")

    def get_current_model(self) -> Optional[Dict]:
        """Return the current model configuration."""
        self.logger.info(f"Retrieved current model: {self.current_model['name'] if self.current_model else 'None'}")
        return self.current_model
