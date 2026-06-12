# LinkedIn Post

---

Nos últimos meses trabalhei num projeto de portfólio que acabou virando algo mais estruturado do que eu esperava: o **Compliance Copilot**.

A ideia surgiu de uma pergunta simples que colaboradores de gestoras de ativos fazem com frequência: *"Posso fazer essa operação?"*

Parece trivial, mas na prática envolve consultar a política interna (geralmente um PDF extenso), verificar se o produto está em lista restrita, entender se precisa de pré-aprovação — e registrar tudo para auditoria.

---

**O que eu quis resolver:**

Construir uma ferramenta de compliance interna que responde a perguntas sobre operações financeiras de forma estruturada, rastreável e auditável.

**A decisão de design mais importante:**

A decisão de compliance nunca vem da IA. Existe um motor de regras determinístico que produz a decisão (PERMITIDO / RESTRITO / REQUER PRÉ-APROVAÇÃO / etc). A IA só redige a justificativa em linguagem natural. Se não há fonte documental suficiente, a resposta é INCONCLUSIVO — o sistema não chuta.

---

**O que aprendi construindo isso:**

- Como estruturar um pipeline RAG sem depender de infraestrutura externa (provider mock com embeddings por hash, fallback lexical)
- Como combinar motor de regras determinístico com LLM de forma que um não quebre o outro
- Como pensar em trilha de auditoria desde o início (muito mais difícil de adicionar depois)
- Como implementar os requisitos da LGPD de forma prática: exportação, anonimização, retenção
- Como um produto B2B enterprise difere de uma demo rápida: RBAC granular, empty states, tratamento de erro, confirmações antes de ações críticas

---

**Stack principal:**

Backend: FastAPI · Python 3.12 · SQLAlchemy 2 · PostgreSQL · Pydantic v2 · PyJWT · bcrypt
Frontend: Next.js 14 · TypeScript · Tailwind · TanStack Query · Recharts
Infra: Docker Compose · Alembic · pgvector-ready

---

**O que o projeto tem:**

✅ Motor de regras de compliance
✅ RAG com documentos de política (PDF, DOCX, TXT)
✅ Provider de IA mock (funciona 100% offline)
✅ Pré-aprovações com workflow e comentários
✅ Auditoria append-only
✅ Relatórios e dashboard
✅ LGPD — exportação, anonimização, retenção
✅ Treinamentos e onboarding
✅ RBAC com 4 perfis
✅ Testes automatizados
✅ Documentação técnica

Não é um produto de mercado — é um projeto de portfólio e aprendizado. Mas achei interessante por combinar engenharia backend sólida, design de produto e considerações práticas de conformidade.

O código está no GitHub: [link]

Se você trabalha com compliance, FinTech ou simplesmente gosta de arquitetura de sistemas — feedback é bem-vindo.

---

*As respostas do sistema apoiam a análise de compliance, mas não substituem revisão humana quando exigida pela política interna.*

#Python #FastAPI #NextJS #RAG #MachineLearning #Compliance #LGPD #PortfolioProject #SoftwareEngineering
