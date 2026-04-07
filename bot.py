import os

import discord
import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

load_dotenv()

MAX_TOKENS = 10000

# Инициализация OpenAI клиента
openai_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents, activity=discord.CustomActivity(name="Исследование"))

# Инициализируем кодировщик
encoding = tiktoken.get_encoding("o200k_base")


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    Обработчик сообщений с полной типизацией для Mypy.
    """
    # Type Guard: bot.user может быть None, пока бот не залогинился
    if bot.user is None:
        return

    # Игнорируем свои же сообщения
    if message.author == bot.user:
        return

    # Реакция только на упоминание
    if bot.user.mentioned_in(message):
        current_model = "openai/gpt-4o-mini"

        # Очистка запроса от упоминания
        user_request = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not user_request:
            user_request = "Проанализируй переписку выше:"

        system_prompt = "Ты — суровый инженер. Обращайся ко мне на ты. Отвечай коротко и по делу, как мужик. Взвешивай плюсы и минусы."
        base_prompt_text = f"{user_request}\n\n--- КОНТЕКСТ ИЗ ЧАТА ---\n"

        base_tokens = len(encoding.encode(system_prompt + base_prompt_text))
        available_tokens_for_log = MAX_TOKENS - base_tokens

        messages_to_process: list[str] = []
        current_log_tokens = 0
        message_count = 0

        # Выгребаем историю
        async for msg in message.channel.history(limit=500, before=message):
            msg_line = f"{msg.author.name}: {msg.content}\n"
            msg_tokens = len(encoding.encode(msg_line))

            if current_log_tokens + msg_tokens > available_tokens_for_log:
                break

            messages_to_process.append(msg_line)
            current_log_tokens += msg_tokens
            message_count += 1

        messages_to_process.reverse()
        context = "".join(messages_to_process)
        final_prompt = base_prompt_text + context

        try:
            response: ChatCompletion = await openai_client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0.9,
            )

            usage = response.usage
            # Usage может быть None, если API глючит, Mypy требует проверки
            usage_info = f"Tokens: {usage.prompt_tokens}+{usage.completion_tokens}" if usage else "N/A"

            debug_info = f"**[{current_model} | Msgs: {message_count} | {usage_info}]**"
            bot_answer = response.choices[0].message.content or "..."

            full_response = f"{debug_info}\n\n{bot_answer}"

            # Разбивка длинных сообщений
            if len(full_response) <= 2000:
                await message.reply(full_response)
            else:
                for i in range(0, len(full_response), 1900):
                    part = full_response[i : i + 1900]
                    if i == 0:
                        await message.reply(part)
                    else:
                        await message.channel.send(part)

        except Exception as e:
            await message.reply(f"**[Error]** Произошла ошибка: {e}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN не задан")
    bot.run(token)
