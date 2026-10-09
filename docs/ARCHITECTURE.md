# Architecture and implementation decisions

## Service boundaries

The browser and REST API share a process. `app.service` owns orchestration, `app.domain` owns domain-specific calculations, and `app.models` owns deterministic training. `app.rag` loads paragraph chunks from committed Markdown policies. Both REST and MCP call the same service so input validation and mandatory routing rules cannot diverge between interfaces.

The MCP transport is local stdio and uses the official v1 Python SDK. A host launches the server as a child process. There is no unauthenticated MCP HTTP listener. The REST service binds to loopback by default in local and Compose instructions. No queues, vector database, agents framework or Kubernetes deployment is claimed.

## Request lifecycle

1. Pydantic rejects unknown, missing, nonfinite, fractional-count or out-of-range inputs. Domain validation catches inconsistent combinations.
2. The cache identity includes canonical request JSON, provider/model, source and training-data hash, and policy corpus hash.
3. A trained model supplies an illustrative score or forecast; explicit domain rules establish the minimum review action.
4. Lexical TF-IDF retrieval ranks paragraphs, drops zero-similarity matches, deduplicates text and packs whole chunks within a byte budget. Chunk IDs identify the source filename and paragraph position; SHA-256 verifies content.
5. The provider returns a Pydantic object. Live citations must be present and must reference selected evidence. The final action is the higher priority of the rule minimum and the model proposal. Citation membership does not prove that prose is entailed; human review remains necessary.
6. SQLite stores a cached result and a new audit row. Each cache hit receives its own run ID and zero current-request token usage. Original generation usage remains visible separately.

## Tradeoffs

TF-IDF is interpretable and needs no external embeddings, but has limited semantic recall. The tiny corpus and hand-written retrieval checks are integration fixtures, not an unbiased RAG benchmark. SQLite is suitable for a local single-instance prototype; it is not a multi-tenant database or tamper-proof audit store. Cache rows expire after one hour and expired entries are cleaned on writes. Audit rows require an explicit retention plan in a real deployment.

ML training is inexpensive for 800 records and cached once per process. Multiple workers train separate copies. A production model registry, frozen artifacts, metadata lineage and deployment validation would be follow-on work. RAG source changes require process restart, which also reloads model/source versions.

## LLM behavior

Demo responses are deterministic templates. Live mode sends a structured prompt to the OpenAI Responses API, validates the output, restricts cited IDs and preserves the minimum action. Retrieved text and the analyst question are treated as data, not instructions. These measures reduce risk but do not guarantee factual prose. There is no autonomous execution channel or external side-effect tool. Provider exceptions are returned as a generic 503; invalid structured decisions return a validation error rather than silently falling back to demo mode.

## Cost and observability

The response includes generation usage, current-request usage, cache hit, elapsed service time, evidence IDs, code/corpus versions and the prompt-unit reduction. No dollar savings are asserted. Full provider prompts are not logged. An API retry may consume additional provider work not reflected in a successful response's usage; use the provider billing console for authoritative spend. Add aggregated metrics, structured error logging, tracing, request-size limits and tenant quotas before shared production use.
