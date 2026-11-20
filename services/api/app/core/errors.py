from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    correlation_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
