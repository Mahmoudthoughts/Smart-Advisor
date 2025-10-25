"""Alpha Vantage client tests."""

from __future__ import annotations


import pytest

from app.providers.alpha_vantage import AlphaVantageClient, AlphaVantageError


class StubResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("error")

    def json(self) -> dict[str, object]:
        return self._payload


class StubClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def get(self, url: str, params: dict[str, object], timeout: float) -> StubResponse:
        self.calls.append(params)
        return StubResponse({"data": "ok"})

    async def aclose(self) -> None:  # pragma: no cover - included for interface completeness
        return None


@pytest.mark.asyncio
async def test_injects_api_key_and_respects_rate_limit(monkeypatch):
    client = AlphaVantageClient(api_key="test", requests_per_minute=10, client=StubClient())
    await client.daily_adjusted("PATH")
    assert client._client.calls[0]["apikey"] == "test"


@pytest.mark.asyncio
async def test_raises_on_note(monkeypatch):
    class NoteClient(StubClient):
        async def get(self, url: str, params: dict[str, object], timeout: float) -> StubResponse:
            return StubResponse({"Note": "limit"})

    client = AlphaVantageClient(api_key="test", requests_per_minute=10, client=NoteClient())
    with pytest.raises(AlphaVantageError):
        await client.daily_adjusted("PATH")
