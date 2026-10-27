# Product Master Data AI Agent for Sales Representatives

SAP S/4HANA Product Master Data Natural Language Query Agent

## Business challenge

Sales Representatives spend too long navigating SAP S/4HANA screens to find product master data details (descriptions, specifications, classifications). They need an instant, conversational interface embedded in SAP Joule that allows them to ask natural language questions and receive accurate answers without technical S/4HANA knowledge.

## Business Goals & Success Criteria

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Time to look up product master data per Sales Rep | 5 minutes | Under 30 seconds | Within 1 month | Product Master Data Query | user |

## Key Milestones

1. **Query Received**: Agent receives and understands a natural language product question from a Sales Rep via SAP Joule.
2. **Data Retrieved**: Agent calls S/4HANA Product Master OData APIs (API_PRODUCT_SRV, API_CLFN_PRODUCT_SRV) and retrieves relevant product descriptions and specifications.
3. **Answer Delivered**: Agent returns a clear, structured, human-readable answer within SAP Joule.
4. **Ambiguity Handled**: Agent gracefully handles partial or ambiguous product names by asking clarifying questions or listing candidates.
5. **Production Ready**: Agent is deployed, tested, and accessible to Sales Representatives via SAP Joule.

## Business Architecture (RBA)

### End-to-End Process

Lead to Cash Standard B2B

### Process Hierarchy

```
Lead to Cash Standard B2B (E2E)
└── Plan to Optimize Marketing and Sales (Phase)
    └── Plan prices and promotions (BPS-359_002)
        └── Plan and define sales prices
        └── Access product master data for sales quoting
```

### Summary

The challenge maps to the Lead to Cash Standard B2B E2E, specifically the "Plan Prices and Promotions" sub-process, where Sales Reps need rapid access to product master data (descriptions, specs, classification) to support customer conversations and quoting activities.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Webhook API ORD ID | Data Product ORD ID | Gap? | Notes / assumptions |
|------------------------|-------------------------|------------|-------------------|--------------------|--------------------|---------------------|------|---------------------|
| Query product descriptions & basic data | SAP S/4HANA Cloud Public Edition | `sap.s4:apiResource:API_PRODUCT_SRV:v1` | — | — | — | — | No | OData API available; custom MCP translation file needed |
| Query product classification & categories | SAP S/4HANA Cloud Public Edition | `sap.s4:apiResource:API_CLFN_PRODUCT_SRV:v1` | — | — | — | — | No | OData API available; custom MCP translation file needed |
| Product availability info | SAP S/4HANA Cloud Public Edition | `sap.s4:apiResource:CE_API_PRODUCT_AVAILY_INFO_0001:v1` | — | — | — | — | Maybe | Available but out of initial scope (descriptions & specs focus) |
| Natural language query interface for Sales Reps | — | — | — | — | — | — | Yes | Requires custom AI Agent — no standard SAP product covers NLQ over product master data |
| Integration via SAP Joule | SAP Joule (A2A protocol) | — | — | — | — | — | No | Agent deployed as Joule extension via A2A |

### Key findings

- SAP S/4HANA Cloud Public Edition provides the required product master data via standard OData APIs (API_PRODUCT_SRV, API_CLFN_PRODUCT_SRV).
- No pre-built MCP servers exist for these APIs; custom MCP translation files must be generated from the EDMX/OpenAPI specs.
- The natural language query capability is a gap that is best filled by a custom Python AI agent (A2A protocol).
- The agent will be surfaced to Sales Reps through SAP Joule, requiring A2A protocol compliance.
- Availability and pricing APIs are available but are out of scope for the initial release (focus: descriptions & specifications).
- No external webhooks or n8n workflows are required.

## Recommendations

### Product Master Data AI Agent for SAP Joule

#### Executive Summary

Python A2A agent with MCP tools over S/4HANA product master OData APIs

#### Recommended Solution

Build a Python-based AI agent following the A2A protocol, deployed as an SAP Joule extension. The agent exposes MCP tools backed by SAP S/4HANA Cloud Public Edition OData APIs (API_PRODUCT_SRV for product master data and API_CLFN_PRODUCT_SRV for classification data). Sales Representatives ask questions in natural language via SAP Joule; the agent resolves intent, calls the appropriate OData operations, and returns structured, readable answers.

#### Problem Statement

Sales Representatives must navigate multiple S/4HANA screens to find basic product information, consuming 5+ minutes per lookup. This slows customer conversations, delays quoting, and frustrates non-technical users who lack S/4HANA expertise.

#### Affected User Roles

- Sales Representatives (primary users)
- Sales Managers (potential secondary users reviewing product portfolios)

#### Important factors

##### Reduces manual effort through conversational AI
Sales Reps can ask plain questions like "What are the dimensions of product X?" instead of navigating multiple S/4HANA transactions — reducing lookup time from minutes to seconds.

##### No pre-built MCP servers require custom tooling
The required OData APIs do not have pre-built MCP servers in the customer landscape; MCP translation files must be generated from API specs before the agent can be wired up.

##### Joule integration via A2A protocol
Deploying as a Joule extension requires A2A protocol compliance, which is natively supported by the Python agent template.

#### Potential risks

##### OData API field coverage
The standard OData APIs may not expose every product attribute Sales Reps need. Custom fields or extensions in S/4HANA may require additional configuration.

##### Ambiguous product queries
Sales Reps may use colloquial names or partial product IDs. The agent must handle disambiguation gracefully to avoid returning incorrect results.

#### Recommended solution category

AI Agent

#### Intent fit

90%
