FROM python:3.13


WORKDIR /code

RUN apt-get update && apt-get install -y build-essential libpq-dev

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir -r /code/requirements.txt


COPY ./app /code/app


CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
