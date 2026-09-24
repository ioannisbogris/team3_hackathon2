# NFS Vendor Assessment Deep Agent

First implementation slice for Hackathon 2:

```text
structured vendor request -> assessment plan -> executable todos
```

The initial core is deterministic and testable. LLM reasoning, RAG, MCP and
specialist-agent execution will be added around this contract without changing
the business objects.

## Run

```bash
python -m vendor_assessment.main
pytest -q
```

## Initial business domains

- Security
- Procurement and Commercial
- Legal and Compliance
- AI Governance

