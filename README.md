# 🤖 Elemental Bot

> Модульный Discord-бот, построенный на LLM.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.7-5865F2)](https://discordpy.readthedocs.io/)
[![Mypy](https://img.shields.io/badge/Mypy-Strict-blue)](https://mypy.readthedocs.io/)
[![Ruff](https://img.shields.io/badge/Ruff-Lint-red)](https://docs.astral.sh/ruff/)

[📚 Архитектура](./docs/ARCHITECTURE.md) | [📉 Технический долг](./docs/TECH_DEBT.md)

## ✨ Возможности

- 🧠 **Multi-Model Routing** — легкое переключение между провайдерами (OpenRouter, Google AI Studio, Anthropic).
- 🛡 **Defense in Depth** — строгая типизация через `mypy` и `pydantic` предотвращает runtime-ошибки при работе с API.
- 📦 **Context Awareness** — умное управление историей чата с подсчетом токенов через `tiktoken`.

## 🛠 Технические особенности

- **Strict Type System** — `mypy --strict` не прощает ошибок типов.
- **Async First** — вся логика взаимодействия с внешними API строится на асинхронности.
- **Tool-Agnostic** — архитектура позволяет добавлять новые модели LLM через простые адаптеры.

## 🚀 Начало работы

### Установка

1. **Зависимости:**

   ```bash
   pip install uv
   uv sync
   ```

2. **Настройка окружения:**
   Создайте `.env` на основе примера:
   ```env
   DISCORD_TOKEN=your_token
   OPENROUTER_API_KEY=your_key
   ```

### Скрипты

- `uv run python bot.py` — Запуск бота.
- `mypy .` — Проверка типов (обязательный этап перед коммитом).
- `ruff check .` — Линтинг и исправление импортов.

## 📚 Документация

- [🏛 Архитектура](./docs/ARCHITECTURE.md) — Как мы разделяем `core`, `lib` и `features`.
- [📉 Технический долг](./docs/TECH_DEBT.md) — Планы по внедрению провайдеров.
