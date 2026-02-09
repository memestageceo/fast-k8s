import os
import sys
import socket
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from threading import Lock

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Simple in-memory counter (per container - important)
counter = 0
lock = Lock()

# simulates slow start for readiness
START_TIME = time.time()
READY_AFTER = int(os.getenv("READY_AFTER", "5"))  # in seconds


def increment():
    global counter
    with lock:
        counter += 1
        return counter


def is_ready():
    return (time.time() - START_TIME) > READY_AFTER


# ----------
# Probes
# ----------


@app.get("/live")
async def liveness():
    return {"status": "alive"}


@app.get("/ready")
async def readiness():
    if not is_ready():
        return JSONResponse(status_code=503, content={"status": "not ready"})
    return {"status": "ready"}


# --------
# Main Page
# -------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
def home(request: Request):
    count = increment()

    hostname = socket.gethostname()

    pod_name = os.getenv("POD_NAME", "unknown")
    env = {
        "APP_ENV": os.getenv("APP_ENV"),
        "SERVICE_NAME": os.getenv("SERVICE_NAME"),
        "POD_NAME": pod_name,
        "NODE_NAME": os.getenv("NODE_NAME"),
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hostname": hostname,
            "env": env,
            "args": sys.argv,
            "count": count,
            "ready": is_ready(),
        },
    )


@app.get("/whoami")
async def whoami():
    return {
        "pod": os.getenv("POD_NAME"),
        "node": os.getenv("NODE_NAME"),
        "hostname": socket.gethostname(),
        "count": counter,
    }
