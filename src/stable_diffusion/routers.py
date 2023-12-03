from typing import List
import uuid
from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from src.publisher import send_to_rabbitmq
from src.stable_diffusion.dependencies import get_entry_service
from src.stable_diffusion.constants import Status
from .models import Entry

from .schemas import EntryBase, ImageRequest


img_router = APIRouter(prefix="/stable_diffusion", tags=["image"])


@img_router.post("/generate-image")
async def generate_image(
    request: ImageRequest, service: Entry = Depends(get_entry_service)
):
    """Generate image from prompt"""
    entry = service.create(
        EntryBase(
            user_email="test@gmail.com",
            status=Status.PENDING,
            request_data=request.model_dump(),
        ).model_dump()
    )
    img_gen_request = {"id": str(entry.id), "request": request.model_dump()}
    send_to_rabbitmq(img_gen_request)
    return {
        "message": "Image generation request submitted successfully",
        "id": str(entry.id),
    }


@img_router.get("/image/{request_id}")
async def get_image(request_id: uuid.UUID, service=Depends(get_entry_service)) -> dict:
    # Todo: Add this to the service and update
    db_image_request = service.get_by_primary_key(request_id)
    if db_image_request is None:
        raise HTTPException(status_code=404, detail="Image request not found")
    if db_image_request.status != Status.COMPLETED.name:
        raise HTTPException(
            status_code=400,
            detail="Image generation request is still processing, try again later",
        )
    return db_image_request.response_data
