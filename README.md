# Django + PostgreSQL Docker Project

Готовий проект Django з PostgreSQL для розробки в Docker контейнерах.

## 📋 Структура проекту

```
django_postgres_docker/
├── config/              # Django конфігурація
│   ├── __init__.py
│   ├── settings.py      # Основні налаштування
│   ├── urls.py          # URL маршрути
│   └── wsgi.py          # WSGI додаток
├── apps/                # Django додатки
├── templates/           # HTML шаблони
├── static/              # Статичні файли (CSS, JS)
├── media/               # Завантажені файли користувачів
├── Dockerfile           # Docker конфігурація
├── docker-compose.yml   # Docker Compose конфігурація
├── requirements.txt     # Python залежності
├── manage.py            # Django управління
├── .env.example         # Приклад .env файлу
└── README.md            # Цей файл
```

## 🚀 Як запустити

### Вимоги
- Docker
- Docker Compose

### Кроки запуску

1. **Клонуйте/завантажте проект**
   ```bash
   cd django_postgres_docker
   ```

2. **Створіть `.env` файл з змінних оточення**
   ```bash
   cp .env.example .env
   ```

3. **Запустіть Docker контейнери**
   ```bash
   docker-compose up -d
   ```

4. **Виконайте міграції (автоматично під час запуску)**
   Docker Compose автоматично запустить міграції та зберегти статичні файли.

5. **Отримайте доступ до додатку**
   - Django додаток: http://localhost:8000
   - Django admin: http://localhost:8000/admin (username: admin, пароль: admin)

## 📚 Основні команди

### Запуск проекту
```bash
docker-compose up -d
```

### Зупинення проекту
```bash
docker-compose down
```

### Перегляд логів
```bash
docker-compose logs -f web
docker-compose logs -f db
```

### Запуск Django команд всередині контейнера
```bash
# Міграції
docker-compose exec web python manage.py migrate

# Створення суперкористувача
docker-compose exec web python manage.py createsuperuser

# Колекціонування статичних файлів
docker-compose exec web python manage.py collectstatic --noinput

# Django shell
docker-compose exec web python manage.py shell
```

### Видалення контейнерів та об'ємів
```bash
docker-compose down -v
```

## 🔧 Налаштування

### Змінні оточення (.env файл)
- `DEBUG` - Режим налагодження (True/False)
- `SECRET_KEY` - Таємний ключ Django
- `DB_NAME` - Назва бази даних PostgreSQL
- `DB_USER` - Користувач PostgreSQL
- `DB_PASSWORD` - Пароль PostgreSQL
- `DB_HOST` - Хост серверу PostgreSQL (у Docker Compose: "db")
- `DB_PORT` - Порт PostgreSQL (за замовчуванням: 5432)

### Доступ до БД PostgreSQL
```bash
# Використовуючи psql всередині контейнера
docker-compose exec db psql -U django_user -d django_db

# З хоста (якщо встановлений psql)
psql -h localhost -U django_user -d django_db
```

## 📦 Встановлення додаткових пакетів

1. Додайте пакет у `requirements.txt`
2. Перебудуйте Docker образ:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## 🖥️ PostgreSQL контейнер

- **Образ**: postgres:15
- **Порт**: 5432
- **Користувач**: django_user
- **Пароль**: django_password
- **База даних**: django_db
- **Том даних**: postgres_data (зберігає дані між перезавантаженнями)

## 🌐 Django контейнер

- **Образ**: Python 3.11
- **Сервер**: Gunicorn
- **Порт**: 8000
- **Команда запуску**: Міграція → Collectstatic → Gunicorn

## 💾 Постійність даних

Дані PostgreSQL зберігаються у Docker томі `postgres_data`. Навіть якщо видалити контейнер, дані будуть збережені і доступні при новому запуску.

Щоб видалити всі дані:
```bash
docker-compose down -v
```

## 🐛 Розв'язування проблем

### Контейнер Django не запускається
```bash
docker-compose logs web
```

### Помилка підключення до БД
Переконайтеся, що контейнер PostgreSQL запущений:
```bash
docker-compose ps
```

### Видалення старих контейнерів та образів
```bash
docker-compose down
docker system prune -a
```

## 📝 Ліцензія

MIT

## 🤝 Контрибьютори

Created for development purposes.
