"""
FastAPI Kubernetes Inspector Application

A demonstration application showing how web servers, Docker containers,
and Kubernetes work together with health probes, environment variables,
and load balancing.
"""
import logging
import os
import socket
import sys
import time
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Application starting up...")
    logger.info(f"Ready after: {READY_AFTER} seconds")
    logger.info(f"Running on hostname: {socket.gethostname()}")
    yield
    logger.info("Application shutting down...")


app = FastAPI(
    title="FastAPI Kubernetes Inspector",
    description="A demonstration application for learning Kubernetes concepts",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - configure allowed origins via environment variable for production
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # Disabled for security when using wildcard origins
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Simple in-memory counter (per container - important for K8s demonstration)
counter: int = 0
lock: Lock = Lock()

# Simulates slow start for readiness probe demonstration
START_TIME: float = time.time()

# Validate and parse READY_AFTER environment variable
try:
    READY_AFTER: int = int(os.getenv("READY_AFTER", "5"))
    if READY_AFTER < 0:
        logger.warning("READY_AFTER must be non-negative, using default: 5")
        READY_AFTER = 5
except ValueError:
    logger.warning("Invalid READY_AFTER value, using default: 5")
    READY_AFTER = 5


def increment() -> int:
    """
    Thread-safe counter increment.

    Returns:
        int: The new counter value after incrementing
    """
    global counter
    with lock:
        counter += 1
        current = counter
    logger.debug(f"Counter incremented to {current}")
    return current


def is_ready() -> bool:
    """
    Check if the application has completed its startup warmup period.

    Returns:
        bool: True if the app has been running longer than READY_AFTER seconds
    """
    elapsed = time.time() - START_TIME
    ready = elapsed > READY_AFTER
    logger.debug(f"Readiness check: elapsed={elapsed:.2f}s, ready={ready}")
    return ready


def get_counter() -> int:
    """
    Thread-safe read of the current counter value.

    Returns:
        int: The current counter value
    """
    with lock:
        return counter


def get_pod_identity() -> dict[str, str]:
    """
    Get pod identity information from environment variables.

    Returns:
        dict: Dictionary containing pod, node, app_env, and service_name
    """
    return {
        "pod": os.getenv("POD_NAME", "unknown"),
        "node": os.getenv("NODE_NAME", "unknown"),
        "app_env": os.getenv("APP_ENV", "unknown"),
        "service_name": os.getenv("SERVICE_NAME", "unknown"),
    }


# ----------
# Health Probes
# ----------


@app.get("/live", tags=["health"])
async def liveness() -> dict[str, str]:
    """
    Liveness probe endpoint for Kubernetes.

    This endpoint tells Kubernetes whether the application process is alive.
    If this endpoint stops responding, Kubernetes will restart the container.

    Returns:
        dict: Status indicating the application is alive
    """
    return {"status": "alive"}


@app.get("/ready", tags=["health"], response_model=None)
async def readiness():
    """
    Readiness probe endpoint for Kubernetes.

    This endpoint tells Kubernetes whether the application is ready to accept traffic.
    During the initial READY_AFTER seconds, this returns 503 to prevent traffic
    from being routed to the pod before it's fully initialized.

    Returns:
        JSONResponse or dict: Status 503 if not ready, 200 with status if ready
    """
    if not is_ready():
        logger.info("Readiness probe: not ready yet")
        return JSONResponse(status_code=503, content={"status": "not ready"})
    return {"status": "ready"}


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """
    General health check endpoint.

    A simple endpoint that always returns OK. Useful for load balancers
    or manual health verification.

    Returns:
        dict: Status indicating the application is healthy
    """
    return {"status": "ok"}


# ----------
# Main Endpoints
# ----------


@app.get("/", response_class=HTMLResponse, tags=["dashboard"])
def home(request: Request) -> HTMLResponse:
    """
    Main dashboard page showing application state and environment.

    This page displays:
    - Request counter (per-pod)
    - Hostname and pod information
    - Environment variables
    - Application startup arguments
    - Readiness status

    Args:
        request: The incoming HTTP request object

    Returns:
        HTMLResponse: Rendered HTML template with application state
    """
    try:
        count = increment()
        hostname = socket.gethostname()

        identity = get_pod_identity()
        env = {
            "APP_ENV": identity["app_env"],
            "SERVICE_NAME": identity["service_name"],
            "POD_NAME": identity["pod"],
            "NODE_NAME": identity["node"],
        }

        logger.info(f"Home page accessed - count: {count}, pod: {identity['pod']}")

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "hostname": hostname,
                "env": env,
                "args": sys.argv,
                "count": count,
                "ready": is_ready(),
            },
        )
    except Exception as e:
        logger.error(f"Error rendering home page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/whoami", tags=["info"])
async def whoami() -> dict[str, Any]:
    """
    Returns pod identity and state information in JSON format.

    This endpoint is useful for testing load balancing and seeing which
    pod is handling each request. The counter value is read in a thread-safe
    manner to prevent race conditions.

    Returns:
        dict: Pod name, node name, hostname, and request counter
    """
    try:
        identity = get_pod_identity()

        return {
            "pod": identity["pod"],
            "node": identity["node"],
            "hostname": socket.gethostname(),
            "count": get_counter(),
            "ready": is_ready(),
        }
    except Exception as e:
        logger.error(f"Error in whoami endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
