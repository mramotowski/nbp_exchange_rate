FROM ubuntu:latest

COPY requirements.txt requirements.txt
COPY nbp_exchange_rate.py nbp_exchange_rate.py

RUN apt-get update && apt-get install -y \
  python3-pip \
  && rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3", "nbp_exchange_rate.py"]
