import secret
import telebot

class IUser:

    @classmethod
    def get_all():
        pass

    def __init__(self, user_id) -> None:
        
        self.tg_user_id = user_id

    def show_main_menu():
        pass

    def _send_message_to_user_(message):
        pass

    def clear_messages():
        pass

    def try_log_in():
        pass

    def log_out():
        pass

class IReferee(IUser):
    
    def try_log_in():
        
        super().try_authorize()

    def receive_request():
        pass

    def accept_request():
        pass    

    def refuse_request():
        pass
    
    def withdrew_acceptance_of_request():
        pass
    
    def get_acceptance_withdrawn():
        pass

    def get_acceptance_approved():
        pass

    def view_future_games():
        pass

    def get_request_edited():
        pass

class ITeamRepresentitive(IUser):
    
    def try_log_in():
        
        super().try_authorize()

    def see_referees_list():
        pass
    
    def view_future_games():
        pass

    def start_loving_referee():
        pass

    def start_hating_referee():
        pass

    def start_forming_request():
        pass

    def update_request_form():
        pass

    def send_request():
        pass

    def cancel_request():
        pass

    def receive_acceptance_of_a_request():
        pass

    def decline_acceptance_of_a_request():
        pass

    def receive_withdrawal_of_the_acceptance():
        pass

class IGame:
    
    @classmethod
    def get_all():
        pass


class IRequest:
    
    @classmethod
    def get_all():
        pass

    def get_sent():
        pass

    def get_accepted():
        pass

    def get_refused():
        pass

    def get_cancelled():
        pass

    def get_withdrawn():
        pass

if __name__ == "__main__":
    
    global users, games, requests

    users = IUser.get_all()
    games = IGame.get_all()
    requests = IRequest.get_all()

    bot = telebot.TeleBot(secret.tg_bot_key)

    @bot.message_handler(commands=['start'])
    def start_message(message):
        pass 