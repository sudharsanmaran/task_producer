import uuid
from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
import requests
from src.publisher import send_to_rabbitmq
from src.stable_diffusion.dependencies import get_entry_service
from src.stable_diffusion.constants import Status
from .models import Entry
from fastapi.responses import JSONResponse

from .schemas import EntryBase, ImageRequest


img_router = APIRouter(prefix="/stable_diffusion", tags=["image"])


def analyze_content(content):
    """
    Analyzes content using the ContentFilter API.

    Args:
    content: The string content to be analyzed.

    Returns:
    A dictionary containing the API response data or None if the request fails.
    """

    # Define the URL base
    url_base = "https://contentfilter.azurewebsites.net/analyze-content"

    # Build the final URL with the provided content
    url = f"{url_base}?content={content}"

    # Set optional headers if needed (adjust based on the API documentation)
    headers = {
        "Content-Type": "application/json",
    }

    # Send the POST request
    try:
        response = requests.post(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

    # Check for successful response code (200)
    if response.status_code == 200:
        # Process the response data
        data = response.json()
        verdict = data["vedict"]
        return verdict
    else:
        print(f"Error: {response.status_code} - {response.reason}")
        return None


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
    # before pushing into the queue, please check whether the prompt doesn't
    # violate Rules of Microsoft Azure Open AI content Filter API
    verdict = analyze_content(request.prompt)
    if verdict == "Reject":
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Prompt contains inappropriate content. Please try again with a different prompt."
            },
        )

    send_to_rabbitmq(img_gen_request)
    return {
        "message": "Image generation request submitted successfully",
        "id": str(entry.id),
    }


@img_router.get("/image/{request_id}")
async def get_image(request_id: str, service=Depends(get_entry_service)):
    try:
        valid_request_id = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format.")

    db_image_request = service.get_by_primary_key(valid_request_id)

    if db_image_request is None:
        raise HTTPException(status_code=404, detail="Image request not found.")

    if db_image_request.status == Status.PENDING.name:
        return JSONResponse(
            status_code=202,
            content={
                "detail": "Image generation request is still processing, try again later."
            },
        )
    elif db_image_request.status == Status.FAILED.name:
        raise HTTPException(
            status_code=500, detail="Image generation request failed, please try again."
        )
    elif db_image_request.status == Status.COMPLETED.name:
        return {
            "message": "Image generation request completed successfully.",
            "id": str(db_image_request.id),
            "response": db_image_request.response_data,
        }
    else:
        raise HTTPException(
            status_code=500, detail="Unknown status of the image generation request."
        )
