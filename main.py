from tkinter.tix import Tree
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
        def get_all(cls):

            cur = db_connector.cursor()
            cur.execute("SELECT tg_id, is_logged_in, referee_core_db_id, staff_core_db_id, messages_ids, trash_ignore FROM goukv_ukv.referee_bot_users")
            
            users = []
            
            for user in cur.fetchall():
                users.append(IUser({
                    "tg_id": user[0], 
                    "is_logged_in": user[1],
                    "referee_core_db_id": user[2],
                    "staff_core_db_id": user[3],
                    "messages_ids": user[4],
                    "trash_ignore": user[5]
                    }))

            return users

        @classmethod
        def register_new(cls, tg_id):
            
            new_user = IUser({
                "tg_id": tg_id,
                "is_logged_in": 0,
                "referee_core_db_id": 0,
                "staff_core_db_id": 0,
                "messages_ids": ";",
                "trash_ignore": 0
                })

            users.append(new_user)

            cur = db_connector.cursor()
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_users` (`tg_id`, `is_logged_in`, `referee_core_db_id`, `staff_core_db_id`, `messages_ids`) VALUES ({tg_id}, 0, 0, 0, ';');")

            return new_user

        def _receive_button_press_from_user_(self, callback_data):
            
            if callback_data == "log_out":
                self.log_out()

            elif callback_data == "see_referees":
                self.see_referees_list()

            elif callback_data.startswith("iaq-ref-id"):

                ref_id = callback_data.split('_')[1]
                action = callback_data.split('_')[2]

                getattr(self, f"start_{action}_referee")(int(ref_id))

                self._send_message_to_user_(local["successfully_applied_changes"], clear_previous=True)
                self.show_main_menu(False)

        def _receive_message_from_user_(self, message):
            
            if hasattr(self, "trash_ignore") and self.trash_ignore:
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

        @classmethod
        def make_relationships(cls):

            for user in users:
                for another_user in users:
                    if user.tg_id != another_user.tg_id:
                        
                        if another_user.staff_core_db_id != 0 and user.referee_core_db_id != 0:

                            cur = db_connector.cursor()
                            cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_relationships WHERE staff_core_db_id = {another_user.staff_core_db_id} AND referee_core_db_id = {user.referee_core_db_id}")
                            res = cur.fetchall()

                            if len(res) == 0:

                                cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_relationships` (`staff_core_db_id`, `referee_core_db_id`, `relationship_level`) VALUES ({another_user.staff_core_db_id}, {user.referee_core_db_id}, 1);")

                                cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_relationships WHERE staff_core_db_id = {another_user.staff_core_db_id} AND referee_core_db_id = {user.referee_core_db_id};")
                                res = cur.fetchall()
                                id = res[0][0]

                                relationships.append(IRelationship({
                                    "id": id, 
                                    "staff_core_db_id": another_user.staff_core_db_id,
                                    "referee_core_db_id": user.referee_core_db_id,
                                    "relationship_level": 1}))

                        if another_user.referee_core_db_id != 0 and user.staff_core_db_id != 0:

                            cur = db_connector.cursor()
                            cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_relationships WHERE staff_core_db_id = {user.staff_core_db_id} AND referee_core_db_id = {another_user.referee_core_db_id}")
                            res = cur.fetchall()

                            if len(res) == 0:

                                cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_relationships` (`staff_core_db_id`, `referee_core_db_id`, `relationship_level`) VALUES ({user.staff_core_db_id}, {another_user.referee_core_db_id}, 1);")

                                cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_relationships WHERE staff_core_db_id = {user.staff_core_db_id} AND referee_core_db_id = {another_user.referee_core_db_id};")
                                res = cur.fetchall()
                                id = res[0][0]

                                relationships.append(IRelationship({
                                    "id": id, 
                                    "staff_core_db_id": user.staff_core_db_id,
                                    "referee_core_db_id": another_user.referee_core_db_id,
                                    "relationship_level": 1}))

        def get_first_name(self):

            if self.referee_core_db_id != 0:
                
                cur = db_connector.cursor()
                cur.execute(f"SELECT firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {self.referee_core_db_id};")
                res = cur.fetchall()
                
                return res[0][0]

            if self.staff_core_db_id != 0:
                
                cur = db_connector.cursor()
                cur.execute(f"SELECT firstname FROM goukv_ukv.jos_joomleague_players WHERE id = {self.staff_core_db_id};")
                res = cur.fetchall()
                
                return res[0][0]

        def show_main_menu(self, refresh_screen=True):

            name = self.get_first_name()
            welcome_message = local["main_menu"].format(name)

            keyboard_layout = []

            if self.referee_core_db_id != 0:
                pass

            if self.staff_core_db_id == 0:
                
                see_my_team_future_games_button = types.InlineKeyboardButton(local["see_my_team_future_games_button"], callback_data="see_my_team_future_games")
                see_referees_list_button = types.InlineKeyboardButton(local["see_referees_list_button"], callback_data="see_referees")

                keyboard_layout.append((see_my_team_future_games_button,))
                keyboard_layout.append((see_referees_list_button,))

            log_out_button = types.InlineKeyboardButton(local["log_out_button"], callback_data="log_out")
            keyboard_layout.append((log_out_button,))

            keyboard_obj = types.InlineKeyboardMarkup(keyboard_layout)

            self._send_message_to_user_(welcome_message, keyboard_obj, refresh_screen)

        def invite_to_log_in(self):
            
            self._send_message_to_user_(local["proposition_to_log_in"], clear_previous=True)
            self.trash_ignore = 1

            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET trash_ignore = 1 WHERE tg_id = {self.tg_id};")
                    
        def receive_password(self, password):
            
            # MAKE REQUEST TO REFEREE DB
            # CHANGE STATUS IF LEN(FETCHALL IS 1)
            # MAKE REQUEST TO PLAYERS DB
            # SAME

            passed = False

            cur = db_connector.cursor()

            cur.execute(f"SELECT id FROM goukv_ukv.jos_joomleague_referees WHERE referee_bot_auth_token = '{password}'")

            res = cur.fetchall()

            if len(res) > 0 and res[0]:

                passed = True 
                cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET referee_core_db_id = {res[0][0]} WHERE tg_id = {self.tg_id}")
                self.referee_core_db_id = res[0][0]

            cur.execute(f"SELECT id FROM goukv_ukv.jos_joomleague_players WHERE referee_bot_auth_token = '{password}'")

            res = cur.fetchall()

            if len(res) > 0 and res[0]:

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
            self.trash_ignore = 0

            self.make_relationships()

            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET is_logged_in = 1, trash_ignore = 0 WHERE tg_id = {self.tg_id}")

            self.show_main_menu()

        def log_out(self):
            
            self.is_logged_in = 0

            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET is_logged_in = 0 WHERE tg_id = {self.tg_id};")

            self.invite_to_log_in()

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

        def view_future_games_as_referee(self):
            pass

        def get_request_edited(self):
            pass

        # /// TEAM REPRESENTITIVE FUNTIONS

        def see_referees_list(self):
            
            for user in users:
                if user.referee_core_db_id != 0:
                    
                    for relationship in relationships:
                        if relationship.staff_core_db_id == self.staff_core_db_id and relationship.referee_core_db_id == user.referee_core_db_id:
                            rel_level = relationship.relationship_level
                            res_sign = (local["love_referee"] if rel_level == 2 else (local["dont_care_referee"] if rel_level == 1 else local["hate_referee"]))

                    cur = db_connector.cursor()
                    cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {user.referee_core_db_id}")
                    
                    res = cur.fetchall()
                    name_string = f"{res[0][0]}, {res[0][1]} ({res_sign})"

                    love_button = types.InlineKeyboardButton(local["love_referee"], callback_data=f"iaq-ref-id_{user.referee_core_db_id}_loving")
                    hate_button = types.InlineKeyboardButton(local["hate_referee"], callback_data=f"iaq-ref-id_{user.referee_core_db_id}_hating")
                    neutral_button = types.InlineKeyboardButton(local["dont_care_referee"], callback_data=f"iaq-ref-id_{user.referee_core_db_id}_notcaring")

                    keyboard_layout = [[]]

                    if rel_level != 0:
                        keyboard_layout[0].append(hate_button)                        
                    if rel_level != 1:
                        keyboard_layout[0].append(neutral_button)  
                    if rel_level != 2:
                        keyboard_layout[0].append(love_button)  

                    keyboard_obj = types.InlineKeyboardMarkup(keyboard_layout)

                    self._send_message_to_user_(name_string, keyboard_obj)

        def view_future_games_as_team_rep(self):
            
            cur = db_connector.cursor()
            
            teams = cur.fetchall()
            for team in teams:

                print(team)

                cur.execute(f"SELECT id, playground_id, match_date, matchpart1, matchpart2, referee_id, referee_id2, referee_id3 FROM goukv_ukv.jos_joomleague_matches WHERE ((matchpart1 = {team[0]} OR matchpart2 = {team[1]}) AND (match_date > GETDATE()))")

                matches = cur.fetchall()
                for match in matches:
                    print(match)

        def start_loving_referee(self, ref_id): # TODO update requests as well
            
            for relation in relationships:
                if relation.referee_core_db_id == ref_id and relation.staff_core_db_id == self.staff_core_db_id:
                    relation.relationship_level = 2

                cur = db_connector.cursor()
                cur.execute(f"UPDATE goukv_ukv.referee_bot_relationships SET relationship_level = 2 WHERE id = {relation.id};")

        def start_hating_referee(self, ref_id):

            for relation in relationships:
                if relation.referee_core_db_id == ref_id and relation.staff_core_db_id == self.staff_core_db_id:
                    relation.relationship_level = 0

            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_relationships SET relationship_level = 0 WHERE id = {relation.id};")

        def start_notcaring_referee(self, ref_id):

            for relation in relationships:
                if ((relation.referee_core_db_id == ref_id) and (relation.staff_core_db_id == self.staff_core_db_id)):
                    relation.relationship_level = 1

            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_relationships SET relationship_level = 1 WHERE id = {relation.id};")

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

    class IRelationship:

        @classmethod
        def get_all(cls):
        
            cur = db_connector.cursor()
            cur.execute("SELECT id, staff_core_db_id, referee_core_db_id, relationship_level FROM goukv_ukv.referee_bot_relationships")
            
            relationships = []
            
            for relationship in cur.fetchall():
                relationships.append(IRelationship({
                    "id": relationship[0],
                    "staff_core_db_id": relationship[1], 
                    "referee_core_db_id": relationship[2],
                    "relationship_level": relationship[3]
                    }))

            return relationships

        def __init__(self, init_values) -> None:
            
            for key, value in init_values.items():
                setattr(self, key, value)

    class IRequest:
        
        @classmethod
        def get_all(cls):
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
    relationships = IRelationship.get_all()
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
            if user.tg_id == callback_data.from_user.id:

                if not callback_data.data.startswith('iaq'):
                    bot.answer_callback_query(callback_data.id)

                user._receive_button_press_from_user_(callback_data.data)

    while True:
        bot.infinity_polling()