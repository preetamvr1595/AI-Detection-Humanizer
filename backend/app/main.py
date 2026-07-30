from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import auth, documents, admin, tools

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ScholarShield API",
    description="AI-Powered Document Intelligence & Cybersecurity Platform — academic prototype",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(tools.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "scholarshield-api"}
