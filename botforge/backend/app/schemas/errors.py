"""
Standard error response schema.
Spec: docs/reference/reference.md (Standard Error Response Format)

All API errors return:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": [...],        // optional
        "trace_id": "abc-123"    // from request context
    }
}
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    trace_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
