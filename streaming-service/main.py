from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Streaming Service Manager",
    version="1.0",
    description="A service for managing Twitch VODs and post-processing workflows."
)

# Include API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)