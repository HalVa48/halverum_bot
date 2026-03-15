#!/usr/bin/env python3
"""Script to clear all user configs from database"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, func, select

from database.database import async_session_maker, init_db
from database.models import UserConfig


async def main():
    await init_db()

    async with async_session_maker() as session:
        # Count configs before deletion
        result = await session.execute(select(func.count()).select_from(UserConfig))
        count = result.scalar()

        print(f"Found {count} configs to delete")

        # Delete all configs
        await session.execute(delete(UserConfig))
        await session.commit()

        print("All user configs have been deleted")


if __name__ == "__main__":
    asyncio.run(main())
