
# Import and run the bot
from music import bot
from keep_alive import keep_alive
# Run the bot
import os
from dotenv import load_dotenv


# Keep the bot alive
keep_alive()



load_dotenv()  # Load environment variables

bot.run(os.getenv("DISCORD_TOKEN"))

