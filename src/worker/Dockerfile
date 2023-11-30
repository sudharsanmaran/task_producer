FROM python:3.11.6

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

COPY src/worker.py /app/worker.py

ENV AZURE_ACCOUNT_KEY=nkPQwjPikC0i3gc6aURqINL+XkWtGtzTOoEKQMTkjPN6TFi4LsLYfMSKH925BEbZ13qgURXPzHrW+AStQYxtyw==
ENV AZURE_ACCOUNT_NAME=eaglebotlandingstorage
ENV AZURE_CONTAINER_NAME=stable-diffusion-images
ENV BASE_NAME=eagle-bot
ENV MODLE_ID=stabilityai/stable-diffusion-2-1-base  
ENV RABBITMQ_HOST=rabbitmq
ENV REQUEST_QUEUE=image_request
ENV RESPONSE_QUEUE=image_response
ENV OMP_NUM_THREADS=1


CMD ["python", "/app/worker.py"]
