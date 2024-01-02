import io
import os
import json
import logging
import uuid
from celery import Celery
from io import BytesIO
import cv2
from dotenv import load_dotenv
import numpy as np
import pika
from azure.storage.blob import BlobServiceClient
from PIL import Image

load_dotenv()


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Celery
app = Celery("img_gen_worker", broker=os.getenv("RABBITMQ_BROKER_URL"))

# Celery configuration for image generation worker
app.conf.update(
    task_queues={
        "image_generation_queue": {
            "exchange": "image_generation_queue",
            "routing_key": "image_generation_queue",
        },
    },
    task_default_queue="image_generation_queue",
    task_default_exchange="image_generation_queue",
    task_default_routing_key="image_generation_queue",
    task_routes={
        "img_gen_worker.handle_img_gen_request": {"queue": "image_generation_queue"},
    },
)
logger.info("Celery image generation worker started")


class ImageGenerationError(Exception):
    pass


def adjust_contrast_saturation_sharpness(
    image, clip_limit=1.0, saturation_factor=1.5, sharpness_factor=0.5
):
    print("Adjusting contrast, saturation, and sharpness")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    h, s, v = cv2.split(hsv)

    s = s.astype(np.float32)

    s *= saturation_factor

    s = np.clip(s, 0, 255)

    s = s.astype(np.uint8)

    hsv = cv2.merge([h, s, v])

    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    blurred = cv2.GaussianBlur(bgr, (0, 0), 3)
    sharpened = cv2.addWeighted(
        bgr, 1.0 + sharpness_factor, blurred, -sharpness_factor, 0
    )

    hsv_sharpened = cv2.cvtColor(sharpened, cv2.COLOR_BGR2HSV)

    h_s, s_s, v_s = cv2.split(hsv_sharpened)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))

    v_s = clahe.apply(v_s)

    enhanced_hsv = cv2.merge([h_s, s_s, v_s])

    return cv2.cvtColor(enhanced_hsv, cv2.COLOR_HSV2BGR)


def generate_image(
    prompt,
    height=512,
    width=512,
    num_inference_steps=50,
    guidance_scale=7.5,
    negative_prompt=None,
    clip_limit=1.1,
    saturation_factor=1.2,
    sharpness_factor=0.1,
    enhance_image=False,
):
    try:
        from diffusers import DiffusionPipeline
        import torch

        pipe = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )
        pipe.to("cuda")

        refiner = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=pipe.text_encoder_2,
            vae=pipe.vae,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
        )
        refiner.to("cuda")

        high_noise_frac = 0.8

        image = pipe(
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            denoising_end=high_noise_frac,
            output_type="latent",
            height=height,
            width=width,
            guidance_scale=guidance_scale,
            negative_prompt=negative_prompt,
        ).images
        image = refiner(
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            denoising_start=high_noise_frac,
            image=image,
        ).images[0]
        print("enhance_image value", enhance_image)
        if enhance_image:
            print("Enhancing image")
            image_np = np.array(image)

            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

            adjusted_image_np = adjust_contrast_saturation_sharpness(
                image_np, clip_limit, saturation_factor, sharpness_factor
            )

            image = Image.fromarray(
                cv2.cvtColor(adjusted_image_np, cv2.COLOR_BGR2RGB)
            )

    except Exception as e:
        raise ImageGenerationError(f"An exception occurred while generating image: {e}")

    finally:
        del pipe
        del refiner
        torch.cuda.empty_cache()

    # Convert adjusted image to bytes
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr


def upload_image_to_blob(byte_arr, name):
    # Connect to the blob storage account

    print("Uploading image to blob")
    connect_str = f"DefaultEndpointsProtocol=https;AccountName={os.getenv('AZURE_ACCOUNT_NAME')};AccountKey={os.getenv('AZURE_ACCOUNT_KEY')}"

    # Check the image format
    image = Image.open(io.BytesIO(byte_arr))

    # Convert the image to PNG if it's not already
    byte_arr = io.BytesIO()
    image.save(byte_arr, format="PNG")
    byte_arr = byte_arr.getvalue()

    try:
        # Create the BlobServiceClient object which will be used to create a container client
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    except Exception as e:
        print(f"An exception occurred while creating BlobServiceClient: {e}")
        raise ImageGenerationError(
            f"An exception occurred while creating BlobServiceClient: {e}"
        )

    # Get the existing container
    container_name = os.getenv("AZURE_CONTAINER_NAME")

    try:
        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)
    except Exception as e:
        print(f"An exception occurred while getting container client: {e}")
        raise ImageGenerationError(
            f"An exception occurred while getting container client: {e}"
        )

    try:
        # Ensure the name ends with .png
        if not name.endswith(".png"):
            name += ".png"

        # Create a blob client using the blob name
        blob_client = container_client.get_blob_client(name)

        # Upload image data to blob
        blob_client.upload_blob(byte_arr, overwrite=True)

        # Generate image URL
        image_url = blob_client.url

        # Print the image URL
        print(image_url, "image url")
        return image_url

    except Exception as e:
        print(f"An exception occurred while uploading the file: {e}")
        raise ImageGenerationError(
            f"An exception occurred while uploading the file: {e}"
        )


def send_to_rabbitmq(obj, rabbitmq_host="rabbitmq", response_queue="image_response"):
    connection = None
    try:
        # Establish a connection with RabbitMQ server
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host)
        )
        channel = connection.channel()

        # Declare the response queue
        channel.queue_declare(queue=response_queue, durable=True)

        # Prepare the message
        message_body = json.dumps(obj)
        properties = pika.BasicProperties(
            delivery_mode=2,  # make message persistent
            correlation_id=obj.get(
                "id", ""
            ),  # use the id field from the obj as the correlation_id
        )

        # Publish the message to the response queue
        channel.basic_publish(
            exchange="",
            routing_key=response_queue,
            body=message_body,
            properties=properties,
        )

        print(f" [x] Sent {message_body} to queue {response_queue}")
    finally:
        # Close the connection if it was successfully opened
        if connection and connection.is_open:
            connection.close()


@app.task(name="handle_img_gen_request")
def handle_img_gen_request(request):
    # Parse the message and extract the data to be updated in the database
    data = json.loads(request)
    logger.info(f"Received image generation request: {data}")

    # Extract the data from the request
    request_data = data["request"]
    id = data["id"]
    prompt = request_data["prompt"]
    height = request_data["height"]
    width = request_data["width"]
    num_inference_steps = request_data["num_inference_steps"]
    guidance_scale = request_data["guidance_scale"]
    enhance_image = request_data["enhance_image"]
    negative_prompt = request_data["negative_prompt"]

    # Generate image URL
    try:
        byte_arr = generate_image(
            prompt,
            height,
            width,
            num_inference_steps,
            guidance_scale,
            negative_prompt,
            enhance_image,
        )
        random_str = str(uuid.uuid4())
        images_name = f"{os.getenv('BASE_NAME')}-{random_str}"

        # Upload image to blob
        image_url = upload_image_to_blob(byte_arr, images_name)

        response_obj = {"response": image_url, "id": id, "status": "completed"}

        send_to_rabbitmq(response_obj)
    except ImageGenerationError as e:
        logger.error(f"An exception occurred while generating image: {e}")
        response_obj = {"response": None, "id": id, "status": "failed"}
        send_to_rabbitmq(response_obj)
        return
