# Build and start the bot
docker-compose up -d --build

# View logs
docker-compose logs -f vpn_bot

# Stop the bot
docker-compose down

# Restart the bot
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build
