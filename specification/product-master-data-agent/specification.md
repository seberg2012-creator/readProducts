# Specification: product-master-data-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` as the primary inputs for this agent.
- [x] Bootstrap agent code in `assets/product-master-data-agent/` using instructions from the `sap-agent-bootstrap` skill. Invoke from inside `assets/product-master-data-agent/`, using copy commands — do NOT create files manually.
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`.

---

## Runtime Skills

Based on the PRD, no complex multi-step workflow or domain-specific knowledge base is required. The agent's task is a direct natural language query → API call → formatted response flow. No runtime skills are needed.

---

## Project-Specific Tasks

### Agent Identity & System Prompt

- [x] Set agent name: `Product Master Data Agent`
- [x] Set agent description: `Answers natural language questions about product descriptions, specifications, and classifications from SAP S/4HANA Cloud Public Edition`
- [x] Write system prompt in `app/agent.py` (`get_system_prompt`) with the following instructions:
  - You are a Product Master Data assistant for Sales Representatives. You help them quickly find product descriptions, specifications, and classification information from SAP S/4HANA.
  - IMPORTANT: You MUST use tools to retrieve live data. Never fabricate, guess, or invent product information. Relay tool errors verbatim without adding suggestions.
  - When a user asks about a product, use the available MCP tools to search for and retrieve product master data.
  - When calling tools that support pagination, always set the page size parameter (`$top`, `top`, `limit`, etc.) to a maximum of 100 items to prevent context overflow. Inform the user when this limit is applied.
  - When a query matches multiple products, always list the candidates and ask the user to confirm which product they mean before returning detailed information.
  - When no product is found, inform the user clearly that the product could not be found and suggest trying with a different product ID or name.
  - Format all product information in clear, readable plain language. Do not expose raw field names or technical S/4HANA codes to the user unless specifically requested.
  - If a tool returns an error, report the error message exactly as received. Do not suggest workarounds unless asked.
  - Only retrieve product data — never create, update, or delete any data.

### Natural Language Product Query (R1)

- [x] Implement handling for natural language questions about a product by name or product ID using the `get_product_master` MCP tool (from `API_PRODUCT_SRV`).
- [x] Support queries like: "Tell me about product [name/ID]", "What is [product]?", "Give me the description of [product]".
- [x] Return product description, base unit of measure, product type, and key attributes in a readable format.
- [x] Ensure response is delivered within 30 seconds end-to-end.

### Product Classification Query (R2)

- [x] Implement handling for classification and category queries using the `get_product_classification` MCP tool (from `API_CLFN_PRODUCT_SRV`).
- [x] Support queries like: "What category does [product] belong to?", "What is the classification of [product]?".
- [x] Return classification hierarchy and class assignments in readable plain language.

### Disambiguation for Ambiguous Queries (R3)

- [x] Implement a disambiguation flow: when a query matches multiple products, list them as candidates and prompt the user to select one before returning full details.
- [x] Implement a not-found flow: when a query returns no results, inform the user clearly with a helpful message (e.g., suggest retrying with a product ID if a name was used).
- [x] The agent must never guess or return data for the wrong product.

### SAP Joule Integration (R4)

- [x] Ensure A2A protocol compliance: `/.well-known/agent.json` endpoint is available and correct.
- [x] Streaming responses via A2A `stream()` method are properly implemented.

### Read-Only Enforcement (R5)

- [x] Confirm that only read (GET) MCP tool calls are used — no create, update, or delete operations are invoked.
- [x] Document in system prompt that the agent is read-only.

---

## API Integration

### API Specs Downloaded

| API Name | ORD ID | Spec File | Type |
|----------|--------|-----------|------|
| Product Master (A2X) | `sap.s4:apiResource:API_PRODUCT_SRV:v1` | `specification/product-master-data-agent/api-specs/API_PRODUCT_SRV.edmx` | OData (EDMX) |
| Product Master Data Including Classification – Read | `sap.s4:apiResource:API_CLFN_PRODUCT_SRV:v1` | `specification/product-master-data-agent/api-specs/API_CLFN_PRODUCT_SRV.json` | REST (OpenAPI JSON) |

### MCP Tool Scope

```
MCP API: sap.s4:apiResource:API_PRODUCT_SRV:v1
MCP tool scope: read-only
Resources in scope: A_Product, A_ProductDescription, A_ProductBasicText, A_ProductPlant
```

```
MCP API: sap.s4:apiResource:API_CLFN_PRODUCT_SRV:v1
MCP tool scope: read-only
Resources in scope: all
```

---

## Business Instrumentation

- [x] Implement the following milestones from the PRD with structured logging (`[MILESTONE_ID].[achieved|missed]: [description]`) and OpenTelemetry spans. Extract all business logic from `stream()` into a plain async helper `_run_agent()` to avoid `GeneratorExit` context errors — instrument `_run_agent()` instead.

  | ID | Milestone | Achieved when | Log on achievement | Log on miss |
  |----|-----------|---------------|-------------------|-------------|
  | M1 | Query Received | Agent interprets user intent as a product data request | `M1.achieved: product query received and intent classified successfully` | `M1.missed: query intent could not be classified as a product data request` |
  | M2 | Data Retrieved | At least one product record returned from S/4HANA OData API | `M2.achieved: product data retrieved from S/4HANA successfully` | `M2.missed: S/4HANA API call returned no data or an error` |
  | M3 | Answer Delivered | Formatted response produced and delivered to user | `M3.achieved: product answer delivered to user in Joule` | `M3.missed: agent failed to produce or deliver a formatted response` |
  | M4 | Ambiguity Handled | User guided through disambiguation to a specific product | `M4.achieved: ambiguous query resolved through user-guided disambiguation` | `M4.missed: disambiguation step was skipped or failed, potentially returning incorrect data` |
  | M5 | Production Ready | Agent passes end-to-end tests and Joule validation | `M5.achieved: agent deployed and validated in production Joule environment` | `M5.missed: agent deployment or Joule integration validation failed` |

- [x] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`.

---

## MCP Tool Integration

- [x] Verify `specification/product-master-data-agent/api-specs/` contains both spec files before proceeding.
- [x] Invoke `mcp-translation-file` skill for each API spec:
  - `API_PRODUCT_SRV.edmx` → generate MCP translation file (EDMX, OData)
  - `API_CLFN_PRODUCT_SRV.json` → generate MCP translation file (OpenAPI JSON, REST)
- [x] Invoke `setup-solution` skill to create and register MCP server assets for both translation files.
- [x] Read the generated `asset.yaml` for each MCP server asset and copy the exact `ordId` value — NEVER invent or guess ORD IDs.
- [x] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from the `mcp_tools` module — never import directly from `sap_cloud_sdk.agentgateway`.
- [x] Add both MCP server dependencies to the agent's `asset.yaml` under `requires` using the exact ORD IDs from the generated assets.
- [x] After `mcp-translation-file` and `setup-solution` complete, generate `mcp-mock.json` using the `mcp-mock-config` skill.

---

## Testing

- [x] `conftest.py` only sets `IBD_TESTING=true`.
- [x] Write unit tests in `assets/product-master-data-agent/tests/` — exactly one per MCP tool, run each immediately after writing:
  - `test_get_product_master.py` — test product description and basic data retrieval
  - `test_get_product_classification.py` — test classification and category retrieval
- [x] Write one integration test `test_agent_integration.py` executing the end-to-end flow (mocked LLM + mocked MCP tools, runs offline).
- [x] Run `pytest` from `assets/product-master-data-agent/` (no args) — fix failures immediately.
- [x] If coverage < 70%, add targeted tests until threshold met.
- [x] Run `pytest` again from `assets/product-master-data-agent/` (no args) to generate final `test_report.json`.
- [x] Verify `test_report.json` exists in `assets/product-master-data-agent/`.
