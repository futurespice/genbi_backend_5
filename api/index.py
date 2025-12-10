from mangum import Mangum
from app.main import app

# Mangum - это ASGI adapter для serverless (AWS Lambda, Vercel)
handler = Mangum(app, lifespan="off")
