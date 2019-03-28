FROM python:3.4-slim-jessie
RUN apt-get update && apt-get install --yes python3-pip
RUN pip3 install --user --upgrade pip setuptools wheel
WORKDIR /tnetbuild
COPY tnetserver /tnetbuild
COPY setup.py /tnetbuild/
CMD ["python3", "setup.py", "sdist", "bdist_wheel"]
