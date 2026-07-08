import json

from openai import OpenAI

from app.config import Settings
from app.schemas import (
    AuditReport,
    JudgeResult,
)



class LLMClient:
    def __init__(
        self,
        settings: Settings,
    ):
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is required "
                "for auditing."
            )

        self.settings = settings

        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )

    def structured_audit(
        self,
        *,
        document_id: str,
        framework: str,
        rules: list[dict],
        evidence: list[dict],
    ) -> AuditReport:

        expected_rule_ids = [
            rule["rule_id"]
            for rule in rules
        ]


        # ---------------------------------------------------------
        # Build Pydantic JSON Schema
        # ---------------------------------------------------------

        audit_schema = (
            AuditReport.model_json_schema()
        )


        # Require the exact number of findings.
        findings_schema = (
            audit_schema["properties"]["findings"]
        )

        findings_schema["minItems"] = len(rules)
        findings_schema["maxItems"] = len(rules)


        # Restrict rule IDs to the expected framework rules.
        finding_definition = (
            audit_schema["$defs"]
            ["ComplianceFinding"]
        )

        finding_definition[
            "properties"
        ][
            "rule_id"
        ][
            "enum"
        ] = expected_rule_ids


        # ---------------------------------------------------------
        # Strong system prompt
        # ---------------------------------------------------------

        system_prompt = f"""
    You are a compliance audit extraction system.

    Your job is to evaluate every provided rule against
    the supplied evidence.

    IMPORTANT REQUIREMENTS:

    1. Return exactly {len(rules)} findings.

    2. Return exactly one finding for each required rule.

    Required rule IDs:

    {json.dumps(expected_rule_ids)}

    3. Do not skip any rule.

    4. If evidence is insufficient, use:

    status = "unclear"

    5. Every finding must contain:

    rule_id
    rule_name
    status
    severity
    summary
    evidence
    remediation

    6. evidence must always be present.

    Use [] when no direct evidence is available.

    7. limitations must always be present.

    Use [] when there are no limitations.

    8. Never invent evidence.

    9. Use only chunk IDs that appear in the
    supplied evidence.

    10. This is an educational compliance audit,
    not legal advice.
    """.strip()


        payload = {
            "document_id": document_id,
            "framework": framework,
            "rules": rules,
            "evidence": evidence,
        }


        last_error: Exception | None = None


        # ---------------------------------------------------------
        # Retry only for business coverage problems
        # ---------------------------------------------------------

        for attempt in range(1, 4):

            try:

                response = (
                    self.client
                    .chat
                    .completions
                    .create(
                        model=self.settings.groq_model,

                        messages=[
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
                        ],

                        temperature=0.3,

                        response_format={
                            "type": "json_schema",

                            "json_schema": {
                                "name": "audit_report",

                                "strict": True,

                                "schema": audit_schema,
                            },
                        },
                    )
                )


                raw_content = (
                    response
                    .choices[0]
                    .message
                    .content
                )


                if not raw_content:
                    raise ValueError(
                        "Model returned empty content."
                    )


                # -------------------------------------------------
                # Pydantic validation
                # -------------------------------------------------

                report = AuditReport.model_validate(
                    json.loads(raw_content)
                )


                # -------------------------------------------------
                # Business completeness validation
                # -------------------------------------------------

                actual_rule_ids = [
                    finding.rule_id
                    for finding in report.findings
                ]


                missing_rule_ids = sorted(
                    set(expected_rule_ids)
                    - set(actual_rule_ids)
                )


                duplicate_rule_ids = sorted({
                    rule_id
                    for rule_id in actual_rule_ids
                    if actual_rule_ids.count(
                        rule_id
                    ) > 1
                })


                unexpected_rule_ids = sorted(
                    set(actual_rule_ids)
                    - set(expected_rule_ids)
                )


                if (
                    missing_rule_ids
                    or duplicate_rule_ids
                    or unexpected_rule_ids
                ):

                    raise ValueError(
                        "Audit coverage validation failed. "
                        f"Missing: {missing_rule_ids}. "
                        f"Duplicates: {duplicate_rule_ids}. "
                        f"Unexpected: {unexpected_rule_ids}."
                    )


                return report


            except ValueError as exc:

                last_error = exc

                print(
                    "[Structured Audit Retry] "
                    f"Attempt {attempt}/3 failed: "
                    f"{exc}"
                )


        raise RuntimeError(
            "Structured audit generation failed "
            "after 3 attempts. "
            f"Last error: {last_error}"
    )

    def judge(
        self,
        *,
        source_text: str,
        report: AuditReport,
        rules: list[dict],
    ) -> JudgeResult:

        judge_schema = (
            JudgeResult.model_json_schema()
        )


        system_prompt = """
    You are an independent compliance audit evaluator.

    Compare the final audit report against the original
    source document and the audit rules.

    Evaluate:

    1. Faithfulness
    2. Completeness
    3. Hallucination rate
    4. Unsupported findings
    5. Fabricated claims

    All scores must be between 0 and 1.

    unsupported_finding_ids must always be present.
    Use [] when none exist.

    fabricated_claims must always be present.
    Use [] when none exist.

    comments must always be present.

    Be strict, evidence grounded, and concise.
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


        response = (
            self.client
            .chat
            .completions
            .create(
                model=self.settings.groq_model,

                messages=[
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
                ],

                temperature=0.1,

                response_format={
                    "type": "json_schema",

                    "json_schema": {
                        "name": "judge_result",

                        "strict": True,

                        "schema": judge_schema,
                    },
                },
            )
        )


        raw_content = (
            response
            .choices[0]
            .message
            .content
        )


        if not raw_content:
            raise RuntimeError(
                "Judge returned empty content."
            )


        return JudgeResult.model_validate(
            json.loads(raw_content)
        )
        if response.output_parsed is None:
            raise RuntimeError("Judge returned no parsed output.")
        return response.output_parsed
