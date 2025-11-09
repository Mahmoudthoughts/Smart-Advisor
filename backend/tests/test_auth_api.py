import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from smart_advisor.api.database import Database
from smart_advisor.api.main import create_app


def _database(tmp_path: Path) -> Database:
    db_path = tmp_path / "test_auth.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    database = Database(url=url)
    asyncio.run(database.create_all())
    return database


def _client(database: Database):
    app = create_app(database)

    @asynccontextmanager
    async def _manager():
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client

    return _manager


def test_register_and_login_flow(tmp_path: Path):
    database = _database(tmp_path)
    client_manager = _client(database)

    async def _scenario():
        async with client_manager() as api_client:
            register_response = await api_client.post(
                "/auth/register",
                json={"name": "Alex", "email": "alex@example.com", "password": "supersecret"},
            )
            assert register_response.status_code == 201
            register_payload = register_response.json()
            assert register_payload["user"]["email"] == "alex@example.com"
            assert register_payload["access_token"]

            login_response = await api_client.post(
                "/auth/login",
                json={"email": "alex@example.com", "password": "supersecret"},
            )
            assert login_response.status_code == 200
            login_payload = login_response.json()
            assert login_payload["user"]["id"] == register_payload["user"]["id"]
            assert login_payload["access_token"] != register_payload["access_token"]

    asyncio.run(_scenario())


def test_duplicate_registration_fails(tmp_path: Path):
    database = _database(tmp_path)
    client_manager = _client(database)

    async def _scenario():
        async with client_manager() as api_client:
            first = await api_client.post(
                "/auth/register",
                json={"name": "Jamie", "email": "jamie@example.com", "password": "supersecret"},
            )
            assert first.status_code == 201

            second = await api_client.post(
                "/auth/register",
                json={"name": "Jamie Clone", "email": "jamie@example.com", "password": "anotherpass"},
            )
            assert second.status_code == 409

    asyncio.run(_scenario())


def test_login_requires_valid_credentials(tmp_path: Path):
    database = _database(tmp_path)
    client_manager = _client(database)

    async def _scenario():
        async with client_manager() as api_client:
            await api_client.post(
                "/auth/register",
                json={"name": "Morgan", "email": "morgan@example.com", "password": "supersecret"},
            )

            response = await api_client.post(
                "/auth/login",
                json={"email": "morgan@example.com", "password": "wrongpass"},
            )
            assert response.status_code == 401

    asyncio.run(_scenario())

