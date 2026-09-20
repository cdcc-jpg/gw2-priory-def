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
        user_part = prompt.split("New user message:\n")[-1] if "New user message:\n" in prompt else prompt
        p_user = user_part.lower()

        # Extract category filter from new user message (preventing context contamination)
        cat_filter = None
        cat_tokens = [
            "generation 1", "gen 1", "generation 2", "gen 2", "generation 3", "gen 3",
            "aurene", "soto", "obsidian", "janthir",
            "rings", "ring", "amulets", "amulet", "accessories", "accessory",
            "trinkets", "trinket", "backpack", "back", "jewelry", "armor",
            "upgrades", "upgrade", "spears", "spear"
        ]
        for term in cat_tokens:
            if re.search(r"\b" + re.escape(term) + r"\b", p_user):
                cat_filter = term
                break

        plural_map = {
            "rings": "ring",
            "amulets": "amulet",
            "accessories": "accessory",
            "trinkets": "trinket",
            "upgrades": "upgrade",
            "spears": "spear",
            "generation 1": "gen 1",
            "generation 2": "gen 2",
            "generation 3": "gen 3",
        }
        if cat_filter in plural_map:
            cat_filter = plural_map[cat_filter]

        # Extract target quantity (e.g. "2 legendaries", "which 2 legendaries", "fastest 2", "top 2 legendaries", "2 rings")
        target_qty = 1
        qty_match = re.search(
            r"\b(\d+)\s*(?:legendaries|legendary|sigils?|runes?|twilight|dusk|clovers?|weapons?|items?|upgrades?|leggy|rings?|amulets?|accessories?|trinkets?|backpacks?|spears?)\b",
            p_lower
        )
        if qty_match:
            target_qty = int(qty_match.group(1))
        else:
            count_match = re.search(r"\b(?:which|top|fastest|quickest|easiest|closest|best)\s+(\d+)\b", p_lower)
            if count_match:
                target_qty = int(count_match.group(1))

        # Extract time budget (supports decimal hours like 1.5 hours -> 90 minutes)
        time_budget = 120
        time_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)", p_lower)
        if time_match:
            time_budget = int(float(time_match.group(1)) * 60)
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

        # Extract exhausted/completed sources (e.g. "already bought all clovers from wizard's vault")
        exhausted = []
        if "already bought" in p_lower or ("vault" in p_lower and any(w in p_lower for w in ["bought", "done", "finished", "exhausted", "completed", "claimed", "sold out"])):
            exhausted.append("WizardVault")
        if "provisioner" in p_lower and any(w in p_lower for w in ["bought", "done", "finished", "exhausted", "completed"]):
            exhausted.append("Provisioners")

        # Extract gold budget
        gold_budget = None
        gold_match = re.search(r"(\d+)\s*g(?:old)?", p_lower)
        if gold_match:
            gold_budget = int(gold_match.group(1))

        # Specific item extraction
        specific_item_matches = [
            ("legendary sigil", "Legendary Sigil"),
            ("legendary rune", "Legendary Rune"),
            ("legendary relic", "Legendary Relic"),
            ("the moot", "The Moot"),
            ("the juggernaut", "The Juggernaut"),
            ("chuka and champawat", "Chuka and Champawat"),
            ("prismatic champion's regalia", "Prismatic Champion's Regalia"),
            ("ad infinitum", "Ad Infinitum"),
            ("the ascension", "The Ascension"),
            ("klobjarne geirr", "Klobjarne Geirr"),
            ("klobjarne harvester", "Klobjarne Geirr"),
            ("kamohoali'i kotaki", "Kamohoali'i Kotaki"),
            ("twilight", "Twilight"),
            ("sunrise", "Sunrise"),
            ("eternity", "Eternity"),
            ("kudzu", "Kudzu"),
            ("bolt", "Bolt"),
            ("incinerator", "Incinerator"),
            ("nevermore", "Nevermore"),
            ("astralaria", "Astralaria"),
            ("hope", "HOPE"),
            ("conflux", "Conflux"),
            ("coalescence", "Coalescence"),
            ("transcendence", "Transcendence"),
            ("vision", "Vision"),
            ("aurora", "Aurora"),
            ("warbringer", "Warbringer"),
            ("aurene's weight", "Aurene's Weight"),
            ("aurene's bite", "Aurene's Bite"),
            ("aurene's argument", "Aurene's Argument"),
            ("aurene's claw", "Aurene's Claw"),
            ("aurene's fang", "Aurene's Fang"),
            ("dusk", "Dusk"),
            ("mystic clover", "Mystic Clover"),
            ("mystic coin", "Mystic Coin"),
            ("ectoplasm", "Glob of Ectoplasm"),
            ("provisioner token", "Provisioner Token"),
        ]
        goal_item = None
        has_specific_item = False
        for pattern, canon_name in specific_item_matches:
            if re.search(r"\b" + re.escape(pattern) + r"\b", p_lower):
                goal_item = canon_name
                has_specific_item = True
                break

        if not goal_item:
            if re.search(r"\bsigils?\b", p_lower):
                goal_item = "Legendary Sigil"
                has_specific_item = True
            elif re.search(r"\brunes?\b", p_lower):
                goal_item = "Legendary Rune"
                has_specific_item = True
            elif re.search(r"\bclovers?\b", p_lower):
                goal_item = "Mystic Clover"
                has_specific_item = True

        # Extract currency
        currency_name = None
        currency_id = None
        if "astral acclaim" in p_lower or "astral" in p_lower:
            currency_name = "Astral Acclaim"
            currency_id = 68
        elif "clover" in p_lower or "mystic clover" in p_lower:
            currency_name = "Mystic Clover"
            currency_id = 19675
        elif "spirit shard" in p_lower:
            currency_name = "Spirit Shard"
            currency_id = 23
        elif "laurel" in p_lower:
            currency_name = "Laurel"
            currency_id = 3
        elif "fractal relic" in p_lower:
            currency_name = "Fractal Relic"
            currency_id = 7
        elif "volatile magic" in p_lower:
            currency_name = "Volatile Magic"
            currency_id = 45
        elif "provisioner token" in p_lower:
            currency_name = "Provisioner Token"
            currency_id = 29
        elif "karma" in p_lower:
            currency_name = "Karma"
            currency_id = 2
        elif "ectoplasm" in p_lower or "ecto" in p_lower:
            currency_name = "Glob of Ectoplasm"
            currency_id = 19721
        elif "mystic coin" in p_lower:
            currency_name = "Mystic Coin"
            currency_id = 19976
        elif "gold" in p_lower:
            currency_name = "Gold"
            currency_id = 1

        # Extract dragon facet variants
        facet_name = None
        for facet in ["zhaitan", "mordremoth", "kralkatorrik", "primordus", "jormag", "soo-won"]:
            if facet in p_lower:
                facet_name = facet.title()
                break

        # Extract acquisition / farming intent
        is_acquisition = any(k in p_lower for k in [
            "how do i farm", "how to farm", "ways to get", "where can i get", "where to get",
            "how to acquire", "farm clovers", "need mystic clovers", "without gambling",
            "without the mystic forge", "how to get"
        ])

        # Extract new goal types from the new user message (preventing context contamination)
        is_arbitrage = any(k in p_user for k in [
            "buy vs craft", "craft or buy", "arbitrage", "cheaper to buy",
            "profitable to craft", "craft vs buy", "buy or craft",
            "cheaper to craft", "should i craft or buy", "should i buy or craft"
        ])
        is_opportunity_cost = any(k in p_user for k in [
            "best use of", "opportunity cost", "spend astral acclaim",
            "clovers or gold", "clover or gold", "how should i spend",
            "where should i spend", "spend my laurels", "best way to spend"
        ])
        is_session = any(k in p_user for k in [
            "session", "itinerary", "routine", "playtime", "knapsack", "schedule"
        ]) or any(k in p_user for k in [
            "what should i do tonight", "what to do tonight", "what can i do tonight",
            "what should i do in", "what to do in"
        ]) or ("what should i do" in p_user and any(t in p_user for t in ["tonight", "today", "mins", "minutes", "hour"]))

        # Slot and comparative detection
        slot_terms = [
            "ring", "rings", "amulet", "amulets", "accessory", "accessories",
            "trinket", "trinkets", "backpack", "back", "jewelry", "armor",
            "upgrade", "upgrades", "spear", "spears"
        ]
        has_slot_term = any(re.search(r"\b" + re.escape(w) + r"\b", p_user) for w in slot_terms)
        has_action_or_rank = any(w in p_user for w in [
            "craft", "get", "make", "closest", "rank", "which", "what", "can i", "recommend",
            "top", "best", "fastest", "quickest", "easiest", "leaderboard", "how far", "how close"
        ])
        is_slot_query = has_slot_term and has_action_or_rank and not has_specific_item

        has_count_comparative = (
            bool(re.search(r"\b(?:which|what|top|fastest|quickest|easiest|closest|best)\s+\d+\b", p_user))
            or bool(re.search(r"\b\d+\s+legendaries\b", p_user))
            or bool(re.search(r"\b(?:which|what)\s+legendaries\b", p_user))
        )
        has_speed_qualifier = any(w in p_user for w in ["fastest", "quickest", "easiest"])
        has_plural_legendaries = bool(re.search(r"\blegendaries\b", p_user))

        comparative_phrases = [
            "closest", "which legendary", "which legendaries", "what legendary", "what legendaries",
            "rank all", "what should i craft", "what to craft", "leaderboard", "rank", "how far",
            "how close", "where am i", "what can i craft", "next legendary", "best legendary",
            "recommend", "fastest", "quickest", "can i quickly craft"
        ]
        has_comp_phrase = any(k in p_user for k in comparative_phrases)

        is_comparative = (
            (has_comp_phrase and not has_specific_item)
            or (has_plural_legendaries and not has_specific_item)
            or (has_count_comparative and not has_specific_item)
            or is_slot_query
            or (has_speed_qualifier and not has_specific_item and any(w in p_user for w in ["legendary", "legendaries", "craft", "make", "get", "item", "to craft"]))
            or (cat_filter is not None and not has_specific_item)
        )

        # Fix is_prerequisite: prevent broad category queries from hijacking into PREREQUISITE_AUDIT
        is_category_query = ((cat_filter is not None) or has_slot_term or has_plural_legendaries) and not has_specific_item

        is_prerequisite = (
            any(k in p_user for k in [
                "prerequisite", "prerequisites", "mastery", "masteries",
                "collection unlocked"
            ])
            or (any(k in p_user for k in ["am i ready", "ready to craft"]) and (has_specific_item or not is_category_query))
            or ("can i craft" in p_user and has_specific_item and not is_category_query)
        )
        if is_category_query and not has_specific_item:
            is_prerequisite = False

        # DO NOT default goal_item to "Twilight" if query contains comparative, ranking, or category patterns
        is_comp_or_cat = is_comparative or is_category_query
        if not goal_item and not is_comp_or_cat:
            goal_item = "Twilight"

        prefer_speed = any(w in p_lower for w in ["quick", "quickly", "fast", "fastest", "speed", "least effort", "instant", "soon"])
        prefer_cheap = any(w in p_lower for w in ["cheapest", "least gold", "cost effective", "cheap", "lowest cost", "save gold", "saving gold", "cheaper"])
        vault_exhausted = "WizardVault" in exhausted or "already bought" in p_lower or ("vault" in p_lower and any(w in p_lower for w in ["bought", "done", "finished", "exhausted", "completed", "claimed", "sold out"]))
        opt_target = "cheapest_gold" if (prefer_cheap or vault_exhausted) else None

        # Instantiate target schema dynamically
        fields = schema.model_fields.keys()
        data: Dict[str, Any] = {}
        if "goal_type" in fields:
            if is_arbitrage:
                data["goal_type"] = "ARBITRAGE_EVALUATION"
            elif is_prerequisite:
                data["goal_type"] = "PREREQUISITE_AUDIT"
            elif is_opportunity_cost:
                data["goal_type"] = "CURRENCY_OPPORTUNITY_COST"
            elif is_session:
                data["goal_type"] = "SESSION_ITINERARY"
            elif is_comparative or (cat_filter and not has_specific_item):
                data["goal_type"] = "COMPARATIVE_RANKING"
            elif is_acquisition:
                data["goal_type"] = "ACQUISITION_DISCOVERY"
            else:
                data["goal_type"] = "SPECIFIC_ITEM"
        if "target_item_name" in fields:
            data["target_item_name"] = None if ((is_comparative and not has_specific_item) or is_comp_or_cat or (is_session and not any(it in p_lower for it in ["twilight", "nevermore", "bolt", "sunrise", "eternity", "moot", "sigil"]))) else goal_item
        if "currency_name" in fields:
            data["currency_name"] = currency_name
        if "currency_id" in fields:
            data["currency_id"] = currency_id
        if "is_acquisition_query" in fields:
            data["is_acquisition_query"] = is_acquisition
        if "facet_name" in fields:
            data["facet_name"] = facet_name
        if "category_filter" in fields:
            data["category_filter"] = cat_filter
        if "prefer_speed" in fields:
            data["prefer_speed"] = prefer_speed
        if "prefer_cheap" in fields:
            data["prefer_cheap"] = prefer_cheap
        if "wizards_vault_exhausted" in fields:
            data["wizards_vault_exhausted"] = vault_exhausted or prefer_cheap
        if "optimization_target" in fields:
            data["optimization_target"] = opt_target
        if "goal_item_query" in fields:
            data["goal_item_query"] = cat_filter or goal_item
        if "is_ranking_query" in fields:
            data["is_ranking_query"] = is_comparative or is_comp_or_cat
        if "filter_category" in fields:
            data["filter_category"] = cat_filter
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

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment.")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.fallback = RuleBasedMockLLMClient()
        self.fallback_active = False
        self.last_error = None

        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    def check_liveness(self) -> bool:
        """Tests live provider connectivity with 1-token probe."""
        if self.fallback_active:
            return False
        try:
            from google.genai import types
            config = types.GenerateContentConfig(max_output_tokens=1)
            self.client.models.generate_content(
                model=self.model,
                contents="ping",
                config=config,
            )
            self.fallback_active = False
            return True
        except Exception as e:
            self.fallback_active = True
            self.last_error = str(e)
            return False

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
            self.fallback_active = False
            return schema.model_validate_json(response.text)
        except Exception as e:
            self.fallback_active = True
            self.last_error = str(e)
            print(f"[Gemini API Warning] Structured generation error: {e}")
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
            self.fallback_active = False
            return response.text or ""
        except Exception as e:
            self.fallback_active = True
            self.last_error = str(e)
            print(f"[Gemini API Warning] Text generation error: {e}")
            return self.fallback.generate_text(prompt, system_prompt)


class LocalOllamaClient(BaseLLMClient):
    """Client for local models via Ollama (e.g. http://localhost:11434)."""

    def __init__(self, model_name: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.fallback = RuleBasedMockLLMClient()
        self.fallback_active = False
        self.last_error = None

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
            self.fallback_active = False
            return schema.model_validate_json(resp_text)
        except Exception as e:
            self.fallback_active = True
            self.last_error = str(e)
            return self.fallback.generate_structured(prompt, system_prompt, schema)

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        try:
            full_prompt = f"{system_prompt}\n\nUser:\n{prompt}\n\nAssistant:"
            text = self._post_generate(full_prompt, json_format=False)
            self.fallback_active = False
            return text
        except Exception as e:
            self.fallback_active = True
            self.last_error = str(e)
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
