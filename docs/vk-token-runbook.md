# VK user token (runbook)

Цель: получить **VK_USER_ACCESS_TOKEN** (user access token) для пользователя `id1039539516`, чтобы работала **загрузка фото** на стену сообщества.

## Нужны 2 токена

- `VK_ACCESS_TOKEN` — **токен сообщества** (обычно долгоживущий). Нужен для `wall.post` от имени `club229926764`.
- `VK_USER_ACCESS_TOKEN` — **user token**. Нужен для `photos.getWallUploadServer`/`saveWallPhoto` (иначе будет ошибка `27 method is unavailable with group auth`).

## Важно

- **Не** храните токены в git. Файл `secrets/.env` уже в `.gitignore`.
- Токен должен быть получен **в браузере, где вы залогинены именно пользователем** `https://vk.com/id1039539516` (должно быть “Моя страница”).

## Быстрый способ (vkhost)

1) Откройте `https://vkhost.github.io/`
2) Выберите приложение **vk.com** (или **VK Admin**).
3) В `Настройки` отметьте права: `photos`, `wall`, `groups`, `offline`.
4) Нажмите “Разрешить”.
5) В адресной строке будет `access_token=...&...` — скопируйте **только значение** после `access_token=` и **до** первого `&`.
6) Вставьте в `secrets/.env`:

```env
VK_USER_ACCESS_TOKEN=vk1.a....
```

## Проверка токена

```bash
cd "/Users/maksimlesnikov/Documents/New project/_omni-poster"
source .venv/bin/activate
python -m omniposter vk-check
```

Ожидается `response` с `id: 1039539516`.

Если приходит `error_code: 5 invalid access_token`:
- токен скопирован не полностью, или
- вы залогинены не тем аккаунтом, или
- токен был отозван/невалиден → получите новый на vkhost.

Если пишет `network/DNS error`:
- проверьте интернет/ВПН/ДНС,
- попробуйте открыть `https://api.vk.com` в браузере.

## Проверка токена сообщества

Добавьте `VK_ACCESS_TOKEN=...` (токен сообщества) и проверьте:

```bash
python -m omniposter vk-check --check-group
```
