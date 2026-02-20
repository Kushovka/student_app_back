from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.behavior_records import router as behavior_router
from app.api.students import router as students_router


app = FastAPI(title="STUDENTS-LIST")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students_router)
app.include_router(behavior_router)
