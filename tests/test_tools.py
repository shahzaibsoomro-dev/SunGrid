"""The eligibility tool is the stub, not a second copy of its rules."""

import json
import unittest

from app.services.tools import run_tool


class ToolTest(unittest.TestCase):
    def test_passing_household_gets_the_stub_amount(self) -> None:
        result = json.loads(
            run_tool(
                "check_rebate_eligibility",
                {
                    "household_zip": "94103",
                    "annual_income_usd": 80000,
                    "system_size_kw": 5,
                    "installer_approved": True,
                },
            )
        )

        self.assertTrue(result["eligible"])
        self.assertEqual(result["estimated_rebate_usd"], 2000.0)

    def test_failed_check_does_not_invent_an_amount(self) -> None:
        result = json.loads(
            run_tool(
                "check_rebate_eligibility",
                {
                    "household_zip": "94103",
                    "annual_income_usd": 120000,
                    "system_size_kw": 5,
                    "installer_approved": True,
                },
            )
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["estimated_rebate_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
