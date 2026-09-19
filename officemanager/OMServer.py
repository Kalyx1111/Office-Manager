"""
OMServer.py — Office Manager (by Aryan)
Ties the app together and serves the single-file frontend.

Run directly: python OMServer.py
Or:           uvicorn OMServer:app --host 0.0.0.0 --port 8000
"""
import logging
import socket
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from OMCore import init_db, DATA_DIR
from OMSeed import seed
import OMAuth
import OMDocket
import OMEvents
import OMAdmin

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = BASE_DIR / "OMFrontend.html"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(DATA_DIR / "app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("office_manager")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()  # idempotent — only creates accounts that don't already exist
    logger.info("Office Manager started. Data file: %s", DATA_DIR / "office_manager.db")
    yield
    logger.info("Office Manager shutting down.")


app = FastAPI(title="Office Manager", docs_url=None, redoc_url=None, lifespan=lifespan)

app.include_router(OMAuth.router)
app.include_router(OMDocket.router)
app.include_router(OMEvents.router)
app.include_router(OMAdmin.router)


# Never leak stack traces / internals to the client (Fortress rule #4) —
# log the real error server-side, return an opaque tracking hash instead.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    ref = uuid.uuid4().hex[:10]
    logger.error("UNHANDLED [%s] %s %s\n%s", ref, request.method, request.url,
                 "".join(traceback.format_exception(exc)))
    return JSONResponse(
        status_code=500,
        content={"detail": f"Something went wrong on the server. Reference: {ref}"},
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND_FILE.read_text(encoding="utf-8")


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    import uvicorn
    ip = lan_ip()
    print("=" * 60)
    print("  OFFICE MANAGER — starting")
    print(f"  On this PC:      http://localhost:8000")
    print(f"  From other desks: http://{ip}:8000")
    print("  (If other desks can't reach it, allow port 8000 through")
    print("   Windows Firewall for this program.)")
    print("=" * 60)
    uvicorn.run("OMServer:app", host="0.0.0.0", port=8000, log_level="warning")
