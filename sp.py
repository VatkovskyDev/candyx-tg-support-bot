import json
import logging
import time
import uuid
from datetime import datetime, timedelta
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
import g4f

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupportBot:
    VERSION = "0.0.2"
    CODE_NAME = "NOVA"

    MESSAGES = {
        "welcome": "😘 Добро пожаловать в бота тех.поддержки CandyxPE!\n\nВыберите действие:\n╰─> Официальное сообщество — информация о проекте.",
        "unknown": "▸ Команда не распознана.",
        "ai_on": "🤖 ИИ запущен! Задавайте вопросы.",
        "ai_off": "✱ ИИ отключен. Вернулись в меню.",
        "ask_question": "⦿ Задать вопрос агенту.\n\nОпишите ваш вопрос подробно.",
        "question_sent": "▸ Ваш вопрос отправлен! Токен: {token}\nСохраните токен для отслеживания.",
        "question_failed": "▸ Ошибка при отправке вопроса.",
        "report_staff": "⦿ Жалоба на персонал.\n\nОпишите ситуацию подробно.",
        "report_bug": "⦿ Сообщите о недочете техподдержке.",
        "cancel": "▸ Действие отменено.",
        "admin_denied": "╰─> Доступ ограничен.",
        "admin_panel": "▪️ Панель управления.",
        "manage_agents": "◾◾ Управление сотрудниками.",
        "ban_user": "⦯ Управление блокировками.\n\nОзнакомьтесь с правилами.",
        "broadcast": "◾ Введите текст объявления.",
        "add_agent": "▸ Укажите ID и роль: '123456789 agent/admin/manager'.",
        "remove_agent": "▸ Укажите ID для снятия роли.",
        "ban": "◾ Укажите ID и часы блокировки: '123456789 24'.",
        "unban": "✱ Укажите ID для разблокировки.",
        "no_input": "▸ Вы не ввели данные.",
        "report_staff_sent": "▸ Жалоба отправлена.",
        "report_bug_sent": "▸ Недочет зафиксирован. Спасибо!",
        "report_staff_failed": "▸ Ошибка при отправке жалобы.",
        "report_bug_failed": "▸ Ошибка при отправке недочета.",
        "broadcast_sent": "⦯ Объявление отправлено!",
        "broadcast_failed": "▸ Ошибка отправки объявления.",
        "self_agent": "◾ Нельзя назначить себя.",
        "already_agent": "╰─> @{agent_id} уже сотрудник.",
        "agent_added": "╰─> {role} @{agent_id} назначен.",
        "self_remove": "▸ Нельзя снять роль с себя.",
        "agent_removed": "╰─> @{agent_id} снят с роли {role}.",
        "not_agent": "⦯ @{agent_id} не сотрудник.",
        "invalid_format": "▸ Формат: {text}. Пример: '{example}'.",
        "invalid_id": "▸ Укажите корректный ID.",
        "self_ban": "╰─> Нельзя заблокировать себя.",
        "agent_ban": "╰─> Нельзя заблокировать сотрудника.",
        "banned": "▸ БЛОКИРОВКА:\n╰─> @{target_id}\n╰─> Срок: {hours} ч.",
        "banned_notify": "▸ БЛОКИРОВКА:\n╰─> Причина: нарушение.\n╰─> Срок: {hours} ч.\nОбратитесь к СЕО или СОО.",
        "unbanned": "◾ @{target_id} разблокирован.",
        "unbanned_notify": "▸ БЛОКИРОВКА ОТМЕНЕНА:\n╰─> Причина: решение руководства.",
        "not_banned": "▸ @{target_id} не заблокирован.",
        "banned_user": "▸ Вы заблокированы.",
        "chat_unavailable": "⦯ Чат недоступен! Обратитесь к СОО.",
        "error": "◾ Ошибка! Попробуйте позже.",
        "get_agents": "▸ Сотрудники:\n{agents_list}",
        "version": "⦯ Версия: {version} ({code_name})",
        "stats": "▸ Статистика:\nПользователей: {users}\nСессий: {sessions}\nБлокировок: {bans}",
        "message_too_long": "◾ Сообщение слишком длинное (макс. 4096).",
        "permission_denied": "◾ Разрешите сообщения от бота.",
        "token_success": "▸ Авторизация успешна! Вы назначены {role}.",
        "token_invalid": "▸ Неверный токен. Обратитесь к администрации.",
        "token_already_used": "▸ Токен уже использован.",
        "response_menu": "▸ Выберите действие для ответа.",
        "no_pending_questions": "▸ Нет открытых вопросов.",
        "select_question": "▸ Выберите вопрос для ответа:",
        "enter_response": "▸ Введите ответ для вопроса с токеном {token}:\nВопрос: {question}",
        "response_sent": "▸ Ответ отправлен пользователю @{user_id}."
    }

    PREFIXES = {
        "staff": "📝 НАРУШЕНИЕ ПЕРСОНАЛА",
        "bug": "⚠️ ТЕХНИЧЕСКАЯ ОШИБКА",
        "question": "✉️ ВОПРОС ПОЛЬЗОВАТЕЛЯ",
        "broadcast": "📢 ОБЩЕЕ ОБЪЯВЛЕНИЕ",
        "ban": "🔒 НАЛОЖЕНИЕ БЛОКИРОВКИ",
        "unban": "🔓 РАЗБЛОКИРОВКА ДОСТУПА",
        "add_agent": "👥 ДОБАВЛЕНИЕ СОТРУДНИКА",
        "remove_agent": "🗑 УДАЛЕНИЕ СОТРУДНИКА"
    }

    def __init__(self, token, admin_chat):
        self.token = token
        self.admin_chat = admin_chat
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.rules = self.load_file('candyxpe_rules.txt', "Правила отсутствуют.", text=True)
        self.agents = self.load_file('candyxpe_agents.json', {"7583895254": {"role": "manager"}})
        self.tokens = self.load_file('tokens.json', {})
        self.banned = {}
        self.ai_users = set()
        self.actions = {}
        self.contexts = {}
        self.stats = {"users": set(), "messages": 0}
        self.spam = {}
        self.pending_questions = {}
        self.prompt = (
            "Ты - ИИ-ассистент техподдержки CandyxPE. Отвечай на русском по темам проекта: техвопросы, геймплей, баги, поддержка. Используй правила:\n{rules}\n\n"
            "Тон: вежливый, профессиональный. Ссылайся на пункты правил, если запрошены. Если пункт не найден, предложи уточнить. "
            "Не давай код или информацию вне CandyxPE. Если запрос неясен, ответь: 'Уточните детали или задайте вопрос агенту.'\n"
            "Примеры:\n- Баг: 'Опишите проблему, укажите ID.'\n- Правила: 'Пункт 3.1: [цитата].'"
        )
        self.setup_handlers()

    def load_file(self, path, default, text=False):
        if not os.path.exists(path):
            self.save_file(path, default)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip() if text else json.load(f)

    def save_file(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)

    async def send_message(self, user, key, keyboard=None, info=None):
        try:
            msg = self.MESSAGES.get(key, key) or "Ошибка: сообщение не найдено"
            if info:
                msg = msg.format(**info)
            await self.bot.send_message(
                chat_id=user,
                text=msg,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"Message sent to user {user}: {msg[:50]}")
        except Exception as e:
            logger.error(f"Error sending message to user {user}: {e}")
            await self.bot.send_message(
                chat_id=user,
                text=self.MESSAGES["error"],
                reply_markup=self.get_keyboard("main", user)
            )

    def get_keyboard(self, mode, user=None):
        keyboards = {
            "main": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🤖️ ПОДДЕРЖКА ИНТЕЛЛЕКТА"), KeyboardButton(text="❓ Задать ВОПРОС")],
                    [KeyboardButton(text="📝 ЖАЛОБА НА ПЕРСОНАЛ"), KeyboardButton(text="⚠️ ВОЗНИКЛА НЕПОЛАДКА")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            "ai": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔄 ЗАВЕРШИТЬ ПОДДЕРЖКУ")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            "action": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔄 АННУЛИРОВАТЬ ОПЕРАЦИЮ")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            "admin": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🧑‍🏫 УПРАВЛЕНИЕ ШТАТОМ"), KeyboardButton(text="⛏ БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ")],
                    [KeyboardButton(text="📢 МАССОВОЕ ОПОВЕЩЕНИЕ"), KeyboardButton(text="🔄 ВЕРНУТЬСЯ НАЗАД")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            "manage_agents": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="👥 ДОБАВЛЕНИЕ СОТРУДНИКА"), KeyboardButton(text="🗑 УДАЛЕНИЕ СОТРУДНИКА")],
                    [KeyboardButton(text="🔄 ВЕРНУТЬСЯ НАЗАД")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            "ban_user": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔒 ЗАБЛОКИРОВАТЬ ДОСТУП"), KeyboardButton(text="🔓 РАЗБЛОКИРОВКА ДОСТУПА")],
                    [KeyboardButton(text="🔄 ВЕРНУТЬСЯ НАЗАД")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            ),
            "response": ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📬 ОТВЕТИТЬ ПОЛЬЗОВАТЕЛЮ"), KeyboardButton(text="📋 СПИСОК ВОПРОСОВ")],
                    [KeyboardButton(text="🔄 ВЕРНУТЬСЯ В МЕНЮ")]
                ],
                resize_keyboard=True,
                one_time_keyboard=False
            )
        }
        keyboard = keyboards.get(mode, keyboards["main"])
        if user and mode == "main" and str(user) in self.agents:
            keyboard.keyboard.insert(0, [KeyboardButton(text="🛠 ПАНЕЛЬ УПРАВЛЕНИЯ")])
            keyboard.keyboard.insert(1, [KeyboardButton(text="📬 МЕНЮ ОТВЕТОВ")])
        return keyboard

    async def get_question_keyboard(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for token, data in self.pending_questions.items():
            button_text = f"Вопрос (Токен: {token[:8]}...)"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=f"answer_{token}")
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔄 ВЕРНУТЬСЯ", callback_data="back_to_response")
        ])
        return keyboard

    async def send_admin(self, user, message, action, token=None):
        prefix = self.PREFIXES.get(action, "◾ СООБЩЕНИЕ")
        try:
            user_info = await self.bot.get_chat(user)
            info = f"\n👤 @{user_info.username or user_info.id}\n◾ ID: {user}\n╰─> Рассмотрите обращение."
        except Exception:
            info = f"\n👤 @{user}\n◾ ID: {user}\n╰─> Рассмотрите обращение."
        if token:
            info += f"\n◾ Токен: {token}"
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat,
                text=f"{prefix}{info}\n\n{message}",
                parse_mode="HTML"
            )
            logger.info(f"Notification sent to admin chat {self.admin_chat} (type: {action}): {message[:50]}")
            for agent_id in self.agents:
                if int(agent_id) in self.stats["users"]:
                    try:
                        await self.bot.send_message(
                            chat_id=int(agent_id),
                            text=f"{prefix}{info}\n\n{message}",
                            parse_mode="HTML",
                            reply_markup=await self.get_question_keyboard()
                        )
                        logger.info(f"Notification sent to agent {agent_id} (type: {action}): {message[:50]}")
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Error sending notification to agent {agent_id}: {e}")
            if action == "question":
                self.pending_questions[token] = {
                    "user_id": user,
                    "message": message,
                    "timestamp": datetime.now()
                }
            return True
        except Exception as e:
            logger.error(f"Error sending to admin chat {self.admin_chat}: {e}")
            await self.send_message(user, "chat_unavailable")
            return False

    def get_ai_response(self, user, message):
        if user not in self.contexts:
            self.contexts[user] = []
        self.contexts[user].append({"role": "user", "content": message})
        self.contexts[user] = self.contexts[user][-5:]
        prompt = self.prompt.format(rules=self.rules)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"Правила CandyxPE:\n{self.rules}"}
        ] + self.contexts[user]
        try:
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                timeout=10
            )
            if isinstance(response, str) and response.strip():
                cleaned_response = response.replace('*', '')
                self.contexts[user].append({"role": "assistant", "content": cleaned_response})
                return cleaned_response[:4090] + "..." if len(cleaned_response) > 4096 else cleaned_response
            logger.error("AI error: empty or invalid response")
            return self.MESSAGES["error"]
        except Exception as e:
            logger.error(f"AI error: {e}")
            return self.MESSAGES["error"]

    async def process_command(self, user, cmd, message):
        async def execute_command(action, success_message, keyboard_mode, condition=True):
            if condition:
                if action:
                    await action()
                if success_message:
                    await self.send_message(user, success_message, self.get_keyboard(keyboard_mode, user))
            else:
                await self.send_message(user, "admin_denied", self.get_keyboard("admin", user))

        commands = {
            "ai_agent": lambda: execute_command(lambda: self.async_action(lambda: self.ai_users.add(user)), "ai_on", "ai", True),
            "ask_question": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "question"})), "ask_question", "action", True),
            "report_staff": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "staff"})), "report_staff", "action", True),
            "report_bug": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "bug"})), "report_bug", "action", True),
            "end_ai": lambda: execute_command(lambda: self.async_action(lambda: (self.ai_users.discard(user), self.actions.pop(user, None), self.contexts.pop(user, None))), "ai_off", "main", True),
            "cancel": lambda: execute_command(lambda: self.async_action(lambda: (self.actions.pop(user, None), self.ai_users.discard(user))), "cancel", "main", True),
            "admin_panel": lambda: execute_command(None, "admin_panel", "admin", str(user) in self.agents),
            "manage_agents": lambda: execute_command(None, "manage_agents", "manage_agents", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "ban_user": lambda: execute_command(None, "ban_user", "ban_user", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "broadcast": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "broadcast"})), "broadcast", "action", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "add_agent": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "add_agent"})), "add_agent", "action", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "remove_agent": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "remove_agent"})), "remove_agent", "action", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "ban": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "ban"})), "ban", "action", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "unban": lambda: execute_command(lambda: self.async_action(lambda: self.actions.update({user: "unban"})), "unban", "action", str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]),
            "getagents": lambda: execute_command(None, "get_agents", "manage_agents", str(user) in self.agents and self.agents[str(user)].get("role") == "manager"),
            "stats": lambda: execute_command(None, "stats", "admin", str(user) in self.agents),
            "version": lambda: execute_command(None, "version", "main", True),
            "response_menu": lambda: execute_command(None, "response_menu", "response", str(user) in self.agents),
            "list_questions": lambda: execute_command(lambda: self.list_pending_questions(user), None, "response", str(user) in self.agents),
            "answer_user": lambda: execute_command(lambda: self.show_questions_for_response(user), None, "response", str(user) in self.agents)
        }

        if cmd == "token":
            await self.handle_token(user, message.text)
        else:
            await commands.get(cmd, lambda: self.send_message(user, "unknown", self.get_keyboard("main", user)))()

    async def handle_token(self, user, text):
        try:
            _, token = text.split(maxsplit=1)
            if token in self.tokens:
                if self.tokens[token].get("used"):
                    await self.send_message(user, "token_already_used", self.get_keyboard("main", user))
                else:
                    role = self.tokens[token]["role"]
                    self.agents[str(user)] = {"role": role}
                    self.tokens[token]["used"] = True
                    self.tokens[token]["user_id"] = user
                    self.save_file('candyxpe_agents.json', self.agents)
                    self.save_file('tokens.json', self.tokens)
                    await self.send_message(user, "token_success", self.get_keyboard("main", user), {"role": role.capitalize()})
                    logger.info(f"User {user} authorized as {role} with token {token}")
            else:
                await self.send_message(user, "token_invalid", self.get_keyboard("main", user))
        except ValueError:
            await self.send_message(user, "invalid_format", self.get_keyboard("main", user), {"text": "/token <токен>", "example": "/token abc123"})

    async def list_pending_questions(self, user_id):
        if not self.pending_questions:
            await self.send_message(user_id, "no_pending_questions", self.get_keyboard("response", user_id))
            return
        questions_list = "\n".join(
            [f"◾ Токен: {token[:8]}... | ID: {data['user_id']} | Вопрос: {data['message'][:50]}... | Время: {data['timestamp'].strftime('%H:%M:%S')}" 
             for token, data in self.pending_questions.items()]
        )
        await self.send_message(user_id, f"▸ Открытые вопросы:\n{questions_list}", self.get_keyboard("response", user_id))

    async def show_questions_for_response(self, user_id):
        if not self.pending_questions:
            await self.send_message(user_id, "no_pending_questions", self.get_keyboard("response", user_id))
            return
        await self.send_message(user_id, "select_question", await self.get_question_keyboard())

    async def async_action(self, action):
        await asyncio.sleep(0)
        action()

    async def process_action(self, user, action, text):
        if action in ["staff", "bug"]:
            success = await self.send_admin(user, text, action)
            await self.send_message(user, f"report_{action}_sent" if success else f"report_{action}_failed", self.get_keyboard("main", user))
            self.actions.pop(user, None)
        elif action == "question":
            token = str(uuid.uuid4())
            success = await self.send_admin(user, text, "question", token)
            await self.send_message(user, "question_sent" if success else "question_failed", self.get_keyboard("main", user), {"token": token})
            self.actions.pop(user, None)
        elif action == "broadcast":
            if str(user) in self.agents and self.agents[str(user)].get("role") in ["admin", "manager"]:
                if len(text) > 4096:
                    await self.send_message(user, "message_too_long", self.get_keyboard("admin", user))
                else:
                    sent_count = 0
                    for uid in self.stats["users"]:
                        if int(uid) not in self.banned:
                            await self.send_message(int(uid), f"📢 ОПОВЕЩЕНИЕ:\n{text}", self.get_keyboard("main", int(uid)))
                            sent_count += 1
                    await self.send_admin(user, f"📢 Объявление отправлено {sent_count} пользователям.", "broadcast")
                    await self.send_message(user, "broadcast_sent", self.get_keyboard("admin", user))
            self.actions.pop(user, None)
        elif action == "add_agent":
            try:
                agent_id, role = text.split()
                if role not in ["agent", "admin", "manager"]:
                    raise ValueError
                agent_id = int(agent_id)
                if agent_id == user:
                    await self.send_message(user, "self_agent", self.get_keyboard("manage_agents", user))
                elif str(agent_id) in self.agents:
                    await self.send_message(user, "already_agent", self.get_keyboard("manage_agents", user), {"agent_id": agent_id})
                else:
                    self.agents[str(agent_id)] = {"role": role}
                    self.save_file('candyxpe_agents.json', self.agents)
                    await self.send_message(user, "agent_added", self.get_keyboard("admin", user), {"role": role.capitalize(), "agent_id": agent_id})
                    await self.send_admin(user, f"{role.capitalize()} @{agent_id} назначен.", "add_agent")
            except ValueError:
                await self.send_message(user, "invalid_format", self.get_keyboard("action", user), {"text": "<ID> <agent/admin/manager>", "example": "123456 agent"})
            self.actions.pop(user, None)
        elif action == "remove_agent":
            try:
                agent_id = int(text)
                if agent_id == user:
                    await self.send_message(user, "self_remove", self.get_keyboard("manage_agents", user))
                elif str(agent_id) in self.agents:
                    role = self.agents[str(agent_id)]["role"]
                    del self.agents[str(agent_id)]
                    self.save_file('candyxpe_agents.json', self.agents)
                    await self.send_message(user, "agent_removed", self.get_keyboard("admin", user), {"role": role.capitalize(), "agent_id": agent_id})
                    await self.send_admin(user, f"{role.capitalize()} @{agent_id} снят.", "remove_agent")
                else:
                    await self.send_message(user, "not_agent", self.get_keyboard("manage_agents", user), {"agent_id": agent_id})
            except ValueError:
                await self.send_message(user, "invalid_id", self.get_keyboard("action", user))
            self.actions.pop(user, None)
        elif action == "ban":
            try:
                target_id, hours = map(int, text.split())
                if target_id == user:
                    await self.send_message(user, "self_ban", self.get_keyboard("ban_user", user))
                elif str(target_id) in self.agents:
                    await self.send_message(user, "agent_ban", self.get_keyboard("ban_user", user))
                else:
                    self.banned[target_id] = datetime.now() + timedelta(hours=hours)
                    await self.send_message(user, "banned", self.get_keyboard("ban_user", user), {"target_id": target_id, "hours": hours})
                    await self.send_message(target_id, "banned_notify", self.get_keyboard("main", target_id), {"hours": hours})
                    await self.send_admin(user, f"@{target_id} забанен на {hours} часов.", "ban")
            except ValueError:
                await self.send_message(user, "invalid_format", self.get_keyboard("action", user), {"text": "<ID> <hours>", "example": "123456 24"})
            self.actions.pop(user, None)
        elif action == "unban":
            try:
                target_id = int(text)
                if target_id in self.banned:
                    del self.banned[target_id]
                    await self.send_message(user, "unbanned", self.get_keyboard("ban_user", user), {"target_id": target_id})
                    await self.send_message(target_id, "unbanned_notify", self.get_keyboard("main", target_id))
                    await self.send_admin(user, f"@{target_id} разбанен.", "unban")
                else:
                    await self.send_message(user, "not_banned", self.get_keyboard("ban_user", user), {"target_id": target_id})
            except ValueError:
                await self.send_message(user, "invalid_id", self.get_keyboard("action", user))
            self.actions.pop(user, None)
        elif action == "answer_user":
            if str(user) in self.agents:
                token = self.actions[user].get("current_token")
                if token and token in self.pending_questions:
                    target_id = self.pending_questions[token]["user_id"]
                    await self.send_message(target_id, f"📢 Ответ на ваш вопрос (Токен: {token}):\n{text}", self.get_keyboard("main", target_id))
                    await self.send_message(user, "response_sent", self.get_keyboard("response", user), {"user_id": target_id})
                    del self.pending_questions[token]
                    logger.info(f"Agent {user} responded to user {target_id} (token: {token}): {text[:50]}")
                else:
                    await self.send_message(user, "invalid_id", self.get_keyboard("response", user))
            self.actions.pop(user, None)

    def check_spam(self, user):
        now = time.time()
        self.spam[user] = [t for t in self.spam.get(user, []) if now - t < 60]
        if len(self.spam[user]) >= 25:
            logger.warning(f"User {user} exceeded message limit (spam)")
            return False
        self.spam[user].append(now)
        return True

    def setup_handlers(self):
        @self.dp.message(CommandStart())
        async def start_command(message: types.Message):
            await self.send_message(message.from_user.id, "welcome", self.get_keyboard("main", message.from_user.id))

        @self.dp.callback_query()
        async def handle_callback(callback: types.CallbackQuery):
            user_id = callback.from_user.id
            if not str(user_id) in self.agents:
                await callback.answer("Доступ запрещен")
                return
            if callback.data.startswith("answer_"):
                token = callback.data.split("_")[1]
                if token in self.pending_questions:
                    self.actions[user_id] = {"action": "answer_user", "current_token": token}
                    question = self.pending_questions[token]["message"]
                    await self.send_message(user_id, "enter_response", self.get_keyboard("action", user_id), {"token": token, "question": question})
                else:
                    await self.send_message(user_id, "no_pending_questions", self.get_keyboard("response", user_id))
            elif callback.data == "back_to_response":
                await self.send_message(user_id, "response_menu", self.get_keyboard("response", user_id))
            await callback.answer()

        @self.dp.message()
        async def handle_message(message: types.Message):
            user = message.from_user.id
            text = message.text.strip() if message.text else ""
            logger.debug(f"Processing message from {user}, text: {text}")
            self.banned = {uid: expiry for uid, expiry in self.banned.items() if datetime.now() <= expiry}
            if user in self.banned:
                await self.send_message(user, "banned_user", self.get_keyboard("main", user))
                return
            if not self.check_spam(user):
                await self.send_message(user, "error", self.get_keyboard("main", user))
                return
            self.stats["users"].add(user)
            self.stats["messages"] += 1

            button_commands = {
                "🤖️ ПОДДЕРЖКА ИНТЕЛЛЕКТА": "ai_agent",
                "❓ Задать ВОПРОС": "ask_question",
                "📝 ЖАЛОБА НА ПЕРСОНАЛ": "report_staff",
                "⚠️ ВОЗНИКЛА НЕПОЛАДКА": "report_bug",
                "🔄 ЗАВЕРШИТЬ ПОДДЕРЖКУ": "end_ai",
                "🔄 АННУЛИРОВАТЬ ОПЕРАЦИЮ": "cancel",
                "🛠 ПАНЕЛЬ УПРАВЛЕНИЯ": "admin_panel",
                "🧑‍🏫 УПРАВЛЕНИЕ ШТАТОМ": "manage_agents",
                "⛏ БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ": "ban_user",
                "📢 МАССОВОЕ ОПОВЕЩЕНИЕ": "broadcast",
                "👥 ДОБАВЛЕНИЕ СОТРУДНИКА": "add_agent",
                "🗑 УДАЛЕНИЕ СОТРУДНИКА": "remove_agent",
                "🔒 ЗАБЛОКИРОВАТЬ ДОСТУП": "ban",
                "🔓 РАЗБЛОКИРОВКА ДОСТУПА": "unban",
                "📬 МЕНЮ ОТВЕТОВ": "response_menu",
                "📬 ОТВЕТИТЬ ПОЛЬЗОВАТЕЛЮ": "answer_user",
                "📋 СПИСОК ВОПРОСОВ": "list_questions",
                "🔄 ВЕРНУТЬСЯ В МЕНЮ": "cancel"
            }

            if text.startswith("/"):
                await self.process_command(user, text[1:].split()[0], message)
                return
            if text in button_commands:
                await self.process_command(user, button_commands[text], message)
                return
            if not text:
                await self.send_message(user, "no_input", self.get_keyboard("main", user))
                return
            if user in self.actions:
                await self.process_action(user, self.actions[user]["action"] if isinstance(self.actions[user], dict) else self.actions[user], text)
                return
            if user in self.ai_users:
                if text.lower() in {"выйти", "выход", "стоп"}:
                    await self.process_command(user, "end_ai", message)
                else:
                    response = self.get_ai_response(user, text)
                    await self.send_message(user, response, self.get_keyboard("ai", user))
                return
            if text.lower() in {"начать", "привет", "продвет"}:
                await self.send_message(user, "welcome", self.get_keyboard("main", user))
            else:
                await self.send_message(user, "unknown", self.get_keyboard("main", user))

    async def run(self):
        print(f"\n🚖 CandyxPE v{self.VERSION} {self.CODE_NAME}\n{'-' * 40}")
        print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Техподдержка CandyxPE by vatkovskydev под руководством dsuslov67\n{'-' * 40}\n")
        logger.info("Bot started")
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    TELEGRAM_TOKEN = "7738965237:AAGIkAz01LRaTtPII8LPxyUoYD0ucy5IgB4"
    ADMIN_CHAT_ID = -1002739303737
    bot = SupportBot(TELEGRAM_TOKEN, ADMIN_CHAT_ID)
    asyncio.run(bot.run())
