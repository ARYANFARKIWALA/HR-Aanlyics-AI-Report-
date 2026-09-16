# AI Provider Setup & Fallback Handling (Module 6)

## 1. Supported Providers

The platform supports multiple AI model providers:
1. **Google Gemini** (`gemini-1.5-flash`, `gemini-1.5-pro`): Default high-performance engine for complex query planning and plain English explanations.
2. **OpenAI** (`gpt-4o`, `gpt-4o-mini`): Configurable via `DEFAULT_LLM_PROVIDER=openai` and `OPENAI_API_KEY`.
3. **Deterministic Offline Fallback**: In environments without internet access or API keys, the system falls back to semantic repository pattern matching and rule template synthesis.

---

## 2. Strict Generation Invariant

The AI Text-to-SQL Engine **NEVER directly executes SQL**.
Generated queries MUST pass through the Module 7 Zero-Trust AST Validator Gate and obtain an approved cryptographic token before execution can take place in Module 8.

---

## 3. Graceful Failure & Cost Guardrails
- If an AI API rate limit or outage occurs, the engine returns a standardized error: `"AI service temporarily unavailable. Please try again later or select a pre-verified repository template."`
- The system prevents hallucination loops by enforcing single-pass generation with deterministic validation.
