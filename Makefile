BACKEND_PYTHON ?= backend/.venv/bin/python
BACKEND_MANAGE := $(BACKEND_PYTHON) backend/manage.py
COMPOSE_DEV := docker compose -f docker-compose.dev.yml
COMPOSE_PROD := docker compose -f docker-compose.prod.yml
COMPOSE_STAGING := docker compose -f docker-compose.staging.yml

.PHONY: help backend-setup backend-run backend-migrate frontend-setup frontend-run dev-up dev-up-d dev-down dev-logs dev-ps prod-up prod-down prod-logs prod-deploy-shared staging-up staging-down staging-logs staging-deploy-shared

help:
	@echo "Targets disponiveis:"
	@echo "  backend-setup     cria backend/.venv e instala dependencias"
	@echo "  backend-migrate   aplica migrations locais em config.settings.dev"
	@echo "  backend-run       sobe o backend local em http://localhost:8000"
	@echo "  backend-superadmin cria superadmin se nao existir"
	@echo "  frontend-setup    instala dependencias do frontend"
	@echo "  frontend-run      sobe o frontend local em http://localhost:3000"
	@echo "  dev-up            sobe stack Docker dev em foreground"
	@echo "  dev-up-d          sobe stack Docker dev em background"
	@echo "  dev-down          desce stack Docker dev"
	@echo "  dev-logs          segue logs da stack Docker dev"
	@echo "  dev-ps            mostra estado da stack Docker dev"
	@echo "  prod-up           sobe stack Docker prod"
	@echo "  prod-down         desce stack Docker prod"
	@echo "  prod-logs         segue logs da stack Docker prod"
	@echo "  prod-deploy-shared deploy prod atras do proxy shared_web"
	@echo "  staging-up        sobe stack Docker staging"
	@echo "  staging-down      desce stack Docker staging"
	@echo "  staging-logs      segue logs da stack Docker staging"
	@echo "  staging-deploy-shared deploy staging atras do proxy shared_web"

backend-setup:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

backend-migrate:
	$(BACKEND_MANAGE) migrate --settings=config.settings.dev

backend-superadmin:
	$(BACKEND_MANAGE) ensure_superadmin --settings=config.settings.dev

backend-run:
	cd backend && .venv/bin/python manage.py runserver 0.0.0.0:8000 --settings=config.settings.dev

frontend-setup:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 3000

dev-up:
	$(COMPOSE_DEV) up --build

dev-up-d:
	$(COMPOSE_DEV) up --build -d

dev-down:
	$(COMPOSE_DEV) down

dev-logs:
	$(COMPOSE_DEV) logs -f

dev-ps:
	$(COMPOSE_DEV) ps

prod-up:
	$(COMPOSE_PROD) up --build -d

prod-down:
	$(COMPOSE_PROD) down

prod-logs:
	$(COMPOSE_PROD) logs -f

prod-deploy-shared:
	./scripts/prod_deploy_shared.sh

staging-up:
	$(COMPOSE_STAGING) up --build -d

staging-down:
	$(COMPOSE_STAGING) down

staging-logs:
	$(COMPOSE_STAGING) logs -f

staging-deploy-shared:
	./scripts/staging_deploy_shared.sh
