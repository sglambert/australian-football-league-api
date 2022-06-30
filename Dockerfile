FROM r-base:4.2.0

# Install Python 3.9
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    python3.9 python3-pip python3-setuptools python3-dev \
    libcurl4-openssl-dev libxml2-dev libssl-dev

# Install R dependency
RUN install2.r --error fitzRoy

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python3" ]

CMD [ "main.py" ]
