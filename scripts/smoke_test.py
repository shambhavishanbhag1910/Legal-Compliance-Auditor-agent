import json
from pathlib import Path

import httpx


BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    # =========================================================
    # STEP 1: Upload document
    # =========================================================

    path = Path(
        "sample_docs/privacy_policy_acme.txt"
    )

    print("\nUploading document...")

    with path.open("rb") as handle:
        upload_response = httpx.post(
            f"{BASE_URL}/documents",
            files={
                "file": (
                    path.name,
                    handle,
                    "text/plain",
                )
            },
            timeout=60,
        )


    # Check document upload response

    if upload_response.is_error:
        print(
            "\n========== DOCUMENT ERROR =========="
        )

        print(
            "Status Code:",
            upload_response.status_code,
        )

        print("Response Body:")

        print(
            upload_response.text
        )

        print(
            "====================================\n"
        )

        upload_response.raise_for_status()


    document = upload_response.json()


    print("\nDOCUMENT")

    print(
        json.dumps(
            document,
            indent=2,
        )
    )


    # =========================================================
    # STEP 2: Run audit
    # =========================================================

    print("\nRunning compliance audit...")

    print(
        "Agent search + 3 audit runs + "
        "consensus + LLM judge"
    )


    audit_response = httpx.post(
        f"{BASE_URL}/audits",
        json={
            "document_id": document["document_id"],
            "framework": "privacy",
            "runs": 3,
        },
        timeout=600,
    )


    # Check audit response

    if audit_response.is_error:
        print(
            "\n========== AUDIT ERROR =========="
        )

        print(
            "Status Code:",
            audit_response.status_code,
        )

        print("Response Body:")

        print(
            audit_response.text
        )

        print(
            "=================================\n"
        )

        audit_response.raise_for_status()


    # =========================================================
    # STEP 3: Read audit JSON
    # =========================================================

    audit = audit_response.json()


    print("\nAUDIT RESULT")

    print(
        json.dumps(
            audit,
            indent=2,
        )
    )


    # =========================================================
    # STEP 4: Display summary
    # =========================================================

    print("\n========== SUMMARY ==========")

    print(
        "Audit ID:",
        audit.get("audit_id"),
    )

    print(
        "Framework:",
        audit.get(
            "report",
            {},
        ).get(
            "framework"
        ),
    )

    print(
        "Overall Risk:",
        audit.get(
            "report",
            {},
        ).get(
            "overall_risk"
        ),
    )

    print(
        "Consensus Agreement:",
        audit.get(
            "consensus_agreement"
        ),
    )

    print(
        "Candidate Count:",
        audit.get(
            "candidate_count"
        ),
    )

    print(
        "Faithfulness:",
        audit.get(
            "judge",
            {},
        ).get(
            "faithfulness"
        ),
    )

    print(
        "Hallucination Rate:",
        audit.get(
            "judge",
            {},
        ).get(
            "hallucination_rate"
        ),
    )

    print("=============================")


if __name__ == "__main__":
    main()