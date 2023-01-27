"""
Tests targeting the REST API
"""
import asyncio
import re

import httpx

from docleaner.api.core.job import JobStatus, JobType


async def test_clean_document_workflow(web_app: str, sample_pdf: bytes) -> None:
    """End-to-end test uploading a PDF via the REST API, polling until success and downloading the result."""
    async with httpx.AsyncClient() as client:
        # Upload document
        upload_resp = await client.post(
            f"{web_app}/api/v1/jobs", files={"doc_src": ("test.pdf", sample_pdf)}
        )
        assert upload_resp.status_code == 201  # Created
        upload_resp_json = upload_resp.json()
        jid = upload_resp_json["id"]
        assert upload_resp_json["type"] == JobType.PDF
        assert upload_resp.headers["content-type"] == "application/json"
        job_url = f"{web_app}/api/v1/jobs/{jid}"
        assert upload_resp.headers["location"] == job_url
        # Poll job details until it has been executed
        while (await client.get(job_url)).json()["status"] != JobStatus.SUCCESS:
            await asyncio.sleep(0.2)
        job_data = (await client.get(job_url)).json()
        assert len(job_data["metadata_src"]["doc"]) > 0  # Metadata is present
        # Download result
        dl_resp = await client.get(f"{web_app}/api/v1/jobs/{jid}/result")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/octet-stream"
        # Result file name suggested by the server matches the uploaded one
        filename_match = re.search(
            r'filename="(\S+)"', dl_resp.headers["content-disposition"]
        )
        assert filename_match is not None
        assert filename_match.group(1) == "test.pdf"
        assert "PDF" in dl_resp.text


async def test_upload_invalid_document(web_app: str) -> None:
    """End-to-end test attempting to upload an invalid/unsupported document via the REST API."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{web_app}/api/v1/jobs", files={"doc_src": ("test.pdf", b"INVALID")}
        )
        assert r.headers["content-type"] == "application/json"
        assert r.status_code == 422
        assert "unsupported document type" in r.json()["msg"]


async def test_request_invalid_sids(web_app: str) -> None:
    """End-to-end test attempting to fetch details or a download for
    an invalid job or session id via the REST API."""
    async with httpx.AsyncClient() as client:
        r_details = await client.get(f"{web_app}/api/v1/jobs/invalid")
        assert r_details.status_code == 404
        r_result = await client.get(f"{web_app}/api/v1/jobs/invalid/result")
        assert r_result.status_code == 404
        r_details = await client.get(f"{web_app}/api/v1/sessions/invalid")
        assert r_details.status_code == 404


async def test_clean_multiple_documents_with_session_workflow(
    web_app: str, sample_pdf: bytes
) -> None:
    """End-to-end test creating a session, then uploading multiple PDFs via the REST API
    into that session. Polling until success and downloading one of the results."""
    async with httpx.AsyncClient() as client:
        # Create session and receive sid
        create_session_resp = await client.post(f"{web_app}/api/v1/sessions")
        assert create_session_resp.status_code == 201  # Created
        assert create_session_resp.headers["content-type"] == "application/json"
        create_session_json = create_session_resp.json()
        sid = create_session_json["id"]
        session_url = f"{web_app}/api/v1/sessions/{sid}"
        assert create_session_resp.headers["location"] == session_url
        # Upload two documents
        upload1_resp = await client.post(
            f"{web_app}/api/v1/jobs?session={sid}",
            files={"doc_src": ("test.pdf", sample_pdf)},
        )
        assert upload1_resp.status_code == 201  # Created
        jid1 = upload1_resp.json()["id"]
        upload2_resp = await client.post(
            f"{web_app}/api/v1/jobs?session={sid}",
            files={"doc_src": ("test.pdf", sample_pdf)},
        )
        assert upload2_resp.status_code == 201  # Created
        jid2 = upload2_resp.json()["id"]
        # Poll session details until all jobs have been executed
        while True:
            session_data = (await client.get(session_url)).json()
            assert isinstance(session_data["created"], str)
            assert isinstance(session_data["updated"], str)
            assert session_data["jobs_total"] == len(session_data["jobs"]) == 2
            if session_data["jobs_finished"] == 2:
                break
            await asyncio.sleep(0.2)
        # Verify job data
        for job_data in session_data["jobs"]:
            assert job_data["id"] in {jid1, jid2}
            assert job_data["status"] == JobStatus.SUCCESS
            assert job_data["type"] == JobType.PDF
            assert isinstance(job_data["created"], str)
            assert isinstance(job_data["updated"], str)
        # Download one of the results
        dl_resp = await client.get(f"{web_app}/api/v1/jobs/{jid2}/result")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/octet-stream"
        assert "PDF" in dl_resp.text


async def test_upload_document_to_invalid_session(
    web_app: str, sample_pdf: bytes
) -> None:
    """End-to-end test attempting to upload a document with a nonexistent session id."""
    async with httpx.AsyncClient() as client:
        upload_resp = await client.post(
            f"{web_app}/api/v1/jobs?session=invalid",
            files={"doc_src": ("test.pdf", sample_pdf)},
        )
        assert upload_resp.status_code == 422
