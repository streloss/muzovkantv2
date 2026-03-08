import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1454107749028855971 # roles channel
roles_message_id = 1454128857102680187
FUNCHOSA_CHANNEL_ID = 1379127661095551048

REACTION_ROLES = {
    '💩': 1454112057329717434,
    '🤙': 1454112345109299281,
    '🤕': 1454112388662956093,
    '🇺🇦': 1454113041305305200,
}