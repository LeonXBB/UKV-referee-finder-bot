import secret
from localization import local

import telebot
from telebot import types

import mysql.connector


if __name__ == "__main__":
    
    global db_connector, users, referees, team_reps, games, requests

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
            cur.execute("SELECT tg_id, is_logged_in, referee_core_db_id, staff_core_db_id, messages_ids FROM goukv_ukv.referee_bot_users")
            
            users = []
            
            for user in cur.fetchall():
                users.append(IUser({
                    "tg_id": user[0], 
                    "is_logged_in": user[1],
                    "referee_core_db_id": user[2],
                    "staff_core_db_id": user[3],
                    "messages_ids": user[4]
                    }))

            return users

        @classmethod
        def register_new(obj, tg_id):
            
            new_user = IUser({
                "tg_id": tg_id,
                "is_logged_in": 0,
                "referee_core_db_id": 0,
                "staff_core_db_id": 0,
                "messages_ids": ";"
                })

            users.append(new_user)

            cur = db_connector.cursor()
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_users` (`tg_id`, `is_logged_in`, `referee_core_db_id`, `staff_core_db_id`, `messages_ids`) VALUES ({tg_id}, 0, 0, 0, ';');")

            return new_user

        def _receive_button_press_from_user_(self, callback_data):
            pass

        def _receive_message_from_user_(self, message):
            
            if hasattr(self, "waiting_for_password") and self.waiting_for_password:
                self.receive_password(message.text)   

            bot.delete_message(self.tg_id, message.id)

        def _send_message_to_user_(self, message, keyboard=None, clear_previous=False):
            
            if clear_previous:
                self._clear_messages_()

            message = bot.send_message(self.tg_id, message, reply_markup=keyboard)
        
            self._add_message_to_history(message)

        def _add_message_to_history(self, message):
            
            self.messages_ids += f"{message.id};"

            cur = db_connector.cursor()
            cur.execute(f"UPDATE `goukv_ukv`.`referee_bot_users` SET messages_ids = concat(messages_ids, '{message.id};') WHERE tg_id = {self.tg_id};")

        def _clear_messages_(self):
            
            for message_id in self.messages_ids.split(';'):
                if message_id:
                    try:
                        bot.delete_message(self.tg_id, int(message_id))
                    except:
                        pass

            self.messages_ids = ";"
            
            cur = db_connector.cursor()
            cur.execute(f"UPDATE `goukv_ukv`.`referee_bot_users` SET messages_ids = ';';")

        def __init__(self, init_values):
            
            for key, value in init_values.items():
                setattr(self, key, value)

        def show_main_menu(self):
            print("this_is_a_main_menu")

        def invite_to_log_in(self):
            
            self._send_message_to_user_(local["proposition_to_log_in"], clear_previous=True)
            self.waiting_for_password = True
                    
        def receive_password(self, password):
            
            # MAKE REQUEST TO REFEREE DB
            # CHANGE STATUS IF LEN(FETCHALL IS 1)
            # MAKE REQUEST TO PLAYERS DB
            # SAME

            passed = False

            cur = db_connector.cursor()

            cur.execute(f"SELECT id FROM goukv_ukv.jos_joomleague_referees WHERE referee_bot_auth_token = '{password}'")

            res = cur.fetchall()

            if len(res) == 1:

                passed = True 
                cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET referee_core_db_id = {res[0][0]} WHERE tg_id = {self.tg_id}")
                self.referee_core_db_id = res[0][0]

            cur.execute(f"SELECT id FROM goukv_ukv.jos_joomleague_players WHERE referee_bot_auth_token = '{password}'")

            res = cur.fetchall()

            if len(res) == 1:

                passed = True
                cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET staff_core_db_id = {res[0][0]} WHERE tg_id = {self.tg_id}")
                self.staff_core_db_id = res[0][0]

            if passed:
                self.log_in()

            else:
                self.fail_to_log_in()

        def fail_to_log_in(self):
            self._send_message_to_user_(local["failed_log_in"])

        def log_in(self):
            
            self.is_logged_in = 1
            self.waiting_for_password = True

            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET is_logged_in = 1 WHERE tg_id = {self.tg_id}")

            self.show_main_menu()

        def log_out(self):
            pass

        # /// REFEREE FUNCTIONS

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

        # /// TEAM REPRESENTITIVE FUNTIONS

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
    requests = IRequest.get_all()

    @bot.message_handler(commands=['start'])
    def start_message(message):

        user = None

        for user_count in users:
            
            if user_count.tg_id == message.from_user.id:
                user = user_count
                break

        if user is None: user = IUser.register_new(message.from_user.id)

        user._add_message_to_history(message)

        if user.is_logged_in:
            user.show_main_menu()
        else:
            user.invite_to_log_in()

    @bot.message_handler(func=lambda message:True, content_types=["text", "photo", "audio", "voice", "video", "document"])
    def message_receive_workaround(message):
        
        for user in users:
            if user.tg_id == message.from_user.id:
                user._receive_message_from_user_(message)
    
    @bot.callback_query_handler(func=lambda call:True)
    def button_press_workaround(callback_data):
        
        for user in users:
            if user.tg_id == callback_data.from_user_id:
                bot.answer_callback_query(callback_data.id)
                user._receive_button_press_from_user_(callback_data)

    while True:
        bot.infinity_polling()