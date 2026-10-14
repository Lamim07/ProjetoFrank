"""Structured, validated model output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, description="Fato identificado no arquivo.")
    evidence: str = Field(min_length=1, description="Trecho literal do arquivo que sustenta o fato.")


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    language: str = Field(min_length=1)
    language_confidence: Literal["alta", "media", "baixa"]
    summary: str = Field(min_length=1)
    structures: list[Finding]
    functions: list[Finding]
    business_rules: list[Finding]
    operations: list[Finding]
    transactions: list[Finding]
    uncertainties: list[str]

    def all_findings(self) -> list[Finding]:
        return (
            self.structures
            + self.functions
            + self.business_rules
            + self.operations
            + self.transactions
        )


class ExplanationStep(Finding):
    pass


class CodeExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=1)
    execution_flow: list[ExplanationStep]
    inputs_outputs: list[ExplanationStep]
    calculations_rules: list[ExplanationStep]
    data_operations: list[ExplanationStep]
    unknowns: list[str]

    def all_findings(self) -> list[Finding]:
        return (
            self.execution_flow
            + self.inputs_outputs
            + self.calculations_rules
            + self.data_operations
        )


def gemini_response_schema() -> dict:
    """Send a small, inline JSON Schema accepted by Gemini's schema subset.

    Pydantic performs the stricter validation locally after the API responds.
    """
    finding = {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "evidence": {"type": "string"},
        },
        "required": ["description", "evidence"],
    }
    return {
        "type": "object",
        "properties": {
            "content_type": {"type": "string"},
            "subject": {"type": "string"},
            "language": {"type": "string"},
            "language_confidence": {
                "type": "string", "enum": ["alta", "media", "baixa"]
            },
            "summary": {"type": "string"},
            "structures": {"type": "array", "items": finding},
            "functions": {"type": "array", "items": finding},
            "business_rules": {"type": "array", "items": finding},
            "operations": {"type": "array", "items": finding},
            "transactions": {"type": "array", "items": finding},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
        "required": list(AnalysisResult.model_fields),
    }


def explanation_response_schema() -> dict:
    finding = {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "evidence": {"type": "string"},
        },
        "required": ["description", "evidence"],
    }
    return {
        "type": "object",
        "properties": {
            "overview": {"type": "string"},
            "execution_flow": {"type": "array", "items": finding},
            "inputs_outputs": {"type": "array", "items": finding},
            "calculations_rules": {"type": "array", "items": finding},
            "data_operations": {"type": "array", "items": finding},
            "unknowns": {"type": "array", "items": {"type": "string"}},
        },
        "required": list(CodeExplanation.model_fields),
    }
