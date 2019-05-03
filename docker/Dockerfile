FROM python:3.7-slim-stretch
RUN apt-get update && apt-get install --yes python3-pip
RUN pip3 install --user --upgrade pip requirements.txt
WORKDIR /build
