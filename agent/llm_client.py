"""Plug-and-play LLM Client Interface for Project Priory.

Supports:
1. GeminiLLMClient (Live Google GenAI Gemini with automatic fallback on API policy/quota limits).
2. LocalOllamaClient (Connects to local models like LLaMA 3.2 or Qwen 2.5 via Ollama).
3. RuleBasedMockLLMClient (Zero setup, deterministic fallback for offline tests/demos).
"""

from __future__ import annotations
import os
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        """Generates structured output conforming to a Pydantic schema."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str) -> str:
        """Generates freeform natural language text."""
        pass


class RuleBasedMockLLMClient(BaseLLMClient):
    """Deterministic, zero-dependency mock LLM client for offline pairing, tests, and CI/CD."""

    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        p_lower = prompt.lower()

        # Extract item name
        # Extract goal item dynamically from natural language prompt
        goal_item = "Twilight"
        verb_match = re.search(r"(?:craft|make|forge|get|buy|obtain|build|target)\s+(?:a\s+|an\s+|the\s+)?(?:\d+\s+)?([A-Za-z0-9'\s]+?)(?:\s+in|\s+with|\s+and|\s+for|\s+from|[.?!,;]|$)", prompt, re.IGNORECASE)
        if verb_match:
            candidate = verb_match.group(1).strip()
            candidate = re.sub(r"\b(tonight|today|now|please|asap|soon)\b", "", candidate, flags=re.I).strip()
            if candidate:
                if "sigil" in candidate.lower():
                    goal_item = "Legendary Sigil" if "legendary" in candidate.lower() or "legendary" in p_lower else "Sigil"
                elif "rune" in candidate.lower():
                    goal_item = "Legendary Rune" if "legendary" in candidate.lower() or "legendary" in p_lower else "Rune"
                else:
                    goal_item = candidate
        elif "sigil" in p_lower or "upgrades" in p_lower:
            goal_item = "Legendary Sigil"
        elif "dusk" in p_lower:
            goal_item = "Dusk"
        elif "clover" in p_lower or "mystic clover" in p_lower:
            goal_item = "Mystic Clover"

        # Extract target quantity (e.g. "2 legendary sigils", "3 twilight", "2 sigils", "2 leggy upgrades")
        target_qty = 1
        qty_match = re.search(r"(\d+)\s*(?:legendary|sigils?|twilight|dusk|clovers?|weapons?|items?|upgrades?|leggy)", p_lower)
        if qty_match:
            target_qty = int(qty_match.group(1))

        # Extract time budget
        time_budget = 120
        time_match = re.search(r"(\d+)\s*(?:hours?|hrs?|h)", p_lower)
        if time_match:
            time_budget = int(time_match.group(1)) * 60
        else:
            min_match = re.search(r"(\d+)\s*(?:minutes?|mins?|m)", p_lower)
            if min_match:
                time_budget = int(min_match.group(1))

        # Extract game mode preferences & exclusions
        excluded = []
        if "no pvp" in p_lower or "hate pvp" in p_lower or "avoid pvp" in p_lower:
            excluded.append("PvP")
        if "no wvw" in p_lower or "hate wvw" in p_lower or "avoid wvw" in p_lower:
            excluded.append("WvW")

        # Extract exhausted/completed sources (e.g. "already bought clovers from wizard vault")
        exhausted = []
        if "already bought" in p_lower or "vault" in p_lower and ("bought" in p_lower or "done" in p_lower or "finished" in p_lower):
            exhausted.append("WizardVault")
        if "provisioner" in p_lower and ("bought" in p_lower or "done" in p_lower or "finished" in p_lower):
            exhausted.append("Provisioners")

        # Extract gold budget
        gold_budget = None
        gold_match = re.search(r"(\d+)\s*g(?:old)?", p_lower)
        if gold_match:
            gold_budget = int(gold_match.group(1))

        # Instantiate target schema dynamically
        fields = schema.model_fields.keys()
        data: Dict[str, Any] = {}
        if "goal_item_query" in fields:
            data["goal_item_query"] = goal_item
        if "target_quantity" in fields:
            data["target_quantity"] = target_qty
        if "time_budget_minutes" in fields:
            data["time_budget_minutes"] = time_budget
        if "excluded_game_modes" in fields:
            data["excluded_game_modes"] = excluded
        if "exhausted_sources" in fields:
            data["exhausted_sources"] = exhausted
        if "liquid_gold_budget" in fields:
            data["liquid_gold_budget"] = gold_budget
        if "user_playstyle_notes" in fields:
            data["user_playstyle_notes"] = "Extracted from natural language prompt."

        return schema.model_validate(data)

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        return f"[Mock LLM Response based on prompt length {len(prompt)}]"


class GeminiLLMClient(BaseLLMClient):
    """Live LLM client using Google GenAI SDK (Gemini 2.0 Flash / 1.5 Flash)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment.")
        self.model = model
        self.fallback = RuleBasedMockLLMClient()

        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        from google.genai import types
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.1,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return schema.model_validate_json(response.text)
        except Exception:
            return self.fallback.generate_structured(prompt, system_prompt, schema)

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        from google.genai import types
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception:
            return self.fallback.generate_text(prompt, system_prompt)


class LocalOllamaClient(BaseLLMClient):
    """Client for local models via Ollama (e.g. http://localhost:11434)."""

    def __init__(self, model_name: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.fallback = RuleBasedMockLLMClient()

    def generate_structured(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        try:
            schema_json = json.dumps(schema.model_json_schema())
            full_prompt = (
                f"{system_prompt}\n\n"
                f"You MUST output valid JSON matching this schema:\n{schema_json}\n\n"
                f"User input:\n{prompt}\n\n"
                f"JSON Output:"
            )
            resp_text = self._post_generate(full_prompt, json_format=True)
            return schema.model_validate_json(resp_text)
        except Exception:
            return self.fallback.generate_structured(prompt, system_prompt, schema)

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        try:
            full_prompt = f"{system_prompt}\n\nUser:\n{prompt}\n\nAssistant:"
            return self._post_generate(full_prompt, json_format=False)
        except Exception:
            return self.fallback.generate_text(prompt, system_prompt)

    def _post_generate(self, prompt: str, json_format: bool = False) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if json_format:
            payload["format"] = "json"

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{self.host}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "{}")


def get_default_llm_client() -> BaseLLMClient:
    """Factory creating the best available LLM client."""
    # 1. Check for Gemini API Key
    if os.getenv("GEMINI_API_KEY"):
        try:
            return GeminiLLMClient()
        except Exception:
            pass

    # 2. Check if Ollama is running locally
    try:
        with httpx.Client(timeout=1.0) as client:
            r = client.get("http://localhost:11434/api/version")
            if r.status_code == 200:
                return LocalOllamaClient()
    except Exception:
        pass

    # 3. Default to built-in Mock provider
    return RuleBasedMockLLMClient()
