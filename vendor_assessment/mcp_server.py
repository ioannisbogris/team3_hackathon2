from mcp.server.mcpserver import MCPServer


mcp = MCPServer(
    "NFS Vendor Tools",
    instructions="Controlled access to approved NFS vendor-assessment data.",
)


VENDOR_HISTORY = {
    "Vendor Alpha": {
        "previous_assessments": 1,
        "previous_decision": "request_more_evidence",
        "last_review": "2026-01-15",
    }
}


VENDOR_PRICING = {
    "Vendor Alpha": {
        "annual_cost": 120000,
        "currency": "USD",
        "contract_term_years": 2,
    }
}


POLICIES = {
    "vendor_approval": (
        "Vendor approval requires Security, Procurement and Commercial, "
        "Legal and Compliance, and AI Governance evidence."
    ),
    "security": (
        "Security review must cover access control, encryption, "
        "incident response and independent security evidence."
    ),
}


@mcp.tool()
def get_vendor_history(vendor_name: str) -> dict:
    """Retrieve previous assessment history."""
    return VENDOR_HISTORY.get(
        vendor_name,
        {
            "previous_assessments": 0,
            "previous_decision": "no_previous_assessment",
            "last_review": None,
        },
    )


@mcp.tool()
def get_vendor_pricing(vendor_name: str) -> dict:
    """Retrieve approved commercial information."""
    return VENDOR_PRICING.get(
        vendor_name,
        {"status": "pricing_not_found"},
    )


@mcp.tool()
def retrieve_policy(policy_name: str) -> dict:
    """Retrieve an approved NFS policy."""
    policy = POLICIES.get(policy_name)

    if policy is None:
        return {
            "status": "policy_not_found",
            "policy_name": policy_name,
        }

    return {
        "status": "found",
        "policy_name": policy_name,
        "content": policy,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")