import json
import logging
import sys
import time
from datetime import datetime, timedelta
import os
import g4f
import asyncio
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

VERSION = "0.0.1-BASED"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s - User: %(user_id)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class BotCore:
    _MESSAGES = {
        "welcome": "🎮 Добро пожаловать в техподдержку CandyxPE!\nВыберите опцию:",
        "unknown": "⚠️ Неверная команда.",
        "ai_on": "🧠 ИИ-ассистент готов! Задавайте вопросы.",
        "human_on": "👨‍💻 Агент подключён. Опишите проблему.",
        "human_off": "🔙 Вы вернулись к боту.",
        "report_staff": "🚨 Жалоба на сотрудника\nПодробно опишите ситуацию:",
        "report_bug": "🛠 Сообщение о баге\nОпишите проблему:",
        "ai_off": "🔙 ИИ-ассистент отключён.",
        "cancel": "✅ Операция отменена.",
        "admin_denied": "🔒 Доступ запрещён.",
        "admin_panel": "⚙️ Панель управления\nВыберите опцию:",
        "manage_agents": "👥 Управление агентами\nВыберите действие:",
        "ban_user": "🚫 Управление блокировками\nВыберите действие:",
        "broadcast": "📣 Введите текст объявления:",
        "add_agent": "➕ Введите ID и роль (agent/admin/manager, например, '123456 agent'):",
        "remove_agent": "➖ Введите ID для удаления роли:",
        "ban": "🚫 Введите ID и часы блокировки (например, '123456 24'):",
        "unban": "✅ Введите ID для разблокировки:",
        "no_input": "⚠️ Введите данные.",
        "report_staff_sent": "✅ Жалоба отправлена.",
        "report_bug_sent": "✅ Баг отправлен.",
        "report_staff_failed": "⚠️ Ошибка отправки жалобы.",
        "report_bug_failed": "⚠️ Ошибка отправки бага.",
        "broadcast_sent": "✅ Объявление разослано.",
        "broadcast_failed": "⚠️ Ошибка рассылки объявления.",
        "self_agent": "⚠️ Нельзя назначить себя.",
        "already_agent": "⚠️ id{agent_id} уже агент.",
        "agent_added": "✅ {role} id{agent_id} назначен.",
        "self_remove": "⚠️ Нельзя удалить себя.",
        "agent_removed": "✅ {role} id{agent_id} удалён.",
        "not_agent": "⚠️ id{agent_id} не агент.",
        "invalid_format": "⚠️ Формат: {text}. Пример: '{example}'.",
        "invalid_id": "⚠️ Введите корректный ID.",
        "self_ban": "⚠️ Нельзя заблокировать себя.",
        "agent_ban": "⚠️ Нельзя заблокировать агента.",
        "banned": "🚫 id{target_id} заблокирован на {hours} часов.",
        "banned_notify": "🚫 Вы заблокированы на {hours} часов.",
        "unbanned": "✅ id{target_id} разблокирован.",
        "unbanned_notify": "✅ Вы разблокированы.",
        "not_banned": "⚠️ id{target_id} не заблокирован.",
        "banned_user": "🚫 Вы заблокированы. Попробуйте позже.",
        "chat_unavailable": "⚠️ Админ-чат недоступен.",
        "error": "⚠️ Ошибка. Попробуйте снова.",
        "get_agents": "📋 Агенты:\n{agents_list}",
        "stats": "📈 Статистика:\nПользователи: {users}\nСессии: {sessions}\nБлокировки: {bans}",
        "message_too_long": "⚠️ Сообщение слишком длинное (макс. 4096 символов).",
        "permission_denied": "⚠️ Разрешите сообщения от бота."
    }

    _PREFIXES = {
        "staff": "🚨 ЖАЛОБА НА СОТРУДНИКА",
        "bug": "🛠 БАГ",
        "agent": "✅ ПОДКЛЮЧЕНИЕ К АГЕНТУ",
        "broadcast": "📣 ОБЪЯВЛЕНИЕ",
        "ban": "🚫 БЛОКИРОВКА",
        "unban": "✅ РАЗБЛОКИРОВКА",
        "add_agent": "➕ НОВЫЙ АГЕНТ",
        "remove_agent": "➖ УДАЛЕНИЕ АГENTA"
    }

    def __init__(self, admin_chat_id):
        self.admin_chat_id = admin_chat_id
        self.rules = self._load_file('candyxpe_rules.txt', "Правила отсутствуют.", text=True)
        self.user_contexts = defaultdict(list)
        self.user_ai_mode = set()
        self.user_action_mode = {}
        self.user_human_mode = set()
        self.banned_users = {}
        self.agents = self._load_file('candyxpe_agents.json', {})
        self.stats = {"messages_processed": 0, "users": set()}
        self.spam_protection = defaultdict(list)
        self.system_prompt = (
            "Ты - ИИ-ассистент техподдержки CandyxPE. Отвечай на русском, только по темам CandyxPE: тех. вопросы, геймплей, баги, поддержка. Используй правила:\n{rules}\n"
            "Тон: вежливый, профессиональный, краткий. Ссылайся на пункты правил при запросе (например, 3.1). Если пункт не найден, укажи это. "
            "Не давай код, инструкции по взлому или оффтоп. Если запрос неясен, ответь: 'Уточните детали или обратитесь к агенту.'\n"
            "Примеры:\n- Баг: 'Опишите проблему, укажите ID.'\n- Правила: 'Пункт 3.1: [цитата].'"
        )

    def _load_file(self, path, default, text=False):
        if not os.path.exists(path):
            self._save_file(path, default)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip() if text else json.load(f)
                if text and not content:
                    return default
                if text and len(content) > 100000:
                    return content[:1000] + "..."
                return content
        except Exception as e:
            return default

    def _save_file(self, path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if isinstance(data, str):
                    f.write(data)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    async def _handle_error(self, user_id, error, context):
        await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))

    def is_agent(self, user_id):
        return str(user_id) in self.agents

    def is_admin(self, user_id):
        return self.is_agent(user_id) and self.agents.get(str(user_id), {}).get("role") in ["admin", "manager"]

    def clean_message(self, message):
        return message.replace('{}', '').replace('{{', '').replace('}}', '').strip()[:4096]

    async def _get_keyboard(self, mode, user_id=None):
        keyboards = {
            "main": [
                [InlineKeyboardButton("🧠 ИИ-Ассистент", callback_data="ai_agent")],
                [InlineKeyboardButton("👨‍💻 Связь с агентом", callback_data="contact_agent")],
                [InlineKeyboardButton("🚨 Жалоба на персонал", callback_data="report_staff")],
                [InlineKeyboardButton("🛠 Сообщение о баге", callback_data="report_bug")]
            ],
            "ai": [[InlineKeyboardButton("🔙 Выход", callback_data="end_ai")]],
            "human": [[InlineKeyboardButton("🔙 Выход", callback_data="end_human")]],
            "action": [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]],
            "admin": [
                [InlineKeyboardButton("👥 Агенты", callback_data="manage_agents")],
                [InlineKeyboardButton("🚫 Блокировки", callback_data="ban_user")],
                [InlineKeyboardButton("📣 Объявление", callback_data="broadcast")],
                [InlineKeyboardButton("📈 Статистика", callback_data="stats")],
                [InlineKeyboardButton("🔙 Выход", callback_data="cancel")]
            ],
            "manage_agents": [
                [InlineKeyboardButton("➕ Добавить", callback_data="add_agent")],
                [InlineKeyboardButton("➖ Удалить", callback_data="remove_agent")],
                [InlineKeyboardButton("📋 Список", callback_data="getagents")],
                [InlineKeyboardButton("🔙 Выход", callback_data="cancel")]
            ],
            "ban_user": [
                [InlineKeyboardButton("🚫 Заблокировать", callback_data="ban")],
                [InlineKeyboardButton("✅ Разблокировать", callback_data="unban")],
                [InlineKeyboardButton("🔙 Выход", callback_data="cancel")]
            ]
        }
        buttons = keyboards.get(mode, keyboards["main"])
        if user_id and mode == "main" and self.is_admin(user_id):
            buttons.insert(0, [InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])
        return InlineKeyboardMarkup(buttons)

    async def _send_to_admin(self, platform, user_id, message, action, attachments=None):
        if platform != "telegram":
            return False
        for attempt in range(3):
            try:
                prefix = self._PREFIXES.get(action, "✅ СООБЩЕНИЕ")
                msg = f"{prefix}{await self._get_user_info(user_id)}\n\n{self.clean_message(message)}"
                if attachments:
                    for att in attachments.split(','):
                        await self.app.bot.send_message(chat_id=self.admin_chat_id, text=msg)
                        await self.app.bot.send_document(chat_id=self.admin_chat_id, document=att)
                else:
                    await self.app.bot.send_message(chat_id=self.admin_chat_id, text=msg)
                return True
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    return False

    async def _send_broadcast(self, user_id, message):
        if not self.is_admin(user_id):
            return False
        sent_count = 0
        async for uid in self._async_iter_agents():
            if int(uid) not in self.banned_users:
                try:
                    await self._send_message(int(uid), f"📣 CandyxPE:\n{self.clean_message(message)}", await self._get_keyboard("main", int(uid)))
                    sent_count += 1
                except Exception:
                    pass
        await self._send_to_admin("telegram", user_id, f"Объявление отправлено {sent_count} пользователям.", "broadcast")
        return True

    async def _async_iter_agents(self):
        for uid in self.agents:
            yield uid

    async def _send_message(self, user_id, message_key, keyboard=None, info=None):
        if not isinstance(user_id, int):
            return
        msg = self._MESSAGES.get(message_key, message_key)
        if info:
            try:
                msg = msg.format(**info)
            except KeyError:
                msg = message_key
        cleaned_message = self.clean_message(msg)
        try:
            if await self._check_user_permission(user_id):
                await self.app.bot.send_message(chat_id=user_id, text=cleaned_message, reply_markup=keyboard)
            else:
                await self.app.bot.send_message(chat_id=user_id, text=self._MESSAGES["permission_denied"])
        except Exception:
            await self.app.bot.send_message(chat_id=user_id, text=self._MESSAGES["permission_denied"])

    async def _check_user_permission(self, user_id):
        try:
            chat = await self.app.bot.get_chat(user_id)
            return chat.can_send_messages if hasattr(chat, 'can_send_messages') else True
        except Exception:
            return False

    async def _process_ai_response(self, user_id, response):
        await asyncio.sleep(1)
        processed_response = response.replace('*', '')
        if not processed_response:
            processed_response = "⚠️ Ошибка обработки ответа."
        await self._send_message(user_id, processed_response, await self._get_keyboard("ai", user_id))

    async def _get_ai_response(self, user_id, message):
        try:
            self.user_contexts[user_id].append({"role": "user", "content": message})
            self.user_contexts[user_id] = self.user_contexts[user_id][-5:]
            prompt = self.system_prompt.format(rules=self.rules)
            messages = [
                {"role": "system", "content": prompt},
                {"role": "system", "content": f"Правила CandyxPE:\n{self.rules}"}
            ] + self.user_contexts[user_id]
            response = await asyncio.to_thread(g4f.ChatCompletion.create,
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                timeout=10
            )
            if isinstance(response, str) and response.strip():
                cleaned_response = self.clean_message(response)
                self.user_contexts[user_id].append({"role": "assistant", "content": cleaned_response})
                return cleaned_response
            return "⚠️ Ошибка. Обратитесь к поддержке."
        except Exception:
            return "⚠️ Ошибка. Обратитесь к поддержке."

    async def _handle_report(self, user_id, action, text, attachments=None):
        success_key = f"report_{action}_sent"
        failure_key = f"report_{action}_failed"
        try:
            if await self._send_to_admin("telegram", user_id, text, action, attachments):
                await self._send_message(user_id, success_key, await self._get_keyboard("main", user_id))
            else:
                await self._send_message(user_id, failure_key, await self._get_keyboard("main", user_id))
        except Exception:
            await self._send_message(user_id, failure_key, await self._get_keyboard("main", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _handle_broadcast(self, user_id, message):
        try:
            if await self._send_broadcast(user_id, message):
                await self._send_message(user_id, "broadcast_sent", await self._get_keyboard("admin", user_id))
            else:
                await self._send_message(user_id, "broadcast_failed", await self._get_keyboard("admin", user_id))
        except Exception:
            await self._send_message(user_id, "broadcast_failed", await self._get_keyboard("admin", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _handle_add_agent(self, user_id, text):
        try:
            agent_id, role = map(str.strip, text.split(maxsplit=1))
            agent_id = int(agent_id)
            if role not in ["agent", "admin", "manager"]:
                raise ValueError
            if agent_id == user_id:
                await self._send_message(user_id, "self_agent", await self._get_keyboard("manage_agents", user_id))
            elif str(agent_id) in self.agents:
                await self._send_message(user_id, "already_agent", await self._get_keyboard("manage_agents", user_id), {"agent_id": agent_id})
            else:
                self.agents[str(agent_id)] = {"role": role}
                self._save_file('candyxpe_agents.json', self.agents)
                await self._send_message(user_id, "agent_added", await self._get_keyboard("admin", user_id), {"role": role.capitalize(), "agent_id": agent_id})
                await self._send_to_admin("telegram", user_id, f"{role.capitalize()} @id{agent_id} назначен.", "add_agent")
        except ValueError:
            await self._send_message(user_id, "invalid_format", await self._get_user_info("action", user_id), {"type": "<ID> <agent/admin/manager>", "example": "123456 agent"})
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _handle_remove_agent(self, user_id, text):
        try:
            agent_id = int(text.strip())
            if agent_id == user_id:
                await self._send_message(user_id, "self_remove", await self._get_keyboard("manage_agents", user_id))
            elif str(agent_id) in self.agents:
                role = self.agents[str(agent_id)]["role"]
                del self.agents[str(agent_id)]
                self._save_file('candyxpe_agents.json', self.agents)
                await self._send_message(user_id, "agent_removed", await self._get_keyboard("admin", user_id), {"role": role.capitalize(), "agent_id": agent_id})
                await self._send_to_admin("telegram", user_id, f"{role.capitalize()} @id{agent_id} удалён.", "remove")
            else:
                await self._send_message(user_id, "not_agent", await self._get_keyboard("manage_agents", user_id), {"agent_id": agent_id})
        except ValueError:
            await self._send_message(user_id, "invalid_id", await self._get_keyboard("action", user_id))
        except Exception as e:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _handle_get_agents(self, user_id):
        try:
            if not self.is_admin(user_id) or self.agents.get(str(user_id), []).get("role") != "manager":
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))
                return
            agents_list = "\n".join([f"@id{agent_id} - {role['role'].capitalize()}" for agent_id, role in self.agents.items()])
            await self.app.bot.send_message(user_id, "get agents", await self._get_keyboard("manage_users", user_id), extra={"agents_list": agents_list or "No agents."})
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))

    async def _handle_stats(self, user_id):
        try:
            if not self.is_admin(user_id):
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))
                return
            stats_info = {
                "users": len(self.stats["users"]),
                "sessions": len(self.user_ai_mode | self.user_human_mode),
                "bans": len(self.banned_users)
            }
            await self._send_message(user_id, "stats", await self._get_keyboard("admin", user_id), stats_info)

        except Exception as e:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))

    async def _handle_ban(self, user_id, text):
        try:
            target_id, hours = map(int, text.split())
            if target_id == user_id:
                await self._send_message(user_id, "self_ban", await self._get_keyboard("ban_user", user_id))
            elif self.is_agent(target_id):
                await self._send_message(user_id, "agent_ban", await self._get_keyboard("ban_user", user_id))
            else:
                self.banned_users[target_id] = datetime.now() + timedelta(hours=hours)
                await self._send_message(user_id, "banned", await self._get_keyboard("ban_user", user_id), {"target_id": target_id, "hours": hours})
                await self._send_message(target_id, "banned_notify", await self._get_keyboard("main", target_id), {"hours": hours})
                await self._send_to_admin("telegram", user_id, f"id{target_id} заблокирован на {hours} часов.", "ban")
        except ValueError:
            await self._send_message(user_id, "invalid_format", await self._get_keyboard("action", user_id), {"text": "<ID> <hours>", "example": "123456 24"})
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _handle_unban(self, user_id, text):
        try:
            target_id = int(text.strip())
            if target_id in self.banned_users:
                del self.banned_users[target_id]
                await self._send_message(user_id, "unbanned", await self._get_keyboard("ban_user", user_id), {"target_id": target_id})
                await self._send_message(target_id, "unbanned_notify", await self._get_keyboard("main", target_id))
                await self._send_to_admin("telegram", user_id, f"id{target_id} разблокирован.", "unban")
            else:
                await self._send_message(user_id, "not_banned", await self._get_keyboard("ban_user", user_id), {"target_id": target_id})
        except ValueError:
            await self._send_message(user_id, "invalid_id", await self._get_keyboard("action", user_id))
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _reset_user_state(self, user_id):
        self.user_action_mode.pop(user_id, None)
        self.user_ai_mode.discard(user_id)
        self.user_human_mode.discard(user_id)
        self.user_contexts.pop(user_id, None)

    async def _handle_command(self, user_id, cmd):
        async def ai_agent():
            self.user_ai_mode.add(user_id)
            self.user_human_mode.discard(user_id)
            await self._send_message(user_id, "ai_on", await self._get_keyboard("ai", user_id))

        async def contact_agent():
            self.user_human_mode.add(user_id)
            self.user_ai_mode.discard(user_id)
            await self._send_to_admin("telegram", user_id, "Игрок подключён к агенту.", "agent")
            await self._send_message(user_id, "human_on", await self._get_keyboard("human", user_id))

        async def end_human():
            self.user_human_mode.discard(user_id)
            await self._send_message(user_id, "human_off", await self._get_keyboard("main", user_id))
            await self._reset_user_state(user_id)

        async def report_staff():
            self.user_action_mode[user_id] = "staff"
            self.user_human_mode.discard(user_id)
            await self._send_message(user_id, "report_staff", await self._get_keyboard("action", user_id))

        async def report_bug():
            self.user_action_mode[user_id] = "bug"
            await self._send_message(user_id, "report_bug", await self._get_keyboard("action", user_id))

        async def end_ai():
            self.user_ai_mode.discard(user_id)
            self.user_action_mode.pop(user_id, None)
            self.user_contexts.pop(user_id, None)
            self.user_human_mode.discard(user_id)
            await self._send_message(user_id, "ai_off", await self._get_keyboard("main", user_id))
            await self._reset_user_state(user_id)

        async def cancel():
            self.user_action_mode.pop(user_id, None)
            self.user_ai_mode.discard(user_id)
            self.user_human_mode.discard(user_id)
            await self._send_message(user_id, "cancel", await self._get_keyboard("main", user_id))
            await self._reset_user_state(user_id)

        async def admin_panel():
            if self.is_admin(user_id):
                await self._send_message(user_id, "admin_panel", await self._get_keyboard("admin", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("main", user_id))

        async def manage_agents():
            if self.is_admin(user_id):
                await self._send_message(user_id, "manage_agents", await self._get_keyboard("manage_agents", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def ban_user():
            if self.is_admin(user_id):
                await self._send_message(user_id, "ban_user", await self._get_keyboard("ban_user", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def broadcast():
            if self.is_admin(user_id):
                self.user_action_mode[user_id] = "broadcast"
                await self._send_message(user_id, "broadcast", await self._get_keyboard("action", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def add_agent():
            if self.is_admin(user_id):
                self.user_action_mode[user_id] = "add_agent"
                await self._send_message(user_id, "add_agent", await self._get_keyboard("action", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def remove_agent():
            if self.is_admin(user_id):
                self.user_action_mode[user_id] = "remove_agent"
                await self._send_message(user_id, "remove_agent", await self._get_keyboard("action", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def ban():
            if self.is_admin(user_id):
                self.user_action_mode[user_id] = "ban"
                await self._send_message(user_id, "ban", await self._get_keyboard("action", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def unban():
            if self.is_admin(user_id):
                self.user_action_mode[user_id] = "unban"
                await self._send_message(user_id, "unban", await self._get_keyboard("action", user_id))
            else:
                await self._send_message(user_id, "admin_denied", await self._get_keyboard("admin", user_id))

        async def getagents():
            await self._handle_get_agents(user_id)

        async def stats():
            await self._handle_stats(user_id)

        async def unknown():
            await self._send_message(user_id, "unknown", await self._get_keyboard("main", user_id))

        commands = {
            "ai_agent": ai_agent,
            "contact_agent": contact_agent,
            "end_human": end_human,
            "report_staff": report_staff,
            "report_bug": report_bug,
            "end_ai": end_ai,
            "cancel": cancel,
            "admin_panel": admin_panel,
            "manage_agents": manage_agents,
            "ban_user": ban_user,
            "broadcast": broadcast,
            "add_agent": add_agent,
            "remove_agent": remove_agent,
            "ban": ban,
            "unban": unban,
            "getagents": getagents,
            "stats": stats
        }
        await commands.get(cmd.lower(), unknown)()

    async def _check_spam(self, user_id):
        current_time = time.time()
        self.spam_protection[user_id] = [t for t in self.spam_protection[user_id] if current_time - t < 30]
        if len(self.spam_protection[user_id]) >= 3:
            return False
        self.spam_protection[user_id].append(current_time)
        return True

    async def _process_action(self, user_id, action, text, attachments=None):
        try:
            if action not in ["staff", "bug", "broadcast", "ban", "unban", "add_agent", "remove_agent"]:
                await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
                return
            actions = {
                "staff": self._handle_report,
                "bug": self._handle_report,
                "broadcast": self._handle_broadcast,
                "ban": self._handle_ban,
                "unban": self._handle_unban,
                "add_agent": self._handle_add_agent,
                "remove_agent": self._handle_remove_agent
            }
            handler = actions.get(action)
            if handler:
                await handler(user_id, text, attachments if action in ["staff", "bug"] else None)
            else:
                await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
        finally:
            self.user_action_mode.pop(user_id, None)

    async def _handle_ai_message(self, user_id, text):
        if text.lower() in {"выйти", "выход", "стоп"}:
            await self._handle_command(user_id, "end_ai")
        else:
            ai_response = await self._get_ai_response(user_id, text)
            await self._process_ai_response(user_id, ai_response)

    async def _handle_human_message(self, user_id, text, attachments=None):
        await self._send_to_admin("telegram", user_id, text, "agent", attachments)

class TelegramBot(BotCore):
    def __init__(self, telegram_token, admin_chat_id):
        super().__init__(admin_chat_id)
        self.telegram_token = telegram_token
        self.app = Application.builder().token(self.telegram_token).build()

    async def _get_user_info(self, user_id):
        try:
            user = await self.app.bot.get_chat(user_id)
            return f"\n👤 @{user.username or f'id{user_id}'}\n📲 Диалог: Telegram обращение."
        except Exception:
            return f"\n👤 id{user_id}\n📲 Диалог: Telegram обращение."

    async def _send_message(self, user_id, message_key, keyboard=None, info=None):
        if not isinstance(user_id, int):
            return
        msg = self._MESSAGES.get(message_key, message_key)
        if info:
            try:
                msg = msg.format(**info)
            except KeyError:
                msg = message_key
        cleaned_message = self.clean_message(msg)
        try:
            if await self._check_user_permission(user_id):
                await self.app.bot.send_message(chat_id=user_id, text=cleaned_message, reply_markup=keyboard)
            else:
                await self.app.bot.send_message(chat_id=user_id, text=self._MESSAGES["permission_denied"])
        except Exception:
            await self.app.bot.send_message(user_id, text=self._MESSAGES["permission_denied"])

    async def _process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip() if update.message.text else ""
        try:
            self.banned_users = {uid: expiry for uid, expiry in self.banned_users.items() if datetime.now() <= expiry}
            if user_id in self.banned_users:
                await self._send_message(user_id, "banned_user", await self._get_keyboard("main", user_id))
                return
            if not await self._check_spam(user_id):
                await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
                return
            self.stats["users"].add(user_id)
            self.stats["messages_processed"] += 1
            if text.startswith('/'):
                await self._handle_command(user_id, text[1:])
                return
            if not text:
                await self._send_message(user_id, "no_input", await self._get_keyboard("main", user_id))
                return
            if user_id in self.user_human_mode:
                attachments = []
                if update.message.document or update.message.photo:
                    if update.message.document:
                        attachments.append(update.message.document.file_id)
                    elif update.message.photo:
                        attachments.append(update.message.photo[-1].file_id)
                await self._handle_human_message(user_id, text, ",".join(attachments) if attachments else None)
                return
            if user_id in self.user_action_mode:
                attachments = []
                if update.message.document or update.message.photo:
                    if update.message.document:
                        attachments.append(update.message.document.file_id)
                    elif update.message.photo:
                        attachments.append(update.message.photo[-1].file_id)
                await self._process_action(user_id, self.user_action_mode[user_id], text, join(attachments) if attachments else None)
                return
            if user_id in self.user_ai_mode:
                await self._send_message(user_id, "ai_mode", await self._get_keyboard("ai", user_id))
            if text.lower() in ["start", "привет", "прод"]:
                await self._send_message(user_id, "welcome", await self._get_keyboard("main", user_id))
            else:
                await self._send_message(user_id, "unknown", await self._get_keyboard("main", user_id))
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))
            await self._reset_user_state(user_id)

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        callback_data = update.callback_query.data
        try:
            await self._handle_command(user_id, callback_data)
            await update.callback_query.answer()
        except Exception:
            await self._send_message(user_id, "error", await self._get_keyboard("main", user_id))

    async def run(self):
        print(f"\nБот технической поддержки Candyx. (TG-версия)\n{'-'*40}")
        print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Версия: {VERSION}")
        print(f"Техподдержка by vatkovskydev\n{'-'*40}\n")
        self.app.add_handler(CommandHandler("start", self._process_message))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._process_message))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

async def main():
    TELEGRAM_TOKEN = "suslov:daun"
    ADMIN_CHAT_ID = 2

    telegram_bot = TelegramBot(TELEGRAM_TOKEN, ADMIN_CHAT_ID)
    await telegram_bot.run()

if __name__ == "__main__":
    asyncio.run(main())
