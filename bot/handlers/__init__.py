from .auth import router as auth_router
from .configs import router as configs_router
from .instruction import router as instruction_router
from .menu import router as menu_router

__all__ = ["auth_router", "configs_router", "instruction_router", "menu_router"]
