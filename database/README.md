# Database

JARVIS uses PostgreSQL as its primary store and Redis for cache + pub/sub.

* Schema is defined in `backend/app/db/models.py`
* Tables are created automatically on backend startup via `init_db()`
* For production migrations, switch to Alembic — a starter config can be added later

## Local development

```bash
docker compose -f deployment/docker-compose.yml up postgres redis
```

Then run the backend; it will create / upgrade tables itself.
