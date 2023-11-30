import asyncio
import json
import os
import aio_pika
import pika
import torch
from azure.storage.blob import BlobServiceClient
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler
from io import BytesIO
from dotenv import load_dotenv
import uuid

load_dotenv()

# Initialize Stable Diffusion model
model_id = os.getenv("MODLE_ID")
scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
pipe = StableDiffusionPipeline.from_pretrained(
    model_id, scheduler=scheduler, torch_dtype=torch.float16
).to("cuda")

# RabbitMQ setup
rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")  # Use environment variable
queue_name = os.getenv("REQUEST_QUEUE", "image_request")  # Use environment variable
response_queue = os.getenv(
    "RESPONSE_QUEUE", "image_response"
)  # Use environment variable

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=rabbitmq_host,
        heartbeat=900,
    )
)
channel = connection.channel()
channel.queue_declare(queue=queue_name, durable=True)
channel.queue_declare(queue=response_queue, durable=True)


async def upload_image_to_blob(byte_arr, name):
    # Connect to the blob storage account
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


async def generate_image(
    prompt, height=512, width=512, num_inference_steps=50, guidance_scale=7.5
):
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


async def on_request(message: aio_pika.IncomingMessage):
    async with message.process():
        # Your existing on_request code here

        msg = json.loads(message.body)
        print("ai worker **********", msg)
        request_data = msg["request"]
        id = msg["id"]
        prompt = request_data["prompt"]
        height = request_data["height"]
        width = request_data["width"]
        num_inference_steps = request_data["num_inference_steps"]
        guidance_scale = request_data["guidance_scale"]
        # Generate image

        byte_arr = await generate_image(
            prompt, height, width, num_inference_steps, guidance_scale
        )

        random_str = str(uuid.uuid4())
        images_name = f"{os.getenv('BASE_NAME')}-{random_str}"

        # Upload image to blob
        image_url = await upload_image_to_blob(byte_arr, images_name)

        response_obj = {"response": image_url, "id": id}

        # Send response back to response queue
        await message.reply(json.dumps(response_obj))


async def main(loop):
    connection = await aio_pika.connect_robust(f"amqp://{rabbitmq_host}", loop=loop)

    async with connection:
        # Creating channel
        channel = await connection.channel()

        # Declaring queue
        queue = await channel.declare_queue(queue_name, durable=True)

        # Start listening the queue with name 'task_queue'
        await queue.consume(on_request)


loop = asyncio.get_event_loop()
loop.create_task(main(loop))

# we enter a never-ending loop that waits for data and
# runs callbacks whenever necessary.
print("Awaiting RPC requests")
loop.run_forever()
