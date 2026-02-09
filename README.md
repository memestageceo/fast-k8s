# fast-k8s — A Beginner's Guide

A tiny FastAPI web app built to teach you how **web servers**, **Docker containers**, and **Kubernetes** work together. This README walks through every line of `main.py` so you can understand exactly what is going on — no prior experience required.

---

## Table of Contents

1. [What Does This Project Do?](#what-does-this-project-do)
2. [Prerequisites](#prerequisites)
3. [Running the App Locally](#running-the-app-locally)
4. [main.py — Line by Line](#mainpy--line-by-line)
   - [Imports](#1-imports)
   - [Creating the App](#2-creating-the-app)
   - [In-Memory Counter](#3-in-memory-counter--thread-safety)
   - [Simulating a Slow Start](#4-simulating-a-slow-start)
   - [Helper Functions](#5-helper-functions)
   - [Health Probes (Liveness & Readiness)](#6-health-probes--liveness--readiness)
   - [The Home Page](#7-the-home-page--endpoint)
   - [The /whoami Endpoint](#8-the-whoami-endpoint)
5. [Python Fundamentals Used in This Project](#python-fundamentals-used-in-this-project)
   - [The `os` Module](#the-os-module)
   - [The `sys` Module](#the-sys-module)
   - [The `socket` Module](#the-socket-module)
   - [The `time` Module](#the-time-module)
   - [The `threading.Lock` Class](#the-threadinglock-class)
   - [`import` vs `from ... import`](#import-vs-from--import)
   - [Functions in Python (`def`)](#functions-in-python-def)
   - [Default Parameter Values](#default-parameter-values)
   - [Type Hints](#type-hints)
   - [The `global` Keyword](#the-global-keyword)
   - [Context Managers (`with`)](#context-managers-with)
   - [Dictionaries](#dictionaries)
   - [Type Casting with `int()`](#type-casting-with-int)
6. [Key Concepts Explained](#key-concepts-explained)
7. [Running with Docker](#running-with-docker)
8. [Running on Kubernetes (Kind)](#running-on-kubernetes-kind)
9. [Project File Overview](#project-file-overview)

---

## What Does This Project Do?

When you run this app and open it in a browser, it shows you a dashboard with:

- **How many times** the page has been visited (a simple counter).
- **Which container/pod** is serving your request (its hostname).
- **Environment variables** injected by Docker or Kubernetes.
- **Whether the app is "ready"** to serve traffic (it intentionally waits a few seconds after starting).

This makes it a great tool for *seeing* how Kubernetes distributes requests across multiple copies (replicas) of the same app.

---

## Prerequisites

- **Python 3.12+** installed
- **uv** (a fast Python package manager) — install with `pip install uv`
- **Docker** (optional, for containerisation)
- **kind** + **kubectl** (optional, for Kubernetes)

---

## Running the App Locally

```bash
# Install dependencies
uv pip install --system fastapi "fastapi[standard]" jinja2

# Start the server
fastapi dev main.py
```

Open <http://127.0.0.1:8000> in your browser. You should see the dashboard.

---

## main.py — Line by Line

### 1. Imports

```python
import os
import sys
import socket
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from threading import Lock
```

| Import | What It Does |
|---|---|
| `os` | Read **environment variables** (e.g. `os.getenv("POD_NAME")`). Environment variables are key-value settings passed into a program from the outside — Docker and Kubernetes use them to configure containers. |
| `sys` | Access **command-line arguments** via `sys.argv`. For example if you run `python main.py --port 8000`, then `sys.argv` would be `["main.py", "--port", "8000"]`. |
| `socket` | Get the machine's **hostname** with `socket.gethostname()`. In Kubernetes, each pod gets a unique hostname, so this tells you *which pod* answered your request. |
| `time` | Track elapsed time with `time.time()`. Used here to simulate a slow startup. |
| `FastAPI` | The web framework — it handles incoming HTTP requests and routes them to your Python functions. |
| `Request` | Represents an incoming HTTP request. FastAPI passes this to your route function so you can inspect headers, query params, etc. |
| `JSONResponse` | Lets you return a JSON response with a custom HTTP **status code** (like `503 Service Unavailable`). |
| `Jinja2Templates` | A template engine. Instead of building HTML strings in Python, you write an HTML file with placeholders like `{{ count }}` and Jinja fills them in. |
| `Lock` | A **thread lock** — makes sure only one thread can modify the counter at a time, preventing race conditions (more on this below). |

### 2. Creating the App

```python
app = FastAPI()
templates = Jinja2Templates(directory="templates")
```

- `app = FastAPI()` — Creates the application object. All your routes (URL handlers) are attached to this object.
- `templates = Jinja2Templates(directory="templates")` — Tells Jinja2 to look for HTML files inside the `templates/` folder. This project has one template: `templates/index.html`.

**Example:** When a user visits `/`, the app renders `templates/index.html` and fills in values like the visit counter and hostname.

### 3. In-Memory Counter & Thread Safety

```python
counter = 0
lock = Lock()
```

- `counter` — A simple integer that tracks how many times the home page has been visited. It starts at `0` and goes up by `1` on each request.
- `lock` — A threading Lock.

**Why do we need a lock?** A web server handles many requests at the same time (concurrently). Imagine two requests arrive at the exact same moment:

```
Request A reads counter → 5
Request B reads counter → 5   (same value, hasn't been updated yet!)
Request A writes counter → 6
Request B writes counter → 6   (should be 7!)
```

This is called a **race condition**. The `Lock` prevents it by making sure only one thread can read-and-update the counter at a time. While one thread holds the lock, all others wait their turn.

**Important Kubernetes concept:** This counter is stored **in memory**, which means each pod (copy of the app) has its own separate counter. If you have 3 replicas, each one counts independently. This demonstrates why real applications use external storage (like a database) for shared state.

### 4. Simulating a Slow Start

```python
START_TIME = time.time()
READY_AFTER = int(os.getenv("READY_AFTER", "5"))  # in seconds
```

- `START_TIME` — Records the exact moment the app started (as a Unix timestamp, e.g. `1700000000.0`).
- `READY_AFTER` — How many seconds the app pretends to "warm up" before declaring itself ready. Defaults to `5` seconds but can be overridden with an environment variable.

**Example:** To make the app take 15 seconds to become ready:

```bash
READY_AFTER=15 fastapi dev main.py
```

**Why?** Real applications often need time to load caches, connect to databases, or warm up ML models before they can handle traffic. This simulates that behaviour so you can see Kubernetes readiness probes in action.

### 5. Helper Functions

```python
def increment():
    global counter
    with lock:
        counter += 1
        return counter
```

- `global counter` — Tells Python we want to modify the module-level `counter` variable, not create a local one.
- `with lock:` — Acquires the lock before touching `counter`, and automatically releases it when the block finishes (even if an error occurs). This is a **context manager** pattern.

```python
def is_ready():
    return (time.time() - START_TIME) > READY_AFTER
```

Returns `True` if enough time has passed since the app started. For example, if `READY_AFTER` is `5` and the app has been running for 8 seconds, then `8 > 5` is `True`, so the app is ready.

### 6. Health Probes — Liveness & Readiness

These are **the most important Kubernetes concept** in this app.

```python
@app.get("/live")
async def liveness():
    return {"status": "alive"}
```

**Liveness probe** — Kubernetes periodically hits this endpoint to ask: *"Is the process still running and not stuck?"* This always returns `200 OK` with `{"status": "alive"}`. If it ever stops responding, Kubernetes will **restart** the container.

```python
@app.get("/ready")
async def readiness():
    if not is_ready():
        return JSONResponse(status_code=503, content={"status": "not ready"})
    return {"status": "ready"}
```

**Readiness probe** — Kubernetes asks: *"Are you ready to accept traffic?"* During the first few seconds after startup, `is_ready()` returns `False`, so this endpoint returns HTTP `503` (Service Unavailable). Kubernetes sees that and **stops sending traffic** to this pod until it returns `200`.

**Real-world analogy:**
- **Liveness** = "Are you alive?" → If no, restart you.
- **Readiness** = "Are you ready for customers?" → If no, don't send anyone to you yet.

Think of a restaurant: the lights are on (alive), but the kitchen is still prepping (not ready). You wouldn't seat customers until the kitchen signals it's good to go.

**How Kubernetes uses these** (configured in `deploy.yaml`):

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 5   # wait 5s before first check
  periodSeconds: 10         # then check every 10s

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 2   # wait 2s before first check
  periodSeconds: 5          # then check every 5s
```

### 7. The Home Page — `/` Endpoint

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

A simple health check that always returns OK. Useful for manual testing or load balancers.

```python
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
```

This is the main page. Here's what happens step by step when you visit `http://localhost:8000/`:

1. **`count = increment()`** — Bumps the counter by 1 (thread-safe) and stores the new value.
2. **`hostname = socket.gethostname()`** — Gets the machine/container hostname. In Kubernetes this is the pod name (e.g. `fastapi-inspector-7b9d4f6c8-x2k9z`).
3. **`os.getenv(...)`** — Reads environment variables injected by Docker Compose or Kubernetes:
   - `APP_ENV` — Which environment you're in (`compose`, `kind`, etc.).
   - `SERVICE_NAME` — The name of the Kubernetes service.
   - `POD_NAME` — The name of the specific pod. In Kubernetes, this uses the **Downward API** to inject the pod's own name.
   - `NODE_NAME` — Which cluster node the pod is running on.
4. **`templates.TemplateResponse("index.html", {...})`** — Renders the HTML template with all the collected data and sends it back to the browser.

**What is the Downward API?** Kubernetes can inject metadata about a pod *into* that pod's environment variables. In `deploy.yaml`:

```yaml
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name    # the pod's own name
```

This lets the app know its own identity without hardcoding anything.

### 8. The `/whoami` Endpoint

```python
@app.get("/whoami")
async def whoami():
    return {
        "pod": os.getenv("POD_NAME"),
        "node": os.getenv("NODE_NAME"),
        "hostname": socket.gethostname(),
        "count": counter,
    }
```

A JSON-only endpoint that returns the pod's identity. Handy for testing load balancing from the command line:

```bash
# Hit the endpoint 5 times and see which pod responds each time
for i in $(seq 1 5); do curl -s http://localhost:8080/whoami | python -m json.tool; done
```

If you have 3 replicas running in Kubernetes, you'll see different `pod` names in the responses — proving that Kubernetes is distributing traffic across pods.

---

## Python Fundamentals Used in This Project

This section dives deep into the Python language features and standard-library modules that appear in `main.py`. If you're new to Python, read this first — everything below is used directly in the project.

---

### The `os` Module

`os` stands for **Operating System**. It's a built-in Python module (no install needed) that lets your program talk to the operating system it's running on.

**How it's used in `main.py`:**

```python
os.getenv("POD_NAME", "unknown")
```

`os.getenv(key, default)` reads an **environment variable**. Environment variables are key-value pairs that live *outside* your code — they're set by the shell, Docker, or Kubernetes before your program starts.

```python
# Syntax
os.getenv("KEY")              # returns None if KEY doesn't exist
os.getenv("KEY", "fallback")  # returns "fallback" if KEY doesn't exist
```

**Try it yourself** — open a Python shell:

```python
>>> import os

# Read an env var that exists on every system
>>> os.getenv("HOME")
'/home/yourname'

# Read one that doesn't exist — returns None
>>> os.getenv("DOES_NOT_EXIST")
None

# Provide a default value
>>> os.getenv("DOES_NOT_EXIST", "my-default")
'my-default'
```

**Other common `os` uses** (not in this project but good to know):

```python
os.getcwd()                  # Get current working directory → "/home/user/fast-k8s"
os.listdir(".")              # List files in a directory → ["main.py", "Dockerfile", ...]
os.path.exists("main.py")    # Check if a file exists → True
os.path.join("a", "b.txt")   # Build a path safely → "a/b.txt" (or "a\\b.txt" on Windows)
os.makedirs("logs/2024")     # Create nested directories
os.environ                   # A dict of ALL environment variables
```

---

### The `sys` Module

`sys` stands for **System**. It gives you access to things related to the Python interpreter itself.

**How it's used in `main.py`:**

```python
"args": sys.argv
```

`sys.argv` is a **list of strings** — the command-line arguments used to start the program.

```bash
# If you run:
fastapi run main.py --host 0.0.0.0

# Then inside Python:
sys.argv == ["main.py", "--host", "0.0.0.0"]
#            ↑ [0]       ↑ [1]    ↑ [2]
```

The first element (`sys.argv[0]`) is always the script name. Everything after it is arguments you passed.

**Try it yourself** — create a file called `test.py`:

```python
import sys
print("Script name:", sys.argv[0])
print("All arguments:", sys.argv)
print("Number of arguments:", len(sys.argv))
```

```bash
$ python test.py hello world 42
Script name: test.py
All arguments: ['test.py', 'hello', 'world', '42']
Number of arguments: 4
```

**Other common `sys` uses:**

```python
sys.exit(0)        # Exit the program (0 = success, 1 = error)
sys.version        # Python version string → "3.12.0 (main, Oct  2 2023, ...)"
sys.platform       # Operating system → "linux", "darwin" (macOS), "win32"
sys.path           # List of directories Python searches for imports
sys.stdin          # Read from standard input
sys.stdout.write() # Write to standard output (like print but lower level)
```

---

### The `socket` Module

`socket` handles **network communication**. In this project it's used for just one thing:

```python
hostname = socket.gethostname()
```

This returns the machine's hostname — a name that identifies the computer on a network.

- On your laptop it might be `"my-macbook.local"`.
- Inside a Docker container it's the container ID, like `"a1b2c3d4e5f6"`.
- Inside a Kubernetes pod it's the pod name, like `"fastapi-inspector-7b9d4f6c8-x2k9z"`.

**Try it yourself:**

```python
>>> import socket
>>> socket.gethostname()
'your-computer-name'
```

**Other common `socket` uses** (not in this project):

```python
# Resolve a domain name to an IP address
socket.gethostbyname("google.com")   # → "142.250.80.46"

# Get your machine's IP address
socket.gethostbyname(socket.gethostname())   # → "192.168.1.42"
```

---

### The `time` Module

`time` provides time-related functions. This project uses it to track how long the app has been running.

```python
START_TIME = time.time()
```

`time.time()` returns the current time as a **Unix timestamp** — the number of seconds since January 1, 1970 (a universal reference point):

```python
>>> import time
>>> time.time()
1700000000.123456    # roughly November 2023
```

Then later, `is_ready()` checks elapsed time:

```python
def is_ready():
    return (time.time() - START_TIME) > READY_AFTER
```

This is simply: *"Has the current time minus the start time exceeded the threshold?"*

```python
# If START_TIME was 1000.0, current time is 1008.0, READY_AFTER is 5:
#   1008.0 - 1000.0 = 8.0
#   8.0 > 5 → True (the app IS ready)
```

**Other common `time` uses:**

```python
time.sleep(2)          # Pause execution for 2 seconds
time.time()            # Current time as float (seconds since epoch)

# Measure how long something takes
start = time.time()
do_something()
elapsed = time.time() - start
print(f"Took {elapsed:.2f} seconds")
```

---

### The `threading.Lock` Class

A `Lock` is a synchronisation primitive from the `threading` module. Think of it like a **bathroom lock** — only one person (thread) can hold it at a time. Everyone else waits in line.

```python
from threading import Lock

lock = Lock()
```

**How it's used in `main.py`:**

```python
def increment():
    global counter
    with lock:           # Acquire the lock (wait if someone else has it)
        counter += 1     # Only one thread can be here at a time
        return counter   # Lock is released automatically when we leave the 'with' block
```

**Why does this matter?** FastAPI uses multiple threads. Without a lock:

```
Thread 1: reads counter (value: 10)
Thread 2: reads counter (value: 10)   ← stale value!
Thread 1: writes counter = 11
Thread 2: writes counter = 11          ← should be 12, but it's 11!
```

With a lock:

```
Thread 1: acquires lock, reads 10, writes 11, releases lock
Thread 2: was waiting... now acquires lock, reads 11, writes 12, releases lock  ✓
```

**Standalone example:**

```python
from threading import Thread, Lock

counter = 0
lock = Lock()

def count_to_1000():
    global counter
    for _ in range(1000):
        with lock:
            counter += 1

# Run 10 threads simultaneously
threads = [Thread(target=count_to_1000) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter)  # Always 10000 with the lock
                 # Without the lock, you might get 9837, 9956, etc.
```

---

### `import` vs `from ... import`

Python has two styles of imports. Both appear in `main.py`:

**Style 1: `import module`**

```python
import os
import sys
import socket
import time
```

This imports the entire module. You access things inside it with a dot:

```python
os.getenv("KEY")        # module.function()
sys.argv                # module.attribute
socket.gethostname()    # module.function()
time.time()             # module.function()
```

**Style 2: `from module import thing`**

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from threading import Lock
```

This imports specific items directly into your namespace. You use them without the module prefix:

```python
app = FastAPI()     # instead of fastapi.FastAPI()
lock = Lock()       # instead of threading.Lock()
```

**When to use which:**
- `import os` — When you'll use many things from the module, or when the module name is short and adds clarity (`os.getenv` is clearer than just `getenv`).
- `from X import Y` — When you only need a few specific items, or when the full path would be verbose (`FastAPI` is nicer than `fastapi.FastAPI`).

---

### Functions in Python (`def`)

A function is a reusable block of code. You define it with the `def` keyword:

```python
def function_name(parameter1, parameter2):
    # code goes here
    return result
```

**Functions from `main.py`:**

```python
# No parameters, no explicit return (returns None implicitly)
# The @app.get decorator makes FastAPI return the dict as JSON
async def liveness():
    return {"status": "alive"}

# One parameter with a type hint
def home(request: Request):
    count = increment()
    ...
    return templates.TemplateResponse("index.html", {...})

# No parameters, returns a boolean (True/False)
def is_ready():
    return (time.time() - START_TIME) > READY_AFTER
```

**Key rules:**
- Indentation matters — the function body *must* be indented (usually 4 spaces).
- `return` sends a value back to the caller. If there's no `return`, the function returns `None`.
- Functions can call other functions: `home()` calls `increment()`, which calls `lock.__enter__()` internally.

**Standalone example:**

```python
def greet(name):
    return f"Hello, {name}!"

message = greet("Alice")
print(message)   # "Hello, Alice!"
```

---

### Default Parameter Values

When you define a function, you can give parameters a **default value**. If the caller doesn't provide that argument, the default is used.

**How it appears in `main.py`:**

```python
os.getenv("READY_AFTER", "5")
#                         ↑ "5" is the default value
```

While `os.getenv` isn't your function, it follows the same pattern. Here's how you write your own:

```python
def connect(host, port=5432, timeout=30):
    print(f"Connecting to {host}:{port} (timeout={timeout}s)")

connect("db.example.com")                  # uses port=5432, timeout=30
connect("db.example.com", 3306)            # uses port=3306, timeout=30
connect("db.example.com", timeout=10)      # uses port=5432, timeout=10
```

**Rules for defaults:**
1. Parameters with defaults must come **after** parameters without defaults:
   ```python
   def good(name, greeting="Hello"):  ...   # ✓
   def bad(greeting="Hello", name):   ...   # ✗ SyntaxError
   ```
2. Default values are evaluated **once** when the function is defined, not each time it's called. This is a common gotcha with mutable defaults:
   ```python
   # WRONG — all calls share the same list!
   def add_item(item, items=[]):
       items.append(item)
       return items

   # RIGHT — use None and create a new list each time
   def add_item(item, items=None):
       if items is None:
           items = []
       items.append(item)
       return items
   ```

---

### Type Hints

Type hints tell the reader (and tools like editors/linters) what type a variable or parameter should be. Python does **not** enforce them at runtime — they're purely informational.

**How it appears in `main.py`:**

```python
def home(request: Request):
#                ↑ type hint — tells you 'request' should be a Request object
```

FastAPI actually *does* use type hints at runtime to do automatic validation and dependency injection — this is special FastAPI behaviour, not standard Python.

**Examples:**

```python
# Basic type hints
def add(a: int, b: int) -> int:
    return a + b

# With default values
def greet(name: str = "World") -> str:
    return f"Hello, {name}!"

# Variable annotations
count: int = 0
name: str = "inspector"
ready: bool = False
```

Common types: `int`, `float`, `str`, `bool`, `list`, `dict`, `None`.

```python
# More complex types (from the typing module)
from typing import Optional, List, Dict

def find_user(user_id: int) -> Optional[str]:
    """Returns the username or None if not found."""
    ...

def get_scores() -> Dict[str, int]:
    """Returns {"alice": 95, "bob": 87}"""
    ...
```

---

### The `global` Keyword

By default, assigning to a variable inside a function creates a **local** variable. If you want to modify a variable defined outside the function (at module level), you need the `global` keyword.

**How it appears in `main.py`:**

```python
counter = 0   # module-level variable

def increment():
    global counter     # "I want to modify the module-level 'counter'"
    with lock:
        counter += 1   # this modifies the module-level counter
        return counter
```

**Without `global`:**

```python
counter = 0

def increment():
    counter += 1   # ✗ UnboundLocalError!
    # Python sees an assignment to 'counter' and assumes it's local,
    # but you're trying to read it before assigning → error
```

**Reading vs writing:**

```python
counter = 0

def read_counter():
    print(counter)     # ✓ Reading a global works without the keyword

def write_counter():
    global counter     # Required only for WRITING to a global
    counter += 1
```

**Standalone example:**

```python
score = 0

def add_points(points):
    global score
    score += points

add_points(10)
add_points(5)
print(score)   # 15
```

> **Note:** Heavy use of `global` is generally discouraged in large programs (it makes code harder to reason about). In this small demo app, it's fine and keeps things simple.

---

### Context Managers (`with`)

The `with` statement automatically handles setup and cleanup. You've seen it with the lock:

```python
with lock:
    counter += 1   # lock is held here
# lock is automatically released here, even if an error occurred
```

This is equivalent to:

```python
lock.acquire()      # setup
try:
    counter += 1
finally:
    lock.release()  # cleanup (always runs, even on error)
```

The `with` version is shorter, cleaner, and less error-prone.

**Most common use — opening files:**

```python
# BAD — if an error happens, the file might never get closed
f = open("data.txt")
data = f.read()
f.close()

# GOOD — file is closed automatically when the block ends
with open("data.txt") as f:
    data = f.read()
# f is closed here, guaranteed
```

Any object that implements `__enter__` and `__exit__` methods can be used with `with`. Both `Lock` and `open()` implement these.

---

### Dictionaries

A **dictionary** (`dict`) is a collection of key-value pairs. They appear all over `main.py`:

```python
# Creating a dictionary
env = {
    "APP_ENV": os.getenv("APP_ENV"),
    "SERVICE_NAME": os.getenv("SERVICE_NAME"),
    "POD_NAME": pod_name,
    "NODE_NAME": os.getenv("NODE_NAME"),
}
```

```python
# Returning a dictionary (FastAPI auto-converts this to JSON)
return {"status": "alive"}

# A bigger example from the /whoami endpoint
return {
    "pod": os.getenv("POD_NAME"),
    "node": os.getenv("NODE_NAME"),
    "hostname": socket.gethostname(),
    "count": counter,
}
```

**Quick reference:**

```python
# Create
user = {"name": "Alice", "age": 30}

# Read
user["name"]              # "Alice"
user.get("email", "N/A")  # "N/A" (key missing, returns default)

# Write
user["email"] = "alice@example.com"

# Delete
del user["age"]

# Loop
for key, value in user.items():
    print(f"{key} = {value}")
# name = Alice
# email = alice@example.com

# Check if key exists
"name" in user   # True
"phone" in user  # False
```

In FastAPI, when a function returns a `dict`, it's automatically serialised to **JSON** and sent back to the browser:

```python
return {"status": "alive"}
# Browser receives: {"status": "alive"} with Content-Type: application/json
```

---

### Type Casting with `int()`

`int()` converts a value to an integer.

**How it appears in `main.py`:**

```python
READY_AFTER = int(os.getenv("READY_AFTER", "5"))
```

`os.getenv()` always returns a **string** (or `None`). Since we need to do math (`> READY_AFTER`), we convert it to an integer with `int()`.

```python
int("5")       # → 5
int("42")      # → 42
int("hello")   # → ValueError: invalid literal for int()
int(3.7)       # → 3 (truncates, doesn't round)
```

**Other common type conversions:**

```python
str(42)        # → "42"     (int to string)
float("3.14")  # → 3.14     (string to float)
bool(0)        # → False    (0 is falsy)
bool(1)        # → True     (non-zero is truthy)
list("abc")    # → ['a', 'b', 'c']
```

---

## Key Concepts Explained

### What is FastAPI?

FastAPI is a modern Python web framework for building APIs. You define **routes** using decorators like `@app.get("/")`, and FastAPI handles incoming HTTP requests, parameter validation, and JSON serialisation for you.

### What is a Decorator (`@app.get(...)`)?

A decorator is a Python feature that modifies a function. `@app.get("/live")` tells FastAPI: *"When someone sends an HTTP GET request to `/live`, call this function and return its result as the response."*

### What are Environment Variables?

Environment variables are key-value pairs set *outside* your code that your code can read at runtime. They're the standard way to configure applications in containers:

```bash
# Set an environment variable and run the app
APP_ENV=production fastapi run main.py
```

```python
# Read it in Python
os.getenv("APP_ENV")  # returns "production"
```

### `async def` vs `def`

You'll notice some functions use `async def` and others use plain `def`:
- `async def` — The function can be paused and resumed, allowing the server to handle other requests while waiting (e.g. for a database query). Best for I/O-bound work.
- `def` — A regular synchronous function. FastAPI runs it in a **thread pool** so it doesn't block other requests.

Both work fine in FastAPI. The `home()` function uses `def` because it calls `increment()` which uses a thread lock (mixing `async` with thread locks can cause issues).

---

## Running with Docker

```bash
# Build the Docker image
docker build -t fastapi-inspector .

# Run a single container
docker run -p 8000:8000 fastapi-inspector
```

Or use Docker Compose:

```bash
# Start one instance
docker compose up

# Start 3 instances (load balanced)
docker compose up --scale inspector=3
```

---

## Running on Kubernetes (Kind)

[Kind](https://kind.sigs.k8s.io/) lets you run a Kubernetes cluster locally using Docker.

```bash
# 1. Create the cluster with custom port mappings
kind create cluster --config kind-config.yaml

# 2. Build the Docker image
docker build -t fastapi-inspector .

# 3. Load the image into the Kind cluster
kind load docker-image fastapi-inspector

# 4. Deploy the app (3 replicas + a Service)
kubectl apply -f deploy.yaml

# 5. Watch pods come up
kubectl get pods -w

# 6. Open the app
#    (Kind maps NodePort 30080 → host port 8080 via kind-config.yaml)
open http://localhost:8080
```

Refresh the page multiple times — you'll see different pod names and independent counters, showing that Kubernetes is routing you to different replicas.

---

## Project File Overview

| File | Purpose |
|---|---|
| `main.py` | The FastAPI application — all the Python code explained above. |
| `templates/index.html` | The HTML dashboard rendered by Jinja2. Uses Tailwind CSS and DaisyUI for styling. |
| `Dockerfile` | Instructions for building a Docker image: start from Python 3.12, install dependencies, copy code, run the server. |
| `compose.yaml` | Docker Compose config for running locally with one command. |
| `deploy.yaml` | Kubernetes manifests — a **Deployment** (3 replicas with health probes) and a **Service** (NodePort to expose the app). |
| `kind-config.yaml` | Kind cluster config that maps port 30080 inside the cluster to port 8080 on your machine. |
| `pyproject.toml` | Python project metadata and dependencies. |
| `uv.lock` | Lock file for reproducible dependency installs. |
