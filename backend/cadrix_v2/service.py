from __future__ import annotations

import logging
import math
import uuid
from typing import Any, Dict

from fastapi import Request

from cadrix_v2.exporters import export_generated_geometry
from cadrix_v2.geometry import estimate_dimensions_mm, generate_geometry
from cadrix_v2.parsers.llm_parser import LLMParser
from cadrix_v2.parsers.parser_interface import ParserOutput
from cadrix_v2.parsers.rule_based_parser import RuleBasedParser
from cadrix_v2.registry import MODEL_REGISTRY, capability_categories, get_model_spec, list_capabilities
from cadrix_v2.schemas import CapabilitiesResponseV2, GenerateResponseV2, GenerationMetadata, PlanResponseV2
from cadrix_v2.validators import ValidationResult, validate_parameters


def get_capabilities_response() -> CapabilitiesResponseV2:
    from cadrix_v2.registry import HIGHLIGHTED_BUILDS

    return CapabilitiesResponseV2(
        app_name="CadrixAI V2",
        tagline="AI-assisted parametric CAD with validated geometry and optional local Ollama parsing",
        categories=capability_categories(),
        supported=list_capabilities(),
        highlighted_builds=HIGHLIGHTED_BUILDS,
    )


def _choose_parser(use_llm: bool):
    if use_llm:
        return LLMParser(), []
    return RuleBasedParser(), []


def _merge_parameters(model_type: str, defaults: Dict[str, Any], parser_output: ParserOutput) -> Dict[str, Any]:
    intent = parser_output.intent
    if not intent:
        return {**defaults}

    parameters = {**defaults}
    parameters.update(intent.dimensions)
    parameters.update(intent.features)
    parameters.update(intent.print_settings)

    if "cable_hole" in parameters:
        parameters["cable_slot"] = bool(parameters["cable_hole"])
    if "tolerance_mm" in intent.print_settings:
        # Defaults already exist in parameters; use explicit intent to decide
        # whether a general clearance request should replace a fit default.
        clearance = intent.print_settings["tolerance_mm"]
        if model_type in {"box_with_lid", "snap_fit_box"} and "lid_clearance_mm" not in intent.dimensions:
            parameters["lid_clearance_mm"] = clearance
        if model_type == "pcb_enclosure" and "board_clearance_mm" not in intent.dimensions:
            parameters["board_clearance_mm"] = clearance
        if "fit_clearance_mm" in defaults and "fit_clearance_mm" not in intent.dimensions:
            parameters["fit_clearance_mm"] = clearance

    return parameters


def _coerce_overrides(model_type: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
    spec = get_model_spec(model_type)
    if not spec:
        return overrides

    definitions = {definition.key: definition for definition in spec.parameter_definitions}
    coerced: Dict[str, Any] = {}
    for key, value in overrides.items():
        definition = definitions.get(key)
        if value is None or definition is None:
            coerced[key] = value
            continue
        try:
            if definition.type == "boolean":
                if isinstance(value, str):
                    lowered = value.lower()
                    coerced[key] = lowered in {"1", "true", "yes", "on"} if lowered in {"1", "true", "yes", "on", "0", "false", "no", "off"} else value
                else:
                    coerced[key] = bool(value)
            elif definition.type == "integer":
                number = float(value)
                coerced[key] = int(number) if math.isfinite(number) and number.is_integer() else value
            elif definition.type == "number":
                coerced[key] = float(value)
            else:
                coerced[key] = value
        except (TypeError, ValueError):
            coerced[key] = value

    if "cable_hole" in coerced:
        coerced["cable_slot"] = bool(coerced["cable_hole"])
    return coerced


def _collect_messages(validation: ValidationResult, parser_output: ParserOutput, parser_warnings: list[str]) -> tuple[list[str], list[str]]:
    warnings = [*parser_warnings, *parser_output.warnings, *(issue.message for issue in validation.warnings)]
    errors = [*parser_output.errors, *(issue.message for issue in validation.errors)]
    return warnings, errors


def plan_design(prompt: str, requested_model_type: str | None = None, use_llm: bool = False) -> PlanResponseV2:
    parser, parser_warnings = _choose_parser(use_llm)
    parser_output = parser.parse(prompt, requested_model_type)
    if parser_output.intent is None:
        return PlanResponseV2(
            success=False,
            prompt=prompt,
            warnings=parser_warnings + parser_output.warnings,
            errors=parser_output.errors,
            assumptions=parser_output.assumptions,
        )

    spec = MODEL_REGISTRY[parser_output.intent.model_type]
    parameters = _merge_parameters(spec.model_type, spec.defaults, parser_output)
    validation = validate_parameters(spec, parameters)
    warnings, errors = _collect_messages(validation, parser_output, parser_warnings)

    return PlanResponseV2(
        success=len(errors) == 0,
        prompt=prompt,
        model_type=spec.model_type,
        title=spec.title,
        category=spec.category,
        implemented=spec.implemented,
        intent=parser_output.intent,
        parameters=validation.parameters,
        warnings=warnings,
        errors=errors,
        assumptions=parser_output.assumptions,
        parameter_definitions=spec.parameter_definitions,
        todo=spec.todo,
    )


def generate_design(
    prompt: str,
    request: Request,
    requested_model_type: str | None = None,
    parameter_overrides: Dict[str, Any] | None = None,
    use_llm: bool = False,
) -> GenerateResponseV2:
    plan = plan_design(prompt, requested_model_type=requested_model_type, use_llm=use_llm)
    if not plan.model_type:
        return GenerateResponseV2(success=False, errors=plan.errors, warnings=plan.warnings, assumptions=plan.assumptions)

    spec = MODEL_REGISTRY[plan.model_type]
    parameters = {**plan.parameters, **_coerce_overrides(plan.model_type, parameter_overrides or {})}
    validation = validate_parameters(spec, parameters)
    warnings = list(dict.fromkeys([*plan.warnings, *(issue.message for issue in validation.warnings)]))
    # Revalidate the final overrides: errors in the original plan may have been
    # corrected in Adjust and must not permanently block that design.
    errors = list(dict.fromkeys(issue.message for issue in validation.errors))

    if not spec.implemented:
        errors.append(f"{spec.title} is registered in V2 but not implemented yet.")

    if errors:
        return GenerateResponseV2(
            success=False,
            model_type=spec.model_type,
            title=spec.title,
            implemented=spec.implemented,
            intent=plan.intent,
            parameters=validation.parameters,
            warnings=warnings,
            errors=errors,
            assumptions=plan.assumptions,
            metadata=GenerationMetadata(printability_score=validation.printability_score),
        )

    try:
        geometry = generate_geometry(spec.model_type, validation.parameters)
        files = export_generated_geometry(geometry, f"v2_{uuid.uuid4().hex[:12]}", request)
    except Exception:
        logging.getLogger(__name__).exception("Generation failed for %s", spec.model_type)
        return GenerateResponseV2(
            success=False, model_type=spec.model_type, title=spec.title, implemented=True,
            parameters=validation.parameters, intent=plan.intent, assumptions=plan.assumptions,
            warnings=warnings,
            errors=["This combination could not be built or exported as a valid solid. Try simpler dimensions, thicker walls, or the template defaults."],
            metadata=GenerationMetadata(printability_score=0),
        )
    metadata = GenerationMetadata(
        estimated_dimensions_mm=estimate_dimensions_mm(geometry.primary_solid),
        printability_score=validation.printability_score,
        generator_version="v2",
    )

    return GenerateResponseV2(
        success=True,
        model_type=spec.model_type,
        title=spec.title,
        implemented=spec.implemented,
        intent=plan.intent,
        parameters=validation.parameters,
        warnings=warnings,
        errors=[],
        assumptions=plan.assumptions,
        files=files,
        metadata=metadata,
    )
