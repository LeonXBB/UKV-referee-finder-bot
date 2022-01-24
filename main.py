import re
from tkinter import N
import secret
from localization import local

import telebot
from telebot import types

import mysql.connector
import threading
import time

if __name__ == "__main__":
    
    global db_connector, users, referees, team_reps, games, requests, request_messages

    bot = telebot.TeleBot(secret.tg_bot_key)

    def get_db_connector():
    
        cnx = mysql.connector.connect(
            host=secret.db_host,
            port=secret.db_port,
            user=secret.db_user,
            password=secret.db_password)

        return cnx

    class IUser:

        @classmethod
        def get_all(cls):

            db_connector.reconnect()
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

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_users` (`tg_id`, `is_logged_in`, `referee_core_db_id`, `staff_core_db_id`, `messages_ids`) VALUES ({tg_id}, 0, 0, 0, ';');")

            return new_user

        def _receive_button_press_from_user_(self, callback_data, message_id):
            
            if callback_data == "log_out":
                self.log_out()

            elif callback_data == "show_main_menu":
                self.show_main_menu()

            elif callback_data == "see_my_future_games":
                self.view_future_games_as_referee()

            elif callback_data.startswith("req_agree"):

                try:
                    bot.delete_message(self.tg_id, message_id)
                except:
                    pass

                request_id = callback_data.split("_")[2]
                self.accept_request(request_id)

            elif callback_data.startswith("req_deny"):

                try:
                    bot.delete_message(self.tg_id, message_id)
                except:
                    pass

                request_id = callback_data.split("_")[2]
                self.deny_request(callback_data.split("_")[2])

            elif callback_data.startswith("see_my_team_future_games"):
                team_id = callback_data.split("_")[5]
                self.view_future_games_as_team_rep(team_id)

            elif callback_data.startswith("lfr"):

                self.forming_request = f"000_{callback_data}"
                self.start_forming_request()

            elif callback_data.startswith("cr"):
                
                referee_index = callback_data.split("_")[1]
                request_id = callback_data.split("_")[2]

                for request in requests:
                    request.get_cancelled()

            elif callback_data.startswith("cas"):
                
                for request in requests:
                    request.get_withdrawn('s')

            elif callback_data.startswith("car"):

                for request in requests:
                    request.get_withdrawn('r')

            elif callback_data.startswith("rrc"):
                self.forming_request = callback_data.split("_")[1] + self.forming_request[1:]
                self.start_forming_request()

            elif callback_data.startswith("rp"):
                self.forming_request = self.forming_request[0] + callback_data.split("_")[1] + self.forming_request[2:]
                self.start_forming_request()

            elif callback_data.startswith("rt"):
                self.forming_request = self.forming_request[:2] + callback_data.split("_")[1] + self.forming_request[3:]
                self.start_forming_request()

            elif callback_data == "send_request":
                self.send_request(self.forming_request)

            elif callback_data.startswith("s_req_agree"):

                try:
                    bot.delete_message(self.tg_id, message_id)
                except:
                    pass

                request_id = callback_data.split("_")[3]
                self.accept_acceptance_of_a_request(request_id, self.referee_core_db_id)

            elif callback_data.startswith("s_req_deny"):

                try:
                    bot.delete_message(self.tg_id, message_id)
                except:
                    pass

                request_id = callback_data.split("_")[3]
                self.decline_acceptance_of_a_request(request_id, self.referee_core_db_id)

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

            try:
                bot.delete_message(self.tg_id, message_id)
            except:
                pass

        def _send_message_to_user_(self, message, keyboard=None, clear_previous=False, return_message=False, parse_mode="html"):
            
            if clear_previous:
                self._clear_messages_()

            message = bot.send_message(self.tg_id, message, reply_markup=keyboard, parse_mode=parse_mode)
        
            self._add_message_to_history(message)

            if return_message: return message

        def _add_message_to_history(self, message):
            
            self.messages_ids += f"{message.id};"

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE `goukv_ukv`.`referee_bot_users` SET messages_ids = concat(messages_ids, '{message.id};') WHERE tg_id = {self.tg_id};")

        def _clear_messages_(self):
            
            def is_important():
                for request_message in request_messages:
                    if int(request_message.message_id) == int(message_id):
                        return True
                return False

            for message_id in self.messages_ids.split(';'):
                if message_id and not is_important():
                    try:
                        bot.delete_message(self.tg_id, int(message_id))
                    except:
                        pass

            self.messages_ids = ";"
            
            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE `goukv_ukv`.`referee_bot_users` SET messages_ids = ';' WHERE tg_id = {self.tg_id}")

        def __init__(self, init_values):
            
            for key, value in init_values.items():
                setattr(self, key, value)

        @classmethod
        def make_relationships(cls):

            for user in users:
                for another_user in users:
                    if user.tg_id != another_user.tg_id:
                        
                        if another_user.staff_core_db_id != 0 and user.referee_core_db_id != 0:

                            db_connector.reconnect()
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

                            db_connector.reconnect()
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
                
                db_connector.reconnect()
                cur = db_connector.cursor()
                cur.execute(f"SELECT firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {self.referee_core_db_id};")
                res = cur.fetchall()
                
                return res[0][0]

            if self.staff_core_db_id != 0:
                
                db_connector.reconnect()
                cur = db_connector.cursor()
                cur.execute(f"SELECT firstname FROM goukv_ukv.jos_joomleague_players WHERE id = {self.staff_core_db_id};")
                res = cur.fetchall()
                
                return res[0][0]

        def show_main_menu(self, refresh_screen=True):

            name = self.get_first_name()
            welcome_message = local["main_menu"].format(name)

            keyboard_layout = []

            if self.referee_core_db_id != 0:
                
                see_my_future_games_button = types.InlineKeyboardButton(local["see_my_future_games_button"], callback_data="see_my_future_games")

                keyboard_layout.append((see_my_future_games_button,))

            if self.staff_core_db_id != 0:
                
                self.teams_ids = self._get_teams_ids()
                self.teams_ids = list(set(self.teams_ids))

                team_buttons = []

                for team_id in self.teams_ids:

                    db_connector.reconnect()
                    cur = db_connector.cursor()
                    cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {team_id[0]};")
                    res = cur.fetchall()
                    team_buttons.append([types.InlineKeyboardButton(local["see_my_team_future_games_button"].format(res[0][0]), callback_data=f"see_my_team_future_games_{team_id[0]}"),])
                
                see_referees_list_button = types.InlineKeyboardButton(local["see_referees_list_button"], callback_data="see_referees")

                keyboard_layout.extend(team_buttons)
                keyboard_layout.append((see_referees_list_button,))

            log_out_button = types.InlineKeyboardButton(local["log_out_button"], callback_data="log_out")
            keyboard_layout.append((log_out_button,))

            keyboard_obj = types.InlineKeyboardMarkup(keyboard_layout)

            self._send_message_to_user_(welcome_message, keyboard_obj, refresh_screen)

        def _send_return_to_the_main_menu_keyboard_(self, with_return=False):    
            
            return_to_the_main_menu_keyboard_button = types.InlineKeyboardButton(local["return_to_main_menu_button"], callback_data="show_main_menu")
            return_to_the_main_menu_keyboard_layout = [[return_to_the_main_menu_keyboard_button]]
            return_to_the_main_menu_keyboard_obj = types.InlineKeyboardMarkup(return_to_the_main_menu_keyboard_layout)

            mess = self._send_message_to_user_(local["return_to_main_menu_text"], return_to_the_main_menu_keyboard_obj, return_message=True)

            if with_return: return mess

        def invite_to_log_in(self):
            
            self._send_message_to_user_(local["proposition_to_log_in"], clear_previous=True)
            self.trash_ignore = 1

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET trash_ignore = 1 WHERE tg_id = {self.tg_id};")
                    
        def receive_password(self, password):
            
            passed = False

            db_connector.reconnect()
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

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET is_logged_in = 1, trash_ignore = 0 WHERE tg_id = {self.tg_id}")

            self.show_main_menu()

            for request_message in request_messages:
                pass # TODO resend messages if they're unsolved

        def log_out(self):
            
            self.is_logged_in = 0

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_users SET is_logged_in = 0 WHERE tg_id = {self.tg_id};")

            self.invite_to_log_in()

            for request_message in request_messages:
                if request_message.user_id == self.tg_id:
                    try:
                        bot.delete_message(self.tg_id, request_message.message_id)
                    except:
                        pass

        # /// REFEREE FUNCTIONS

        def view_future_games_as_referee(self):
            
            self._clear_messages_()

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT match_id, playground_id, match_date, matchpart1, matchpart2, referee_id, referee_id2, referee_id3 FROM goukv_ukv.jos_joomleague_matches WHERE (match_date > NOW()) AND (referee_id = {self.referee_core_db_id} OR referee_id2 = {self.referee_core_db_id} OR referee_id3 = {self.referee_core_db_id})")
            matches = cur.fetchall()

            for match in matches:

                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_teams WHERE id = {match[3]}")
                try:
                    match_team_name_one = cur.fetchall()[0][0]
                except:
                    match_team_name_one = ''
                
                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_teams WHERE id = {match[4]}")
                try: 
                    match_team_name_two = cur.fetchall()[0][0]
                except:
                    match_team_name_two = ''

                match_date_time = str(match[2]).replace('-', '.')[:-3]
                
                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_playgrounds WHERE id = {match[1]}")
                try:
                    match_court_address = cur.fetchall()[0][0]
                except:
                    match_court_address = ""

                cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {match[5]}")
                try:
                    res = cur.fetchall()
                    referee_one = f"{res[0][0]}, {res[0][1]}"
                except:
                    referee_one = local["referee_not_found"]
                    
                cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {match[6]}")
                try:
                    res = cur.fetchall()
                    referee_two = f"{res[0][0]}, {res[0][1]}"
                except:
                    referee_two = local["referee_not_found"]

                cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {match[7]}")
                try:
                    res = cur.fetchall()
                    referee_three = f"{res[0][0]}, {res[0][1]}"                
                except:
                    referee_three = local["referee_not_found"]

                cancel_request_keyboard = None

                ref_ind = 0

                if match[6] == self.referee_core_db_id:
                    i = 1
                if match[7] == self.referee_core_db_id:
                    i = 2

                print(match[7] == self.referee_core_db_id)
                print(match, self.referee_core_db_id, ref_ind)
                cur.execute(f"SELECT referee_index, id FROM goukv_ukv.referee_bot_requests WHERE match_id = {match[0]} AND referee_id = {self.referee_core_db_id} AND referee_index = {i}")
                res = cur.fetchall()
                print(res)
                if len(res) > 0 and len(res[0]) > 0:

                    cancel_keyboard_button = types.InlineKeyboardButton(local["cancel_agreement_button"], callback_data=f"car_{i}_{res[0][1]}")
                    cancel_keyboard_layout = ((cancel_keyboard_button,),)
                    cancel_request_keyboard = types.InlineKeyboardMarkup(cancel_keyboard_layout)
                
                self._send_message_to_user_(local["match_template_with_referees"].format(match_team_name_one, match_team_name_two, match_date_time, match_court_address, referee_one, referee_two, referee_three), cancel_request_keyboard)

            if len(matches) == 0 or len(matches[0]) == 0:
                self._send_message_to_user_(local["no_games_yet"])

            self._send_return_to_the_main_menu_keyboard_()

        def receive_request(self, request):
            
            yes = types.InlineKeyboardButton(local["agree_to_request"], callback_data=f"req_agree_{request.id}")
            no = types.InlineKeyboardButton(local["deny_request"], callback_data=f"req_deny_{request.id}")
            yes_no_layout = ((yes, no),)
            yes_no_keyboard = types.InlineKeyboardMarkup(yes_no_layout)

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT matchpart1, matchpart2, playground_id, match_date FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {request.match_id}")
            res = cur.fetchall()
            match_info = res[0]

            cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {match_info[0]}")
            res = cur.fetchall()
            team_name_one = res[0][0]

            cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {match_info[1]}")
            res = cur.fetchall()
            team_name_two = res[0][0]

            cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_playgrounds WHERE id = {match_info[2]}")
            res = cur.fetchall()
            address = res[0][0]

            role = local["referee_titles_empty"][int(request.referee_index)]

            pay = local["pay_titles"][int(request.pay)]

            transfer = local["transfer_titles"][int(request.transfer)]
            
            match_time = ":".join(str(match_info[3]).split(':')[:-1]).replace("-", ".")

            mess = self._send_message_to_user_(local["match_request"].format(team_name_one, team_name_two, address, match_time, role, pay, transfer), yes_no_keyboard, True, True)

            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_request_messages` (`request_id`, `user_id`, `message_id`, `decision`, `type`) VALUES ({request.id}, {self.tg_id}, {mess.id}, 1, 0)")

            cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_request_messages WHERE request_id = {request.id} AND user_id = {self.tg_id} AND message_id = {mess.id}")
            res = cur.fetchall()

            request_messages.append(IRequestMessage({
                "id": res[0][0],
                "request_id": request.id,
                "user_id": self.tg_id,
                "message_id": mess.id,
                "decision": 1,
                "type": 0
            }))

        def accept_request(self, request_id):

            for request in requests:
                if int(request.id) == int(request_id) and request.status != 3 and request.status != 0 and request.status != "3" and request.status != "0":
                    request.get_accepted(self.referee_core_db_id)
                    mess = self._send_message_to_user_(local["thank you"], return_message=True)

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_request_messages` (`request_id`, `user_id`, `message_id`, `decision`, `type`) VALUES ({request.id}, {self.tg_id}, {mess.id}, 1, 1)")

            cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_request_messages WHERE request_id = {request.id} AND user_id = {self.tg_id} AND message_id = {mess.id}")
            res = cur.fetchall()

            request_messages.append(IRequestMessage({
                "id": res[0][0],
                "request_id": request.id,
                "user_id": self.tg_id,
                "message_id": mess.id,
                "decision": 1,
                "type": 1
            }))

            menu_mess = self._send_return_to_the_main_menu_keyboard_(with_return=True)
            
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_request_messages` (`request_id`, `user_id`, `message_id`, `decision`, `type`) VALUES ({request.id}, {self.tg_id}, {menu_mess.id}, 1, 9)")

            cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_request_messages WHERE request_id = {request.id} AND user_id = {self.tg_id} AND message_id = {menu_mess.id}")
            res = cur.fetchall()

            request_messages.append(IRequestMessage({
                "id": res[0][0],
                "request_id": request.id,
                "user_id": self.tg_id,
                "message_id": menu_mess.id,
                "decision": 1,
                "type": 9
            }))

        def deny_request(self, request_id):

            self.show_main_menu()
        
            for request in requests:
                if request.id == request_id:
                    request.decision = 0

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_request_messages SET decision = 0 WHERE id = {request_id} AND user_id = {self.tg_id}")

        def withdrew_acceptance_of_request_as_referee(self):
            
            self._send_message_to_user_(local["agreement_cancelled"], clear_previous=True)
            self._send_return_to_the_main_menu_keyboard_()
        
        def get_acceptance_declined(self, request_id):
            
            for request_message in request_messages:
                    if (request_message.type == 1 or request_message.type == 9) and request_message.user_id == self.tg_id:
                        try:
                            bot.delete_message(self.tg_id, request_message.message_id)
                        except:
                            pass

            match_id = 0

            for request in requests:
                if request.id == request_id:
                    match_id = request.match_id

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT matchpart1 FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {match_id}")
            res = cur.fetchall()[0][0]
            cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {res}")
            team_name = cur.fetchall()[0][0]

            self._send_message_to_user_(local["final_acceptance_declined"].format(team_name))
            self._send_return_to_the_main_menu_keyboard_()

        def get_acceptance_approved(self, request_id):

            for request_message in request_messages:
                if request_message.type == 1 and request_message.user_id == self.tg_id:
                    try:
                        bot.delete_message(self.tg_id, request_message.message_id)
                    except:
                        pass

            match_id = 0

            for request in requests:
                if request.id == request_id:
                    match_id = request.match_id

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT matchpart1 FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {match_id}")
            res = cur.fetchall()[0][0]
            cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {res}")
            team_name = cur.fetchall()[0][0]

            self._send_message_to_user_(local["final_acceptance_referee"].format(team_name))
            self._send_return_to_the_main_menu_keyboard_()

        def receive_withdrawal_of_acceptance_by_the_staff(self, match_id):
            
            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT matchpart1 FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {match_id}")

            team_id = cur.fetchall()[0][0]
            
            cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {team_id}")
            team_name = cur.fetchall()[0][0]
            
            self._send_message_to_user_(local["agreement_cancelled_by_staff"].format(team_name))
            self._send_return_to_the_main_menu_keyboard_()

        # /// TEAM REPRESENTITIVE FUNTIONS

        def see_referees_list(self):
            
            rel_level = 1
            res_sign = local["dont_care_referee"]

            for user in users:
                if user.referee_core_db_id != 0:
                    
                    for relationship in relationships:
                        if relationship.staff_core_db_id == self.staff_core_db_id and relationship.referee_core_db_id == user.referee_core_db_id:
                            rel_level = relationship.relationship_level
                            res_sign = (local["love_referee"] if rel_level == 2 else (local["dont_care_referee"] if rel_level == 1 else local["hate_referee"]))

                    db_connector.reconnect()
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

            self._send_return_to_the_main_menu_keyboard_()

        def _get_teams_ids(self):
            
            rv = []

            db_connector.reconnect()
            cur = db_connector.cursor()
            
            cur.execute(f"SELECT projectteam_id FROM goukv_ukv.jos_joomleague_teamstaff_project WHERE person_id = {self.staff_core_db_id}")

            project_teams_ids = cur.fetchall()

            for project_team_id in project_teams_ids:
                cur.execute(f"SELECT team_id FROM goukv_ukv.jos_joomleague_team_joomleague WHERE id = {project_team_id[0]}")
                
                rv.extend(cur.fetchall())
            
            return rv
            
        def view_future_games_as_team_rep(self, team_id):

            self._clear_messages_()

            db_connector.reconnect()
            cur = db_connector.cursor()    
            cur.execute(f"SELECT match_id, playground_id, match_date, matchpart1, matchpart2, referee_id, referee_id2, referee_id3 FROM goukv_ukv.jos_joomleague_matches WHERE matchpart1 = {team_id} AND match_date > NOW()")

            matches = cur.fetchall()
            matches = list(set(matches))

            for match in matches:

                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_teams WHERE id = {match[3]}")
                try:
                    match_team_name_one = cur.fetchall()[0][0]
                except:
                    match_team_name_one = ''
                
                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_teams WHERE id = {match[4]}")
                try: 
                    match_team_name_two = cur.fetchall()[0][0]
                except:
                    match_team_name_two = ''

                match_date_time = str(match[2]).replace('-', '.')[:-3]
                
                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_playgrounds WHERE id = {match[1]}")
                try:
                    match_court_address = cur.fetchall()[0][0]
                except:
                    match_court_address = ""

                cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {match[5]}")
                try:
                    res = cur.fetchall()
                    referee_one = f"{res[0][0]}, {res[0][1]}"
                except:
                    referee_one = local["referee_not_found"]
                    
                cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {match[6]}")
                try:
                    res = cur.fetchall()
                    referee_two = f"{res[0][0]}, {res[0][1]}"
                except:
                    referee_two = local["referee_not_found"]

                cur.execute(f"SELECT lastname, firstname FROM goukv_ukv.jos_joomleague_referees WHERE id = {match[7]}")
                try:
                    res = cur.fetchall()
                    referee_three = f"{res[0][0]}, {res[0][1]}"                
                except:
                    referee_three = local["referee_not_found"]

                self._send_message_to_user_(local["match_template"].format(match_team_name_one, match_team_name_two, match_date_time, match_court_address))

                for i, referee in enumerate((referee_one, referee_two, referee_three)):

                    ignore_keyboard = False

                    if referee == local["referee_not_found"]:
                        db_connector.reconnect()
                        cur = db_connector.cursor()
                        cur.execute(f"SELECT status, id FROM goukv_ukv.referee_bot_requests WHERE match_id = {match[0]} AND referee_index = {i}")
                        res = cur.fetchall()
                        if len(res) != 0 and res[0][0] != 10 and res[0][0] != 0:
                            button = types.InlineKeyboardButton(local["cancel_request_button"], callback_data=f"cr_{i}_{res[0][1]}")
                        else:
                            button = types.InlineKeyboardButton(local["look_for_referee_button"], callback_data=f"lfr_{i}_{match[0]}")

                    else:

                        cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_requests WHERE match_id = {match[0]} AND made_by = {self.staff_core_db_id} AND referee_index = {i}")
                        res = cur.fetchall()
                        if len(res) > 0 and len(res[0]) > 0:
                            button = types.InlineKeyboardButton(local["cancel_agreement_button"], callback_data=f"cas_{i}_{res[0][0]}")
                        else:
                            ignore_keyboard = True
                            
                    if not ignore_keyboard:
                        keyboard_obj = types.InlineKeyboardMarkup(((button,),))
                    else:
                        keyboard_obj = None

                    self._send_message_to_user_(local["referees_titles"][i].format(referee), keyboard_obj)

            if len(matches) == 0 or len(matches[0]) == 0:
                self._send_message_to_user_(local["no_games_yet"])

            self._send_return_to_the_main_menu_keyboard_()

        def start_loving_referee(self, ref_id):
            
            for relation in relationships:
                if relation.referee_core_db_id == ref_id and relation.staff_core_db_id == self.staff_core_db_id:
                    relation.relationship_level = 2

                db_connector.reconnect()
                cur = db_connector.cursor()
                cur.execute(f"UPDATE goukv_ukv.referee_bot_relationships SET relationship_level = 2 WHERE id = {relation.id};")

            for request in requests:
                request.get_sent()

        def start_hating_referee(self, ref_id):

            for relation in relationships:
                if relation.referee_core_db_id == ref_id and relation.staff_core_db_id == self.staff_core_db_id:
                    relation.relationship_level = 0

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_relationships SET relationship_level = 0 WHERE id = {relation.id};")

        def start_notcaring_referee(self, ref_id):

            for relation in relationships:
                if ((relation.referee_core_db_id == ref_id) and (relation.staff_core_db_id == self.staff_core_db_id)):
                    relation.relationship_level = 1

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_relationships SET relationship_level = 1 WHERE id = {relation.id};")

        def start_forming_request(self):
            
            category_fourth_button = types.InlineKeyboardButton(local["categories_titles"][0], callback_data="rrc_0")
            category_third_button = types.InlineKeyboardButton(local["categories_titles"][1], callback_data="rrc_1")
            category_second_button = types.InlineKeyboardButton(local["categories_titles"][2], callback_data="rrc_2")
            category_first_button = types.InlineKeyboardButton(local["categories_titles"][3], callback_data="rrc_3")

            no_transfer_button = types.InlineKeyboardButton(local["transfer_titles"][0], callback_data="rt_0")
            transfer_button = types.InlineKeyboardButton(local["transfer_titles"][1], callback_data="rt_1")

            regular_pay_button = types.InlineKeyboardButton(local["pay_titles"][0], callback_data="rp_0")
            higher_pay_button = types.InlineKeyboardButton(local["pay_titles"][1], callback_data="rp_1")

            send_request_button = types.InlineKeyboardButton(local["send_request"], callback_data="send_request")

            category_row = []
            for i, category_button in enumerate((category_fourth_button, category_third_button, category_second_button, category_first_button)):
                if self.forming_request[0] != str(i):
                    category_row.append(category_button)

            transfer_row = []
            for i, transfer_button in enumerate((no_transfer_button, transfer_button)):
                if self.forming_request[2] != str(i):
                    transfer_row.append(transfer_button)

            pay_row = []
            for i, pay_button in enumerate((regular_pay_button, higher_pay_button)):
                if self.forming_request[1] != str(i):
                    pay_row.append(pay_button)

            keyboard_layout = (category_row, pay_row, transfer_row, (send_request_button,))
            keyboard_obj = types.InlineKeyboardMarkup(keyboard_layout)

            text = local["request_template"].format(local["categories_titles"][int(self.forming_request[0])], local["pay_titles"][int(self.forming_request[1])], local["transfer_titles"][int(self.forming_request[2])])

            self._send_message_to_user_(text, keyboard_obj, True)

            self._send_return_to_the_main_menu_keyboard_()

        def send_request(self, request_data):
            
            ref_cat = request_data[0]
            pay = request_data[1]
            transfer = request_data[2]
            ref_index = request_data.split("_")[2]
            match_id = request_data.split("_")[3]

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_requests` (`made_by`, `made_at`, `match_id`, `status`, `referee_id`, `referee_index`, `category_min`, `pay`, `transfer`) VALUES ({self.staff_core_db_id}, CURRENT_TIMESTAMP(), {match_id}, 1, 0, {ref_index}, {ref_cat}, {pay}, {transfer})")

            cur.execute(f"SELECT id, made_at, status, referee_id FROM goukv_ukv.referee_bot_requests WHERE match_id = {match_id} AND referee_index = {ref_index}")
            res = cur.fetchall()

            requests.append(IRequest({
                "id": res[0][0],
                "made_by": self.staff_core_db_id,
                "made_at": res[0][1],
                "match_id": match_id,
                "status": res[0][2],
                "referee_id": res[0][3],
                "referee_index": ref_index,
                "category_min": ref_cat,
                "pay": pay,
                "transfer": transfer
            }))
            self.forming_request = ""

            self._send_message_to_user_(local["successfully_sent_request"], clear_previous=True)
            self._send_return_to_the_main_menu_keyboard_()

        def cancel_request(self):
            
            self._send_message_to_user_(local["request_cancelled"], clear_previous=True)
            self._send_return_to_the_main_menu_keyboard_()

        def receive_acceptance_of_a_request(self, request, referee_id):

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT match_id, playground_id, match_date, matchpart1, matchpart2 FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {request.match_id}")
            matches = cur.fetchall()

            for match in matches:

                cur.execute(f"SELECT firstname, lastname FROM goukv_ukv.jos_joomleague_referees WHERE id = {referee_id}")
                try:
                    res = cur.fetchall()
                    referee_name = f"{res[0][0]} {res[0][1]}"
                except:
                    referee_name = ""

                try:
                    referee_title = local["referee_titles_empty"][int(request.referee_index)]
                except:
                    referee_title = ""

                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_teams WHERE id = {match[3]}")
                try:
                    match_team_name_one = cur.fetchall()[0][0]
                except:
                    match_team_name_one = ''
                
                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_teams WHERE id = {match[4]}")
                try: 
                    match_team_name_two = cur.fetchall()[0][0]
                except:
                    match_team_name_two = ''

                match_date_time = str(match[2]).replace('-', '.')[:-3]
                
                cur.execute(f"SELECT name from goukv_ukv.jos_joomleague_playgrounds WHERE id = {match[1]}")
                try:
                    match_court_address = cur.fetchall()[0][0]
                except:
                    match_court_address = ""            

            approve = types.InlineKeyboardButton(local["agree_to_request"], callback_data=f"s_req_agree_{request.id}")
            decline = types.InlineKeyboardButton(local["deny_request"], callback_data=f"s_req_deny_{request.id}")

            keyboard_layout = ((approve, decline),)
            keyboard_obj = types.InlineKeyboardMarkup(keyboard_layout)

            mess = self._send_message_to_user_(local["received_acceptance_of_the_request"].format(referee_name, match_team_name_one, match_team_name_two, match_date_time, match_court_address, referee_title), keyboard_obj, return_message=True)

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"INSERT INTO `goukv_ukv`.`referee_bot_request_messages` (`request_id`, `user_id`, `message_id`, `decision`, `type`) VALUES ({request.id}, {self.tg_id}, {mess.id}, 1, 2)")

            cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_request_messages WHERE request_id = {request.id} AND user_id = {self.tg_id} AND message_id = {mess.id}")
            res = cur.fetchall()

            request_messages.append(IRequestMessage({
                "id": res[0][0],
                "request_id": request.id,
                "user_id": self.tg_id,
                "message_id": mess.id,
                "decision": 1,
                "type": 2
            }))

        def accept_acceptance_of_a_request(self, request_id, referee_id):
            
            for request in requests:
                if int(request.id) == int(request_id):
                    request.get_approved(referee_id)

            self._send_message_to_user_(local["final_acceptance_staff"])
            self._send_return_to_the_main_menu_keyboard_()

        def decline_acceptance_of_a_request(self, request_id, referee_id):
            
            for request in requests:
                if int(request.id) == int(request_id):
                    request.get_declined(referee_id) 
                if request.id == request_id and request.referee_id == referee_id: # TODO ???
                    request.decision = 0

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_request_messages SET decision = 0 WHERE id = {request_id} AND user_id = {self.tg_id}")

            self._send_return_to_the_main_menu_keyboard_()

        def withdraw_acceptance_of_request_as_staff(self):

            self._send_message_to_user_(local["agreement_cancelled"], clear_previous=True)
            self._send_return_to_the_main_menu_keyboard_()

        def receive_withdrawal_of_acceptance_by_the_referee(self, match_id):
            
            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT matchpart1, matchpart2 FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {match_id}")

            teams_ids = cur.fetchall()[0]

            team_names = []

            for i, team_id in enumerate(teams_ids):
                cur.execute(f"SELECT name FROM goukv_ukv.jos_joomleague_teams WHERE id = {team_id}")
                team_names.append(cur.fetchall()[0][0])
            
            self._send_message_to_user_(local["agreement_cancelled_by_referee"].format(*team_names))
            self._send_return_to_the_main_menu_keyboard_()

    class IRelationship:

        @classmethod
        def get_all(cls):
        
            db_connector.reconnect()
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
            
            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute("SELECT * FROM goukv_ukv.referee_bot_requests")

            requests = []

            for request in cur.fetchall():
                requests.append(IRequest({
                    "id": request[0],
                    "made_by": request[1],
                    "made_at": request[2],
                    "match_id": request[3],
                    "status": request[4],
                    "referee_id": request[5],
                    "referee_index": request[6],
                    "category_min": request[7],
                    "pay": request[8],
                    "transfer": request[9]
                }))
            
            return requests

        def __init__(self, init_values) -> None:
            
            for key, value in init_values.items():
                setattr(self, key, value)

        def get_sent(self):
            
            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT match_date FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {self.match_id}")

            match_time =  time.mktime(cur.fetchall()[0][0].timetuple())
            request_time = time.mktime(self.made_at.timetuple())
            current_time = int(time.time())

            def is_not_self():
                return user.referee_core_db_id != self.made_by

            def is_referee():
                return user.referee_core_db_id != 0

            def is_correct_group(group_number):
                cur.execute(f"SELECT relationship_level FROM goukv_ukv.referee_bot_relationships WHERE referee_core_db_id = {user.referee_core_db_id} AND staff_core_db_id = {self.made_by}") 
                res = cur.fetchall()
                return len(res) > 0 and res[0][0] == group_number

            def is_correct_category():
                cur.execute(f"SELECT classic_voleyball_category FROM goukv_ukv.jos_joomleague_referees WHERE id = {user.referee_core_db_id}")
                res = cur.fetchall()
                for i, category in enumerate(local["categories_titles"]):
                    if res[0][0].startswith(category.split(".")[0]):
                        return i >= int(self.category_min)
                return False

            def is_not_previous_match_referee():
                
                db_connector.reconnect()
                cur = db_connector.cursor()
                
                cur.execute(f"SELECT matchpart1 FROM goukv_ukv.jos_joomleague_matches WHERE match_id = {self.match_id}")
                res = cur.fetchall()
                home_team_id = res[0][0]

                cur.execute(f"SELECT referee_id FROM goukv_ukv.jos_joomleague_matches WHERE matchpart1 = {home_team_id} AND match_date < NOW() ORDER BY match_date DESC LIMIT 1")
                res = cur.fetchall()
                last_home_match = res[0][0]
                return last_home_match != self.referee_id

            def is_not_already_send():
                cur.execute(f"SELECT id FROM goukv_ukv.referee_bot_request_messages WHERE request_id = {self.id} AND user_id = {user.tg_id}")
                res = cur.fetchall()
                return len(res) == 0 or len(res[0]) == 0

            def whole_group_refused(group_level):
                
                relationship_count = 0
                denied_request_messages_count = 0

                for relationship in relationships:
                    if relationship.relationship_level == group_level and self.made_by == relationship.referee_core_db_id:
                        relationship_count += 1
                
                for request_message in request_messages:
                    if request_message.request_id == self.id and request_message.type == 0 and (request_message.decision == 0 or request_message.decision == 2):
                        denied_request_messages_count += 1
                    elif request_message.request_id == self.id and request_message.type == 0 and (request_message.decision == 1 or request_message.decision > 2):
                        return False
                
                return denied_request_messages_count >= relationship_count

            for user in users:
                if is_not_self():
                    if is_referee():
                        if is_correct_group(2):
                            if is_correct_category():
                                if int(self.referee_index) > 0 or is_not_previous_match_referee():
                                    if is_not_already_send():
                                        if user.is_logged_in: 
                                            user.receive_request(self)

            if (current_time >= request_time + ((match_time - request_time) * 0.5)) or whole_group_refused(0):
                for user in users:
                    if is_not_self():
                        if is_referee():
                            if is_correct_group(1):
                                if is_correct_category():
                                    if int(self.referee_index) > 0 or is_not_previous_match_referee():
                                        if is_not_already_send():
                                            if user.is_logged_in: 
                                                user.receive_request(self)

            if (current_time >= request_time + ((match_time - request_time) * 0.75)) or (whole_group_refused(0) and whole_group_refused(1)):
                for user in users:
                     if is_not_self():
                        if is_referee():
                            if is_correct_group(0):
                                if is_correct_category():
                                    if int(self.referee_index) > 0 or is_not_previous_match_referee():
                                        if is_not_already_send():
                                            if user.is_logged_in: 
                                                user.receive_request(self)                                    

        def get_cancelled(self):
            
            for user in users:
                if int(user.staff_core_db_id) == int(self.made_by):
                    user.cancel_request()
            
            self.status = 0

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_requests SET status = 0 WHERE id = {self.id}")

            for request_message in request_messages:
                if request_message.request_id == self.id:
                    try:
                        bot.delete_message(request_message.user_id, request_message.message_id)
                    except:
                        pass
            # TODO fix statuses in messages

        def get_accepted(self, referee_id):
            
            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"SELECT tg_id FROM goukv_ukv.referee_bot_users WHERE staff_core_db_id = {self.made_by}")
            res = cur.fetchall()
            
            for user in users:
                if user.tg_id == res[0][0]:
                    user.receive_acceptance_of_a_request(self, referee_id)

        def get_approved(self, referee_id):
            
            i = ""

            if int(self.referee_index) > 0:
                i = self.referee_index + 1

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.jos_joomleague_matches SET referee_id{i} = {referee_id} WHERE match_id = {self.match_id}")

            cur.execute(f"UPDATE goukv_ukv.referee_bot_requests SET referee_id = {referee_id} WHERE id = {self.id}")
            self.referee_id = referee_id

            cur.execute(f"UPDATE goukv_ukv.referee_bot_requests SET status = 3 WHERE id = {self.id}")
            self.status = 3

            for user in users:
                if user.referee_core_db_id == referee_id:
                    user.get_acceptance_approved(self.id)

            for request_message in request_messages:
                if request_message.request_id == self.id:
                    try:
                        bot.delete_message(request_message.user_id, request_message.message_id)
                    except:
                        pass

        def get_declined(self, referee_id):
            
            for user in users:
                if user.referee_core_db_id == referee_id:
                    user.get_acceptance_declined(self.id)

            for request_message in request_messages:
                if request_message.request_id == self.id:
                    try:
                        bot.delete_message(request_message.user_id, request_message.message_id)
                    except:
                        pass

        def get_withdrawn(self, by):

            for user in users:
                
                if int(user.staff_core_db_id) == int(self.made_by):
                    if by == "s":
                        user.withdraw_acceptance_of_request_as_staff()
                    elif by == "r":
                        user.receive_withdrawal_of_acceptance_by_the_referee(self.match_id)

                if int(user.referee_core_db_id) == int(self.referee_id):
                    if by == "s":
                        user.receive_withdrawal_of_acceptance_by_the_staff(self.match_id)
                    elif by == "r":
                        user.withdrew_acceptance_of_request_as_referee()

            self.status = 1

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute(f"UPDATE goukv_ukv.referee_bot_requests SET status = 1 WHERE id = {self.id}")
            cur.execute(f"UPDATE goukv_ukv.referee_bot_requests SET referee_id = 0 WHERE id = {self.id}")

            for request_message in request_messages:
                if request_message.request_id == self.id: # TODO maybe ignore former referee?
                    try:
                        bot.delete_message(request_message.user_id, request_message.message_id)
                    except:
                        pass

    class IRequestMessage:

        @classmethod
        def get_all(cls):

            db_connector.reconnect()
            cur = db_connector.cursor()
            cur.execute("SELECT * FROM goukv_ukv.referee_bot_request_messages")

            request_messages = []

            for request_message in cur.fetchall():
                request_messages.append(IRequestMessage({
                    "id": request_message[0],
                    "request_id": request_message[1],
                    "user_id": request_message[2],
                    "message_id": request_message[3],
                    "decision": request_message[4],
                    "type": request_message[5]
                }))
            
            return request_messages

        def __init__(self, init_values) -> None:
            
            for key, value in init_values.items():
                setattr(self, key, value)

    db_connector = get_db_connector()

    users = IUser.get_all()
    relationships = IRelationship.get_all()
    requests = IRequest.get_all()
    request_messages = IRequestMessage.get_all()

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

                user._receive_button_press_from_user_(callback_data.data, callback_data.message.id)

    def run_bot():
        while True:
            bot.infinity_polling()
    
    def run_schedulers():
        
        while True:
            time.sleep(20)
            for request in requests:
                if request.status != 0 and request.status != 3 and request.status != "0" and request.status != "3":
                    request.get_sent()

    t1 = threading.Thread(target=run_bot)
    t2 = threading.Thread(target=run_schedulers)

    t1.start()
    t2.start()