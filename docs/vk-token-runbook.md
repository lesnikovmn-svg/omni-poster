# VK user token (runbook)

Цель: получить **VK_USER_ACCESS_TOKEN** (user access token) для пользователя `id1039539516`, чтобы работали загрузка фото и постинг в сообщество.

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
python - <<'PY'
import requests
from omniposter.config import load_config
c = load_config()
print(requests.get("https://api.vk.com/method/users.get", params={"access_token": c.vk_user_access_token, "v":"5.131"}, timeout=30).text)
PY
```

Ожидается `response` с `id: 1039539516`.

Если приходит `error_code: 5 invalid access_token`:
- токен скопирован не полностью, или
- вы залогинены не тем аккаунтом, или
- токен был отозван/невалиден → получите новый на vkhost.

