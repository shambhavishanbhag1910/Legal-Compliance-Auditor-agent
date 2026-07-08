from __future__ import annotations

import json
import random
import time
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from app.config import Settings
from app.frameworks import FRAMEWORKS
from app.schemas import ToolTrace
from app.tools import (
    AuditToolRegistry,
    TOOL_DEFINITIONS,
)


class EvidenceAgent:
    """
    Evidence-gathering agent.

    Responsibilities:

    1. Read framework audit rules.
    2. Let the LLM select document tools.
    3. Execute requested tools.
    4. Return tool observations to the model.
    5. Build an auditable tool trace.
    6. Collect the final evidence bundle.
    7. Retry temporary API failures and rate limits.
    """

    API_MAX_ATTEMPTS = 6


    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is required "
                "for evidence collection."
            )

        if not settings.groq_base_url:
            raise RuntimeError(
                "GROQ_BASE_URL is required."
            )

        if not settings.groq_model:
            raise RuntimeError(
                "GROQ_MODEL is required."
            )

        self.settings = settings

        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )


    # =========================================================
    # RETRY-AFTER HELPER
    # =========================================================

    @staticmethod
    def _get_retry_after_seconds(
        exc: RateLimitError,
    ) -> float | None:
        """
        Read the retry-after value from a 429 response.

        Returns:
            Number of seconds to wait, or None if unavailable.
        """

        response = getattr(
            exc,
            "response",
            None,
        )

        if response is None:
            return None


        headers = getattr(
            response,
            "headers",
            None,
        )

        if headers is None:
            return None


        retry_after = headers.get(
            "retry-after"
        )

        if retry_after is None:
            return None


        try:

            return float(
                retry_after
            )

        except (
            TypeError,
            ValueError,
        ):

            return None


    # =========================================================
    # RESPONSES API CALL WITH RETRIES
    # =========================================================

    def _create_response_with_retry(
        self,
        *,
        input_items: list[Any],
    ) -> Any:
        """
        Call the Groq Responses API with retries for:

        - 429 rate limits
        - connection failures
        - timeout failures
        """

        last_error: Exception | None = None


        for attempt in range(
            1,
            self.API_MAX_ATTEMPTS + 1,
        ):

            try:

                return self.client.responses.create(
                    model=self.settings.groq_model,

                    instructions=(
                        "You are an evidence-gathering "
                        "compliance agent. "

                        "Use document tools iteratively. "

                        "Gather evidence for every framework "
                        "rule. "

                        "Search broadly enough to identify both "
                        "present disclosures and missing or "
                        "unclear disclosures. "

                        "Do not make final legal conclusions "
                        "during this evidence collection phase. "

                        "Do not provide private chain-of-thought. "

                        "For every tool call, provide only a "
                        "short operational purpose describing "
                        "what evidence is being sought."
                    ),

                    input=input_items,

                    tools=TOOL_DEFINITIONS,

                    tool_choice="auto",

                    parallel_tool_calls=False,
                )


            # -------------------------------------------------
            # 429 RATE LIMIT
            # -------------------------------------------------

            except RateLimitError as exc:

                last_error = exc


                if attempt >= self.API_MAX_ATTEMPTS:

                    raise RuntimeError(
                        "Evidence Agent exceeded Groq "
                        "rate limits after maximum retries."
                    ) from exc


                retry_after = (
                    self._get_retry_after_seconds(
                        exc
                    )
                )


                if retry_after is not None:

                    delay = retry_after

                else:

                    delay = min(
                        2 ** (attempt - 1),
                        30,
                    )


                # Small jitter helps prevent repeated collisions.
                delay += random.uniform(
                    0.15,
                    0.50,
                )


                print(
                    "\n[Agent Rate Limit Retry]"
                )

                print(
                    f"Attempt {attempt}/"
                    f"{self.API_MAX_ATTEMPTS} failed."
                )

                print(
                    f"Waiting {delay:.2f} seconds "
                    "before retrying evidence collection..."
                )


                time.sleep(
                    delay
                )


            # -------------------------------------------------
            # TEMPORARY CONNECTION PROBLEMS
            # -------------------------------------------------

            except (
                APIConnectionError,
                APITimeoutError,
            ) as exc:

                last_error = exc


                if attempt >= self.API_MAX_ATTEMPTS:

                    raise RuntimeError(
                        "Evidence Agent API connection "
                        "failed after maximum retries."
                    ) from exc


                delay = min(
                    2 ** (attempt - 1),
                    20,
                )


                delay += random.uniform(
                    0.15,
                    0.50,
                )


                print(
                    "\n[Agent Connection Retry]"
                )

                print(
                    f"Attempt {attempt}/"
                    f"{self.API_MAX_ATTEMPTS} failed."
                )

                print(
                    f"Waiting {delay:.2f} seconds "
                    "before retrying..."
                )


                time.sleep(
                    delay
                )


        raise RuntimeError(
            "Evidence Agent request failed "
            "after all retry attempts."
        ) from last_error


    # =========================================================
    # EVIDENCE COLLECTION
    # =========================================================

    def collect(
        self,
        *,
        framework: str,
        registry: AuditToolRegistry,
    ) -> tuple[
        list[dict[str, Any]],
        list[ToolTrace],
    ]:
        """
        Run the evidence collection agent loop.

        Flow:

        Framework rules
            ↓
        LLM selects tool
            ↓
        Python executes tool
            ↓
        Tool observation returned to model
            ↓
        Model decides next action
            ↓
        Final evidence bundle returned
        """

        if framework not in FRAMEWORKS:

            raise ValueError(
                f"Unknown framework: {framework}"
            )


        rules = FRAMEWORKS[
            framework
        ]


        # -----------------------------------------------------
        # Initial user input
        # -----------------------------------------------------

        input_items: list[Any] = [
            {
                "role": "user",
                "content": (
                    "Perform evidence collection for every "
                    f"rule in the '{framework}' framework.\n\n"

                    "Use the available document tools to search "
                    "for supporting, conflicting, missing, or "
                    "unclear evidence.\n\n"

                    "Audit every rule. Do not stop after finding "
                    "evidence for only the first few rules.\n\n"

                    "Framework rules:\n"
                    + json.dumps(
                        rules,
                        ensure_ascii=False,
                    )
                ),
            }
        ]


        traces: list[ToolTrace] = []


        # -----------------------------------------------------
        # Agent tool loop
        # -----------------------------------------------------

        for step in range(
            1,
            self.settings.max_tool_steps + 1,
        ):

            print(
                f"[Evidence Agent] "
                f"Step {step}/"
                f"{self.settings.max_tool_steps}"
            )


            response = (
                self._create_response_with_retry(
                    input_items=input_items,
                )
            )


            # Add model output to local conversation history.
            input_items.extend(
                response.output
            )


            # Find function calls selected by the model.
            calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]


            # No more tool calls means the agent is finished.
            if not calls:

                print(
                    "[Evidence Agent] "
                    "Evidence collection complete."
                )

                break


            # -------------------------------------------------
            # Execute every requested tool call
            # -------------------------------------------------

            for call in calls:

                result, purpose = registry.execute(
                    call.name,
                    call.arguments,
                )


                try:

                    arguments = json.loads(
                        call.arguments
                    )

                except json.JSONDecodeError:

                    arguments = {
                        "raw_arguments": call.arguments
                    }


                # ---------------------------------------------
                # Audit trace
                # ---------------------------------------------

                traces.append(
                    ToolTrace(
                        tool_name=call.name,

                        purpose=purpose,

                        arguments=arguments,

                        result_preview=(
                            json.dumps(
                                result,
                                ensure_ascii=False,
                            )[:500]
                        ),
                    )
                )


                print(
                    f"[Evidence Agent Tool] "
                    f"{call.name}"
                )

                print(
                    f"Purpose: {purpose}"
                )


                # ---------------------------------------------
                # Return tool result to model
                # ---------------------------------------------

                input_items.append(
                    {
                        "type": "function_call_output",

                        "call_id": call.call_id,

                        "output": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )


        # -----------------------------------------------------
        # Final evidence bundle
        # -----------------------------------------------------

        evidence = registry.evidence_bundle()


        print(
            f"[Evidence Agent] "
            f"Collected {len(evidence)} evidence chunks "
            f"through {len(traces)} tool calls."
        )


        return evidence, traces