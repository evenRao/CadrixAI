from __future__ import annotations

from fastapi import APIRouter, Request

from cadrix_v2.schemas import CapabilitiesResponseV2, GenerateRequestV2, GenerateResponseV2, PlanRequestV2, PlanResponseV2
from cadrix_v2.service import generate_design, get_capabilities_response, plan_design


router = APIRouter(prefix="/v2", tags=["CadrixAI V2"])


@router.get("/capabilities", response_model=CapabilitiesResponseV2)
def capabilities_v2() -> CapabilitiesResponseV2:
    return get_capabilities_response()


@router.post("/plan", response_model=PlanResponseV2)
def plan_v2(req: PlanRequestV2) -> PlanResponseV2:
    return plan_design(req.prompt, requested_model_type=req.model_type, use_llm=req.use_llm)


@router.post("/generate", response_model=GenerateResponseV2)
def generate_v2(req: GenerateRequestV2, request: Request) -> GenerateResponseV2:
    return generate_design(
        req.prompt,
        request,
        requested_model_type=req.model_type,
        parameter_overrides=req.parameters,
        use_llm=req.use_llm,
    )
