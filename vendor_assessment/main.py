from __future__ import annotations

import json
from dataclasses import asdict

from .models import VendorAssessmentRequest
from .planner import build_assessment_plan


def main() -> None:
    request = VendorAssessmentRequest(
        vendor_name="Vendor Alpha",
        service_category="AI platform",
        business_objective="Assess whether NFS should adopt the vendor under controlled conditions.",
    )
    plan = build_assessment_plan(request)
    print(json.dumps(asdict(plan), indent=2, default=str))


if __name__ == "__main__":
    main()

