from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal["error", "warning"]
ParameterType = Literal["number", "integer", "boolean", "text"]


class ParameterDefinition(BaseModel):
    key: str
    label: str
    description: str = ""
    type: ParameterType = "number"
    required: bool = False
    default: Any = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    unit: Optional[str] = None


class DesignIntent(BaseModel):
    model_type: str
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    features: Dict[str, Any] = Field(default_factory=dict)
    print_settings: Dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    severity: Severity
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class DownloadLink(BaseModel):
    label: str
    url: str


class FileBundle(BaseModel):
    stl: Optional[str] = None
    glb: Optional[str] = None
    step: Optional[str] = None
    extra_downloads: List[DownloadLink] = Field(default_factory=list)


class GenerationMetadata(BaseModel):
    estimated_dimensions_mm: Dict[str, float] = Field(default_factory=dict)
    printability_score: int = 0
    generator_version: str = "v2"


class CapabilityItemV2(BaseModel):
    model_type: str
    title: str
    description: str
    category: str
    implemented: bool = True
    examples: List[str] = Field(default_factory=list)
    required_parameters: List[ParameterDefinition] = Field(default_factory=list)
    optional_parameters: List[ParameterDefinition] = Field(default_factory=list)
    todo: Optional[str] = None


class CapabilitiesResponseV2(BaseModel):
    app_name: str
    tagline: str
    categories: List[str]
    supported: List[CapabilityItemV2]
    highlighted_builds: List[str]
    parser_mode: str = "rule_based"


class PlanRequestV2(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=800)
    units: Literal["mm"] = "mm"
    use_llm: bool = False
    model_type: Optional[str] = None


class PlanResponseV2(BaseModel):
    success: bool
    prompt: str
    model_type: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    implemented: bool = False
    intent: Optional[DesignIntent] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    parameter_definitions: List[ParameterDefinition] = Field(default_factory=list)
    todo: Optional[str] = None


class GenerateRequestV2(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=800)
    model_type: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    use_llm: bool = False


class GenerateResponseV2(BaseModel):
    success: bool
    model_type: Optional[str] = None
    title: Optional[str] = None
    implemented: bool = False
    intent: Optional[DesignIntent] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    files: FileBundle = Field(default_factory=FileBundle)
    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
