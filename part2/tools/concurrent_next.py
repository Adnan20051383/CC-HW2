import json
import threading
import http.client
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HOST = "localhost"
PORT = 18080
COUNT = 200
WORKERS = 200

expected_names = [
    f"NEXT_TEST_{i:03d}" for i in range(1, COUNT + 1)
]

def request(method, path, payload=None):
    connection = http.client.HTTPConnection(
        HOST, PORT, timeout=40
    )

    headers = {}
    body = None

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    try:
        connection.request(
            method, path, body=body, headers=headers
        )
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        connection.close()


# Step 1: Seed exactly 200 unique names
seed_errors = []
ticket_errors = []

for index, name in enumerate(expected_names, start=1):
    try:
        status, body = request(
            "POST", "/join", {"name": name}
        )

        if status != 200:
            seed_errors.append(
                {"name": name, "status": status, "body": body}
            )
        elif body != str(index):
            ticket_errors.append(
                {"name": name, "expected": index, "actual": body}
            )

    except Exception as exc:
        seed_errors.append(
            {"name": name, "error": str(exc)}
        )


if seed_errors or ticket_errors:
    result = {
        "seeded": COUNT - len(seed_errors),
        "seed_errors": seed_errors,
        "ticket_errors": ticket_errors,
        "passed": False
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(1)


# Step 2: Send 200 concurrent Next requests
barrier = threading.Barrier(WORKERS)

def take_one(_):
    try:
        barrier.wait(timeout=30)
        status, body = request("POST", "/next")
        return {"status": status, "body": body}
    except Exception as exc:
        return {"error": str(exc)}


with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    responses = list(
        executor.map(take_one, range(WORKERS))
    )


taken_names = [
    item["body"]
    for item in responses
    if item.get("status") == 200
]

errors = [
    item for item in responses
    if "error" in item
]

unexpected_statuses = [
    item for item in responses
    if "status" in item and item["status"] != 200
]

counts = Counter(taken_names)

duplicates = {
    name: count
    for name, count in counts.items()
    if count > 1
}

expected_set = set(expected_names)
actual_set = set(taken_names)

missing_names = sorted(expected_set - actual_set)
extra_names = sorted(actual_set - expected_set)


# Step 3: Confirm queue is empty
try:
    final_status, final_body = request("POST", "/next")
    final_next = {
        "status": final_status,
        "body": final_body
    }
except Exception as exc:
    final_next = {"error": str(exc)}


passed = (
    len(taken_names) == COUNT
    and len(set(taken_names)) == COUNT
    and not duplicates
    and not missing_names
    and not extra_names
    and not errors
    and not unexpected_statuses
    and final_next == {"status": 404, "body": "empty"}
)

result = {
    "seeded": COUNT,
    "concurrent_requests": WORKERS,
    "successful_next": len(taken_names),
    "duplicate_names": duplicates,
    "missing_names": missing_names,
    "extra_names": extra_names,
    "errors": errors,
    "unexpected_statuses": unexpected_statuses,
    "final_next": final_next,
    "passed": passed
}

print(json.dumps(result, indent=2))

raise SystemExit(0 if passed else 1)