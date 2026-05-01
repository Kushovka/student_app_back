from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.behavior_records import router as behavior_router
from app.api.schools import router as schools_router
from app.api.students import router as students_router
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router
from app.api.users import router as users_router
from app.api.report import router as report_router
from app.core.config import settings


app = FastAPI(title="STUDENTS-LIST")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students_router)
app.include_router(behavior_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(schools_router)
app.include_router(users_router)
app.include_router(report_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
