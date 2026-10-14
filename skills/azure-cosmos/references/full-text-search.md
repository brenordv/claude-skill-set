# Azure Cosmos DB: Full-Text Search

Companion to `../SKILL.md`. Native BM25 full-text search in the NoSQL API: container policy,
index, and the query functions.

## Prerequisites

The query functions require enrollment in the Azure Cosmos DB NoSQL Full Text Search feature
(account Features pane), per the
[FULLTEXTCONTAINS](https://learn.microsoft.com/cosmos-db/query/fulltextcontains) and
[FULLTEXTSCORE](https://learn.microsoft.com/cosmos-db/query/fulltextscore) references. On the
container you define two things: a full-text policy and a full-text index. Queries run without
them but skip the inverted index, costing far more RUs.
([Full-text search](https://learn.microsoft.com/azure/cosmos-db/gen-ai/full-text-search))

### Full-Text Policy

Declare the `path` and `language` of every text property to search, using the language codes
exactly as the docs spell them (`en-US`):

```json
{
  "defaultLanguage": "en-US",
  "fullTextPaths": [
    { "path": "/text", "language": "en-US" }
  ]
}
```

Multi-language support (`de-DE`, `es-ES`, `fr-FR`, `it-IT`, `pt-PT`, `pt-BR`) is in early preview:
it needs enrollment in the "New features for full-text search" portal feature, may not be available
in all regions, and stopword removal currently works for English only.

### Full-Text Index

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{ "path": "/*" }],
  "excludedPaths": [{ "path": "/\"_etag\"/?" }],
  "fullTextIndexes": [
    { "path": "/text" }
  ]
}
```

## Query Functions

All take the property path first; search terms can be query parameters (the official hybrid-search
examples parameterize them as `@searchTerm`).

- `FullTextContains(c.text, @term)`: true when the term is present. Use in `WHERE`.
- `FullTextContainsAll(c.text, @t1, @t2)`: all terms present.
- `FullTextContainsAny(c.text, @t1, @t2)`: at least one term present.
- `FullTextScore(c.text, @t1, @t2)`: BM25 score. Usable only in `ORDER BY RANK` or as an `RRF`
  argument, never in `SELECT` or `WHERE`.

```sql
SELECT TOP 10 *
FROM c
WHERE FullTextContains(c.text, @keyword)
ORDER BY RANK FullTextScore(c.text, @keyword)
```

## Prefer FullTextContains over CONTAINS

`FullTextContains` uses the inverted index; `CONTAINS` scans. The
[FULLTEXTCONTAINS reference](https://learn.microsoft.com/cosmos-db/query/fulltextcontains)
measures the same keyword search at 3.11 RUs with `FULLTEXTCONTAINS` against 12,614 RUs with
`CONTAINS`. Note they match differently: full-text matching is tokenized, `CONTAINS` is a literal
substring. When you need literal substring semantics at low cost, prefilter with
`FullTextContains` and apply `CONTAINS` to the smaller candidate set:

```sql
SELECT *
FROM c
WHERE c.tenantId = @tenantId
  AND FullTextContains(c.text, @keyword)
  AND CONTAINS(c.text, @keyword)
```

## Hybrid Queries

Combine full-text predicates with selective indexed filters (partition key, equality, ranges) in
the same `WHERE`; predicate text order does not control execution. For fusing BM25 with vector
similarity through `RRF`, see `vector-search.md`. Full-text and hybrid queries can be RU-heavy;
check the request charge while tuning.
