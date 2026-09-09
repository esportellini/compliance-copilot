# Rule Engine

## Responsabilidade

O motor de regras é a única camada que produz decisões de compliance. O RAG
recupera evidências documentais e a IA redige a explicação, mas nenhuma dessas
camadas pode escolher, relaxar ou substituir a decisão estruturada.

**Rules decide. Retrieval provides evidence. AI explains.** Uma regra
estruturada é evidência normativa suficiente para a decisão. Ausência de chunks
RAG não rebaixa uma decisão coberta por regra, e chunks recuperados não criam
uma decisão quando nenhuma regra é aplicável.

## Resolução do produto

- `product_id` é autoritativo. Se foi informado e não existe, o resultado é
  `INCONCLUSIVE`, sem fallback para tipo ou nome enviados pelo cliente.
- Identifier/ticker e nome usam correspondência exata após normalização; não há
  busca por substring no fluxo decisório.
- Identifiers são persistidos em forma canônica, com trim e caixa alta. Índices
  únicos sobre `upper(trim(identifier))` impedem variantes semanticamente iguais.
- Múltiplos nomes exatos normalizados são tratados como ambíguos e resultam em
  `INCONCLUSIVE`.
- O ID do produto efetivamente resolvido é persistido com a consulta.
- Hard restrictions de um produto concreto são verificadas antes do gate de
  fora de escopo. Uma pergunta ruim não neutraliza uma restrição objetiva.

## Ordem de avaliação

```text
1. Hard restrictions
   ├── identifier/ticker do produto consta na restricted list ativa
   └── status do produto é BLOCKED ou RESTRICTED
       Resultado: RESTRICTED terminal

2. Versões de regras elegíveis
   ├── status ACTIVE
   ├── effective_from <= instante da avaliação
   ├── effective_to ausente ou posterior ao instante da avaliação
   ├── filtrar por product_type e condições
   ├── encontrar o menor valor de priority aplicável
   ├── ignorar todas as prioridades numericamente maiores
   ├── decisões diferentes na prioridade vencedora → INCONCLUSIVE
   └── decisões iguais na prioridade vencedora → aplicar essa decisão

3. Nenhuma regra aplicável
   └── INCONCLUSIVE + decisão humana necessária
```

## Semântica de `priority`

Um número menor representa precedência maior. Se regras de prioridades 5, 10 e
20 forem aplicáveis, somente as regras de prioridade 5 participam da decisão.
Se uma regra de prioridade 5 resultar em `ALLOWED`, uma regra de prioridade 10
com resultado `RESTRICTED` não influencia essa avaliação.

Quando duas ou mais regras da prioridade vencedora têm decisões diferentes, a
política está em conflito e o resultado é `INCONCLUSIVE`. Regras da mesma
prioridade com a mesma decisão são compatíveis. Os nomes das regras aplicadas
são ordenados para que a resposta não dependa da ordem retornada pelo banco.

## Condições suportadas

```json
{ "amount_gt": 100000 }
{ "amount_gte": 50000 }
{ "status": "MONITORED" }
{ "product_type": "STOCK" }
{}
```

Uma regra só é aplicável quando todas as suas condições são satisfeitas.
Somente `status`, `product_type`, `amount_gt` e `amount_gte` são aceitas. A API
rejeita chaves e tipos desconhecidos; o motor também trata uma condição inválida
como não aplicável, preservando o comportamento fail closed.

## Revisão humana e próxima ação

`requires_human_review` significa especificamente que a operação aguarda uma
decisão humana antes de prosseguir.

| Decisão | `requires_human_review` | Conduta |
|---------|-------------------------|---------|
| `ALLOWED` | `false` | Pode prosseguir |
| `REPORT_REQUIRED` | `false` | Registrar conforme a política |
| `PRE_APPROVAL_REQUIRED` | `true` | Aguardar pré-aprovação |
| `RESTRICTED` | `false` | Não executar; decisão terminal |
| `INCONCLUSIVE` | `true` | Aguardar análise do compliance |

## Invariantes

- Hard restrictions são avaliadas antes das regras configuradas.
- `RESTRICTED` por lista ou status não pode ser relaxado por regra, RAG ou IA.
- Não existem decisões padrão hardcoded por tipo de produto.
- Ausência de regra aplicável resulta em `INCONCLUSIVE`.
- A restricted list compara o `identifier` real do produto resolvido, sem usar
  `product_type` como aproximação.
- A orientação operacional de `next_action` é determinística. Se uma explicação
  gerada contiver contradição operacional óbvia, ela é substituída por uma
  explicação determinística segura sem alterar a decisão.

## Versionamento e proveniência

O versionamento acontece antes do motor. Cada regra lógica usa um `rule_key`
estável e versões `DRAFT`, `ACTIVE` ou `ARCHIVED`. DRAFT pode ser corrigida em
seu próprio registro; editar uma versão publicada cria uma nova versão e preserva
a anterior. Apenas versões ACTIVE e efetivas são convertidas em `RuleSpec`.

O motor puro continua sem conhecer banco, lifecycle ou datas e sua precedência
permanece idêntica. Ao persistir a resposta, o serviço grava um snapshot
estruturado das regras vencedoras com ID, chave, versão, nome, prioridade,
decisão e condição. O histórico lê esse snapshot; nunca tenta inferi-lo da versão
atual da regra.
