# RAG Pipeline

O RAG fornece evidência documental para uma decisão já calculada pelo motor de
regras. Ele não altera `decision`, `matched_rules`, `next_action` ou
`requires_human_review`.

## Extração e indexação

PDFs são extraídos por página, DOCX por headings de nível 1–2 e TXT por seções
numeradas detectáveis, como `2. FUNDOS ABERTOS`. O chunker respeita parágrafos e
sentenças e, quando um trecho ainda excede 700 caracteres, divide apenas entre
palavras. Não há overlap.

O upload envia a saída estruturada do extractor diretamente à indexação. Chunks
de documentos `DRAFT` ficam armazenados, mas somente documentos `ACTIVE`
participam do retrieval. Reprocessar substitui os chunks anteriores na mesma
ordem e preserva `page_number` e `section_title`. O seed usa o mesmo parser,
chunker e persistência da aplicação.

## Retrieval offline

O modo offline é lexical e determinístico. A tokenização aplica `casefold`,
normaliza acentos, ignora pontuação e stopwords portuguesas e mantém números e
identificadores relevantes. O ranking usa BM25 local com `k1 = 1.5` e
`b = 0.75`; o score exposto é limitado a `[0, 1)` por `score / (1 + score)`.

O relevance gate aceita somente chunks com BM25 positivo, portanto precisa
existir ao menos um token informativo compartilhado. Se não houver candidato, a
resposta contém `sources = []`. Duplicatas textuais normalizadas são removidas e
empates usam `document_id`, `chunk_index` e `chunk_id`, nessa ordem.

`MockAIProvider` não gera embeddings. O projeto não descreve hashes de texto
como busca semântica.

## Embeddings OpenAI opcionais

Quando `AI_PROVIDER=openai` está configurado, `text-embedding-3-small` fornece
um sinal adicional. O score híbrido usa 80% do BM25 normalizado e 20% da
similaridade de cosseno. Embeddings apenas reordenam candidatos que já passaram
pelo gate lexical; não introduzem uma fonte sem correspondência documental.

Falhas esperadas do serviço de embedding degradam para BM25. Exceções de
programação inesperadas não são escondidas.

## Query e fontes

A query combina a pergunta com nome, ticker e vocabulário neutro do tipo de
produto, por exemplo `ação/ações`, `fundo/fundos aberto/abertos` ou termos de
criptoativos. A decisão calculada não adiciona palavras como “permitido”,
“restrito” ou “pré-aprovação”.

Cada source da API contém documento, chunk, excerpt, score, `page_number` e
`section_title`. Hard restrictions e `ComplianceRule` continuam fontes
estruturadas em `matched_rules`; nenhum `DocumentChunk` artificial é criado para
representá-las.

## Limites

Os cálculos ocorrem em memória e os embeddings permanecem em JSONB. Isso atende
ao corpus pequeno da demonstração, mas não substitui um índice vetorial ou um
mecanismo distribuído para bases grandes. PDFs dependem de texto selecionável;
OCR não faz parte desta fase.
