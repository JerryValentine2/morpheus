# Morpheus simulated Flask preview

This is a **non-production preview**, not an activated Apollo cartridge.

From the repository root:

```bash
python -m pip install -r requirements-preview.txt
python -m unittest discover -s validation -p 'test_api.py' -v
python api.py
```

Open http://127.0.0.1:8080 . The page provides a product selector, request input and safe adaptive preview components.

API:
- `GET /` — browser interface
- `GET /api/health` — simulated-mode status
- `GET /api/products` — candidate product labels/IDs
- `POST /api/preview` — JSON `{"product_id":"calculator","message":"15% of 200"}`

**Simulation boundaries:** `simulated_apollo_search` returns source-grounded fixture excerpts; `simulated_ai_reason` returns fixed preview components, does not invoke an LLM or perform calculations. No actual Apollo credentials, remote transport, cartridge approval, live activation, or production deployment. No secrets should be committed.

**Known limitations:** preview uses existing `runtime/apollo_flow.py`, which only validates UI component type and does not yet perform bounded AI-directed follow-up searches. UI inputs and actions are intentionally disabled; chart displays placeholder. Before production, strengthen UI schema validation, verify actual Apollo transport/authentication, isolate concurrent sessions, load approved exact-version artifacts, and test integration and behavior gates.
