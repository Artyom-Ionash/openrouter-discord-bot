import discord
from openai import AsyncOpenAI
import os
import tiktoken
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

intents = discord.Intents.default()
intents.message_content = True

custom_status = discord.CustomActivity(name="Исследование")
bot = discord.Client(intents=intents, activity=custom_status)

# Инициализируем кодировщик для нашей модели
# Для gpt-4o и gpt-4o-mini используется кодировка o200k_base
encoding = tiktoken.get_encoding("o200k_base")

@bot.event
async def on_message(message):
    if not bot.user:
        return
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        current_model = "openai/gpt-4o-mini"

        # Настройки контекста
        MAX_TOKENS = 10000  # Максимальный размер лога (в токенах), который мы готовы отправить

        user_request = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        if not user_request:
            user_request = "Проанализируй переписку выше:"

        system_prompt = "Ты — суровый инженер. Обращайся ко мне на ты. Отвечай коротки и по делу, как мужик. Взвешивай плюсы и минусы."
        base_prompt_text = f"{user_request}\n\n--- КОНТЕКСТ ИЗ ЧАТА ---\n"

        # Считаем, сколько токенов "съедают" системный промпт и запрос пользователя
        base_tokens = len(encoding.encode(system_prompt + base_prompt_text))
        available_tokens_for_log = MAX_TOKENS - base_tokens

        messages_to_process = []
        current_log_tokens = 0
        message_count = 0

        # Выгребаем историю, пока не заполним доступный лимит токенов
        # limit=500 означает, что мы проверим максимум 500 последних сообщений
        async for msg in message.channel.history(limit=500, before=message):
            msg_line = f"{msg.author.name}: {msg.content}\n"
            msg_tokens = len(encoding.encode(msg_line))

            # Если следующее сообщение превышает лимит — останавливаем сбор
            if current_log_tokens + msg_tokens > available_tokens_for_log:
                break

            messages_to_process.append(msg_line)
            current_log_tokens += msg_tokens
            message_count += 1

        # Переворачиваем сообщения, чтобы они шли в хронологическом порядке
        messages_to_process.reverse()
        context = "".join(messages_to_process)
        final_prompt = base_prompt_text + context

        try:
            response = await client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt}
                ],
                # Ограничиваем ВЫХОД модели (например, до 500 токенов)
                # max_tokens=300,
                # Можно также добавить температуру для более "инженерных" ответов
                temperature=0.9
            )

            usage = response.usage
            debug_info = f"**[{current_model} | Msgs: {message_count} | Tokens: {usage.prompt_tokens} (in) + {usage.completion_tokens} (out) = {usage.total_tokens}]**"
            bot_answer = response.choices[0].message.content

            # Полный текст ответа с подписью
            full_response = f"{debug_info}\n\n{bot_answer}"

            # Проверка лимита Discord (2000 символов)
            if len(full_response) <= 2000:
                await message.reply(full_response)
            else:
                # Если текст длинный, разбиваем его на части
                # Мы режем по 1900, чтобы оставить запас на форматирование
                for i in range(0, len(full_response), 1900):
                    part = full_response[i:i+1900]
                    # Первую часть отправляем реплаем, остальные — просто в канал
                    if i == 0:
                        await message.reply(part)
                    else:
                        await message.channel.send(part)

        except Exception as e:
            await message.reply(f"**[Error]** Произошла ошибка: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
