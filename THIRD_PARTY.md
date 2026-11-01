# Third-party data, software and licences

This project is independent and is not endorsed by any data provider, software
vendor or model provider. It is MIT licensed; see `LICENSE`.

## NHTSA ODI public data

The project uses the public flat files published by the National Highway
Traffic Safety Administration (NHTSA), Office of Defects Investigation:

| role | source |
|---|---|
| consumer complaints 2020-2024 | `https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2020-2024.zip` |
| consumer complaints 2025-2026 | `https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2025-2026.zip` |
| recalls since 2010 | `https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip` |
| defect investigations | `https://static.nhtsa.gov/odi/ffdd/inv/FLAT_INV.zip` |
| manufacturer communications (optional, recorded but not derived) | `https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS_RECEIVED_2020-2024.zip`, `https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS_RECEIVED_2025-2026.zip` |

File layouts: `cmpl/CMPL.txt`, `rcl/RCL.txt`, `inv/INV.txt` and
`tsbs/TSBS.txt` under the same host.

### Public-domain statement

NHTSA's Terms of Use, section **Ownership**, states:

> "Information presented on this web site is considered public information and
> may be distributed or copied."

— National Highway Traffic Safety Administration, *Terms of Use*,
<https://www.nhtsa.gov/node/32151>, accessed 2026-10-31.

The same status follows from the federal-copyright rule: 17 U.S.C. §105
provides that copyright protection is not available for any work of the United
States Government. The NHTSA files are therefore public information. NHTSA/DOT
does not endorse this project, and the downloaded data is provided without any
warranty of accuracy or fitness (the Terms of Use disclaim such warranties).

### What this project stores

- Raw downloads stay under the git-ignored `data/raw/` directory.
- `data/SNAPSHOT.json` records each download's URL, sha256, size,
  `Last-Modified` header and download time.
- The committed files under `data/` are derived selections: location and
  identity columns are dropped, and complaint narratives that match the
  committed PII screen (VIN, e-mail, phone, street address) are removed.
  `data/STATS.md` records the counts. The independent review found
  signature-style personal names that this screen does not cover; see
  `reports/REVIEW.md` B4.
- The recordings under `recordings/` contain model responses and the prompt
  context that produced them. The complaint text in that context is the same
  public, screened text.

## Model service

The agentic desk calls **DeepSeek V4.1 Flash** through an OpenAI-compatible
gateway (OpenCode Go) using the key read from the file named by `FQA_ENV_FILE`.
Use of the model and the gateway is governed by their own terms of service; the
project does not redistribute model weights or the key. Model outputs are stored
as recordings so the run can be replayed offline, and the recordings contain no
credential. Costs recorded in `results/` are the gateway's list prices at the
time of the run (falling back to `config/prices.toml` when a response carries no
cost).

## Software

Versions are the ones resolved in `uv.lock` and `web/package-lock.json`.
Transitive dependencies keep their own licences; the table lists the direct
dependencies the project chooses and the tools it runs.

### Backend and data (Python 3.12, managed by uv)

| package | version | licence |
|---|---|---|
| [duckdb](https://duckdb.org/) | 2.0.0 | MIT |
| [fastapi](https://fastapi.tiangolo.com/) | 0.162.0 | MIT |
| [httpx](https://www.python-httpx.org/) | 0.28.1 | BSD-3-Clause |
| [langchain-core](https://python.langchain.com/) | 1.7.3 | MIT |
| [langgraph](https://langchain-ai.github.io/langgraph/) | 1.2.19 | MIT |
| [mcp](https://modelcontextprotocol.io/) (Python SDK) | 2.3.0 | MIT |
| [pydantic](https://docs.pydantic.dev/) | 2.14.2 | MIT |
| [scikit-learn](https://scikit-learn.org/) | 1.9.1 | BSD-3-Clause |
| [uvicorn](https://www.uvicorn.org/) | 0.54.0 | BSD-3-Clause |
| [PyYAML](https://pyyaml.org/) (facts check) | 6.0.3 | MIT |

### Development tools

| package | version | licence |
|---|---|---|
| [mypy](https://mypy-lang.org/) | 2.4.1 | MIT |
| [pytest](https://pytest.org/) | 9.2.0 | MIT |
| [Ruff](https://docs.astral.sh/ruff/) | 0.17.3 | MIT |
| [uv](https://docs.astral.sh/uv/) | resolved by the environment | MIT or Apache-2.0 |

### Dashboard (Node 22.12 or newer)

| package | version | licence |
|---|---|---|
| [React](https://react.dev/) and React DOM | 19.3.1 | MIT |
| [Apache ECharts](https://echarts.apache.org/) | 6.1.0 | Apache-2.0 |
| [Vite](https://vite.dev/) | 8.3.5 | MIT |
| [TypeScript](https://www.typescriptlang.org/) | 7.0.2 | Apache-2.0 |
| [Vitest](https://vitest.dev/) | 5.0.5 | MIT |
| [Playwright](https://playwright.dev/) (`@playwright/test`) | 1.64.1 | Apache-2.0 |
| [axe-core for Playwright](https://github.com/dequelabs/axe-core-npm) | 4.10.2 | MPL-2.0 |
| [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) | 6.1.2 | MIT |
| [@types/react](https://www.npmjs.com/package/@types/react) and `@types/react-dom` | 19.3.0 | MIT |

### Assets

No web fonts, icon packs, images or chart themes are downloaded or bundled.
Icons are inline SVG authored in `web/src/components/Icon.tsx`; fonts are the
operating system's UI fonts; the chart theme is written for this project in
`web/src/theme/echartsTheme.ts`. Screenshots under `results/screenshots/` are
captured from the project's own dashboard.

## Attribution

If you reuse the data, credit NHTSA as its source and follow their Terms of Use.
If you reuse this project, keep the MIT licence notice in `LICENSE`.
