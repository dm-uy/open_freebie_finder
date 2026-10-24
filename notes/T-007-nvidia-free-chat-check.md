# NVIDIA Free Endpoint chat snapshot and live checks

Date:2026-10-23. P2/T-007; owner-authorized discovery repair and short32-token probes. This is a dated result snapshot, never a model allowlist or configuration input. Models and availability may change.

Public source: [NVIDIA Build Models](https://build.nvidia.com/models), backed by the owned NGC ENDPOINT search with nim_type_preview. The captured snapshot contains43 endpoints,17 chat rows,11 available/public/nondeprecated preview chat rows, and10 exact publisher/name matches in the keyed84-ID API catalog. Unmatched slugs are not guessed. Listed here are those ten pending/qualified exact routes.

Every qualification requires the operator nonbillable-account assertion plus fresh source and both buffered/SSE visible-text proofs. Source labels and successful requests do not prove account pricing. Assurance remains user_asserted; observed effective cost reporting is unavailable. No paid fallback, model-specific options, larger token budget or longer timeout was used.

| Exact API model ID | Route fingerprint | Observed result |
|---|---|---|
| `deepseek-ai/deepseek-v4.1-flash` | `17567520b81b6487` | UNVERIFIED: 15s no-status timeout observed |
| `google/diffusiongemma-26b-a4b-it` | `00de91117ce05b3b` | PASS: qualification and ordinary proxy buffered/SSE; visible text, one SSE DONE |
| `google/gemma-4-31b-it` | `410fa9a7b0347bd0` | UNVERIFIED: 15s no-status timeout observed |
| `meta/llama-3.2-11b-vision-instruct` | `96899a5ea5d4c8b8` | PASS: qualification and ordinary proxy buffered/SSE; visible text, one SSE DONE |
| `meta/llama-3.2-90b-vision-instruct` | `ed29abbe146ddb50` | UNVERIFIED: 15s no-status timeout observed |
| `meta/muse-glimmer-30b` | `bf7f21a45c57e0f7` | UNVERIFIED: HTTP200 length finish,32 reported completion tokens, no visible text |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | `0959cf6545aa26e5` | UNVERIFIED: qualification pair passed, ordinary buffered200/PASS, ordinary SSE503/no visible output; cause not captured |
| `nvidia/nemotron-3-ultra-550b-a55b` | `ad7decc9ae94df12` | PASS: qualification and ordinary proxy buffered/SSE; visible text, one SSE DONE |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | `57b7e204b183bff6` | UNVERIFIED: HTTP200 length finish,32 reported completion tokens, no visible text |
| `openai/gpt-oss-20b` | `a741d960ae90c248` | UNVERIFIED: HTTP200 length finish,32 reported completion tokens, no visible text |

Capture integrity:

| Capture | SHA-256 |
|---|---|
| `/tmp/t007-nvidia-free-source.json` | `d24d22b0561f31a9dbdc8f3c8a5d8ed30b75e572d07f659b4921248fd8cad703` |
| `/tmp/t007-nvidia-current-api-catalog.json` | `2061abd4c6104097bf4fe62ff4437d14ebe6c739d1ab0989bc4c4f6253652ea1` |
| `/tmp/t007-nvidia-free-live-0.jsonl` | `67510e235f0907b1cfc15bf7d1ff6d72af227a7ca7b692750764baf165e0ae58` |
| `/tmp/t007-nvidia-free-live-offset-1.jsonl` | `11f5d61fcab3a4ded92fb04f16c9530aa7576a2ee46f5565784835c6288db314` |
| `/tmp/t007-nvidia-free-live-offset-3.jsonl` | `330be5e2f1a2057afc7fd22e46dfd42f00aacdeec7f1164187f296af5169e857` |
| `/tmp/t007-nvidia-free-live-offset-4.jsonl` | `7feaa0186d4ac211336f2f972e7b6eb17d5a14db81294b4d8d4161ec84cc208d` |
| `/tmp/t007-nvidia-free-live-offset-5.jsonl` | `997fafeb24619244ca162dedab0b0fc42391eec695750dc37de2c5793b774e63` |
| `/tmp/t007-nvidia-free-live-offset-6.jsonl` | `c37a922aa9a6fa0c7033e87d92a42636c8deccc724debda039d35d74210b0c08` |
| `/tmp/t007-nvidia-free-live-offset-7.jsonl` | `d26e8c5e1d34d25d1d629ec6c60350320f5e87557bba1930a85225e553656da0` |
| `/tmp/t007-nvidia-free-live-offset-8.jsonl` | `8caf91fd9f1bc53ce66922a29d1e9c6b82e9dd1e94ea9a1d1be23ab1258ec2f1` |
| `/tmp/t007-nvidia-free-live-offset-9.jsonl` | `97f067f7bc46e20201eb2f5fdc0665058569ef984561b8d101cbad42d956ad99` |

Completed packets observed: 9; actual inference sends: 23. Every send requested max_tokens=32. Buffered/SSE usage may be absent; missing usage is not reported as32 actual tokens. No account/billing/.env change or primary activation.

Implementation: [NVIDIA source parser](../backend/app/core/discovery/nvidia.py), [full T-007 results](T-007-results.md). Source failure/removal revokes admission; no fallback to the generic NVIDIA model list. Public NGC gets no inference credentials, cookies or default client authentication. Strict OpenRouter remains unchanged. At this isolated checkpoint the primary was still the previously accepted OpenRouter service; these isolated assertions/leases ended with each process. The subsequent separately accepted [primary activation](T-007-primary-activation.md) supersedes that environment state.
