from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import datasets, import_export, records

app = FastAPI(title="NER Dataset Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(records.router)
app.include_router(import_export.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
