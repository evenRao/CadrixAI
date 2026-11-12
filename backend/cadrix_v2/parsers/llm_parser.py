from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from cadrix_v2.parsers.parser_interface import DesignParser, ParserOutput
from cadrix_v2.parsers.rule_based_parser import RuleBasedParser
from cadrix_v2.prompt_utils import unit_to_mm
from cadrix_v2.registry import MODEL_REGISTRY
from cadrix_v2.schemas import DesignIntent


DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
PREFERRED_OLLAMA_MODELS = (
    "llama3.1:8b",
    "llama3.2",
    "llama3",
    "qwen2.5",
    "mistral",
    "phi4",
)
INLINE_MEASUREMENT_RE = re.compile(r"^(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|in|inch|inches|\")?$", re.IGNORECASE)


class LLMParser(DesignParser):
    """
    Optional local-LLM parser that prefers Ollama and falls back safely.

    The rule-based parser remains the default V2 path. When users opt into
    LLM parsing, this parser will try a local Ollama instance first and return
    the rule-based result with a warning if Ollama is unavailable or produces
    invalid JSON.
    """

    def __init__(self) -> None:
        self._fallback = RuleBasedParser()

    @staticmethod
    def is_enabled() -> bool:
        return True

    def parse(self, prompt: str, requested_model_type: str | None = None) -> ParserOutput:
        fallback = self._fallback.parse(prompt, requested_model_type)

        try:
            payload = self._request_ollama_payload(prompt, requested_model_type, fallback)
        except Exception:
            return self._with_fallback(
                fallback,
                "LLM parsing was requested, but local Ollama was not reachable. Falling back to the rule-based parser.",
            )

        output = self._payload_to_output(payload, requested_model_type, fallback)
        if output.intent is None:
            return self._with_fallback(
                fallback,
                "LLM parsing was requested, but the Ollama response could not be validated. Falling back to the rule-based parser.",
            )
        return output

    @staticmethod
    def _ollama_host() -> str:
        return (os.getenv("CADRIX_OLLAMA_HOST") or os.getenv("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")

    def _resolve_ollama_model(self, host: str) -> str:
        env_model = os.getenv("CADRIX_OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL")
        if env_model:
            return env_model

        try:
            response = requests.get(f"{host}/api/tags", timeout=(2.0, 3.0))
            response.raise_for_status()
            payload = response.json()
            available = [item.get("name") for item in payload.get("models", []) if item.get("name")]
            for preferred in PREFERRED_OLLAMA_MODELS:
                if preferred in available:
                    return preferred
            if available:
                return available[0]
        except Exception:
            pass

        return DEFAULT_OLLAMA_MODEL

    def _request_ollama_payload(
        self,
        prompt: str,
        requested_model_type: str | None,
        fallback: ParserOutput,
    ) -> dict[str, Any]:
        host = self._ollama_host()
        model = self._resolve_ollama_model(host)
        instruction = self._build_instruction(prompt, requested_model_type, fallback)
        response = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": instruction,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1},
            },
            timeout=(2.5, 20.0),
        )
        response.raise_for_status()
        raw_text = (response.json().get("response") or "").strip()
        if not raw_text:
            raise ValueError("Empty Ollama response.")
        payload = self._extract_json_object(raw_text)
        payload["_ollama_model"] = model
        return payload

    @staticmethod
    def _extract_json_object(raw_text: str) -> dict[str, Any]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            payload = json.loads(cleaned)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in Ollama response.")

        payload = json.loads(cleaned[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("Ollama response was not a JSON object.")
        return payload

    def _build_instruction(
        self,
        prompt: str,
        requested_model_type: str | None,
        fallback: ParserOutput,
    ) -> str:
        fallback_intent = fallback.intent.model_dump() if fallback.intent else {}
        requested_model_note = requested_model_type or "none"
        supported_models = sorted(MODEL_REGISTRY.keys())
        schema = {
            "model_type": "supported model type string",
            "dimensions": {"numeric_parameter_mm": 75},
            "features": {"boolean_feature": True},
            "print_settings": {"tolerance_mm": 0.4},
            "assumptions": ["short human-readable assumption"],
            "warnings": ["short human-readable warning"],
        }
        return f"""
Return only valid JSON.
Use millimeters for all numeric dimensions and booleans for feature flags.
Do not include prose, markdown, or code fences.
If the request already names a supported model, keep that exact model type.
If a requested_model_type is provided, do not change it.

Supported model types:
{json.dumps(supported_models, indent=2)}

Requested model type:
{requested_model_note}

JSON schema:
{json.dumps(schema, indent=2)}

Rule-based draft intent for reference:
{json.dumps(fallback_intent, indent=2)}

Prompt:
{prompt}
""".strip()

    def _payload_to_output(
        self,
        payload: dict[str, Any],
        requested_model_type: str | None,
        fallback: ParserOutput,
    ) -> ParserOutput:
        fallback_intent = fallback.intent
        model_type = requested_model_type or payload.get("model_type")
        if model_type not in MODEL_REGISTRY and fallback_intent is not None:
            model_type = fallback_intent.model_type
        if model_type not in MODEL_REGISTRY:
            return ParserOutput(intent=None, errors=["The Ollama response did not include a supported model type."])

        dimensions = {
            **(fallback_intent.dimensions if fallback_intent else {}),
            **self._normalize_mapping(payload.get("dimensions")),
        }
        features = {
            **(fallback_intent.features if fallback_intent else {}),
            **self._normalize_mapping(payload.get("features")),
        }
        print_settings = {
            **(fallback_intent.print_settings if fallback_intent else {}),
            **self._normalize_mapping(payload.get("print_settings")),
        }

        assumptions = self._normalize_messages(payload.get("assumptions")) or fallback.assumptions
        warnings = self._normalize_messages(payload.get("warnings"))

        return ParserOutput(
            intent=DesignIntent(
                model_type=model_type,
                dimensions=dimensions,
                features=features,
                print_settings=print_settings,
            ),
            assumptions=self._dedupe(assumptions),
            warnings=self._dedupe(warnings),
        )

    @staticmethod
    def _normalize_messages(raw: Any) -> list[str]:
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    def _normalize_mapping(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return {}

        cleaned: dict[str, Any] = {}
        for key, value in raw.items():
            normalized = self._normalize_scalar(value)
            if isinstance(normalized, (dict, list)) or normalized is None:
                continue
            cleaned[str(key)] = normalized
        return cleaned

    @staticmethod
    def _normalize_scalar(value: Any) -> Any:
        if isinstance(value, (bool, int, float)):
            return value
        if not isinstance(value, str):
            return value

        lowered = value.strip().lower().replace(",", "")
        if lowered in {"true", "yes", "on"}:
            return True
        if lowered in {"false", "no", "off"}:
            return False

        match = INLINE_MEASUREMENT_RE.match(lowered)
        if match:
            numeric = float(match.group("value"))
            unit = match.group("unit")
            value_mm = unit_to_mm(numeric, unit)
            if "." not in match.group("value") and not unit:
                return int(numeric)
            return round(value_mm, 4)

        return value.strip()

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in values if item))

    def _with_fallback(self, fallback: ParserOutput, warning: str) -> ParserOutput:
        return ParserOutput(
            intent=fallback.intent,
            assumptions=fallback.assumptions,
            warnings=self._dedupe([warning, *fallback.warnings]),
            errors=fallback.errors,
        )
