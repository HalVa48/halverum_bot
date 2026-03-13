import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from api.vpn_client import VPNAPIError, vpn_client

logger = logging.getLogger(__name__)


async def backup_all_servers():
    """Create backup for all servers"""
    logger.info("Starting daily server backup...")

    try:
        # Получаем все серверы
        servers = await vpn_client.get_servers()

        if not servers:
            logger.info("No servers found for backup")
            return

        for server in servers:
            server_id = server["id"]
            server_name = server["name"]

            try:
                logger.info(
                    f"Creating backup for server {server_name} (ID: {server_id})"
                )

                # Создаем бэкап
                backup_result = await vpn_client.create_backup(server_id)
                logger.info(f"Backup created for {server_name}: {backup_result}")

            except VPNAPIError as e:
                logger.error(f"Failed to backup server {server_name}: {e.message}")
            except Exception as e:
                logger.error(f"Unexpected error backing up {server_name}: {e}")

        logger.info("Daily backup completed")

    except Exception as e:
        logger.error(f"Failed to perform daily backup: {e}")


async def start_scheduler():
    """Start backup scheduler"""
    scheduler = AsyncIOScheduler()

    # Запускать каждый день в 03:00
    scheduler.add_job(
        backup_all_servers,
        CronTrigger(hour=3, minute=0),
        id="daily_backup",
        name="Daily server backup",
        misfire_grace_time=3600,  # 1 час на выполнение если пропущено
    )

    scheduler.start()
    logger.info("Backup scheduler started - daily backups at 03:00")
