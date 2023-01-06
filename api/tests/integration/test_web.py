import httpx
import re


async def test_request_landing_page(web_app: str) -> None:
    """End-to-end test querying the web app's landing page via HTTP."""
    async with httpx.AsyncClient() as client:
        r = await client.get(web_app)
        assert r.status_code == 200
        assert "<html" in r.text


async def test_clean_document_workflow(web_app: str, sample_pdf: bytes) -> None:
    """End-to-end test uploading a PDF to the web app and download the result."""
    async with httpx.AsyncClient() as client:
        # Upload document via HTTP POST
        r1 = await client.post(web_app, files={"doc_src": ("test.pdf", sample_pdf)})
        assert r1.status_code == 302
        assert isinstance(r1.next_request, httpx.Request)
        r1_next = r1.next_request
        assert "/jobs/" in str(r1_next.url)
        # Follow redirect to the job status page
        r2 = await client.send(r1_next)
        assert r2.status_code == 200
        assert "Your job was processed successfully" in r2.text
        match = re.search(r"<a href=\"/jobs/(\S+)/result\"", r2.text)
        assert match is not None
        jid = match.group(1)
        assert len(jid) > 0
        # Download result
        r3 = await client.get(f"{web_app}/jobs/{jid}/result")
        assert r3.status_code == 200
        assert r3.headers["content-type"] == "application/octet-stream"
        assert "PDF" in r3.text


async def test_upload_invalid_document(web_app: str) -> None:
    """End-to-end test attempting to upload an invalid/unsupported document."""
    async with httpx.AsyncClient() as client:
        r = await client.post(web_app, files={"doc_src": ("test.pdf", b"INVALID")})
        assert r.status_code == 400
        assert "unsupported document type" in r.text


async def test_request_invalid_job_details(web_app: str) -> None:
    """End-to-end test attempting to fetch details or a download for an invalid job id."""
    async with httpx.AsyncClient() as client:
        r_details = await client.get(f"{web_app}/jobs/invalid")
        assert r_details.status_code == 404
        r_result = await client.get(f"{web_app}/jobs/invalid/result")
        assert r_result.status_code == 404
