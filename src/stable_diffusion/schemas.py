import uuid
from pydantic import BaseModel, Field, field_validator

from src.stable_diffusion.constants import Status
from typing import Optional


class ImageRequest(BaseModel):
    prompt: str = Field(..., description="Prompt for image generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    height: int = Field(
        1024, description="Max Height: Width: 1024x1024.", le=1024, ge=16
    )
    width: int = Field(
        1024, description="Max Height: Width: 1024x1024.", le=1024, ge=16
    )
    num_inference_steps: int = Field(
        35, description="Number of denoising steps", le=50, ge=1
    )
    guidance_scale: float = Field(5, description="", le=10, ge=1)
    webhook_url: Optional[str] = Field(
        None, description="Webhook url to send result to"
    )

    @field_validator("width", "height")
    def check_width(cls, v):
        if v % 8 != 0:
            raise ValueError("must be divisible by 8")
        return v


class EntryBase(BaseModel):
    user_email: str = Field(..., description="Email of user")
    status: Status = Field(..., description="Status of request")
    request_data: ImageRequest = Field(..., description="Request data")
    response_data: dict = Field(None, description="Response data")
    webhook_url: Optional[str] = Field(
        None, description="Webhook url to send result to"
    )


class ImageRequestResponse(BaseModel):
    id: uuid.UUID = Field(..., description="UUID of request")
    email: str = Field(..., description="Email of user")
    status: Status = Field(..., description="Status of request")
    request_data: ImageRequest = Field(..., description="Request data")
    response_data: dict = Field(description="Response data")
