import sys
from pathlib import Path

# Добавляем корень проекта в path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.main import app

# Экспортируем app напрямую (Vercel попробует обработать как ASGI)
__all__ = ["app"]