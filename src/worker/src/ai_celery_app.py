import os
import json
import logging
import uuid
from celery import Celery
from io import BytesIO
from dotenv import load_dotenv
import pika

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


def generate_image(
    prompt, height=512, width=512, num_inference_steps=50, guidance_scale=7.5
):
    import torch
    from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler

    # Initialize Stable Diffusion model
    model_id = os.getenv("MODLE_ID")
    scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, scheduler=scheduler, torch_dtype=torch.float32
    ).to("cpu")

    print("Generating image for prompt: ", prompt)
    # Generate an image
    image = pipe(
        prompt,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
    ).images[0]

    # Convert image to bytes
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr


def upload_image_to_blob(byte_arr, name):
    # Connect to the blob storage account
    from azure.storage.blob import BlobServiceClient

    print("Uploading image to blob")
    connect_str = f"DefaultEndpointsProtocol=https;AccountName={os.getenv('AZURE_ACCOUNT_NAME')};AccountKey={os.getenv('AZURE_ACCOUNT_KEY')}"

    try:
        # Create the BlobServiceClient object which will be used to create a container client
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    except Exception as e:
        print(f"An exception occurred while creating BlobServiceClient: {e}")
        return

    # Get the existing container
    container_name = os.getenv("AZURE_CONTAINER_NAME")

    try:
        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)
    except Exception as e:
        print(f"An exception occurred while getting container client: {e}")
        return

    try:
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

    # Generate image URL
    byte_arr = generate_image(
        prompt, height, width, num_inference_steps, guidance_scale
    )

    random_str = str(uuid.uuid4())
    images_name = f"{os.getenv('BASE_NAME')}-{random_str}"

    # Upload image to blob
    image_url = upload_image_to_blob(byte_arr, images_name)

    response_obj = {"response": image_url, "id": id}

    send_to_rabbitmq(response_obj)
    return