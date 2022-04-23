FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libfreetype6 \
    libjpeg62-turbo \
    liblcms2-2 \
    libtiff5 \
    libwebp6 \
    libwebpdemux2 \
    libwebpmux3 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src/ .

COPY VERSION .

ARG GIT_SHA=local

RUN echo "BUILD_VERSION=$(cat ./VERSION)" >> build.env && \
    echo "BUILD_DATE=$(date -u -Iminutes)" >> build.env && \
    echo "GIT_SHA=$GIT_SHA" >> build.env

CMD [ "python", "./main.py" ]
