SHELL := /bin/bash

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
RUFF := $(PYTHON) -m ruff
UVICORN := $(VENV)/bin/uvicorn

FRONTEND_DIR := ../frontend
# Must match STATIC_DIR in the environment file; app.main serves the SPA from here.
STATIC_ROOT := static
TLS_KEY := certs/server-key.pem
TLS_CERT := certs/server-cert.pem
# First non-loopback address, for the URL testers type and the certificate SAN.
LAN_IP = $(shell ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 127.0.0.1)

.PHONY: help install upgrade dev test lint format check clean py-compile \
        build-frontend tls-cert serve url

help:
	@echo "DUX Vault Backend Commands"
	@echo "  make install        Install dependencies from requirements.txt"
	@echo "  make upgrade        Upgrade pip in the project venv"
	@echo "  make dev            Run FastAPI in reload mode (API only, http)"
	@echo "  make test           Run pytest"
	@echo "  make lint           Run ruff check"
	@echo "  make format         Run ruff format"
	@echo "  make py-compile     Compile all Python files for syntax validation"
	@echo "  make check          Run compile + lint + test"
	@echo "  make clean          Remove python cache artifacts"
	@echo ""
	@echo "Serving the app to testers on one URL:"
	@echo "  make build-frontend Build the SPA into $(STATIC_ROOT)/"
	@echo "  make tls-cert       Generate a self-signed TLS certificate"
	@echo "  make serve          Run over https on all interfaces (no reload)"
	@echo "  make url            Print the URL to hand out"

install:
	$(PIP) install -r requirements.txt

upgrade:
	$(PIP) install --upgrade pip

# SESSION_COOKIE_SECURE is on in the env file because the app is served over https.
# This target is plain http, and a browser will not store a Secure cookie over http from
# anything but localhost - so signing in over the LAN address would appear to work and then
# drop the session on the next request. The env var overrides the file for this process only.
# Note --reload watches .py files, not .env: restart this by hand after a config change.
dev:
	SESSION_COOKIE_SECURE=false $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTEST) -q

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

py-compile:
	$(PYTHON) -m py_compile $$(find app scripts tests -name '*.py')

check: py-compile lint test

# The SPA is built with no VITE_BACKEND_URL, so client.ts falls back to same-origin and
# emits relative /api paths. That keeps the browser on one origin, which is what makes
# the session cookie and the document viewer work without any CORS configuration.
build-frontend:
	cd $(FRONTEND_DIR) && npm run build
	rm -rf $(STATIC_ROOT)
	mkdir -p $(STATIC_ROOT)
	cp -R $(FRONTEND_DIR)/dist/. $(STATIC_ROOT)/
	@echo "Built SPA into $(STATIC_ROOT)/"
	@grep -q 'localhost:8000' $(STATIC_ROOT)/assets/*.js \
	  && echo "WARNING: the bundle still references localhost:8000 - check VITE_BACKEND_URL" \
	  || echo "Verified: no absolute backend URL baked into the bundle."

# Self-signed, because testers type real Active Directory passwords into this app and
# plain http would put them on the wire in clear. Browsers will warn once per tester;
# an internal-CA certificate would avoid that, at the cost of an IT round-trip.
tls-cert:
	@mkdir -p certs
	openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
	  -keyout $(TLS_KEY) -out $(TLS_CERT) \
	  -subj "/CN=$(shell hostname)" \
	  -addext "subjectAltName=DNS:$(shell hostname),DNS:localhost,IP:127.0.0.1,IP:$(LAN_IP)"
	@chmod 600 $(TLS_KEY)
	@echo "Wrote $(TLS_CERT) and $(TLS_KEY)"

serve:
	@test -f $(STATIC_ROOT)/index.html || { echo "No $(STATIC_ROOT)/index.html - run 'make build-frontend' first."; exit 1; }
	@test -f $(TLS_CERT) || { echo "No $(TLS_CERT) - run 'make tls-cert' first."; exit 1; }
	@$(MAKE) --no-print-directory url
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 \
	  --ssl-keyfile $(TLS_KEY) --ssl-certfile $(TLS_CERT)

url:
	@echo "Hand testers: https://$(LAN_IP):8000/"

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
