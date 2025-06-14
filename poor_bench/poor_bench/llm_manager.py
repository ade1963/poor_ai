import os
import json
import requests
import time
import re
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI

class LLMManager:
    """
    Handles all LLM API interactions for poor_bench. Add LLM providers here as needed.
    Usage:
        response, exec_time_ms = LLMManager().run(
            llm_config, prompt, system_prompt, extra_params={}
        )
    llm_config is a dict from llms.json; prompt is user/work prompt; system_prompt may be from test class.
    """
    def __init__(self):
        self.provider_handlers = {
            "openai": self._call_openai,
            "ollama": self._call_ollama,
            "llm7": self._call_openai_compartible,
            "openrouter": self._call_openai_compartible
        }

    def run(
        self, 
        llm_config: Dict[str, Any], 
        prompt: str,
        system_prompt: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        remove_think_tag: bool = True  # Remove first occurrence of <think>...</think> tags and content
    ) -> Tuple[str, int]:
        """
        Runs a prompt against the given LLM config, returning response text and execution time ms.
        If remove_think_tag is True, removes first occurrence of <think>...</think> tags and their content.
        """
        provider = llm_config.get("provider")
        handler = self.provider_handlers.get(provider)
        if handler is None:
            raise ValueError(f"Unknown/unsupported provider '{provider}' in LLM config.")
        params = dict(llm_config.get('parameters', {}))
        if extra_params:
            params.update(extra_params)
        start = time.time()
        try:
            completion = handler(
                llm_config=llm_config,
                prompt=prompt,
                system_prompt=system_prompt,
                parameters=params
            )
            # Remove first occurrence of <think>...</think> tags and content if requested
            if remove_think_tag:
                completion = re.sub(r'<think>.*?</think>', '', completion, count=1, flags=re.DOTALL)
        except Exception as e:
            completion = f"[API ERROR] {e}"
        exec_time = int((time.time() - start)*1000)
        return completion, exec_time

    def _call_openai(
        self,
        llm_config: Dict[str, Any],
        prompt: str,
        system_prompt: Optional[str],
        parameters: Dict[str, Any]
    ) -> str:
        endpoint = llm_config["endpoint"].rstrip('/')
        api_key_env = llm_config.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env)
        model = llm_config["name"] if ':' not in llm_config["name"] else llm_config["name"].split(':')[0]
        messages = []
        # OpenAI expects messages for chat; use system/user as needed
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif llm_config.get("base_system_prompt"):
            messages.append({"role": "system", "content": llm_config["base_system_prompt"]})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        payload.update({k: v for k, v in parameters.items() 
                        if k not in ("top_k", "api_key_env", "endpoint", "think")})
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            resp = requests.post(f"{endpoint}/chat/completions", headers=headers, json=payload, timeout=60*10) # 10 min
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")
        data = resp.json()
        # Defensive: Try to extract message content
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)

    def _call_ollama(
        self,
        llm_config: Dict[str, Any],
        prompt: str,
        system_prompt: Optional[str],
        parameters: Dict[str, Any]
    ) -> str:
        endpoint = llm_config["endpoint"].rstrip('/')
        model = llm_config["name"]
    
        if not system_prompt:
            system_prompt = system_prompt or llm_config.get("base_system_prompt")
    
        options = {}
        options.update({k: v for k, v in parameters.items() if k != "think"})
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "think": parameters.get("think", False),
            "stream": False,
            "options": options
        }
        headers = {"Content-Type": "application/json"}
    
        try:
            resp = requests.post(f"{endpoint}/api/generate", headers=headers, json=payload, timeout=60*10) # 10 min
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Ollama API call failed: {e}")
    
        data = resp.json()
        return data["response"]
    
    
    def _call_openai_compartible(
        self,
        llm_config: Dict[str, Any],
        prompt: str,
        system_prompt: Optional[str],
        parameters: Dict[str, Any]
    ) -> str:
        endpoint = llm_config["endpoint"].rstrip('/')
        model = llm_config["name"]
        provider = llm_config["provider"]

        syspt = ''
        if system_prompt or llm_config.get("base_system_prompt"):
            syspt = system_prompt or llm_config.get("base_system_prompt")

        messages = [
            {"role": "system", "content": syspt}
        ] if syspt else []
        messages.append({"role": "user", "content": prompt})
        api_key = "no_key"
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")    

        client = OpenAI(
                base_url=endpoint,
                api_key=api_key
            )
        response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=parameters.get('temperature', None),
                top_p=parameters.get('top_p', None),
                max_tokens=parameters.get('max_tokens', None)
            )
        result = response.choices[0].message.content
        return result

    @staticmethod
    def llm_id(llm_config: Dict[str, Any]) -> str:
        provider = llm_config.get("provider", "")
        name = llm_config.get("name", "")
        think = llm_config.get("parameters", {}).get("think", False)
        return f"{provider}:{name}:{'true' if think else 'false'}"

    @staticmethod
    def split_llm_id(llm_id_str: str):
        parts = llm_id_str.split(":")
        provider = parts[0]
        if parts[-1].lower() in ("true", "false"):
            think_str = parts[-1]
            name = ":".join(parts[1:-1])
        else:
            think_str = None
            name = ":".join(parts[1:])

        return provider, name, think_str
