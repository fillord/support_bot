# bot/config.py

from pydantic_settings import BaseSettings


class BotConfig(BaseSettings):
    bot_token: str
    database_url: str
    admin_ids: str  # ID админов через запятую, например: "123456789,987654321"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def get_admin_list(self) -> list[int]:
        # Превращаем строку "ID1,ID2" → [ID1, ID2]
        return [
            int(uid.strip())
            for uid in self.admin_ids.split(",")
            if uid.strip().isdigit()
        ]


config = BotConfig()
