## Prerequisites
- Python
- Docker

## Testing Locally
docker build -t afl-api .

docker run -it -p 5000:5000 afl-api

The following resources are then available:

API Home page: http://127.0.0.1:5000

API docs: http://127.0.0.1:5000/api/docs

## Licence
MIT Licence