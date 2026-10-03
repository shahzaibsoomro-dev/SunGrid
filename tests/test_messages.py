"""The saved transcript is not the same list the model receives."""

import unittest

from app.llm.messages import to_llm_input


class MessageViewTest(unittest.TestCase):
    def test_model_input_drops_at(self) -> None:
        messages = [
            {"role": "system", "content": "You are the SunGrid copilot.", "at": "t"},
            {"role": "user", "content": "Am I eligible?", "at": "t"},
            {
                "role": "assistant",
                "content": {
                    "reasoning": "The tool said eligible.",
                    "result": "Yes. The rebate is $2,000.",
                },
                "at": "t",
            },
            {
                "result": [
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "check_rebate_eligibility",
                        "arguments": '{"household_zip": "94103"}',
                    }
                ],
                "at": "t",
            },
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": '{"eligible": true}',
                "at": "t",
            },
        ]

        self.assertEqual(
            to_llm_input(messages),
            [
                {"role": "system", "content": "You are the SunGrid copilot."},
                {"role": "user", "content": "Am I eligible?"},
                {
                    "role": "assistant",
                    "content": '{"reasoning": "The tool said eligible.", "result": "Yes. The rebate is $2,000."}',
                },
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "check_rebate_eligibility",
                    "arguments": '{"household_zip": "94103"}',
                },
                {
                    "type": "function_call_output",
                    "call_id": "call_1",
                    "output": '{"eligible": true}',
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
