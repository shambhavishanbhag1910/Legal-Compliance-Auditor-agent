import json

from openai import OpenAI

from app.config import Settings
from app.frameworks import FRAMEWORKS
from app.schemas import ToolTrace
from app.tools import TOOL_DEFINITIONS, AuditToolRegistry


class EvidenceAgent:
    def __init__(self, settings: Settings):
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is required for auditing."
            )

        self.settings = settings

        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )

    def collect(self, *, framework: str, registry: AuditToolRegistry) -> tuple[list[dict], list[ToolTrace]]:
        rules = FRAMEWORKS[framework]
        input_items = [
            {
                "role": "user",
                "content": (
                    "Audit the current source document against every rule below. "
                    "Use the tools to gather direct evidence. Search broadly enough to cover all rules. "
                    "Do not provide private chain-of-thought. Tool calls should include only a brief evidence purpose.\n\n"
                    + json.dumps(rules)
                ),
            }
        ]

        traces = []

        for _ in range(self.settings.max_tool_steps):
            response = self.client.responses.create(
                model=self.settings.groq_model,
                instructions=(
                    "You are an evidence-gathering compliance agent. "
                    "Use document tools iteratively. Gather evidence for all framework rules. "
                    "Do not make final legal conclusions in this phase."
                ),
                input=input_items,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                parallel_tool_calls=False,
            )

            input_items += response.output
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break

            for call in calls:
                result, purpose = registry.execute(call.name, call.arguments)
                args = json.loads(call.arguments)
                traces.append(
                    ToolTrace(
                        tool_name=call.name,
                        purpose=purpose,
                        arguments=args,
                        result_preview=json.dumps(result, ensure_ascii=False)[:500],
                    )
                )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )

        return registry.evidence_bundle(), traces
