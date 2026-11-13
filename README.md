# App Futebol (FutQuinta)

App interno dos organizadores do futebol de quinta: lista semanal, goleiros,
avulsos, coletes, mensalidades e caixa.

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, APScheduler (`backend/`)
- **Frontend:** React + Vite + Tailwind, PWA (`frontend/`)
- **Banco:** PostgreSQL (valores em centavos, datas em UTC)

As regras de negócio ficam em `backend/app/services/`, separadas das rotas,
para o bot de WhatsApp da Fase 2 reaproveitar.

## Como funciona

**Lista semanal**
- Vagas por posição (padrão 2 goleiros + 15 de linha). Vaga de goleiro só para
  goleiro; de linha só para linha. O app avisa quando falta goleiro.
- Mensalistas entram como pendentes e seguram a vaga até o prazo de confirmação.
  Quem desmarca libera a vaga na hora; desmarcar a partir do horário de
  "em cima da hora" (padrão quinta 18h) fica registrado.
- Avulsos entram numa fila por ordem de candidatura e são chamados quando há
  vaga. Avulso confirmado gera cobrança de R$ 25; se não for, fica isento.

**Rotina automática** (a cada minuto, idempotente, horários lidos das Configurações)
| Quando (padrão) | O que faz |
|---|---|
| Terça 10h | Cria o jogo de quinta e abre a lista com os mensalistas pendentes (só até o prazo de confirmação) |
| Quinta 12h | Pendentes perdem a vaga garantida; a vaga vai para os avulsos |
| Após o jogo (23h) | Confirmados viram "compareceu"; o organizador corrige as faltas |
| Dia 1 | Gera as mensalidades (R$ 59, vencimento dia 15) e lança o aluguel da quadra |
| Diariamente | Cobranças vencidas e não pagas viram "atrasadas" (mensalidade: dia 16) |

Se o servidor ficar fora do ar, a rotina recupera o atraso quando volta.

**Caixa** = saldo inicial + tudo recebido − despesas. Estatísticas do perfil e o
caixa são sempre calculados a partir dos registros (sem contadores duplicados).

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

```bash
cd frontend
npm test
```

O backend usa o banco `futquinta_test` (variável `TEST_DATABASE_URL`); cada
teste roda numa transação desfeita no final. O GitHub Actions
(`.github/workflows/ci.yml`) roda backend e frontend a cada push na `main`.

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
