"""Tools the agent can run. The eligibility check is the stub service."""

import importlib.util
import json
from typing import Any

from app.config import root_dir
from app.llm.prompt import RETRIEVAL_TOOL
from app.rag.retrieval import retrieve

_STUB_PATH = root_dir() / "SunGrid Starter Kit" / "stub_tools.py"
_SPEC = importlib.util.spec_from_file_location("sungrid_stub_tools", _STUB_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load {_STUB_PATH}.")
_STUB = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_STUB)
check_rebate_eligibility = _STUB.check_rebate_eligibility

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "check_rebate_eligibility",
        "description": (
            "Decide rooftop rebate eligibility for one household. "
            "Call this only when ZIP, income, system size in kW, and installer approval are all known. "
            "The result is final: a failed check has estimated_rebate_usd of 0, and that amount must not be replaced with an estimate."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "household_zip": {"type": "string", "description": "Household ZIP code."},
                "annual_income_usd": {"type": "number", "description": "Annual household income in USD."},
                "system_size_kw": {"type": "number", "description": "Rooftop system size in kW."},
                "installer_approved": {
                    "type": "boolean",
                    "description": "True when the installer is on the approved list.",
                },
            },
            "required": [
                "household_zip",
                "annual_income_usd",
                "system_size_kw",
                "installer_approved",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


async def run_tool(name: str, arguments: dict[str, Any]) -> str:
    """Run one tool and return a JSON string the model can read."""
    if name == RETRIEVAL_TOOL:
        hits = await retrieve(str(arguments["query"]), list(arguments["categories"]))
        return json.dumps(hits)
    if name != "check_rebate_eligibility":
        return json.dumps({"error": f"Unknown tool: {name}"})
    approved = arguments.get("installer_approved")
    if not isinstance(approved, bool):
        return json.dumps({"error": "installer_approved must be true or false."})
    try:
        result = check_rebate_eligibility(
            household_zip=str(arguments["household_zip"]),
            annual_income_usd=float(arguments["annual_income_usd"]),
            system_size_kw=float(arguments["system_size_kw"]),
            installer_approved=approved,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return json.dumps({"error": f"Invalid arguments: {exc}"})
    return json.dumps(result)
