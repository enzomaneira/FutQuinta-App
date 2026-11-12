# App Futebol (FutQuinta)

App interno dos organizadores do futebol de quinta: lista semanal, goleiros,
avulsos, coletes, mensalidades e caixa.

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, APScheduler (`backend/`)
- **Frontend:** React + Vite + Tailwind, PWA (`frontend/`)
- **Banco:** PostgreSQL (valores em centavos, datas em UTC)

As regras de negócio ficam em `backend/app/services/`, separadas das rotas,
para o bot de WhatsApp da Fase 2 reaproveitar.

## Pré-requisitos

- Python 3.12
- Node 22+
- Docker Desktop (para o Postgres local)

## Rodando localmente

```bash
cp .env.example .env          # depois troque o JWT_SECRET
docker compose up -d db       # sobe o Postgres (cria também o banco de teste)
```

Backend (em um terminal):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.cli create-organizer --email voce@exemplo.com --admin
uvicorn app.main:app --reload
```

Frontend (em outro terminal):

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 (repassa /api para a porta 8000)
```

Ou tudo junto em Docker, igual à produção: `docker compose up --build` e acesse
http://localhost:8000.

## Testes

```bash
cd backend
pytest
```

Usam o banco `futquinta_test` (variável `TEST_DATABASE_URL`). Cada teste roda
numa transação desfeita no final.

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "descricao"
alembic upgrade head
```

## Deploy no Railway

1. Crie um projeto com dois serviços: **postgres** (plugin do Railway) e **app**
   (este repositório; o `railway.toml` manda buildar pelo `Dockerfile`).
2. No serviço **app**, defina as variáveis:
   - `DATABASE_URL` = `${{postgres.DATABASE_URL}}`
   - `JWT_SECRET` = valor aleatório longo
   - `TZ` = `America/Sao_Paulo`
3. Mantenha **1 réplica** (o agendador roda dentro da API).
4. Depois do primeiro deploy, crie o organizador pelo shell do serviço:
   `python -m app.cli create-organizer --email voce@exemplo.com --admin`

As migrations rodam automaticamente a cada deploy (`alembic upgrade head`).

## Ícones do PWA

Gerados a partir de `frontend/public/logo.svg` com `npm run icons`.
