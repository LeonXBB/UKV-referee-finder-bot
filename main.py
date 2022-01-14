import secret
import telebot


class User:
    
    def __init__(self, user_id) -> None:
        
        self.tg_user_id = user_id

    def send_message_to():
        pass


class Referee(User):
    pass


class TeamRepresentitive(User):
    pass


class Game:
    pass


if __name__ == "__main__":
    
    bot = telebot.TeleBot(secret.tg_bot_key)


# / start
# авторизуватися як рефері | авторизуватися як керівник 
# def матчі
# - список минулих
# - надіслати запит (на два судді)
# - скасувати запис
# def особи (рефері та керівники команд)
# - hate list, love list
# авторизуватися (опціонально)
#...
# отримати запит
# підтвердити (44) | скасувати (ок)
# отримати запис (45)
# підтвердити (48)| скасувати (52)
# видалити запит (50)
# видалити запис (51)
# отримати підтвердження запису (ок)
# отримати неактуальність запиту (ок)
# отримати видалення запиту (ок)
# отримати видалення запису (ок)
# отримати скасування запису (ок)