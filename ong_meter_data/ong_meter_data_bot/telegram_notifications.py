"""
Defines a OngTelegramBot class to send messages via Telegram
Needs the following configuration variables:
    telegram_token
    telegram_chat_id
"""
import telegram
from ong_meter_data import config, logger, add_app_config


class OngTelegramBot:
    def __init__(self, user_name: str = "Ong", chat_id=None):
        """
        Creates a simple Bot Wrapper to send messages
        :param user_name: telegram user_name to send the message
        :param chat_id: chat_id to use
        """
        self.bot = telegram.Bot(token=config('telegram_token'))
        self.chat_id = chat_id
        if self.chat_id is None:
            updates = self.bot.get_updates(timeout=2, read_latency=2, offset=0)
            for update in updates:
                if update.effective_user.name == user_name:
                    self.chat_id = update.effective_user.id
                    # Save chat_id for further use
                    add_app_config("telegram_chat_id", self.chat_id)
                    break

        if self.chat_id is None:
            raise Exception(f"Chat with {user_name=} not found")
        else:
            logger.info(f"{self.chat_id=}")

    def send_msg(self, msg) -> bool:
        """Sends a message to chat_id created in __init__"""
        if self.chat_id is None:
            return False
        retval = self.bot.send_message(text=msg, chat_id=self.chat_id)
        if retval:
            return True
        else:
            return False


if __name__ == '__main__':
    chat_id = config("telegram_chat_id", ()) or None
    bot = OngTelegramBot(chat_id=chat_id)
    bot.send_msg("Hello world")
