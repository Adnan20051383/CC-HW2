# Lab Queue — Part 2

## Overview

A file-backed laboratory queue service implemented with Python.

The application provides HTTP endpoints for joining and serving a queue.
Three application replicas run behind an Nginx reverse proxy and share
a Docker named volume for persistent queue storage.

## Architecture

- Application: Python 3.12
- HTTP server: Python standard library
- Reverse proxy: Nginx
- Application replicas: 3
- Shared storage: Docker named volume `queue-data`
- Queue file: `/data/queue.txt`
- Internal application port: `8000`
- External access: `http://localhost:18080`

## Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configuration:

```env
APP_PORT=18080
```

## Running the application

Run the three application replicas first:

```powershell
docker compose up -d --build --scale app=3 app
```

Start Nginx after the application replicas are running:

```powershell
docker compose up -d nginx
```

Check the services:

```powershell
docker compose ps
```

Check the application health:

```powershell
Invoke-WebRequest http://localhost:18080/health
```

Expected response:

```text
HTTP 200
ok
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/join` | Add a person to the queue |
| POST | `/next` | Remove and return the next person |

### Join

Request:

```json
{"name": "Ali"}
```

Successful response: HTTP 200 with the queue number as plain text.

Invalid names return HTTP 400.

### Next

Returns the first person's name as plain text.

If the queue is empty, returns HTTP 404 with:

```text
empty
```

## Queue Storage and Concurrency

All three application replicas share the same named volume:

`queue-data:/data`

The queue implementation uses file locking with `fcntl.flock`
to protect concurrent operations.

Queue updates use a temporary file and `os.replace` for atomic
replacement.

This prevents duplicate ticket allocation and lost queue entries
during concurrent requests.

## Running Tests

From the `part2` directory:

```powershell
python -m pip install -r requirements-dev.txt
pytest
```

The development dependencies are not installed in the runtime image.

## Concurrent Testing

The following script tests concurrent queue joins:

```powershell
python tools/concurrent_join.py --url http://localhost:18080 --drain
```

The companion script `tools/concurrent_next.py` tests concurrent
queue consumption.

Both tests should verify that no entries are duplicated or lost.

## Logs and Monitoring

Inspect application and proxy status:

```powershell
docker compose ps
docker compose logs --tail 50 nginx
```

Nginx upstream logs can be used to verify that requests reach
all three application replicas.

## Stopping the Services

```powershell
docker compose down
```

This stops and removes the containers while preserving the
named queue volume.

Do not use `docker compose down -v` unless you intend to
delete the stored queue data.