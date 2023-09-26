import telebot as tlb
from env import *
from questions import questions
from os import path, listdir, makedirs

makedirs("requests\\", exist_ok=True)

bot = tlb.TeleBot(BOT_TOKEN)

clients = {}

def download_file(message):
    """Returns local path to saved file"""
    makedirs(f"temp\\", exist_ok=True)
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_name = message.document.file_name
    with open(
        f"temp\\{message.chat.id}__file______{file_name}",
        "wb",
    ) as new_file:
        new_file.write(downloaded_file)
    return f"temp\\{message.chat.id}__file______{file_name}"

def send_file(path_: str, id: int):
    with open(path_, "rb") as file:
        bot.send_document(id, file)


def load_templates(dir: str) -> dict:
    file_dict = {}
    for file_name in listdir(dir):
        file_path = path.join(dir, file_name)
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            file_dict[file_name.replace(".txt", "")] = content
    return file_dict


templates = load_templates("templates\\")


class user:
    def __init__(self, chat_id) -> None:
        self.chat_id = chat_id
        self.filling_request = False
        self.request = {}
        self.please_select_option = False
        start_keyboard = tlb.types.InlineKeyboardMarkup()
        start_button = tlb.types.InlineKeyboardButton(
            text="Начать",
            callback_data="start_filling_request",
        )
        start_keyboard.add(start_button)
        bot.send_message(
            self.chat_id, templates["welcome"], reply_markup=start_keyboard
        )

    def new_message(self, message, call=False):
        if not call and message.content_type == "document":
            local_path = download_file(message)
            for id_ in primary_chat_ids:
                bot.send_message(id_,f"[Кто-то](tg://user?id={self.chat_id}) отправил резюме :D  ",parse_mode="Markdown")
                send_file(local_path,id_)
            bot.reply_to(message,"Спасибо!")
            return
        if not call and self.please_select_option:
            bot.send_message(
                self.chat_id, "Пожалуйста, выберите из предложенных вариантов"
            )
            return
        if call and self.filling_request:
            q_number = int(message.data.split("_")[1])
            if q_number < self.cur_q_number:
                bot.send_message(
                    self.chat_id,
                    "Вы уже ответили на этот вопрос.",
                )
                return
            self.generator.send(message.data.split("_")[-1])
        elif self.filling_request:
            self.generator.send(message.text)

    def fill_request(self):
        self.filling_request = True

        for q in questions:
            self.cur_q_number = q.id
            if q.variants:
                keyboard = tlb.types.InlineKeyboardMarkup()
                for v in q.variants:
                    button = tlb.types.InlineKeyboardButton(
                        text=v,
                        callback_data=f"question_{q.id}_{v}",
                    )
                    keyboard.add(button)
                self.please_select_option = True
                answer = yield bot.send_message(
                    self.chat_id, f"Вопрос {q.id}/10 \n {q.q_t}", reply_markup=keyboard
                )
                self.request[q.q_t] = answer
                self.please_select_option = False
                continue

            answer = yield bot.send_message(
                self.chat_id, f"Вопрос {q.id}/10 \n {q.q_t}"
            )
            self.request[q.q_t] = answer

        # Send results
        keyboard = tlb.types.InlineKeyboardMarkup()
        button1 = tlb.types.InlineKeyboardButton(text="Согласен", callback_data="ready")
        button2 = tlb.types.InlineKeyboardButton(
            text="Не согласен", callback_data="not_ready"
        )
        button3 = tlb.types.InlineKeyboardButton(
            text="Работодатель", url="https://t.me/impersa"
        )
        keyboard.add(button1, button2)
        keyboard.add(button3)
        bot.send_message(self.chat_id, templates["end"], reply_markup=keyboard)

        self.filling_request = False

        yield  # this is needed because we cant use "send" at the last iteration


@bot.callback_query_handler(func=lambda call: True)
def buttons_handler(call):
    if call.data.startswith("question"):
        clients[call.message.chat.id].new_message(call, call=True)
        return
    if call.data == "start_filling_request":
        clients[call.message.chat.id].generator = clients[
            call.message.chat.id
        ].fill_request()
        next(clients[call.message.chat.id].generator)
    if call.data ==  "ready":
        content = "Результаты:\n\n"
        for key, val in clients[call.message.chat.id].request.items():
            content += key + " - " + val + "\n\n"
        content += f"user id: {call.message.chat.id}"
        with open(
            f"requests\\{call.message.chat.id}.txt", "w", encoding="utf-8"
        ) as f:
            f.write(content)

        for id_ in primary_chat_ids:
            send_file(f"requests\\{call.message.chat.id}.txt", id_)
            bot.send_message(
                id_,
                f"[ссылка](tg://user?id={call.message.chat.id})",
                parse_mode="Markdown",
            )

        bot.send_message(
            call.message.chat.id,
            "Отлично! Пришлите пожалуйста Ваше резюме и я передам его вместе с данной перепиской на утверждение руководителю бухгалтерской службы.",
        )
    if call.data == "not_ready":
        bot.reply_to(call.message, "Спасибо, были рады сотрудничеству!")


@bot.message_handler(
    content_types=[
        "text",
        "document",
    ]
)
def main_messages_handler(message):
    """Handles all messages"""
    if message.chat.id not in clients:
        clients[message.chat.id] = user(message.chat.id)
    else:
        clients[message.chat.id].new_message(message)


bot.infinity_polling(timeout=500)
