import httpx


async def test_web_landing(web_app: str) -> None:
    """End-to-end test querying the web app's landing page via HTTP."""
    async with httpx.AsyncClient() as client:
        r = await client.get(web_app)
        assert r.status_code == 200
        assert "<html" in r.text
