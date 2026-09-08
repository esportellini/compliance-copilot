# Compliance Copilot

> Plataforma interna de compliance para gestores de ativos e family offices — motor de regras determinístico, RAG sobre documentos de política, trilha de auditoria e fluxo de pré-aprovação.

⚠️ **Projeto educacional / portfólio.** Não é um produto de mercado. As respostas do sistema apoiam a análise de compliance, mas não substituem revisão humana quando exigida pela política interna.

---

## Problema

Colaboradores de gestoras de ativos precisam constantemente responder: *"Posso fazer essa operação?"*

Isso envolve:
- Consultar a política interna (PDF extenso, frequentemente desatualizado)
- Verificar listas restritas
- Entender se precisa de pré-aprovação
- Registrar tudo para auditoria regulatória

O processo é lento, inconsistente e propenso a erros.

## Solução

O Compliance Copilot é uma ferramenta interna que:

1. Aceita perguntas em linguagem natural sobre operações financeiras
2. Roda um **motor de regras determinístico** — a decisão é sempre estruturada
3. Recupera trechos de documentos de política via **RAG**
4. Usa IA apenas para redigir a justificativa em linguagem natural
5. Registra tudo em trilha de auditoria imutável

**Rules decide. Retrieval provides evidence. AI explains.** Sem regra aplicável,
o resultado é `INCONCLUSIVE`; a presença ou ausência de evidência RAG não altera
uma decisão estruturada.

---

## Funcionalidades

| Módulo | Funcionalidades |
|--------|----------------|
| **Copilot** | Consultas em linguagem natural, decisão estruturada, fontes citadas |
| **Motor de regras** | Regras configuráveis por tipo de produto, prioridade e condições |
| **RAG** | Upload PDF/DOCX/TXT, chunking estruturado, BM25 offline e sinal semântico opcional |
| **Pré-aprovações** | Fluxo de solicitação, análise, aprovação/rejeição com comentários |
| **Auditoria** | Log append-only de todos os eventos, filtros, export CSV |
| **Relatórios** | Dashboard, gráficos por decisão/risco, top produtos e regras |
| **LGPD** | Exportação de dados, anonimização, política de retenção |
| **Treinamentos** | Conteúdos de onboarding com checklist de aceite |
| **Configurações** | Retenção de logs, único controle dinâmico com consumidor nesta versão |
| **RBAC** | 4 perfis: Admin, Compliance, Colaborador, Auditor |

---

## Stack

**Backend**
- Python 3.12 · FastAPI 0.115 · Pydantic v2
- SQLAlchemy 2.0 · Alembic · PostgreSQL 16
- PyJWT · bcrypt · psycopg (v3)
- pypdf · python-docx (extração de texto)

**Frontend**
- Next.js 14 · TypeScript · Tailwind CSS
- TanStack Query · React Hook Form · Zod
- Recharts · lucide-react

**Infra**
- Docker Compose
- pgvector-ready (embeddings em JSONB, swap documentado)

---

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                  Next.js Frontend                    │
│  Login · Dashboard · Copilot · History · Products   │
│  Documents · Rules · Pre-approvals · Audit · Reports │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP/JSON
┌─────────────────────▼───────────────────────────────┐
│                  FastAPI Backend                     │
│                                                      │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Rules Engine│  │   RAG    │  │  AI Provider   │  │
│  │ (pure, det.)│  │(chunking │  │ mock / OpenAI  │  │
│  └──────┬──────┘  │+retrieval│  └───────┬────────┘  │
│         │         └────┬─────┘          │            │
│         └──────────────┼────────────────┘            │
│                    Copilot Service                    │
│               (orchestrates all three)               │
└─────────────────────┬───────────────────────────────┘
                      │ psycopg
┌─────────────────────▼───────────────────────────────┐
│              PostgreSQL 16                           │
│  users · products · rules · documents · chunks      │
│  copilot_queries · pre_approvals · audit_logs       │
└─────────────────────────────────────────────────────┘
```

---

## Rodar localmente

### Pré-requisitos

- Docker Desktop instalado e rodando

### 1. Clonar e configurar

```bash
git clone https://github.com/seu-usuario/compliance-copilot.git
cd compliance-copilot
copy .env.example .env        # Windows
# cp .env.example .env        # Mac/Linux
```

### 2. Subir os serviços

```bash
docker compose up --build
```

Aguarde até aparecer:
```
backend | INFO:     Application startup complete.
frontend | ✓ Ready in 59ms
```

### 3. Popular com dados de demonstração

```bash
docker compose exec backend python -m app.seed
```

### 4. Acessar

- **Frontend:** http://localhost:3000
- **API (Swagger):** http://localhost:8000/docs

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATABASE_URL` | `postgresql+psycopg://...` | String de conexão PostgreSQL |
| `SECRET_KEY` | ⚠️ Alterar | Chave JWT — gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `AI_PROVIDER` | `mock` | `mock` (offline) ou `openai` |
| `OPENAI_API_KEY` | vazio | Necessário se `AI_PROVIDER=openai` |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens CORS permitidas |
| `ENVIRONMENT` | `local` | `local` / `staging` / `production` |

---

## Usuários demo

Senha de todos: **Compliance123!**

| E-mail | Papel | Acesso |
|--------|-------|--------|
| `admin@demo.local` | Administrador | Total |
| `compliance@demo.local` | Compliance | Regras, documentos, pré-aprovações |
| `colaborador@demo.local` | Colaborador | Copilot, histórico próprio |
| `auditor@demo.local` | Auditor | Leitura de tudo |

---

## Comandos úteis

```bash
# Subir
docker compose up

# Parar
docker compose down

# Rebuildar após mudanças
docker compose up --build

# Rodar seed (primeira vez)
docker compose exec backend python -m app.seed

# Reiniciar só o backend
docker compose restart backend

# Ver logs
docker compose logs -f backend

# Rodar testes
docker compose exec backend pytest app/tests/ -v

# Gerar migração Alembic
docker compose exec backend alembic revision --autogenerate -m "description"

# Aplicar migrações
docker compose exec backend alembic upgrade head
```

> A migration `0001_initial` foi substituída pelo schema atual porque este
> projeto de portfólio não possui migrations publicadas nem bases reais que
> dependam do rascunho anterior. Em sistemas já publicados, migrations iniciais
> não devem ser reescritas; a evolução deve ocorrer por novas migrations.

---

## Fluxos principais

### Fluxo do Copilot

```
1. Usuário envia pergunta (+ produto/tipo/valor opcionais)
2. Resolução do produto por ID, ticker exato ou nome exato normalizado
3. Hard restriction do produto concreto → RESTRITO, mesmo com pergunta fora do escopo
4. Sem hard restriction, detecção de fora-de-escopo
5. ID inexistente ou resolução ambígua → INCONCLUSIVO, sem fallback por tipo
6. Motor de regras → decisão AUTORITATIVA
7. RAG → evidências relevantes de documentos ativos
8. AI Provider → justificativa da decisão estruturada, com fallback seguro
9. Persistência: query + answer + produto resolvido + sources + audit log
10. Resposta estruturada ao frontend
```

### Fluxo do Motor de Regras

```
1. Lista restrita? → RESTRITO (terminal)
2. Produto BLOCKED/RESTRICTED? → RESTRITO (terminal)
3. Filtra regras configuradas aplicáveis ao contexto
4. Menor priority vence; regras de prioridades inferiores são ignoradas
5. Decisões diferentes na prioridade vencedora → INCONCLUSIVO
6. Nenhuma regra aplicável? → INCONCLUSIVO (nunca chuta)
```

`requires_human_review` significa que a operação aguarda uma decisão humana. É
verdadeiro somente para `PRE_APPROVAL_REQUIRED` e `INCONCLUSIVE`. Uma decisão
`RESTRICTED` é terminal: a operação não deve ser executada nem encaminhada como
pedido normal de liberação.

### Cenários da demonstração

| Cenário | Decisão |
|---------|---------|
| Fundo aberto até R$ 100.000 | `ALLOWED` |
| Fundo aberto acima de R$ 100.000 | `REPORT_REQUIRED` |
| Ação normal | `PRE_APPROVAL_REQUIRED` |
| Ação ACME3 na lista restrita | `RESTRICTED` por `restricted_list` |
| Criptoativo | `RESTRICTED` |
| Produto sem regra aplicável | `INCONCLUSIVE` |

### Fluxo de Pré-aprovação

```
Consulta vinculada → reutiliza a análise persistida, sem recalcular o Copilot
→ PENDING → IN_REVIEW → APROVADO / REPROVADO / APROVADO COM RESSALVAS
→ comentários, timestamps e decisões aparecem na timeline e no AuditLog
```

Solicitações também podem ser criadas sem consulta de origem; nesse caso, o
Copilot executa uma análise inicial nova. O vínculo opcional com a consulta e
os snapshots da decisão, resposta e produto preservam a rastreabilidade.

## Demo flow

1. Entre como `colaborador@demo.local` com a senha `Compliance123!`.
2. No Copilot, pergunte sobre `XPTO3` e abra a pré-aprovação gerada.
3. Selecione o tipo de operação, envie a solicitação e abra seu detalhe.
4. Entre como `compliance@demo.local`, inicie a revisão, comente e registre a decisão com parecer.
5. Volte ao colaborador para consultar a decisão, as condições e a timeline.
6. Entre como `auditor@demo.local` para inspecionar a solicitação e a trilha de auditoria em modo somente leitura.

---

## LGPD e Segurança

- **Dados mínimos**: sem IP, localização, biometria ou dados de saúde
- **Senhas**: bcrypt com salt, nunca armazenadas em texto claro
- **JWT**: expira em 8h por padrão, configurável
- **Auditoria**: append-only, eventos críticos nunca removidos por retenção
- **Anonimização**: substitui campos pessoais sem excluir registros regulatórios
- **Exportação**: titular pode solicitar todos os seus dados (Art. 18 LGPD)
- **Segredos**: 100% de variáveis de ambiente, nada hardcoded no código

---

## Testes

```bash
docker compose exec backend pytest app/tests/ -v
```

Cobertos: auth, JWT, RBAC por papel, motor de regras (10+ casos), Copilot (invariantes de decisão), pré-aprovações, privacidade/LGPD.

---

## Limitações conhecidas

- Embeddings em JSONB (não pgvector) — adequado para desenvolvimento, não para produção em escala
- Sem notificações por e-mail para pré-aprovações
- Rate limiting não implementado (redis necessário para produção)
- Extração de PDF depende de qualidade do texto selecionável (sem OCR)
- Retrieval offline é lexical/BM25 e determinístico; o mock não produz embeddings
- Embeddings OpenAI, quando configurados, apenas refinam candidatos lexicalmente relevantes

---

## Roadmap

Ver [docs/ROADMAP.md](docs/ROADMAP.md) para v1.1, v1.2 e v2.0.

---

## Documentação técnica

| Documento | Conteúdo |
|-----------|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Estrutura do projeto e fluxo de dados |
| [RULE_ENGINE.md](docs/RULE_ENGINE.md) | Motor de regras — ordem de avaliação e invariantes |
| [RAG_PIPELINE.md](docs/RAG_PIPELINE.md) | Pipeline RAG — extração, chunking, embeddings, busca |
| [SECURITY.md](docs/SECURITY.md) | Autenticação, RBAC, checklist de produção |
| [LGPD_AND_PRIVACY.md](docs/LGPD_AND_PRIVACY.md) | Bases legais, direitos do titular, retenção |
| [API_OVERVIEW.md](docs/API_OVERVIEW.md) | Todos os endpoints documentados |
| [PRODUCT_CASE.md](docs/PRODUCT_CASE.md) | Problema, solução e decisões de design |
| [ROADMAP.md](docs/ROADMAP.md) | Próximas versões |
| [COMMIT_PLAN.md](docs/COMMIT_PLAN.md) | Histórico sugerido de commits |

---

## Aviso

Este projeto foi construído para fins educacionais e de portfólio. Não deve ser usado em produção sem revisão de segurança, adequação jurídica e validação por profissionais de compliance. As regras configuradas no seed são fictícias e não representam nenhuma política real.

