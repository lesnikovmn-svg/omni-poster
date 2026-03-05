# omni-poster

Авто‑публикация постов (текст + 1 фото) в разные каналы/группы через модульные “паблишеры”.

Сейчас из коробки:
- Telegram (Bot API): пост в канал/чат, где бот админ
- Webhook: универсальная интеграция (можно подцепить VK/Instagram/Max через свой сервер/Make/Zapier/любой шлюз)
- VK: пост на стену сообщества (текст или текст + до 10 фото)
- Instagram Graph API: пост в ленту (1 фото) или карусель (несколько фото) по `image_url(s)`
- MAX: через API‑шлюз (если используешь)

> Важно про Instagram: автоматическая публикация легально делается через **официальный Instagram Graph API** (обычно нужен Business/Creator аккаунт, связка с Facebook Page и app/permissions). “Парсинг/вход по паролю” и прочие неофициальные боты часто нарушают ToS — сюда не закладываю.

## Быстрый старт (локально)

```bash
cd omni-poster
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp secrets/.env.example secrets/.env
# заполни переменные

python3 -m omniposter run --posts ./posts --dry-run
python3 -m omniposter run --posts ./posts
```

Если видишь предупреждение `NotOpenSSLWarning` (LibreSSL), проще всего использовать Python из `pyenv`/Homebrew (OpenSSL), либо временно игнорировать warning — на функциональность проекта в большинстве случаев не влияет.

По умолчанию включено состояние (анти‑дубли): `omni-poster/.state/state.json`. Если нужно отключить: `--state ""`.

## Формат постов

Посты — это JSON файлы в папке `posts/` (пример: `posts/sample-post.json`).

Если у тебя несколько брендов, удобно держать отдельные папки и запускать по очереди:

```bash
python3 -m omniposter run --posts ./posts/my_avto5 --state ./.state/my_avto5.json
python3 -m omniposter run --posts ./posts/my_avto_optimal --state ./.state/my_avto_optimal.json
```

Рекомендация: делай `id` поста уникальным (например с префиксом бренда), чтобы не было конфликтов в state.

Поля:
- `id` (string, обязателен)
- `publish_at` (ISO-8601, опционально) — если в будущем, пост пропускается
- `text` (string, обязателен)
- `images` (array, опционально) — список локальных файлов изображений (для TG/VK)
- `image_urls` (array, опционально) — список публичных URL изображений (для Instagram/MAX/webhook)
- `image` / `image_url` — старые single‑поля (можно не использовать)
- `links` (array, опционально) — кнопки/ссылки, формат: `[{ "label": "...", "url": "..." }]`
- `targets` (array, обязателен) — куда публиковать

`targets` поддерживает:
- `{"type":"telegram","chat_id":"@channel_or_chat_id","parse_mode":"HTML"}`
- `{"type":"webhook","url":"https://...","headers":{"Authorization":"Bearer ..."}}`
- `{"type":"vk"}`
- `{"type":"instagram"}`
- `{"type":"max","chat_id":"..."}`

## Кнопки/иконки

- В Telegram `links` превращаются в inline‑кнопки (keyboard). Если пост с альбомом (>1 фото), кнопки отправляются отдельным сообщением “Открыть ссылки:”.
- В VK/Instagram/MAX ссылки просто добавляются в текст (блок “Ссылки:”).

## Переменные окружения

Смотри `secrets/.env.example` (локальные ключи держим в `secrets/.env`, он в `.gitignore`).

## Примечания по Instagram Graph API

- Для публикации в ленту нужен `image_url`, доступный из интернета: API скачивает картинку по URL.
- Публикация идёт в 2 шага: создать media container → `media_publish`. Контейнеры имеют ограничения по времени жизни.

## GitHub Actions (cron)

Workflow уже готов: `.github/workflows/omni-poster.yml` (лежит в корне репозитория).

В GitHub → Settings → Secrets and variables → Actions добавь:
- `TELEGRAM_BOT_TOKEN`
- (если используешь webhook) `WEBHOOK_DEFAULT_URL` и/или свои секреты под заголовки
- VK: `VK_ACCESS_TOKEN`, `VK_GROUP_ID` (для `club229926764` это `229926764`)

## Следующий шаг (подключим VK/Instagram/Max)

Скажи, какие именно каналы нужны и какой способ доступа есть:
- VK: токен сообщества? пост на стену сообщества + фото?
- Instagram: Business/Creator + Graph API? (публикация в ленту)
- Max: нужна точная платформа/API (скинь ссылку на документацию или название сервиса).

## Вариант “постим в Telegram → дальше авторассылка”

Если админ публикует пост прямо в Telegram‑канале, можно автозабирать новые посты ботом и пересылать дальше.

Сейчас реализован первый шаг: **Telegram канал → VK стена** (через `getUpdates`, без вебхуков/сервера).

Требования:
- бот добавлен админом в исходный Telegram‑канал
- заполнены `TELEGRAM_BOT_TOKEN`, `VK_ACCESS_TOKEN`, `VK_GROUP_ID`
  - если VK с фото падает с ошибкой “unavailable with group auth”, добавь `VK_USER_ACCESS_TOKEN`

Команды (рекомендуется отдельный state на каждый источник):

```bash
python -m omniposter tg-sync --source @MY_Avto5 --offset-state ./.state/tg_offset_my_avto5.json --seen-state ./.state/tg_seen_my_avto5.json
python -m omniposter tg-sync --source @My_Avto_Optimal --offset-state ./.state/tg_offset_my_avto_optimal.json --seen-state ./.state/tg_seen_my_avto_optimal.json
```

Чтобы проверить без отправки в VK: добавь `--dry-run`.

Ссылки/иконки, которые надо автоматически добавлять в VK при репосте из Telegram, задаются файлом:
`secrets/tg_links.json` (шаблон: `secrets/tg_links.json.example`).
