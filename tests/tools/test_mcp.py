from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from field_quality_agents.tools import Toolbox

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_NAMES = {
    "similar_cases",
    "recalls_for",
    "investigations_for",
    "cluster_stats",
    "verify_quotes",
    "rulebook",
    "case_lookup",
}


def _payload(result: Any) -> object:
    structured = result.structured_content
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    if structured is not None:
        return structured
    text = "".join(part.text for part in result.content if getattr(part, "type", "") == "text")
    return json.loads(text) if text else None


async def _exercise_server(fixture_db: Path, rulebook: Path) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "FQA_DB": str(fixture_db),
            "FQA_RULEBOOK": str(rulebook),
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "field_quality_agents.mcp_server"],
        env=environment,
        cwd=str(REPO_ROOT),
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = await session.list_tools()
        assert {tool.name for tool in listed.tools} == TOOL_NAMES

        similar = await session.call_tool(
            "similar_cases",
            {
                "text": "intermittent wiper",
                "filters": {
                    "make": "FORD",
                    "model": "F-150",
                    "year": 2021,
                    "group": "body_controls",
                },
                "k": 2,
            },
        )
        assert similar.is_error is False
        similar_payload = cast(list[dict[str, object]], _payload(similar))
        assert [item["id"] for item in similar_payload] == ["c17", "c02"]
        assert similar_payload[0]["score"] == round(float(similar_payload[0]["score"]), 4)

        recalls = await session.call_tool(
            "recalls_for",
            {"make": "FORD", "model": "F-150", "year": 2021, "group": "body_controls"},
        )
        assert [item["id"] for item in cast(list[dict[str, object]], _payload(recalls))] == [
            "r02",
            "r01",
        ]

        investigations = await session.call_tool(
            "investigations_for",
            {"make": "FORD", "model": "F-150", "year": 2021, "group": "body_controls"},
        )
        assert [
            item["id"] for item in cast(list[dict[str, object]], _payload(investigations))
        ] == ["i01", "i02"]

        cluster = await session.call_tool(
            "cluster_stats",
            {
                "make": "FORD",
                "model": "F-150",
                "year": 2021,
                "group": "body_controls",
                "until_date": "2025-07-07",
            },
        )
        cluster_payload = cast(dict[str, object], _payload(cluster))
        assert cluster_payload["until_date"] == "2025-07-07"
        assert cluster_payload["observed"] == 5
        assert cluster_payload["threshold"] == 5.0
        assert cluster_payload["spike"] is True
        assert len(cast(list[object], cluster_payload["weekly"])) == 27

        quoted = await session.call_tool(
            "verify_quotes",
            {
                "text": "The wiper motor stops\n intermittently when cold.",
                "quotes": [
                    {"kind": "symptom", "quote": "wiper motor stops intermittently"},
                    {"kind": "symptom", "quote": "Wiper motor"},
                ],
            },
        )
        assert [item["verified"] for item in cast(list[dict[str, object]], _payload(quoted))] == [
            True,
            False,
        ]

        rules = await session.call_tool("rulebook", {"conditions": ["cold", "moisture"]})
        assert [item["id"] for item in cast(list[dict[str, object]], _payload(rules))] == [
            "moisture",
            "cold",
        ]

        case = await session.call_tool("case_lookup", {"id": "c01"})
        case_payload = cast(dict[str, object], _payload(case))
        assert case_payload["id"] == "c01"
        assert case_payload["received_at"] == "2021-01-05"

        missing = await session.call_tool("case_lookup", {"id": "nope"})
        assert _payload(missing) is None


def test_mcp_lists_and_calls_every_tool(fixture_db: Path, toolbox: Toolbox) -> None:
    asyncio.run(_exercise_server(fixture_db, toolbox.rulebook_path))
