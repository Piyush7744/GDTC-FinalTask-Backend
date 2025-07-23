from fastapi import FastAPI
from Routes.routes import router
from fastapi.middleware.cors import CORSMiddleware
# from apscheduler.schedulers.background import BackgroundScheduler
# from Routes.routes import update_price



app = FastAPI()


app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# scheduler = BackgroundScheduler()
# scheduler.add_job(update_price,'interval',minutes=5)
# scheduler.start()
# scheduler.shutdown()