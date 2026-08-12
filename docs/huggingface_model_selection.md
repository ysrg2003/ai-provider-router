# Hugging Face default model selection findings

Research date: 2026-08-12.

## Official capability findings

Hugging Face Inference Providers documents a unified OpenAI-compatible chat completions endpoint at `https://router.huggingface.co/v1/chat/completions`. It supports a single HF token with provider routing and model suffix policies such as `:fastest`, `:cheapest`, and `:preferred`. The official documentation states that `:fastest` selects the highest-throughput available provider for the selected model, while `:cheapest` selects the lowest-cost provider. The official setup requires a fine-grained token with the permission to make calls to Inference Providers.

Official sources:
- https://huggingface.co/docs/inference-providers/index
- https://huggingface.co/docs/inference-providers/tasks/chat-completion
- https://huggingface.co/models?pipeline_tag=text-generation&inference_provider=all&sort=trending

## Selection criteria

The default list is not presented as a permanent universal benchmark ranking. It is a practical ordered fallback list for structured text/JSON generation: documented chat-completion suitability, broad usefulness across planning/coding/reasoning, current inference-provider visibility, size diversity, and a smaller-model fallback for constrained availability or cost.

## Selected default ten

1. `openai/gpt-oss-120b:fastest` — primary general-purpose and tool-oriented model; used in the official HF quick-start example.
2. `deepseek-ai/DeepSeek-V4-Flash-0731:fastest` — current high-capability flash-style model visible in the trending inference-available list.
3. `zai-org/GLM-5.2:fastest` — high-capability general model visible in the current inference-available trending list.
4. `Qwen/Qwen3-Coder-480B-A35B-Instruct:fastest` — large coding and technical-instruction fallback listed by the official chat-completion recommendations.
5. `deepseek-ai/DeepSeek-R1:fastest` — reasoning-oriented fallback listed by the official recommendations.
6. `Qwen/Qwen3-4B-Thinking-2507:fastest` — smaller reasoning fallback listed by the official recommendations.
7. `Qwen/Qwen2.5-7B-Instruct-1M:fastest` — long-instruction conversational fallback listed by the official recommendations.
8. `Qwen/Qwen2.5-Coder-32B-Instruct:fastest` — coding and structured-output fallback listed by the official recommendations.
9. `meta-llama/Llama-3.1-8B-Instruct:fastest` — widely used smaller instruction model visible in the current inference-available list.
10. `openai/gpt-oss-20b:fastest` — smaller general-purpose fallback from the same family as the primary model.

Availability is provider- and account-dependent. The router must treat a model that returns 404, 403, 429, 5xx, timeout, or invalid JSON as unavailable for that attempt and continue to the next configured model. The list is therefore a resilient default chain, not a guarantee that every model is free or available at every moment.
