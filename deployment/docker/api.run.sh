#!/usr/bin/env sh
echo "Serving web application at ${DOCLEANER_URL}"
uvicorn --host 0.0.0.0 --port 8080 docleaner.api.entrypoints.web.main:app
