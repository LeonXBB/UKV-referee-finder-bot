import secret
from localization import local

import telebot
from telebot import types

import mysql.connector


if __name__ == "__main__":
    
    global db_connector, users, games, requests

    bot = telebot.TeleBot(secret.tg_bot_key)

    def get_db_connector():
    
        cnx = mysql.connector.connect(
            host=secret.db_host,
            port=secret.db_port,
            user=secret.db_user,
            password=secret.db_password)

        rv = cnx.cursor()

        return cnx

    class IUser:

        @classmethod
        def get_all(obj):

            cur = db_connector.cursor()
            cur.execute("SELECT tg_id, is_logged_in, first_name, referee_core_db_id, staff_core_db_id FROM goukv_ukv.referee_bot_users")
            
            users = []
            
            for user in cur.fetchall():
                users.append(IUser({
                    "tg_id": user[0], 
                    "is_logged_in": user[1],
                    "first_name": user[2],
                    "referee_core_db_id": user[3],
                    "staff_core_db_id": user[4]
                    }))

            return users

        def __init__(self, init_values) -> None:
            
            for key, value in init_values.items():
                setattr(self, key, value)

        @classmethod
        def register_new(obj):
            pass

        def show_main_menu(self):
            pass

        def _send_message_to_user_(self, message, keyboard=None):
            bot.send_message(self.tg_id, message, reply_markup=keyboard)

        def clear_messages(self):
            pass

        def propose_log_in(self):

            log_in_as_referee_button = types.InlineKeyboardButton(local["log_in_as_referee_button_text"], callback_data="login as referee")
            log_in_as_representitive_button = types.InlineKeyboardButton(local["log_in_as_representitive_button_text"], callback_data="login as representitive")

            layout = ((log_in_as_referee_button,), (log_in_as_representitive_button,))
            login_keyboard = types.InlineKeyboardMarkup(layout)
            
            print('here')

            self._send_message_to_user_(local["proposition_to_log_in"], login_keyboard)

        def try_log_in(self):
            pass

        def log_out(self):
            pass

    class IReferee(IUser):
        

        def try_log_in(self):
            
            super().try_authorize()

        def receive_request(self):
            pass

        def accept_request(self):
            pass    

        def refuse_request(self):
            pass
        
        def withdrew_acceptance_of_request(self):
            pass
        
        def get_acceptance_withdrawn(self):
            pass

        def get_acceptance_approved(self):
            pass

        def view_future_games(self):
            pass

        def get_request_edited(self):
            pass

    class ITeamRepresentitive(IUser):
        
        def try_log_in(self):
            
            super().try_authorize()

        def see_referees_list(self):
            pass
        
        def view_future_games(self):
            pass

        def start_loving_referee(self):
            pass

        def start_hating_referee(self):
            pass

        def start_forming_request(self):
            pass

        def update_request_form(self):
            pass

        def send_request(self):
            pass

        def cancel_request(self):
            pass

        def receive_acceptance_of_a_request(self):
            pass

        def decline_acceptance_of_a_request(self):
            pass

        def receive_withdrawal_of_the_acceptance(self):
            pass

    class IGame:
        
        @classmethod
        def get_all(obj):
            pass

    class IRequest:
        
        @classmethod
        def get_all(obj):
            pass

        def get_sent(self):
            pass

        def get_accepted(self):
            pass

        def get_refused(self):
            pass

        def get_cancelled(self):
            pass

        def get_withdrawn(self):
            pass

    db_connector = get_db_connector()

    users = IUser.get_all()
    #games = IGame.get_all()
    #requests = IRequest.get_all()

    @bot.message_handler(commands=['start'])
    def start_message(message):
        
        for user in users:
            #if user.tg_id == message.from_user.id:
            if user.tg_id == 333119884:
                if user.is_logged_in:
                    if user.referee_core_db_id != 0:
                        return 
                    if user.staff_core_db_id != 0:
                        return
                else:            
                    user.propose_log_in()
                    return

        new_user = IUser.register_new()
        new_user.propose_log_in()

    start_message(None)