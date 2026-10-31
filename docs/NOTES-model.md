# Model endpoint notes (verified 2026-10-31)

All statements below were checked against the live OpenCode documentation and a
single live probe on **2026-10-31**. Versions and dates are recorded rather than
recalled.

## Sources

| What | Source | Checked |
|---|---|---|
| OpenCode Go plans, model list, limits, endpoints | <https://opencode.ai/docs/go/> | 2026-10-31 |
| Inference API, cost fields | <https://opencode.ai/v2/docs/console/api/inference/> | 2026-10-31 |
| Harness base URLs, session header | <https://opencode.ai/v2/docs/console/harnesses/> | 2026-10-31 |
| Budget exhaustion behaviour | <https://opencode.ai/v2/docs/console/budgets/> | 2026-10-31 |
| Live model metadata | `GET https://opencode.ai/inference/go/v1/models` | 2026-10-31 |

## Endpoint and model

| Item | Value |
|---|---|
| Base URL (Go) | `https://opencode.ai/inference/go` |
| OpenAI-compatible chat path | `/openai/v1/chat/completions` |
| Full endpoint | `https://opencode.ai/inference/go/openai/v1/chat/completions` |
| Model id | `deepseek-v4.1-flash` |
| Model family metadata | `deepseek-flash`, canonical id `deepseek/deepseek-v4.1-flash` |
| Model release / last update | 2026-09-10 |
| Context limit | 1,000,000 tokens |
| Output limit | 384,000 tokens |
| Capabilities | tool calling, structured output, temperature, top_p, top_k; reasoning effort `low`, `high`, `max` |
| Modalities | text and images in; text out |
| Price (off-peak) | USD 0.15 / 1M input, USD 0.60 / 1M output, USD 0.003 / 1M cached read |
| Price (peak) | 2x off-peak; peak is 01:00-04:00 and 06:00-10:00 UTC, Monday-Friday |
| Go monthly allowance | USD 100 on the Go plan (5-hour cap: 20%, weekly: 50%) |

The live metadata lists the Chat Completions base URL for this model as
`https://opencode.ai/inference/go/openai/v1`. The Go and pay-as-you-go bases are
different; use the `/go` base with a Go subscription.

Authentication is `Authorization: Bearer <token>`. The token is read only from
the file named by `FQA_ENV_FILE` (default
`~/.config/field-quality-agents/upstream.env`). Never put it in a command line,
log, trace, recording or commit.

OpenCode asks clients to send a stable `x-opencode-session` header and a
non-generic `User-Agent` such as `field-quality-agents/0.1`.

## Tool-calling request shape

Chat Completions uses the standard OpenAI tool schema. The project sends a
`tools` array and may set `tool_choice` (`auto`, `none`, `required`, or a named
function; the model metadata advertises all four):

```json
{
  "model": "deepseek-v4.1-flash",
  "temperature": 0,
  "max_tokens": 1024,
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "similar_cases",
        "description": "BM25 search over the case knowledge base.",
        "parameters": {
          "type": "object",
          "properties": {
            "text": {"type": "string"},
            "k": {"type": "integer", "minimum": 1, "maximum": 20}
          },
          "required": ["text", "k"],
          "additionalProperties": false
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

A tool result is appended as a `tool` message whose `tool_call_id` matches the
assistant's call, then the model is called again:

```json
{"role": "tool", "tool_call_id": "call_...", "content": "{...json result...}"}
```

## Tool-calling response shape

The assistant message carries `tool_calls`; arguments are a JSON-encoded string:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "deepseek-v4.1-flash",
  "choices": [
    {
      "index": 0,
      "finish_reason": "tool_calls",
      "message": {
        "role": "assistant",
        "content": null,
        "reasoning_content": "...",
        "tool_calls": [
          {
            "id": "call_00_...",
            "type": "function",
            "function": {
              "name": "similar_cases",
              "arguments": "{\"text\": \"intermittent wiper\", \"k\": 5}"
            }
          }
        ]
      }
    }
  ],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

Parse `tool_calls[*].function.arguments` as JSON; do not treat it as an object.
`finish_reason` is `tool_calls` for a pure call. The model also returns a
`reasoning_content` field (metadata notes `reasoning_field: reasoning_content`).
Treat any malformed name, arguments or unknown tool as a bad answer: retry is
not automatic for a bad answer (TASKS Q4).

## Usage and cost fields

Every response reports standard usage plus an OpenCode block:

```json
"usage": {
  "prompt_tokens": 332,
  "completion_tokens": 74,
  "total_tokens": 406,
  "prompt_tokens_details": {"cached_tokens": 0, "...": "..."},
  "completion_tokens_details": {"reasoning_tokens": 35, "...": "..."},
  "cost": 0,
  "opencode": {
    "billing_source": "go",
    "list_cost": 0.0000942,
    "allowance": 0.00005652,
    "tokens": {
      "input": 332,
      "output": 74,
      "reasoning": 35,
      "cache_read": 0,
      "cache_write_5m": 0,
      "cache_write_1h": 0
    }
  }
}
```

| Field | Meaning |
|---|---|
| `usage.cost` | USD charged to the balance. `0` for Go usage inside the plan. |
| `usage.opencode.billing_source` | `free`, `balance`, `go`, `go-plus`, or `byok`. |
| `usage.opencode.list_cost` | USD at list price (includes peak and long-context multipliers). |
| `usage.opencode.allowance` | Go only: USD counted against the plan's monthly limit. |
| `usage.opencode.tokens` | Billed tokens; `input` excludes cache reads/writes, `output` includes reasoning. |

Cost is known when the response ends, before the balance or Go allowance is
updated. If the balance or Go limit runs out mid-request, the charge may be less
than reported, never more. Record `cost` when non-zero; when it is zero on Go,
record `list_cost` and `allowance` too so spend is auditable.

## Rate-limit and quota behaviour

- Go limits are **dollar allowances**, not request counts: monthly 100%, weekly
  50%, 5-hour 20% of the monthly limit. Every response reports the amount that
  counted in `usage.opencode.allowance`.
- A Console budget that is reached makes **new requests fail with HTTP 429**
  until the budget resets or an owner raises it. The response identifies a
  policy budget failure but does not name the budget. Budgets are checked when a
  request starts, so in-flight requests finish and spend can land slightly over.
- The public Go and inference pages do not document a specific `Retry-After`
  header or a separate Go-quota status. The probe response carried no
  rate-limit headers. Treat 429 as retryable only after honouring
  `Retry-After` when present, with bounded exponential backoff (TASKS Q4).
- 401 means revoked/expired key; 403 means the key or plan is not allowed
  (including free models used outside OpenCode). A 403, abuse/policy message or
  account warning is a **stop rule** (PLAN §10), never a retry.
- Authentication uses the Go base URL. The generic pay-as-you-go base needs a
  balance; the two are not interchangeable.

## Live probe (one call, approved)

| Item | Result |
|---|---|
| Time (UTC) | 2026-10-31T11:51Z (request), response 2.05 s later |
| Request | one system + one user message, one `probe_echo` tool, `tool_choice: required`, temperature 0, `max_tokens: 256` |
| Endpoint | `https://opencode.ai/inference/go/openai/v1/chat/completions` |
| Model | `deepseek-v4.1-flash` |
| HTTP status | 200 |
| Response id | `707f32ef4a2fec6a94511d7412da0836` |
| Finish reason | `tool_calls` |
| Tool call | `call_00_m4pqx4c9t6seyf8008pa2oad`, `probe_echo({"text": "ok"})` |
| Valid tool call | **yes**: function type/name, non-empty id, JSON arguments, expected value |
| Tokens | 332 input, 74 output, 35 reasoning, 406 total; 0 cached |
| `usage.cost` | USD 0 (Go usage inside the plan) |
| `usage.opencode.list_cost` | USD 0.0000942 |
| `usage.opencode.allowance` | USD 0.00005652 |
| Billing source | `go` |
| Rate-limit headers | none returned |
| Spend | **USD 0.00 charged**; USD 0.00005652 of Go allowance consumed |

The raw response body is kept outside the repository at
`/tmp/opencode/probe-response.json`; it contains no credential. One call was
made; no retries were needed. Tool calling works, so PLAN §10 rule 5 does not
apply.
