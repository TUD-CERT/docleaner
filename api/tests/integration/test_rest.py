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
        # Upload document via HTTP POST
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
        assert r.status_code == 400
        assert "unsupported document type" in r.json()["msg"]


async def test_request_invalid_job_details(web_app: str) -> None:
    """End-to-end test attempting to fetch details or a download for an invalid job id via the REST API."""
    async with httpx.AsyncClient() as client:
        r_details = await client.get(f"{web_app}/api/v1/jobs/invalid")
        assert r_details.status_code == 404
        r_result = await client.get(f"{web_app}/api/v1/jobs/invalid/result")
        assert r_result.status_code == 404
