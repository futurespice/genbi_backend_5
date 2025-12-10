"""
Vercel serverless function entry point
"""
from app.main import app

# Vercel ищет переменную "app" или "handler"
handler = app