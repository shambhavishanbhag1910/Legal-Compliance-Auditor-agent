from __future__ import annotations

import json
import random
import time
from collections.abc import Callable
from copy import deepcopy
from typing import Any, TypeVar
from app.config import Settings
from app.schemas import AuditReport, JudgeResult
from openai import (
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessageParam

from openai.types.shared_params.response_format_json_schema import (
    ResponseFormatJSONSchema,
)



T = TypeVar("T")


class LLMClient:
    """
    Handles LLM operations for:

    1. Structured compliance audit generation
    2. Independent LLM-as-a-Judge evaluation
    3. Rate-limit retry handling
    4. Strict JSON Schema generation
    5. Business-level audit validation
    """

    # ---------------------------------------------------------
    # Configuration constants
    # ---------------------------------------------------------

    API_MAX_ATTEMPTS = 6

    BUSINESS_VALIDATION_ATTEMPTS = 3

    AUDIT_MAX_COMPLETION_TOKENS = 2200

    JUDGE_MAX_COMPLETION_TOKENS = 1000

    MAX_RETRY_AFTER_SECONDS = 90.0

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        if not settings.groq_api_key.get_secret_value():
            raise RuntimeError(
                "GROQ_API_KEY is required for auditing."
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
            api_key=settings.groq_api_key.get_secret_value(),
            base_url=settings.groq_base_url,
        )


    # =========================================================
    # RETRY HANDLING
    # =========================================================

    @staticmethod
    def _get_retry_after_seconds(
        exc: RateLimitError,
    ) -> float | None:
        """
        Read Groq's retry-after response header.

        Returns:
            Number of seconds to wait, or None when unavailable.
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


    def _with_api_retry(
        self,
        operation: Callable[[], T],
        *,
        operation_name: str,
    ) -> T:
        """
        Execute an API operation with retries for:

        - 429 rate limits
        - connection failures
        - timeout failures

        BadRequestError is intentionally not retried here because
        repeated retries usually do not fix an invalid request schema.
        """

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.API_MAX_ATTEMPTS + 1,
        ):

            try:

                return operation()


            # -------------------------------------------------
            # Rate limit
            # -------------------------------------------------

            except RateLimitError as exc:

                last_error = exc

                if attempt >= self.API_MAX_ATTEMPTS:
                    raise

                retry_after = (
                    self._get_retry_after_seconds(
                        exc
                    )
                )

                if (
                    retry_after is not None
                    and retry_after > self.MAX_RETRY_AFTER_SECONDS
                ):
                    raise RuntimeError(
                        "Groq returned a long rate-limit wait of "
                        f"{retry_after:.2f} seconds. "
                        "Stopping instead of blocking the evaluation process."
                    ) from exc


                if retry_after is not None:
                    delay = retry_after

                else:
                    delay = min(
                        2 ** (attempt - 1),
                        30,
                    )

                # Add small jitter to reduce repeated collisions.
                delay += random.uniform(
                    0.15,
                    0.50,
                )

                print(
                    f"\n[Rate Limit Retry] "
                    f"{operation_name}: "
                    f"attempt {attempt}/"
                    f"{self.API_MAX_ATTEMPTS} failed."
                )

                print(
                    f"Waiting {delay:.2f} seconds "
                    f"before retrying..."
                )

                time.sleep(
                    delay
                )


            # -------------------------------------------------
            # Temporary network problems
            # -------------------------------------------------

            except (
                APIConnectionError,
                APITimeoutError,
            ) as exc:

                last_error = exc

                if attempt >= self.API_MAX_ATTEMPTS:
                    raise

                delay = min(
                    2 ** (attempt - 1),
                    20,
                )

                delay += random.uniform(
                    0.15,
                    0.50,
                )

                print(
                    f"\n[Transient API Retry] "
                    f"{operation_name}: "
                    f"attempt {attempt}/"
                    f"{self.API_MAX_ATTEMPTS} failed."
                )

                print(
                    f"Waiting {delay:.2f} seconds "
                    f"before retrying..."
                )

                time.sleep(
                    delay
                )


        raise RuntimeError(
            f"{operation_name} failed after retries."
        ) from last_error


    # =========================================================
    # STRICT JSON SCHEMA HELPERS
    # =========================================================

    @staticmethod
    def _enforce_strict_objects(
        node: Any,
    ) -> None:
        """
        Recursively modify JSON Schema objects so that:

        - all object properties are required
        - additionalProperties is false

        This helps ensure compatibility with strict structured output.
        """

        if isinstance(
            node,
            dict,
        ):

            if node.get("type") == "object":

                properties = node.get(
                    "properties",
                    {},
                )

                if isinstance(
                    properties,
                    dict,
                ):

                    node["required"] = list(
                        properties.keys()
                    )

                    node[
                        "additionalProperties"
                    ] = False


            for value in node.values():

                LLMClient._enforce_strict_objects(
                    value
                )


        elif isinstance(
            node,
            list,
        ):

            for item in node:

                LLMClient._enforce_strict_objects(
                    item
                )


    @classmethod
    def _strict_schema(
        cls,
        model_class: Any,
    ) -> dict[str, Any]:
        """
        Generate and normalize a strict JSON Schema
        from a Pydantic model.
        """

        schema = deepcopy(
            model_class.model_json_schema()
        )

        cls._enforce_strict_objects(
            schema
        )

        return schema


    # =========================================================
    # RAW STRICT STRUCTURED CALL
    # =========================================================

    def _structured_chat_call(
        self,
        *,
        schema_name: str,
        schema: dict[str, Any],
        system_prompt: str,
        payload: dict[str, Any],
        temperature: float,
        max_completion_tokens: int,
        operation_name: str,
    ) -> dict[str, Any]:
        """
        Make one strict structured-output Chat Completions call.

        Rate-limit and network retries are handled automatically.
        """

        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": json.dumps(
                    payload,
                    ensure_ascii=False,
                ),
            },
        ]


        response_format: ResponseFormatJSONSchema = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema,
            },
        }


        def request() -> Any:
            return (
                self.client
                .chat
                .completions
                .create(
                    model=self.settings.groq_model,

                    messages=messages,

                    temperature=temperature,

                    max_completion_tokens=(
                        max_completion_tokens
                    ),

                    response_format=response_format,

                    extra_body={
                        "reasoning_effort": "low",
                        "include_reasoning": False,
                    },
                )
            )


        try:

            response = self._with_api_retry(
                request,
                operation_name=operation_name,
            )


        except BadRequestError as exc:

            message = str(
                exc
            )

            if (
                "json_validate_failed"
                in message
                or
                "Generated JSON does not match"
                in message
            ):

                raise ValueError(
                    f"{operation_name} returned an incomplete "
                    "or schema-invalid structured response. "
                    f"Original error: {exc}"
                ) from exc

            raise


        raw_content = (
            response
            .choices[0]
            .message
            .content
        )


        if not raw_content:

            raise ValueError(
                f"{operation_name} returned empty content."
            )


        try:

            parsed = json.loads(
                raw_content
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                f"{operation_name} returned invalid JSON."
            ) from exc


        if not isinstance(
            parsed,
            dict,
        ):

            raise ValueError(
                f"{operation_name} must return "
                "a JSON object."
            )


        return parsed


    # =========================================================
    # AUDIT BUSINESS VALIDATION
    # =========================================================

    @staticmethod
    def _validate_audit_business_rules(
        *,
        report: AuditReport,
        document_id: str,
        framework: str,
        expected_rule_ids: list[str],
        evidence: list[dict[str, Any]],
    ) -> None:
        """
        Validate semantic/business completeness.

        JSON Schema validation alone cannot guarantee:

        - every rule is covered exactly once
        - the correct document ID is returned
        - the correct framework is returned
        - evidence chunk IDs really exist
        """

        errors: list[str] = []


        # -----------------------------------------------------
        # Document ID
        # -----------------------------------------------------

        if report.document_id != document_id:

            errors.append(
                "Document ID mismatch: "
                f"expected '{document_id}', "
                f"received '{report.document_id}'."
            )


        # -----------------------------------------------------
        # Framework
        # -----------------------------------------------------

        if report.framework != framework:

            errors.append(
                "Framework mismatch: "
                f"expected '{framework}', "
                f"received '{report.framework}'."
            )


        # -----------------------------------------------------
        # Rule coverage
        # -----------------------------------------------------

        actual_rule_ids = [
            finding.rule_id
            for finding in report.findings
        ]


        missing_rule_ids = sorted(
            set(expected_rule_ids)
            - set(actual_rule_ids)
        )


        unexpected_rule_ids = sorted(
            set(actual_rule_ids)
            - set(expected_rule_ids)
        )


        duplicate_rule_ids = sorted({
            rule_id
            for rule_id in actual_rule_ids
            if actual_rule_ids.count(
                rule_id
            ) > 1
        })


        if missing_rule_ids:

            errors.append(
                f"Missing rules: {missing_rule_ids}"
            )


        if unexpected_rule_ids:

            errors.append(
                "Unexpected rules: "
                f"{unexpected_rule_ids}"
            )


        if duplicate_rule_ids:

            errors.append(
                "Duplicate rules: "
                f"{duplicate_rule_ids}"
            )


        if (
            len(actual_rule_ids)
            != len(expected_rule_ids)
        ):

            errors.append(
                "Finding count mismatch: "
                f"expected {len(expected_rule_ids)}, "
                f"received {len(actual_rule_ids)}."
            )


        # -----------------------------------------------------
        # Evidence chunk validation
        # -----------------------------------------------------

        valid_chunk_ids = {
            item["chunk_id"]
            for item in evidence
            if isinstance(item, dict)
            and item.get("chunk_id")
        }


        invalid_chunk_references: list[str] = []


        for finding in report.findings:

            for quote in finding.evidence:

                if (
                    valid_chunk_ids
                    and quote.chunk_id
                    not in valid_chunk_ids
                ):

                    invalid_chunk_references.append(
                        f"{finding.rule_id}:"
                        f"{quote.chunk_id}"
                    )


        if invalid_chunk_references:

            errors.append(
                "Invalid evidence chunk references: "
                f"{sorted(invalid_chunk_references)}"
            )


        # -----------------------------------------------------
        # Final validation result
        # -----------------------------------------------------

        if errors:

            raise ValueError(
                "Audit business validation failed. "
                + " | ".join(
                    errors
                )
            )


    # =========================================================
    # STRUCTURED AUDIT GENERATION
    # =========================================================

    def structured_audit(
        self,
        *,
        document_id: str,
        framework: str,
        rules: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> AuditReport:
        """
        Generate one structured audit candidate.

        Called multiple times by orchestrator.py for
        self-consistency generation.
        """

        expected_rule_ids = [
            rule["rule_id"]
            for rule in rules
        ]


        # -----------------------------------------------------
        # Generate strict AuditReport schema
        # -----------------------------------------------------

        audit_schema = self._strict_schema(
            AuditReport
        )


        # -----------------------------------------------------
        # Restrict rule_id to valid framework rules
        # -----------------------------------------------------

        try:

            audit_schema[
                "$defs"
            ][
                "ComplianceFinding"
            ][
                "properties"
            ][
                "rule_id"
            ][
                "enum"
            ] = expected_rule_ids

        except KeyError as exc:

            raise RuntimeError(
                "Could not locate ComplianceFinding.rule_id "
                "inside the generated AuditReport schema."
            ) from exc


        # -----------------------------------------------------
        # Prompt
        # -----------------------------------------------------

        system_prompt = f"""
You are a careful compliance audit extraction system.

Evaluate every compliance rule against only the supplied
document evidence.

Required rule IDs:
{json.dumps(expected_rule_ids)}

REQUIREMENTS:

1. Evaluate every required rule exactly once.

2. Never omit a rule.

3. Never duplicate a rule.

4. Use only the supplied document evidence.

5. Never invent evidence or source text.

6. When evidence is insufficient, use status "unclear".

7. Evidence must always be included as a list.
   Use [] when no direct evidence exists.

8. limitations must always be included.
   Use [] when there are no limitations.

9. Use only chunk IDs available in the supplied evidence.

10. Keep all output concise.

11. Executive summary maximum: 45 words.

12. Finding summary maximum: 15 words.

13. Remediation maximum: 15 words.

14. Use maximum one evidence quote per finding.

15. Evidence quote maximum: 35 words.

16. Limitations maximum: two items.

17. Each limitation maximum: 12 words.

18. Complete ALL required rule findings before returning.

19. Before completing the response, verify that every
required rule ID is present exactly once.

20. Always return limitations, even when it is [].

21. This is an educational compliance audit,
not legal advice.

Return the complete structured report.
""".strip()


        payload = {
            "document_id": document_id,
            "framework": framework,
            "rules": rules,
            "evidence": evidence,
        }


        last_error: Exception | None = None


        # -----------------------------------------------------
        # Retry only when business completeness validation fails
        # -----------------------------------------------------

        for attempt in range(
            1,
            self.BUSINESS_VALIDATION_ATTEMPTS + 1,
        ):

            try:

                raw_report = (
                    self._structured_chat_call(
                        schema_name="audit_report",

                        schema=audit_schema,

                        system_prompt=system_prompt,

                        payload=payload,

                        temperature=0.3,

                        max_completion_tokens=(
                            self.AUDIT_MAX_COMPLETION_TOKENS
                        ),

                        operation_name=(
                            "Structured Audit Generation"
                        ),
                    )
                )


                # ---------------------------------------------
                # Pydantic validation
                # ---------------------------------------------

                report = AuditReport.model_validate(
                    raw_report
                )


                # ---------------------------------------------
                # Business validation
                # ---------------------------------------------

                self._validate_audit_business_rules(
                    report=report,

                    document_id=document_id,

                    framework=framework,

                    expected_rule_ids=expected_rule_ids,

                    evidence=evidence,
                )


                return report


            except ValueError as exc:

                last_error = exc

                print(
                    f"\n[Audit Business Validation Retry] "
                    f"Attempt {attempt}/"
                    f"{self.BUSINESS_VALIDATION_ATTEMPTS} "
                    f"failed."
                )

                print(
                    str(exc)
                )


                if (
                    attempt
                    < self.BUSINESS_VALIDATION_ATTEMPTS
                ):

                    delay = (
                        2.0 * attempt
                    )

                    print(
                        f"Retrying candidate generation "
                        f"in {delay:.2f} seconds..."
                    )

                    time.sleep(
                        delay
                    )


        raise RuntimeError(
            "Structured audit generation failed "
            "business validation after "
            f"{self.BUSINESS_VALIDATION_ATTEMPTS} "
            "attempts. "
            f"Last error: {last_error}"
        )


    # =========================================================
    # LLM-AS-A-JUDGE
    # =========================================================

    def judge(
        self,
        *,
        source_text: str,
        report: AuditReport,
        rules: list[dict[str, Any]],
    ) -> JudgeResult:
        """
        Independently evaluate the final consensus report against:

        - source document
        - compliance rules
        - evidence claims
        """

        judge_schema = self._strict_schema(
            JudgeResult
        )


        system_prompt = """
You are an independent compliance audit evaluator.

Evaluate the supplied audit report against:

1. The original source document.
2. The supplied compliance rules.
3. The evidence claims in the audit report.

Score:

faithfulness:
How strongly report claims are supported by the source.

completeness:
How completely the report evaluates the supplied rules.

hallucination_rate:
Approximate fraction of substantive audit claims that are
unsupported or fabricated.

REQUIREMENTS:

1. All scores must be between 0 and 1.

2. unsupported_finding_ids must always be included.
   Use [] when none exist.

3. fabricated_claims must always be included.
   Use [] when none exist.

4. comments must always be included.

5. Judge strictly from the supplied source and rules.

6. Do not reward confident wording.

7. Keep comments under 80 words.

Return only the required structured result.
""".strip()


        payload = {
            "rules": rules,

            "source_document": (
                source_text[:80000]
            ),

            "audit_report": (
                report.model_dump(
                    mode="json"
                )
            ),
        }


        last_error: Exception | None = None


        for attempt in range(
            1,
            self.BUSINESS_VALIDATION_ATTEMPTS + 1,
        ):

            try:

                raw_judge = (
                    self._structured_chat_call(
                        schema_name="judge_result",

                        schema=judge_schema,

                        system_prompt=system_prompt,

                        payload=payload,

                        temperature=0.1,

                        max_completion_tokens=(
                            self.JUDGE_MAX_COMPLETION_TOKENS
                        ),

                        operation_name=(
                            "LLM Judge Evaluation"
                        ),
                    )
                )


                result = JudgeResult.model_validate(
                    raw_judge
                )


                return result


            except ValueError as exc:

                last_error = exc

                print(
                    f"\n[Judge Validation Retry] "
                    f"Attempt {attempt}/"
                    f"{self.BUSINESS_VALIDATION_ATTEMPTS} "
                    f"failed."
                )

                print(
                    str(exc)
                )


                if (
                    attempt
                    < self.BUSINESS_VALIDATION_ATTEMPTS
                ):

                    delay = (
                        0.75 * attempt
                    )

                    time.sleep(
                        delay
                    )


        raise RuntimeError(
            "Judge evaluation failed after "
            f"{self.BUSINESS_VALIDATION_ATTEMPTS} "
            "attempts. "
            f"Last error: {last_error}"
        )