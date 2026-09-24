# Automated Evaluation

The repeatable evaluation suite is implemented in `vendor_assessment/evaluation.py` and `vendor_assessment/evaluation_demo.py`.

It measures:

- retrieval relevance
- groundedness
- citation correctness
- task completion
- tool correctness
- prompt injection resistance
- decision quality

Run the deterministic and OpenAI judge evaluation with:

```bash
uv run python -m vendor_assessment.evaluation_demo
```

The OpenAI API key and model are supplied through the variables documented in `.env.example`.
