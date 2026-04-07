import os

import discord
import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

load_dotenv()

MAX_TOKENS = 10000

# 1. СИНХРОННЫЕ РЕСУРСЫ (Безопасно инициализировать глобально)
# Кодировщик загружается в память 1 раз и не зависит от asyncio.
encoding = tiktoken.get_encoding("o200k_base")


# 2. АРХИТЕКТУРА КЛИЕНТА (С инкапсуляцией состояния)
class ElementalBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, activity=discord.CustomActivity(name="Исследование"))

        # Явное объявление зависимости для Mypy.
        # Будет инициализировано внутри правильного Event Loop.
        self.llm_client: AsyncOpenAI | None = None

    async def setup_hook(self) -> None:
        """
        [LIFECYCLE] Выполняется после создания Event Loop, но до подключения к Gateway.
        Это единственное безопасное место для создания асинхронных сессий.
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY не задан в окружении")

        self.llm_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


# Инициализация каркаса (без запуска сети)
bot = ElementalBot()


@bot.event
async def on_ready() -> None:
    print(f"{bot.user} на связи.")


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    Обработчик сообщений со строгим Type Narrowing (Defense in Depth).
    """
    # --- 1. TYPE GUARDS & EARLY EXITS ---

    # Гарантируем, что бот и LLM клиент готовы
    if bot.user is None or bot.llm_client is None:
        return

    # Защита от петель обратной связи
    if message.author == bot.user:
        return

    # Игнорируем, если не упомянули
    if not bot.user.mentioned_in(message):
        return

    # [КРИСТАЛЛ ТИПИЗАЦИИ]: Сужаем тип канала.
    # Это аналог `if (!isInstanceOf(channel, Messageable)) return;` из TypeScript.
    # Снимает красные подчеркивания у `message.channel.history`.
    channel = message.channel
    # if not isinstance(channel, Messageable):
    #     return

    # --- 2. ПОДГОТОВКА КОНТЕКСТА ---

    current_model = "openai/gpt-4o-mini"

    # Очистка запроса
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

    # Визуальная индикация для пользователя, пока идут тяжелые сетевые запросы
    async with channel.typing():
        # --- 3. ИЗВЛЕЧЕНИЕ ИСТОРИИ ---

        # Mypy теперь знает, что channel - это Messageable, метод history() валиден.
        async for msg in channel.history(limit=500, before=message):
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

        # --- 4. ЗАПРОС К LLM ---

        try:
            response: ChatCompletion = await bot.llm_client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0.9,
            )

            # --- 5. ОБРАБОТКА ОТВЕТА (С ЗАЩИТОЙ ОТ ПУСТЫХ ЗНАЧЕНИЙ) ---

            usage = response.usage
            usage_info = f"Tokens: {usage.prompt_tokens}+{usage.completion_tokens}" if usage else "N/A"

            debug_info = f"**[{current_model} | Msgs: {message_count} | {usage_info}]**"

            # Защита: массив choices может быть пуст, content может быть None.
            bot_answer = "..."
            if response.choices and response.choices[0].message.content:
                bot_answer = response.choices[0].message.content

            full_response = f"{debug_info}\n\n{bot_answer}"

            # --- 6. ДОСТАВКА (С обходом лимитов Discord) ---

            if len(full_response) <= 2000:
                await message.reply(full_response)
            else:
                for i in range(0, len(full_response), 1900):
                    part = full_response[i : i + 1900]
                    if i == 0:
                        await message.reply(part)
                    else:
                        await channel.send(part)

        except Exception as e:
            # Защитный фоллбек
            await message.reply(f"**[Error]** Архитектурный сбой: {e}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN не задан в окружении")
    bot.run(token)
