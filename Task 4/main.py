# Task 4 - Notification microservice
# uvicorn main:app --reload

import asyncio
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("notifier")

app = FastAPI(
    title="Notification Service",
    description="Accepts a request, replies right away and sends the email in the background",
)

#  rate limiting 
# allow only 5 requests per minute for each client IP
MAX_REQUESTS = 5
WINDOW_SECONDS = 60

request_log = defaultdict(deque)  # ip -> times of recent requests


async def rate_limiter(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    times = request_log[ip]

    # throw away requests that are older than the window
    while times and now - times[0] > WINDOW_SECONDS:
        times.popleft()

    if len(times) >= MAX_REQUESTS:
        wait = int(WINDOW_SECONDS - (now - times[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="Too many requests, please try again later",
            headers={"Retry-After": str(wait)},
        )

    times.append(now)


# ---------------- models ----------------
class Notification(BaseModel):
    email: EmailStr
    subject: str
    message: str


# job_id ==> info about the job (in memory only)
jobs = {}


# ---------------- background job ----------------
async def send_email(job_id: str, to: str, subject: str, message: str):
    """Pretends to send an email. A real SMTP call would go here."""
    jobs[job_id]["status"] = "sending"
    log.info("job %s: sending email to %s", job_id, to)

    try:
        await asyncio.sleep(3)  # fake delay, like talking to a mail server
        jobs[job_id]["status"] = "sent"
        log.info("job %s: email sent (subject: %s)", job_id, subject)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        log.error("job %s failed: %s", job_id, e)


# ---------------- endpoints ----------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/notify", status_code=202, dependencies=[Depends(rate_limiter)])
async def notify(data: Notification, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "email": data.email}

    # runs after the response has been sent
    background_tasks.add_task(send_email, job_id, data.email, data.subject, data.message)

    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **jobs[job_id]}
