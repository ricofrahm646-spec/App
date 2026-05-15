from pydantic import BaseModel
from typing import List, Dict
import datetime

class BotInstance(BaseModel):
    id: str
    name: str
    strategy: str
    status: str
    created_at: datetime.datetime

class BotManager:
    def __init__(self):
        self.active_bots: Dict[str, BotInstance] = {}

    def register_bot(self, bot: BotInstance):
        self.active_bots[bot.id] = bot
        return bot

    def get_all_bots(self) -> List[BotInstance]:
        return list(self.active_bots.values())

bot_manager = BotManager()
