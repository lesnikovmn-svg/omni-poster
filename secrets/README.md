# secrets

Папка для локальных ключей/токенов (в git не коммитим).

## Вариант 1 (рекомендуется): secrets/.env

1) Скопируй шаблон:

```bash
cp secrets/.env.example secrets/.env
```

2) Заполни `secrets/.env` токенами.

Приложение автоматически подхватит `secrets/.env` при запуске из корня репозитория.

## Вариант 2: DOTENV_PATH

Можно хранить `.env` где угодно и запускать так:

```bash
DOTENV_PATH=/полный/путь/к/.env python -m omniposter run --posts ./posts
```

