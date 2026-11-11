# Morpheus Gemini AI adapter — development candidate

Status: implemented as an injectable adapter; not yet live-validated, integrated into production Flask app, or activated.

## Technical selection (2026-11-11)
- Development candidate model: `gemini-3.5-flash-lite` (configurable via `MORPHEUS_GEMINI_MODEL`).
- Google lifecycle reference: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions (retirement July 21, 2027 or later).
- Pricing reference: https://cloud.google.com/model-garden/pricing (check current pricing before release).
- SDK reference: https://googleapis.github.io/python-genai/
- Google Vertex AI mode: `genai.Client(vertexai=True, project=..., location=...)`.
- Gemini 2.5 identifiers are explicitly blocked as new-development defaults.

## Contract
`make_gemini_reasoner(model=..., client=...)` returns a callable compatible with `MorpheusFlow(ai_reason=...)`. Fake client injection allows deterministic unit tests without network access or costs. Responses must be JSON objects with `status` of `preview`, `needs_more_context`, or `stop`. The existing `MorpheusFlow` performs bounded retrieval and strict UI validation. Apollo retrieval remains simulated until separately implemented.

## Live configuration (future authorized test)
Install the official `google-genai` SDK in a controlled environment. Set `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `MORPHEUS_GEMINI_MODEL`. Use Application Default Credentials/service identity; never commit secrets. Test model availability, region, JSON response, latency, and measured tokens/cost. The SDK is intentionally not added to the production dependency manifest yet because production integration is not approved.

## Gate
No live provider call, model availability check, measured pricing, or end-to-end Apollo/Gemini validation has been performed. Production remains STOP. A current lifecycle and cost review is required before enabling production.
