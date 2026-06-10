from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import trace

app = FastAPI(title="Recall Blast Radius API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trace.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
