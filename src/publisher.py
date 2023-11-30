import json
import os
import aio_pika

rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
request_queue = os.getenv("REQUEST_QUEUE", "image_request")
response_queue = os.getenv("RESPONSE_QUEUE", "image_response")


async def send_to_rabbitmq(obj: dict):
    connection = await aio_pika.connect_robust(f"amqp://{rabbitmq_host}")

    async with connection:
        channel = await connection.channel()

        # Declare response queue
        await channel.declare_queue(response_queue, durable=True)

        message_body = json.dumps(obj)
        message = aio_pika.Message(
            body=message_body.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=obj["id"],
            reply_to=response_queue,
        )  # Set reply_to to response queue name

        await channel.default_exchange.publish(message, routing_key=request_queue)
