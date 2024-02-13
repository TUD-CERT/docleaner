"""
Tests targeting the user-facing web interface
"""

import asyncio
import httpx
import re


async def test_request_landing_page(web_app: str) -> None:
    """End-to-end test querying the web app's landing page via HTTP."""
    async with httpx.AsyncClient() as client:
        r = await client.get(web_app)
        assert r.status_code == 200
        assert "<html" in r.text


async def test_clean_document_workflow(web_app: str, sample_pdf: bytes) -> None:
    """End-to-end test uploading a PDF to the web app and downloading the result."""
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
        assert "please wait" in r2.text
        # Refresh until job has been executed
        while "Your job was processed successfully" not in r2.text:
            await asyncio.sleep(0.2)
            r2 = await client.send(r1_next)
        jid_match = re.search(r"href=\"/jobs/(\S+)/result\"", r2.text)
        assert jid_match is not None
        jid = jid_match.group(1)
        assert len(jid) > 0
        # Download result
        r3 = await client.get(f"{web_app}/jobs/{jid}/result")
        assert r3.status_code == 200
        assert r3.headers["content-type"] == "application/octet-stream"
        # Result file name suggested by the server matches the uploaded one
        filename_match = re.search(
            r'filename="(\S+)"', r3.headers["content-disposition"]
        )
        assert filename_match is not None
        assert filename_match.group(1) == "test.pdf"
        assert "PDF" in r3.text
        # Delete job manually
        r4 = await client.get(f"{web_app}/jobs/{jid}/delete")
        assert r4.status_code == 200
        r5 = await client.get(f"{web_app}/jobs/{jid}")
        assert r5.status_code == 404


async def test_upload_invalid_document(web_app: str) -> None:
    """End-to-end test attempting to upload an invalid/unsupported document."""
    async with httpx.AsyncClient() as client:
        r = await client.post(web_app, files={"doc_src": ("test.pdf", b"INVALID")})
        assert r.status_code == 422
        assert "unsupported document type" in r.text


async def test_request_invalid_ids(web_app: str) -> None:
    """End-to-end test attempting to fetch details or a download for an invalid job or session id."""
    async with httpx.AsyncClient() as client:
        r_details = await client.get(f"{web_app}/jobs/invalid")
        assert r_details.status_code == 404
        r_result = await client.get(f"{web_app}/jobs/invalid/result")
        assert r_result.status_code == 404
        r_result = await client.get(f"{web_app}/jobs/invalid/delete")
        assert r_result.status_code == 404
        r_result = await client.get(f"{web_app}/sessions/invalid")
        assert r_result.status_code == 404


async def test_get_session_details(web_app: str, sample_pdf: bytes) -> None:
    """End-to-end test creating a session with associated jobs,
    then monitoring session progress via the web interface (with and
    without listing all jobs)."""
    async with httpx.AsyncClient() as client:
        # Create session (via REST API)
        create_session_resp = await client.post(f"{web_app}/api/v1/sessions")
        create_session_json = create_session_resp.json()
        sid = create_session_json["id"]
        # Create a job within that session (via REST API)
        upload_resp = await client.post(
            f"{web_app}/api/v1/jobs?session={sid}",
            files={"doc_src": ("test.pdf", sample_pdf)},
        )
        assert upload_resp.status_code == 201  # Created
        jid = upload_resp.json()["id"]
        # Retrieve session details with jobs
        session_url = f"{web_app}/sessions/{sid}"
        r = await client.get(session_url)
        assert r.status_code == 200
        assert "Session overview" in r.text
        assert jid in r.text
        # Retrieve session details without jobs
        session_url = f"{web_app}/sessions/{sid}?jobs=false"
        r = await client.get(session_url)
        assert "Session overview" in r.text
        assert jid not in r.text
