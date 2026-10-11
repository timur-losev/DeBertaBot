# Small language models and non-generative alternatives for "a very little reasoning" on a desktop CPU (state: October 2026)

Reading notes for the report writer:

- "Published" means the number is in the cited source. "ESTIMATE" means I computed or extrapolated it; every estimate is in an Inferences block and is labelled.
- No source I found measures any of these models on an Intel i9-10900K, and none measures them with a game running. All CPU figures below come from other machines, and each one is named.
- Vendor benchmark tables are not comparable across vendors (different harness versions; for example, Qwen3-1.7B scores 52.2 on BFCL v3 in Alibaba's report and 46.30 in Liquid AI's table).
- Several sources are dated after June 2026 (GLiNER2.5-Decide, LFM2.5 encoders, two arXiv papers numbered 2608.x and 2609.x, the current NVIGI model list). I report them as fetched; they are vendor or author claims without independent replication.

## 1. Which small open models (100M to 4B) exist for on-device use, with sizes, licenses and function-calling claims

### Takeaway
The commercially usable candidates in the sub-1B class are FunctionGemma / Gemma 3 270M (Gemma Terms of Use), Granite 4.0 Nano 350M (Apache-2.0), Qwen3-0.6B and Qwen3.5-0.8B (Apache-2.0), SmolLM2 (Apache-2.0), MiniCPM4-0.5B (Apache-2.0) and LFM2.5-350M (LFM Open License v1.0, free only under 10 million USD annual revenue). Out of the box none of them exceeds about 46 percent on BFCL v3, and the best 1B to 1.7B models reach about 49 to 57 percent, so every vendor of a sub-1B model recommends fine-tuning for the target task. Most of the specialised function-calling fine-tunes (Hammer, xLAM-1b, Arch-Function) carry non-commercial or research licenses.

### Cited Findings

General-purpose and tool-calling models (vendor-reported numbers):

| Model | Parameters | Context | License and commercial conditions | Function-calling / instruction claims | Source |
|---|---|---|---|---|---|
| Gemma 3 270M (IT) | 0.3B (270M) | 32K in, 32K minus input out | "gemma" tag: Gemma Terms of Use plus Prohibited Use Policy | IFEval 51.2; BIG-Bench Hard 26.7; card lists no function-calling score | [HF card](https://huggingface.co/google/gemma-3-270m-it) |
| FunctionGemma 270M | 0.3B | 32K | Gemma Terms of Use plus Prohibited Use Policy | Base model BFCL: Simple 61.6, Multiple 63.5, Parallel 39, Parallel Multiple 29.5, Live Simple 36.2, Live Multiple 25.7, Relevance 61.1, Irrelevance 73.7. "Mobile Actions": 58% base, 85% after fine-tuning. "Not intended for use as a direct dialogue model"; should be fine-tuned for a domain | [HF card](https://huggingface.co/google/functiongemma-270m-it) |
| Gemma 3 1B (IT) | 1B | not re-checked | Gemma Terms of Use (Gemma 3 is listed in the terms' appendix) | BFCL v3 16.3, IFEval 54.5 (as measured by Alibaba) | [Qwen3 report](https://arxiv.org/abs/2505.09388); [Gemma terms](https://ai.google.dev/gemma/terms) |
| Gemma 4 E2B / E4B | 2.3B effective (5.1B with embeddings) / 4.5B effective (8B with embeddings) | 128K | Apache-2.0 (first Gemma generation not under the Gemma terms; released 2 April 2026) | "Native support for structured tool use"; no function-calling benchmark on the card; Tau2 24.5% (E2B), 42.2% (E4B); thinking is switchable | [HF card](https://huggingface.co/google/gemma-4-E2B-it); [The Decoder](https://the-decoder.com/googles-gemma-4-is-now-available-with-apache-2-0-licensing-for-the-first-time/) |
| Qwen3-0.6B / 1.7B / 4B | 0.6B / 1.7B / 4B | 32K / 32K / 128K | Apache-2.0 | BFCL v3 non-thinking 44.1 / 52.2 / 57.6; thinking 46.4 / 56.6 / 65.9. IFEval strict-prompt non-thinking 54.5 / 68.2 / 81.2 | [Qwen3 report](https://arxiv.org/abs/2505.09388) |
| Qwen3.5-0.8B / 2B / 4B / 9B | 0.8B / 2B / 4B / 9B | 262K | Apache-2.0; released about 2 to 3 March 2026 | Hybrid thinking, native vision; about 4-bit memory "under 2 GB" (0.8B, 2B), about 3 GB (4B); no first-party 4-bit files. Vendor positions 0.8B and 2B for edge devices, 4B as "a strong lightweight agent base" | [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models); [Gigazine](https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small) |
| SmolLM2 135M / 360M / 1.7B | 135M / 360M / 1.7B | not stated on card | Apache-2.0 | 1.7B: function calling supported, 27% on BFCL; IFEval 56.7 (Llama-3.2-1B 53.5, Qwen2.5-1.5B 47.4) | [HF card](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) |
| SmolLM3-3B | 3B | 64K native (128K with YaRN) | Apache-2.0 | Dual mode (/think, /no_think; thinking on by default); tool calling with XML and Python tools | [HF card](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) |
| LFM2.5-350M | 350M (16 layers: 10 convolution blocks, 6 attention blocks) | 32,768 | LFM Open License v1.0 | BFCLv3 44.11, BFCLv4 21.86, IFEval 76.96; "recommended for data extraction, structured outputs, and tool use"; "we recommend fine-tuning"; Pythonic tool calls by default, JSON on request | [HF card](https://huggingface.co/LiquidAI/LFM2.5-350M) |
| LFM2.5-1.2B-Instruct | 1.17B | 32,768 | LFM Open License v1.0 | BFCLv3 49.12, IFEval 86.23, Multi-IF 60.98; recommended for "agentic tasks, data extraction, and RAG"; a 296M drafter (DSpark) exists for speculative decoding | [HF card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) |
| Granite 4.0 Nano: 350M / H-350M / 1B / H-1B | 350M / 340M / 1.6B / 1.5B | 32K (350M), 128K (1B) | Apache-2.0; released 28 October 2025 | BFCL v3 39.32 / 43.32 / 54.82 / 50.21; IFEval average 55.4 / 61.63 / 77.38 / 78.53. Tools in OpenAI schema inside `<tools>`, calls returned as JSON in `<tool_call>` | [HF card](https://huggingface.co/ibm-granite/granite-4.0-350m) |
| Phi-4-mini-instruct | 3.8B | 128K | MIT; released February 2025 | Tools passed as JSON between `<|tool|>` tokens; red-team note: "could sometimes hallucinate function names"; BFCL v3 31.3 as measured by Alibaba | [HF card](https://huggingface.co/microsoft/Phi-4-mini-instruct); [Qwen3 report](https://arxiv.org/abs/2505.09388) |
| Phi-4-mini-flash-reasoning | 3.8B (SambaY hybrid) | 64K | MIT; released June 2025 | "Designed and tested for math reasoning only"; speed claim (up to 10x throughput) measured on an NVIDIA A100 GPU, not CPU; card does not mention function calling | [HF card](https://huggingface.co/microsoft/Phi-4-mini-flash-reasoning) |
| MiniCPM4-0.5B | 0.5B (0.4B in file metadata) | 32K pretraining, extended with YaRN | Apache-2.0; released 6 June 2025 | Ternary variants BitCPM4-0.5B and BitCPM4-1B exist; the tool-calling variant MiniCPM4-MCP is based on the 8B model, not the 0.5B | [HF card](https://huggingface.co/openbmb/MiniCPM4-0.5B) |
| BitNet b1.58 2B4T | about 2B (ternary weights) | 4,096 | MIT (weights and code) | IFEval 53.48; no function-calling claim; "We do not recommend using BitNet b1.58 in commercial or real-world applications without further testing and development"; efficiency only with bitnet.cpp | [HF card](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T) |
| Llama 3.2 1B | 1B | not re-checked | Llama 3.2 Community License (text not retrievable in this session, see Gaps) | BFCLv3 21.44 (as measured by Liquid AI) | [Liquid AI blog](https://www.liquid.ai/blog/introducing-lfm2-5-the-next-generation-of-on-device-ai) |

Specialised function-calling fine-tunes:

| Model | Size | License | Published result | Source |
|---|---|---|---|---|
| Hammer2.1-0.5b (MadeAgents) | 0.5B, fine-tuned from Qwen2.5-Coder-0.5B-Instruct | cc-by-nc-4.0 (non-commercial) | BFCL-v3 numbers only as an image; trained with function masking and an irrelevance set (xlam-irrelevance-7.5k) | [HF card](https://huggingface.co/MadeAgents/Hammer2.1-0.5b) |
| xLAM-1b-fc-r (Salesforce) | 1B | CC-BY-NC-4.0 with additional DeepSeek license terms (non-commercial) | 78.94% overall on an early BFCL version | [HF card (GGUF)](https://huggingface.co/Salesforce/xLAM-1b-fc-r-gguf/blob/a7e0ed494e910fef62c46fe7879cd87e9ffcea93/README.md) |
| Arch-Function-1.5B (Katanemo) | 1.5B name, 2B in file metadata; base Qwen2.5-1.5B | "katanemo-research" (Katanemo license; commercial use not stated on the card) | BFCL overall 56.20% as of 21 October 2024 (3B: 57.69%, 7B: 59.62%, GPT-4o FC: 62.19%) | [HF card](https://huggingface.co/katanemo/Arch-Function-1.5B) |
| Octopus v2 (Nexa AI) | about 2B | README revision cited shows `license: apache-2.0`; needs re-checking on the current card, together with the base model's terms | Own benchmark: 99.5% accuracy, 0.38 s average latency (GPU); Phi-3 45.7% and 10.2 s in the same comparison | [HF card](https://huggingface.co/NexaAIDev/Octopus-v2) |
| TinyAgent-1.1B (SqueezeAILab) | 1.1B | not verified | Function-calling success 80.06% (7B: 84.95%; GPT-4-Turbo 79.08%) on the authors' Mac assistant task | [arXiv 2409.00608](https://arxiv.org/html/2409.00608v3) |

License terms:

- Gemma Terms of Use (last modified 1 April 2026) apply to Gemma 3 and FunctionGemma. They grant rights to use, reproduce, modify and distribute; distribution requires passing on the use restrictions as an enforceable provision, giving recipients a copy of the agreement, marking modified files, and shipping a Notice file stating the model is provided under the Gemma Terms of Use. Google "reserves the right to restrict (remotely or otherwise) usage" it reasonably believes violates the agreement. Google claims no rights in outputs. "Model Derivatives" expressly include models made by distillation or by training on synthetic Gemma outputs. Gemma 4 is not in the appendix and is covered by a separate Gemma 4 license. — [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
- LFM Open License v1.0 is Apache-2.0-based. Companies with annual revenue under 10 million USD may use the models commercially at no cost; above the threshold the right to commercial use under the license ends and a commercial license from Liquid AI is needed. The threshold also applies to fine-tuned derivatives. Redistribution requires a copy of the license, retained notices, any NOTICE file, and marked modifications. Downstream customers above 10 million USD need their own license. Page last updated 24 September 2026. — [Liquid AI license docs](https://docs.liquid.ai/lfm/help/model-license)
- The summary text says revenue that "exceeds" 10 million USD, while the license text as indexed by ScanCode says annual revenue of 10 million USD "or more", so the boundary case is ambiguous. — [Liquid AI license page](https://liquid.ai/lfm-license); [ScanCode LicenseDB](https://scancode-licensedb.aboutcode.org/lfm-open-1.0.yml)
- NVIDIA's game-oriented on-device models: Nemotron-Mini-4B-Instruct INT4 uses about 2 GB of VRAM and is 4.22 GB on disk; the ACE archive offers Mistral-NeMo-Minitron in 2B, 4B and 8B sizes. — [NGC catalog](https://catalog.ngc.nvidia.com/orgs/nvidia/models/nemotoron-mini-4b-instruct-onnx-int4-rtx); [NVIDIA ACE model archive](https://forums.developer.nvidia.com/t/nvidia-ace-model-archive/362682)
- Vendor cross-comparisons on BFCL v3: LFM2.5-1.2B 49.12, Qwen3-1.7B 46.30, Granite 4.0-1B 52.43, Llama 3.2 1B 21.44 (Liquid's numbers); LFM2.5-350M 44.11, Granite 4.0-H-350M 43.07, Granite 4.0-350M 39.58, Qwen3.5-0.8B Thinking 39.64 (Liquid's numbers). — [LFM2.5-1.2B card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct); [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M)
- On the harder BFCLv4, LFM2.5-350M scores 21.86, Qwen3.5-0.8B Thinking 25.39 and Qwen3.5-0.8B Instruct 18.70. — [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M)

### Inferences
- For a commercial product the clean-license shortlist is: Granite 4.0 Nano, Qwen3 / Qwen3.5, SmolLM2 / SmolLM3, MiniCPM4, Gemma 4 (all Apache-2.0) and Phi-4-mini (MIT). Gemma 3 270M and FunctionGemma are usable commercially but bring the Gemma terms (pass-through restrictions, Notice file, Google's right to restrict usage, and fine-tunes and distilled students count as Model Derivatives). LFM2.5 is usable only while the licensee's annual revenue is under 10 million USD, which a commercial game studio or its publisher may exceed.
- Hammer, xLAM-1b-fc-r and (probably) Arch-Function are excluded by license regardless of accuracy.
- Gemma 4 E2B is not a "2B-cost" model for CPU memory: its files hold 5.1B parameters including embeddings.
- BitNet b1.58 2B4T has an MIT license but its own card advises against commercial use without further work, and it needs a third runtime (bitnet.cpp).

### Gaps
- Llama 3.2 Community License: the license page redirected twice and then returned 404, so its commercial conditions (attribution, naming rule, the monthly-active-user clause, the EU clause for vision models) are not verified here.
- Gemma 3n (E2B, E4B), LFM2 first generation (350M, 700M, 1.2B, 2.6B), TinyLlama 1.1B and Granite 4.0 "tiny / micro" were not re-checked in this session; no figures are given for them.
- Octopus v2 license needs confirmation on the current model card, and its base model should be identified (if it derives from a Gemma model, the Gemma terms would apply to it as a Model Derivative); TinyAgent license not verified; Arch-Function license text not read.
- No Gemma 4 function-calling benchmark (BFCL) was found on the model card.
- Whether a Qwen3.5-0.8B "intended for prototyping, fine-tuning and research" caveat exists on the official card was reported only by a third-party catalogue and is not verified.

## 2. Measured CPU inference speed, and the time for a 150-token prompt plus a 20-token answer

### Takeaway
Published x86 measurements put 1B to 1.7B transformer models at roughly 15 to 60 generated tokens per second on laptop and desktop CPUs using 4 to 8 or more threads (Liquid AI reports 116 for its own LFM2.5-1.2B), which means a 20-token answer alone costs about 0.3 to 1.3 s; only the 270M to 350M class (vendor figures of 126 to 313 tokens per second) fits a budget of a few hundred milliseconds. No published figure covers an i9-10900K, a 2 to 3 core allowance, or a machine that is also running a game, so every number must be re-measured on the target.

### Cited Findings

| Model | CPU, threads, runtime, precision | Prefill (tok/s) | Decode (tok/s or ms/token) | Memory | Source |
|---|---|---|---|---|---|
| LFM2.5-1.2B-Instruct | AMD Ryzen AI 9 HX 370 (laptop), llama.cpp, Q4_0; 1K prefill, 100 decode; thread count not given | 2975 | 116 | 856 MB | [Liquid AI blog](https://www.liquid.ai/blog/introducing-lfm2-5-the-next-generation-of-on-device-ai) |
| Qwen3-1.7B | same machine and settings | 2008 | 62 | 1465 MB | [Liquid AI blog](https://www.liquid.ai/blog/introducing-lfm2-5-the-next-generation-of-on-device-ai) |
| LFM2.5-1.2B-Instruct | "AMD CPU" (no further detail) | not given | 239 | not given | [LFM2.5-1.2B card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) |
| LFM2.5-350M | "AMD CPU" (no further detail) | not given | about 313 | under 1 GB | [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M) |
| Llama 3.2 1B Instruct | AMD Ryzen AI 9 HX 375, 4-bit, vendor test (CPU-only status unclear) | not given | up to 50.7 | not given | [AMD blog](https://www.amd.com/en/blogs/2024/accelerating-llama-cpp-performance-in-consumer-llm.html) |
| Gemma-3 1B | Intel Core i7-13800H (Surface Laptop Studio 2), 8 threads, llama.cpp, precision not stated; 128 tokens generated | not given | 41 ms/token | 1.4 GB (non-embedding) | [BitNet technical report](https://arxiv.org/html/2504.12285) |
| Llama 3.2 1B | same | not given | 48 ms/token | 2 GB | [BitNet technical report](https://arxiv.org/html/2504.12285) |
| Qwen2.5 1.5B | same | not given | 65 ms/token | 2.6 GB | [BitNet technical report](https://arxiv.org/html/2504.12285) |
| SmolLM2 1.7B | same | not given | 67 ms/token | 3.2 GB | [BitNet technical report](https://arxiv.org/html/2504.12285) |
| BitNet b1.58 2B4T | same CPU, 8 threads, bitnet.cpp | not given | 29 ms/token | 0.4 GB | [BitNet technical report](https://arxiv.org/html/2504.12285) |
| Phi-3-mini 3.8B | Azure Standard F64s v2 (64 vCPU), ONNX Runtime GenAI INT4; first 256 tokens | not given | 14.97 (16-token prompt), 14.47 (64), 13.32 (256), 10.14 (1024) | not given | [Phi-3 ONNX card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-onnx) |
| Phi-3-mini 3.8B | same VM, llama.cpp | not given | 13.57 (16), 10.39 (64), 10.31 (256), 9.83 (1024) | not given | [Phi-3 ONNX card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-onnx) |
| Granite 3.0 3B (a800m) Q8_0 | AMD Threadripper PRO 9995WX (96 cores), llama.cpp b7083, CPU BLAS backend | 215 to 237 (512-token prompt) | 88 to 91 | not given | [OpenBenchmarking](https://mail.openbenchmarking.org/result/2511187-PTS-LLAMACPP54&grs&export=html) |
| Llama-3.1-8B Q4_0 | AMD Ryzen 7950X, mainline llama.cpp (December 2024); 16 threads prefill, 2 threads decode | 153.5 | 11.2 | not given | [ik_llama.cpp discussion 164](https://github.com/ikawrakow/ik_llama.cpp/discussions/164) |
| Phi-4-mini 3.8B | AMD Ryzen 7 5700X, CPU; method not described | not given | 9 | not given | [PromptQuorum](https://www.promptquorum.com/local-llms/best-cpu-only-llm) |
| "Small" tier 0.5B to 1.5B (Falcon3, Qwen2.5, Gemma) | unnamed "edge CPU", llama.cpp with AVX2/FMA, 4 threads | not given | 20 to 30 | 0.7 to 2.5 GB peak | [edge-cpu-inference repo](https://github.com/nandan2003/edge-cpu-inference) |
| "Ultra-small" tier 15M to 160M | same | not given | 60 to 100+ | 0.15 to 0.4 GB | [edge-cpu-inference repo](https://github.com/nandan2003/edge-cpu-inference) |

Labelled extras (not desktop x86):

| Model | Device | Prefill | Decode | Memory | Source |
|---|---|---|---|---|---|
| FunctionGemma 270M, dynamic int8 | Samsung S25 Ultra CPU, LiteRT XNNPACK, 4 threads; 512 prefill, 32 decode | 1718 tok/s | 125.9 tok/s; time to first token 0.3 s | 288 MB file, 551 MB peak RSS | [FunctionGemma card](https://huggingface.co/google/functiongemma-270m-it) |
| LFM2.5-1.2B Q4_0 | Samsung S25 Ultra CPU, llama.cpp | 335 tok/s | 70 tok/s | 719 MB | [LFM2.5-1.2B card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) |
| Qwen3-1.7B Q4_0 | Samsung S25 Ultra CPU, llama.cpp | 181 tok/s | 40 tok/s | 1306 MB | [LFM2.5-1.2B card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) |
| LFM2.5-350M | Snapdragon Gen4 | not given | 188 tok/s | under 1 GB | [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M) |

Thread count, quantization and runtime effects:

- Going from 1 to 4 threads gave roughly a 2x decode speed-up; "Increasing from 4 to 8 threads often shows negligible gains or even performance regression"; the repository recommends 4 threads. — [edge-cpu-inference repo](https://github.com/nandan2003/edge-cpu-inference)
- On the Ryzen 7950X, the best token-generation rate for an 8B model was measured at 2 threads while prompt processing used 16; Q4_0 decode was 11.2 tok/s against 4.95 tok/s for Q8_0 and 4.05 tok/s for BF16 in mainline llama.cpp (4-bit about 2.3x faster to decode than 8-bit). — [ik_llama.cpp discussion 164](https://github.com/ikawrakow/ik_llama.cpp/discussions/164)
- The ik_llama.cpp fork processed prompts 1.8 to 3.3x faster than mainline on the same Ryzen 7950X (273.5 against 153.5 tok/s at Q4_0; 269.6 against 108.4 at Q4_K_S). — [ik_llama.cpp discussion 164](https://github.com/ikawrakow/ik_llama.cpp/discussions/164)
- ONNX Runtime GenAI INT4 was 1.10x to 1.39x faster than llama.cpp for prompts up to 256 tokens on the 64-vCPU VM, and slower (0.83x) at 2048 tokens (2024 figures). — [Phi-3 ONNX card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-onnx)
- 4-bit post-training quantization of Qwen2.5-1.5B cut non-embedding memory from 2.6 GB to 0.7 GB and lowered MMLU from 60.25 to 58.06 (GPTQ) or 57.43 (AWQ) and IFEval from 50.12 to 47.84 or 45.44. — [BitNet technical report](https://arxiv.org/html/2504.12285)
- llama.cpp's server reuses the KV cache from the previous request by default (`cache_prompt` true), "so only the unseen suffix of the prompt is evaluated"; slots can be saved to and restored from disk (`--slot-save-path`, `POST /slots/{id}?action=save|restore`); the response `timings` object reports `prompt_ms`, `prompt_per_second`, `predicted_ms`, `predicted_per_second` and `cache_n`. — [llama.cpp server README](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md)
- KRAFTON's PUBG Ally structures its prompt so that "stable instructions and gameplay context stay consistent across turns" and only the most relevant real-time information changes, specifically to make good use of the KV cache. — [NVIDIA developer blog](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- A per-label NLI classifier is far outside the budget on CPU: DeBERTa zero-shot classification took 1,714 ms for 5 labels, 6,758 ms for 20 and 16,897 ms for 50 (one forward pass per label). — [GLiNER2 paper](https://arxiv.org/html/2507.18546v1)

### Inferences
All figures in this block are ESTIMATES computed as prompt tokens / prefill rate + output tokens / decode rate, from the published rates above.

| Case (machine as published, whole CPU available, no game) | 150-token prefill | 20-token decode | Total |
|---|---|---|---|
| LFM2.5-1.2B Q4_0, Ryzen AI 9 HX 370 | 0.05 s | 0.17 s | about 0.22 s |
| Qwen3-1.7B Q4_0, Ryzen AI 9 HX 370 | 0.07 s | 0.32 s | about 0.40 s |
| LFM2.5-350M, "AMD CPU" (313 tok/s) | unknown | 0.06 s | roughly 0.1 s |
| FunctionGemma 270M int8, S25 Ultra phone CPU | 0.09 s | 0.16 s | about 0.25 s |
| Gemma-3 1B, i7-13800H, 8 threads (precision unknown) | unknown | 0.82 s | over 0.8 s |
| Llama 3.2 1B, i7-13800H, 8 threads | unknown | 0.96 s | about 1 s or more |
| Qwen2.5 1.5B, i7-13800H, 8 threads | unknown | 1.30 s | over 1.3 s |
| BitNet 2B, i7-13800H, 8 threads, bitnet.cpp | unknown | 0.58 s | over 0.6 s |
| Phi-3-mini INT4, 64 vCPU, ONNX Runtime GenAI | unknown | 1.38 s | over 1.4 s |
| Granite 3B Q8_0, 96-core Threadripper | 0.65 s | 0.22 s | about 0.87 s |

- The two families of numbers disagree by a wide margin. The i7-13800H measurements give 15 to 24 tok/s for 1B to 1.7B models; Liquid AI's own tables give 62 to 116 tok/s (and 239 tok/s on the model card) for the same class on a newer 12-core laptop CPU with Q4_0. Part of the gap is precision (the i7 memory figures match unquantized weights), part is CPU generation, and part is that vendor tables use the whole machine. Liquid's prefill rate (2,008 tok/s for a 1.7B transformer) is also about two to three times what linear scaling from the Ryzen 7950X result (153.5 tok/s at 8B, 16 threads) would predict. Treat vendor prefill figures as best case.
- ESTIMATE for the target (i9-10900K, AVX2 without AVX-512/VNNI, DDR4, 2 to 4 threads, game running): a 1B to 1.7B model at 4-bit is likely to decode at about 15 to 40 tok/s, so a 20-token answer costs about 0.5 to 1.3 s before prefill. That alone uses or exceeds the "well under a second" budget. A 270M to 350M model is likely three to four times faster, about 0.2 to 0.5 s in total. These ranges are extrapolations and must be measured.
- Consistency check with the team's own trial: scoring label options with Qwen2.5-1.5B took 5.4 s per line, which is in line with the 65 ms/token published for that model on an i7-13800H once dozens of label tokens are evaluated.
- What prompt caching saves: only the prefill of the fixed prefix. If 100 of the 150 prompt tokens are a stable prefix (instructions, schema, intent list), about two thirds of prefill disappears. At vendor-table rates that is only about 35 to 50 ms; at phone-class rates (181 to 335 tok/s) it is 0.3 to 0.55 s. Decode time is untouched, so with a warm cache the latency is governed almost entirely by the number of generated tokens.
- Consequence for output design: every generated token costs 10 to 65 ms on CPU in this class, so a compact output (a few enumerated tokens such as a relation code and an intent id) matters more than any prompt optimisation. A JSON object with keys can easily be 20 to 40 tokens; a grammar that forces the fixed keys lets a runtime with fast-forwarding skip sampling for them (see section 3).
- Thread contention: published evidence says gains stop at about 4 threads and that over-subscription lowers speed; with the game using most cores, 2 to 3 threads is the realistic allowance, and the model would compete with the classifier's 1 to 3 cores unless the two stages run strictly one after the other.

### Gaps
- No published llama.cpp, ONNX Runtime GenAI or OpenVINO GenAI measurement for Gemma 3 270M, FunctionGemma, Qwen3-0.6B, Qwen3.5-0.8B, Granite 4.0 350M or SmolLM2-360M on a named desktop x86 CPU was found. Searches returned GPU, Apple Silicon or formula-based estimates only.
- No measurement at all on Intel 10th-generation desktop CPUs, and none with a game or other heavy load running concurrently.
- No published OpenVINO GenAI or MLC or ExecuTorch desktop-CPU table for these models was found (OpenVINO results located were for server Xeons with Phi-3 or for NPUs).
- No published measurement of the time saved by KV-cache reuse on a short prompt; the saving above is arithmetic.
- No published model load time for these models on desktop CPUs.
- The precision used for the llama.cpp competitors in the BitNet report is not stated.

## 3. Structured output, function-calling benchmarks, and what narrow fine-tuning of a sub-1B model achieves

### Takeaway
Grammar or JSON-Schema constrained decoding guarantees a parseable order and, in the one broad benchmark available, did not reduce task accuracy (it raised it by 0 to 4 points), but it does not make the decision correct: after fine-tuning a 270M model, parse failures fell from 87% to under 1% while the remaining errors became wrong tool choice and wrong arguments. Narrow fine-tuning is what moves sub-1B models from roughly 40 to 60 percent to roughly 85 percent on their own task (FunctionGemma 58 to 85), and published results above 95 percent come from vendors' own test sets.

### Cited Findings
- JSONSchemaBench (10K real-world schemas; Llama-3.1-8B on the llama.cpp backend, medians): unconstrained time per output token 15.40 ms; Guidance (llguidance) 6.37 ms with 0.00 s grammar compilation; llama.cpp's own grammar engine 29.98 ms with 0.05 s compilation; Outlines 30.33 ms with 3.48 s compilation. — [JSONSchemaBench](https://arxiv.org/html/2501.10868v3)
- Same paper: "Constrained decoding can speed up the generation process by 50% compared to unconstrained decoding", attributed to fast-forwarding of forced tokens (total 0.50 s against 1.08 s unconstrained on the GlaiveAI set). — [JSONSchemaBench](https://arxiv.org/html/2501.10868v3)
- Same paper, downstream accuracy with Llama-3.1-8B: unconstrained 50.7% / 52.6% / 80.1% (Last Letters / Shuffle Objects / GSM8K); XGrammar 51.2 / 52.7 / 83.7; llama.cpp 52.0 / 52.6 / 82.4; Outlines 53.3 / 53.0 / 81.6; Guidance 54.0 / 55.9 / 83.8. Every constrained engine is at or above the unconstrained baseline. — [JSONSchemaBench](https://arxiv.org/html/2501.10868v3)
- Same paper, schema coverage on hard schemas (GitHub Hard): Guidance 0.41, llama.cpp 0.39, XGrammar 0.28, Outlines 0.03; on simple function-call-like schemas (GlaiveAI) all engines are at 0.93 to 0.96 against 0.90 unconstrained. — [JSONSchemaBench](https://arxiv.org/html/2501.10868v3)
- llguidance's README claims about 50 microseconds of CPU time per token for a 128k tokenizer with negligible start-up cost. — [llguidance README (mirror)](https://www.gitlink.org.cn/dnrops/llguidance)
- XGrammar's paper claims up to a 100x reduction in per-token latency for context-free grammars against earlier engines. — [XGrammar paper](https://arxiv.org/pdf/2411.15100)
- A third-party 2026 paper measured much higher mask cost for XGrammar on JSON Schemas with Llama 3 (about 26,000 microseconds per token) against about 73 microseconds for LLGuidance, so the self-reported and independent figures conflict. — [arXiv 2608.03065](https://arxiv.org/pdf/2608.03065)
- llama.cpp's server accepts a `grammar` (BNF-like) or a `json_schema` per request and `response_format` with schema-constrained JSON. — [llama.cpp server README](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md)
- ONNX Runtime GenAI documents constrained decoding through LLGuidance with three constraint types (Lark grammar, JSON schema, regex); the documentation found is a mirror and an older llguidance page listed the integration as a draft, so the shipping status needs checking in the official repository. — [ONNX Runtime GenAI guide (mirror)](https://www.mintlify.com/microsoft/onnxruntime-genai/guides/constrained-decoding)
- OpenVINO GenAI exposes `StructuredOutputConfig` (JSON schema, regex, EBNF grammar, structural tags); XGrammar states it was officially integrated into OpenVINO GenAI in September 2025. — [OpenVINO GenAI API](https://docs.openvino.ai/2025/api/genai_api/_autosummary/openvino_genai.StructuredOutputConfig.html); [XGrammar on PyPI](https://pypi.org/p/xgrammar)
- FunctionGemma 270M: 58% accuracy on Google's Mobile Actions evaluation before fine-tuning, 85% after. — [FunctionGemma card](https://huggingface.co/google/functiongemma-270m-it); [Google blog](https://blog.google/technology/developers/functiongemma/)
- A 270M FunctionGemma fine-tuned for Arabic tool calling (full-parameter supervised fine-tuning after dataset auditing and schema repair): parse failures fell from 87% to below 1% on the held-out set and function-name accuracy improved more than eightfold; remaining errors shifted "from structural collapse to semantic misalignment", and the authors conclude that "serialization stability and decision-level reasoning are separable challenges". — [arXiv 2603.16901](https://arxiv.org/abs/2603.16901)
- A fine-tuned facebook/opt-350m (one epoch, AWS authors) reports a 77.55% ToolBench pass rate against 26.00% for ChatGPT-CoT and 30.18% for ToolLLaMA-DFS; the result is listed as unreproduced. — [arXiv 2512.15943](https://arxiv.org/abs/2512.15943); [sotaverified.org](https://sotaverified.org/papers/251215943)
- Octopus v2 (about 2B, a fine-tuned on-device model) reports 99.5% function-call accuracy and 0.38 s latency on its own benchmark (GPU), against 45.7% and 10.2 s for Phi-3 with a RAG-style approach. — [Octopus v2 card](https://huggingface.co/NexaAIDev/Octopus-v2)
- TinyAgent: 1.1B model 80.06% success, 7B 84.95%, GPT-4-Turbo 79.08% on the authors' own Mac assistant function-calling task. — [TinyAgent paper](https://arxiv.org/html/2409.00608v3)
- Community reports on FunctionGemma (not official): base multi-turn tool-calling accuracy of about 10 to 39%, rising to roughly 90 to 97% after fine-tuning. — [Reddit snapshot](https://reddit.sentinel-team.org/posts/1r6gx75/snapshots/2026-02-17T00%3A30%3A13.01368Z)
- Out-of-the-box BFCL v3 for small general models: Qwen3-0.6B 44.1, Qwen3-1.7B 52.2, Qwen3-4B 57.6, Qwen2.5-1.5B 47.8, Phi-4-mini 31.3, Gemma-3-1B 16.3 (Alibaba); Granite 4.0 350M 39.32 and 1B 54.82 (IBM); LFM2.5-350M 44.11 and LFM2.5-1.2B 49.12 (Liquid); SmolLM2-1.7B 27% BFCL (Hugging Face). — [Qwen3 report](https://arxiv.org/abs/2505.09388); [Granite card](https://huggingface.co/ibm-granite/granite-4.0-350m); [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M); [SmolLM2 card](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct)
- IBM's ToolRM work reports that reward models used for best-of-n sampling raise small models' tool-calling accuracy by up to 25 percentage points (at the cost of n generations). Seen through a search summary only; the linked page was not opened. — [alphaXiv listing](https://alphaxiv.org/overview/2509.11963v1)

### Inferences
- For this bot the output space is tiny and closed (41 intents, a handful of places and directions, a relation to the previous order). A grammar can reduce the generated sequence to a few enumerated tokens, which removes format errors completely and cuts decode time; the published overhead of a good engine (tens of microseconds per token) is negligible beside a 10 to 65 ms CPU forward pass. llama.cpp's built-in grammar engine roughly doubled per-token time in JSONSchemaBench, so llguidance is the engine to prefer if llama.cpp is used.
- Constrained decoding fixes syntax only. The Arabic FunctionGemma result is the clearest published statement that the residual errors of a fine-tuned 270M model are wrong decisions, which is exactly the failure the team already saw with Qwen2.5-1.5B (71 percent of errors in the wrong intent family).
- Realistic expectation from published evidence: a sub-1B decoder fine-tuned on the team's own schema reaches about 85 percent on in-distribution tests in vendor-run evaluations; claims of 95 to 99 percent exist only on the authors' own narrow sets. The existing DeBERTa ensemble is already a fine-tuned narrow model, so a decoder would have to beat it specifically on the context-dependent lines.
- With a closed label set, generation is equivalent to classification done one token at a time; the "scoring label options" method the team tried is the expensive way to do this, and grammar-constrained generation of a single label token would cost one prefill plus a few decode steps instead of 41 scored continuations.

### Gaps
- No published function-calling benchmark covers dialogue-context commands for a game (corrections, repeats, deictic references); BFCL, ToolBench and the vendor sets are API-call tasks.
- BFCL leaderboard figures for late 2026 were not fetched directly; all BFCL numbers above are vendor-reported and use different leaderboard versions.
- The effect of constrained decoding on the accuracy of sub-1B models specifically was not found; JSONSchemaBench's quality test used an 8B model.
- "Small Language Models are the Future of Agentic AI" (NVIDIA position paper), NESTFUL, Nexus and the Hammer paper's tables were not read in this session.
- Grammar overhead measured on CPU (as opposed to GPU-hosted backends) was not found.

## 4. Reliability of very small models on short reasoning, and whether "thinking" modes help

### Takeaway
Published evidence for sub-2B models is consistent: instruction following is moderate (IFEval about 50 to 77 percent, with LFM2.5 as a vendor-reported outlier at 77 to 86), multi-turn instruction following is worse (Multi-IF 33 to 61 percent), and state tracking is a named dominant failure. Thinking modes add 2 to 8 points on BFCL at these sizes but do so by generating many extra tokens, which on CPU turns a sub-second answer into several seconds.

### Cited Findings
- Thinking against non-thinking on BFCL v3: Qwen3-0.6B 46.4 against 44.1; Qwen3-1.7B 56.6 against 52.2; Qwen3-4B 65.9 against 57.6. — [Qwen3 report](https://arxiv.org/abs/2505.09388)
- Multi-turn instruction following (Multi-IF): Qwen3-0.6B 33.3 non-thinking and 36.1 thinking; Qwen3-1.7B 44.7 and 51.2; Qwen3-4B 61.3 and 66.3; Gemma-3-1B 32.8; Phi-4-mini 40.5; Qwen2.5-1.5B 20.2. — [Qwen3 report](https://arxiv.org/abs/2505.09388)
- On BFCLv4, Qwen3.5-0.8B scores 25.39 with thinking and 18.70 in instruct mode. — [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M)
- The Qwen3.5 small models used 230 million or more output tokens to complete Artificial Analysis's index, "well above frontier models and Qwen3 predecessors"; the 4B variant has an 80% hallucination rate on AA-Omniscience. — [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- Distilled reasoning models can be worse at agent tasks than plain small models: DeepSeek-R1-Distill-Qwen-1.5B scores 14.0 on BFCL v3 and 13.3 on Multi-IF. — [Qwen3 report](https://arxiv.org/abs/2505.09388)
- CogniLoad (synthetic reasoning with tunable length and distractors): wrong final attribution from mistracking sequential updates was the most common non-context failure across models; a 1.5B distilled Qwen model often declared puzzles unsolvable at longer lengths; compact models showed instruction-following drift under load. — [CogniLoad](https://arxiv.org/pdf/2509.18458)
- An analysis of negation benchmarks found that increasing model size has almost no effect on negation handling, while instruction fine-tuning helped. — [*SEM 2023](https://aclanthology.org/2023.starsem-1.10.pdf)
- A 2026 study of reasoning models on theory-of-mind tasks found the gains from reasoning "selective rather than universal". — [arXiv 2602.10625](https://arxiv.org/pdf/2602.10625)
- A 2026 paper on small reasoning models reports that reflection mainly consolidates solutions that were already reachable rather than making new ones reachable, and that smaller reasoning models are less able to exploit external help. — [arXiv 2609.34327](https://arxiv.org/pdf/2609.34327)
- Google lists limited common-sense reasoning, weak handling of nuance and difficulty with open-ended or complex tasks among FunctionGemma's limitations. — [FunctionGemma card](https://huggingface.co/google/functiongemma-270m-it)
- Phi-4-mini-flash-reasoning is "designed and tested for math reasoning only". — [Phi-4-mini-flash-reasoning card](https://huggingface.co/microsoft/Phi-4-mini-flash-reasoning)
- Granite 4.0 Nano: the 350M models score 33.07 to 33.28 on BBH (3-shot, chain of thought) against 59.68 to 60.37 for the 1B models, and 55.4 to 61.6 against 77.4 to 78.5 on IFEval. — [Granite card](https://huggingface.co/ibm-granite/granite-4.0-350m)
- Zero-shot dialogue state tracking with function-calling prompts was shown to work at 7B to 13B scale (FnCTOD, ACL 2024); no result for 1B to 3B models was found. — [FnCTOD](https://arxiv.org/html/2402.10466v4)

### Inferences
- ESTIMATE: a thinking trace of even 100 to 300 tokens at 15 to 40 tok/s (the estimated range for a 1B to 1.7B model on the target, section 2) adds about 2.5 to 20 s; at the 100 to 300 tok/s vendor figures for 350M models it still adds 0.3 to 3 s. Thinking modes are therefore incompatible with the latency budget, and the published accuracy gain (2 to 8 BFCL points) does not close the gap to a fine-tuned narrow model.
- The step from 350M to 1B is large on reasoning-style benchmarks (BBH 33 to 60, Multi-IF 33 to 45 between Qwen3-0.6B and 1.7B), and the step from 1.7B to 4B is large again (Multi-IF 45 to 61). The sizes that fit the latency budget are the ones with the weakest multi-turn behaviour.
- What the owner calls "reasoning a very little" (resolve "here" to the standing pin, treat "no, ..." as a correction of the last order, "again" as a repeat) is state tracking over one or two turns. The published failure modes of small generative models are precisely state mistracking and drift, so the zero-shot route is unlikely to be reliable; a fine-tuned model that sees the state as structured input is the only form the evidence supports.

### Gaps
- No benchmark was found that measures sub-2B models on negation, coreference and one-step state tracking together, and nothing specific to coreference at this size.
- No published number for the length of thinking traces of Qwen3-0.6B / 1.7B or Qwen3.5-0.8B on short commands.
- BrainBench's per-category table for thinking modes was not read; its tested models are not sub-2B.

## 5. Non-generative alternatives at classifier cost

### Takeaway
At matched size encoders beat decoders on classification (a 400M encoder beats a 1B decoder on MNLI), and the newest schema-driven encoder classifier (GLiNER2.5-Decide, 340M, Apache-2.0, September 2026) reports beating 4B-class Qwen3.5 decoders on 17 decision tasks in a single forward pass. Voice-assistant research handles exactly this problem (carryover, repair, steering) with small non-autoregressive or pointer models rather than generative LLMs. The cheapest path with published support is to keep the encoder, put the dialogue state into its input, and add a second head for the relation to the previous order.

### Cited Findings
- Ettin (paired encoders and decoders from 17M to 1B trained with the same recipe on up to 2 trillion tokens): "A 400M encoder outperforms a 1B decoder on MNLI", the reverse holds for generation, and converting a decoder to encoder tasks by continued training is "subpar"; the Ettin encoders beat ModernBERT and the decoders beat Llama 3.2 and SmolLM2 at their sizes. — [Ettin paper](https://arxiv.org/abs/2507.11412)
- GLiNER2 (205M parameters, 2,048-token context, Apache-2.0) does entity recognition, text classification and hierarchical structured extraction from one schema in one forward pass. CPU latency for classification: 130 ms with 5 labels, 132 ms with 10, 163 ms with 20, 208 ms with 50 (CPU model and input length not stated); GLiClass 137 / 131 / 140 / 190 ms; GPT-4o by API 358 to 463 ms. — [GLiNER2 paper](https://arxiv.org/html/2507.18546v1)
- GLiNER2 zero-shot intent accuracy is below GPT-4o: SNIPS 0.83 against 0.97, Banking77 0.70 against 0.78, Amazon Intent 0.53 against 0.72 (DeBERTa-v3 NLI: 0.77 / 0.42 / 0.59). — [GLiNER2 paper](https://arxiv.org/html/2507.18546v1)
- GLiNER2.5-Decide (Fastino, 24 September 2026): 340M parameters on a DeBERTa-v3-large encoder, Apache-2.0, English; scores caller-supplied labels or typed questions and returns structured results with probabilities; several decision heads and multi-label heads are scored "in a single forward pass"; full or LoRA fine-tuning supported. It "does not reason, explain, or answer open questions". — [HF card](https://huggingface.co/fastino/GLiNER2.5-Decide)
- GLiNER2.5-Decide latency, batch 1, 64 tokens, two heads, 15-label schema, p50 end to end: 167.3 ms on a 48-vCPU Intel Xeon Platinum 8581C; 38.3 ms on an NVIDIA V100 (GPU, extra). — [Fastino blog](https://fastino.ai/blog/gliner-2-5-decide-open-weight-decision-model)
- On Fastino's own "Fast Decisions" suite (17 English datasets, 5,100 test examples, exact label-set match): GLiNER2.5-Decide 60.1 to 60.2%, a 1B variant 59.6%, JevK5 (Qwen3.5 4B-class decoder) 57.5 to 57.6%, SemIf (Qwen3.5-4B-based decoder) 56.4%, GLiFormer 49.0%, Laya (421M ModernBERT encoder) 46.6%. Vendor-run; prompt format for the decoders not described. — [Fastino blog](https://fastino.ai/blog/gliner-2-5-decide-open-weight-decision-model); [HF card](https://huggingface.co/fastino/GLiNER2.5-Decide)
- Apple's 5IDER is a single non-autoregressive query rewriter covering steering, intent carryover, disfluencies, entity carryover and repair; it is about 15 times smaller than a fine-tuned T5 and about 25 times faster. — [5IDER](https://arxiv.org/pdf/2306.01855)
- Apple's repetition-based recovery model uses a pointer network to merge the original utterance with the user's correction, with a 19% relative word-error-rate reduction at a 2% false-alarm rate against a rule-based baseline. — [arXiv 2108.01208](https://arxiv.org/abs/2108.01208v1)
- Amazon released a contextual query rewrite dataset for resolving referring expressions in spoken dialogue by reformulating the query. — [CQR dataset paper](https://ar5iv.labs.arxiv.org/html/1903.11783)
- Intent detection, SetFit against LLMs (Amazon, 2024): seven LLMs with adaptive in-context learning and chain of thought were compared with contrastively fine-tuned sentence-transformer (SetFit) models; a hybrid that routes to the LLM only on uncertainty reaches "within 2% of native LLM accuracy with 50% less latency"; SetFit-style encoders struggle with out-of-scope detection. — [arXiv 2410.01627](https://arxiv.org/abs/2410.01627)
- A 2026 workshop paper on multi-turn intent classification reports that RoBERTa-based classifiers trained on LLM-labelled transcripts and LLM-simulated multi-turn dialogues outperform zero-shot LLM prompting at substantially lower latency, and that a hybrid of classifier and LLM is better than either. — [ACL Anthology author listing](https://aclanthology.org/people/kaiqi-bian/)
- Natural-language-inference classifiers scale linearly with the number of labels on CPU (1.7 s at 5 labels, 16.9 s at 50). — [GLiNER2 paper](https://arxiv.org/html/2507.18546v1)

### Inferences
- The decision the owner wants has a closed form: {relation to previous order: new / repeat / correct / refine / cancel / ask} plus the completed order fields. That is a multi-head classification over (state, utterance), which published evidence says encoders do better than same-size decoders, in one forward pass, with calibrated probabilities that the deterministic planner can threshold for "ask".
- Three encoder designs follow from the sources, in rising cost: (a) serialise the state (last intent, last place, pin present or not, a few world facts) as extra tokens in the existing DeBERTa input and add a relation head; (b) a separate small "context resolver" encoder that runs only when the utterance carries a context cue; (c) a schema-driven model of the GLiNER2 family fine-tuned on the team's decisions.
- ESTIMATE: option (a) lengthens the input from a short command to perhaps 50 to 80 tokens, which would raise the ensemble's 40 to 70 ms to roughly 100 to 200 ms if all three models read the context; running the context only through one model, or through a separate head-only model, keeps it lower. This needs measurement.
- ESTIMATE: GLiNER2.5-Decide's 167 ms was measured on 48 server vCPUs with a DeBERTa-v3-large encoder (about three times the size of the team's DeBERTa-v3-base). On 2 to 3 desktop cores it would probably take several hundred milliseconds, so the released checkpoint is too heavy as a third stage; the 205M GLiNER2 or the team's own base-size encoder with extra heads is the form that fits.
- Rewriting ("no, here, on my pin" becomes "hold position at pin") is attractive because the existing classifier and planner stay unchanged, but an autoregressive T5-class rewriter pays the same per-token decode cost as a small LLM; Apple's result suggests a non-autoregressive tagger or pointer model for this job.
- The hybrid pattern (cheap encoder always, generative model only when the encoder is uncertain) is the published way to keep average latency low; here the "expensive" branch could equally be a clarifying question to the player.

### Gaps
- No published CPU latency for T5-small, Flan-T5-small or ByT5-small rewriting was collected; no published comparison of these against small decoders on context carryover.
- No published results for NuExtract-tiny-class extraction models or TANL-style extraction were collected in this session.
- No published k-NN-over-embeddings result for context-dependent commands was found; SetFit is the nearest published relative.
- No independent evaluation of GLiNER2.5-Decide exists yet (released 24 September 2026; model card lists no CPU latency, no ONNX export note and no maximum input length).
- No published study adds dialogue-state tokens to a DeBERTa-class intent classifier for game or voice commands with before and after accuracy; the relation-to-previous-order head is supported by analogy with the Apple steering, carryover and repair work, not by a direct benchmark.
- The Ettin finding was read from the abstract only; the size-matched tables were not fetched.

## 6. ModernBERT and other 2025 to 2026 encoders as a base instead of DeBERTa-v3-base

### Takeaway
ModernBERT-base is faster than DeBERTa-v3-base and exports and quantizes cleanly, but it is not clearly more accurate: its own card shows 88.4 against 88.1 on GLUE, and a controlled study that held the training data constant found DeBERTaV3 keeps better sample efficiency and overall benchmark performance while ModernBERT is more sensitive to learning rate. The practical reason to switch is quantization and speed, since the same disentangled-attention design that makes DeBERTa slow is also what resists int8 conversion.

### Cited Findings
- ModernBERT: base 149M parameters and 22 layers, large 395M and 28 layers; native context 8,192 tokens; Apache-2.0; RoPE, alternating local and global attention, unpadding, Flash Attention; no token type IDs; trained on English and code; GLUE 88.4 against 88.1 for DeBERTaV3-base. — [ModernBERT card](https://huggingface.co/answerdotai/ModernBERT-base)
- The ModernBERT paper reports DeBERTaV3 using 5 to 7 times more memory and running about two times slower, and attributes much of the gap to unpadding and FlashAttention, which DeBERTa lacks (GPU measurements). — [ModernBERT paper](https://arxiv.org/pdf/2412.13663)
- Controlled comparison with identical pretraining data: ModernBERT "does not consistently outperform DeBERTaV3" on standard NLU tasks; it offers faster training and inference, while its fine-tuning "may be more brittle in practice" and is sensitive to learning rate. — [ModernBERT or DeBERTaV3?](https://arxiv.org/pdf/2504.08716)
- A model card comparing dynamic int8 export reports that only 50.3% of MatMul nodes in DeBERTa-v3-large were quantized (described as broken), whereas ModernBERT-base "round-trips through quantize_dynamic cleanly"; the ModernBERT int8 variant lost recall (macro F0.5 0.9165 to 0.8944, about 3.4% fewer accepted items) with precision held. Author's own diagnostic. — [HF model card](https://huggingface.co/Bei0001/modernbert-concept-verifier-onnx)
- ModernBERT-large (421M with head) on CPU: 382.4 ms in fp32 against 134.7 ms with ONNX int8 per-channel dynamic quantization, with no accuracy loss on the author's task (CPU not named). — [HF model card](https://huggingface.co/saipy10/qlaya)
- Reference point for a small encoder at sequence length 128: DistilBERT ONNX int8 p50 18.8 ms, a 4.06x speed-up, with 0.46 points lost on SST-2. — [inference-lab repo](https://github.com/SaiArrow/inference-lab)
- Vespa reports CPU int8 embedding models running 2.7 to 3.4 times faster while keeping 94 to 98% of quality, and ModernBERT-based embedders holding up well under quantization. — [Vespa blog](https://blog.vespa.ai/embedding-tradeoffs-quantified/)
- CPU int8 gains depend on the instruction set: BERT-base got only a 25% single-core speed-up from ONNX quantization on an instance without AVX512-VNNI, because before VNNI the vector units could not operate natively on int8 data. — [Towards Data Science](https://towardsdatascience.com/speeding-up-bert-inference-different-approaches-40863b2954c4/)
- NeoBERT: 250M parameters, 4,096-token context, GLUE 89.0, and state-of-the-art MTEB among compared encoders (BERT-large, RoBERTa-large, NomicBERT, ModernBERT) under identical fine-tuning; self-reported. — [NeoBERT paper](https://arxiv.org/abs/2502.19587v2)
- EuroBERT: 210M, 610M and 2.1B parameter models, up to 8,192 tokens, 15 languages plus mathematics and code, Apache-2.0; usage examples pass `trust_remote_code=True`; no English-only classification numbers on the card. — [EuroBERT card](https://huggingface.co/EuroBERT/EuroBERT-210m)
- LFM2.5-Encoder-230M and -350M (Liquid AI, article dated 30 July 2026): bidirectional encoders with 8,192-token context; on 17 classification and understanding tasks the 230M model reportedly beats ModernBERT-base and every EuroBERT variant; at the full 8,192 tokens on CPU a forward pass takes about 28 s against about 90 s for ModernBERT-base (hardware not specified); self-reported. — [AI Weekly](https://aiweekly.co/alerts/liquid-ais-lfm25-encoders-punch-above-their-size-on-cpu)
- Ettin encoders (17M to 1B) outperform ModernBERT at matched sizes according to their authors. — [Ettin paper](https://arxiv.org/abs/2507.11412)

### Inferences
- For short English commands the accuracy case for leaving DeBERTa-v3-base is weak: the one controlled study favours DeBERTaV3 on accuracy and the headline GLUE gap is 0.3 points. The case rests on engineering: ModernBERT uses ordinary attention with rotary positions, so ONNX dynamic quantization covers the whole graph, whereas DeBERTa's relative-position attention leaves about half of the matrix multiplications unquantized in the one report found. That matches the team's own finding that int8 broke DeBERTa-v3-base.
- On an i9-10900K the int8 benefit is limited whichever encoder is used: Comet Lake has AVX2 but no AVX512-VNNI (from general knowledge of the CPU, not re-checked against Intel's specification page in this session), and the published single-core gain without VNNI was about 25%. Newer CPUs in the player base would gain more.
- ModernBERT's advertised speed advantages (unpadding, Flash Attention, long context) are GPU and long-sequence features; for inputs of 20 to 80 tokens on CPU the gain is mainly from simpler attention and has to be measured. ModernBERT-base has 22 layers against 12 for DeBERTa-v3-base (the DeBERTa layer count is from general knowledge, not re-fetched), so it is not automatically faster per forward pass on CPU.
- A lower-risk experiment than replacing the ensemble is to train one ModernBERT-base (or Ettin encoder) member with the context-augmented input and compare it against a DeBERTa member on the same data, checking fp32 and int8 separately.
- LFM2.5 encoders would bring the 10 million USD revenue condition if they are under the LFM Open License; the secondary source did not confirm their license.

### Gaps
- No like-for-like CPU benchmark of ModernBERT-base against DeBERTa-v3-base on short inputs with ONNX Runtime (fp32 and int8, same hardware) was found.
- No published measurement of int8 accuracy loss for DeBERTa-v3-base specifically (the report found is for DeBERTa-v3-large, from a model card).
- NeoBERT's license and ONNX export status were not confirmed; Ettin's license was not confirmed; LFM2.5 encoders' license and primary benchmark table were not read (primary source: liquid.ai/blog/lfm2-5-encoders).
- No English short-text intent benchmark comparing these encoders was found.

## 7. Distilling a large LLM's contextual interpretation into a small encoder or sub-1B decoder

### Takeaway
The published pattern is consistent and matches the shipped game example: a large teacher given a deterministic specification writes or labels grounded examples, and a small student trained on them matches or beats zero-shot prompting of large models on the narrow task (PUBG Ally's 2B on-device model, RoBERTa and other small students in multi-turn intent work, 3 to 4B students matching 70 to 120B teachers on ten datasets). Exact data volumes are rarely published, and diversity of the synthetic data is the documented weak point.

### Cited Findings
- KRAFTON's PUBG Ally: a larger teacher model received a deterministic PUBG specification in its system prompt and produced grounded responses including tool use; these behaviours were distilled into the on-device 2B student; the domain was narrowed to one map, one mode and a fixed item taxonomy; language data came from research on how players actually speak, reviewed by language experts; dataset sizes are not disclosed. — [NVIDIA developer blog](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- Shopee and collaborators (AAAI-26): C-LARA uses LLMs for data augmentation and pseudo-labelling to create synthetic multi-turn dialogues that train a small model for deployment; reported gains are 5.09% in classification accuracy and a 40% cut in annotation cost on multilingual dialogue data; Symbol Tuning simplifies intent labels to make the multi-turn task easier. — [AAAI-26 paper](https://ojs.aaai.org/index.php/AAAI/article/view/41442)
- A 2026 workshop paper on multi-turn intent classification with LLM-based labelling: explanation-guided labelling with a self-critique step gives the most accurate training labels; RoBERTa models trained this way beat zero-shot LLM prompting at much lower latency. — [ACL Anthology author listing](https://aclanthology.org/people/kaiqi-bian/)
- distil labs (keynote paper): starting from a task description and 10 to 50 labelled examples, with teacher-generated synthetic data, rule-based validators and distillation, "distilled 3–4B parameter students consistently match or exceed 70–120B parameter teachers while being 20–30× smaller" across two teacher and student pairings on 10 datasets. Vendor source. — [CEUR-WS keynote](https://ceur-ws.org/Vol-4200/keynote2.pdf)
- distil labs, text-to-SQL example: base Qwen3-0.6B 36% (LLM-judge score), teacher 80%, fine-tuned Qwen3-0.6B 74%. Single vendor-run task. — [Reddit snapshot](https://reddit.sentinel-team.org/posts/1qiu6jo/snapshots/2026-01-21T17%3A11%3A35.0614Z)
- Fuchs et al. (WWW Companion 2025) study LLM-generated annotations for BERT-style student classifiers, comparing a cascade from GPT-4 through a 7B model to BERT with a self-training route that avoids proprietary models. — [BGU publication record](https://cris.bgu.ac.il/en/publications/enhancing-data-annotation-for-student-models-a-self-training-appr/)
- SynthesizRR: plain few-shot prompting of a teacher yields repetitive, low-diversity inputs that carry the teacher's biases into the student; retrieval augmentation is proposed to raise diversity. — [SynthesizRR](https://arxiv.org/html/2405.10040v3)
- FunctionGemma is positioned by Google as a base to be fine-tuned on a product's own function set (58% to 85% on Mobile Actions). — [FunctionGemma card](https://huggingface.co/google/functiongemma-270m-it)
- License side effect: under the Gemma terms a model trained on synthetic outputs of Gemma, or distilled from it, is a "Model Derivative" bound by the same terms. — [Gemma Terms of Use](https://ai.google.dev/gemma/terms)

### Inferences
- The route best supported by evidence for this bot: write a deterministic specification of the contextual rules (what "here", "again", "no, ..." mean given pin, last order and world facts), have a large teacher generate and label short two-turn dialogues grounded in that specification, validate them with rules (the existing planner can act as a validator), and train the student. The student can be an encoder head just as well as a decoder; the cited multi-turn intent papers use encoders.
- The teacher should not be a Gemma model if the student is to stay free of the Gemma terms; the same check applies to any teacher whose terms restrict training on outputs.
- Synthetic two-turn dialogues need deliberate diversity (speech-recognition errors, elliptical phrasing, real player wording), otherwise the student learns the teacher's templates; KRAFTON's use of real player language research and expert review points the same way.
- The 10 to 50 seed examples quoted by distil labs describe what a human must supply, not the size of the synthetic set, which is not stated.

### Gaps
- No source states how many synthetic examples are needed per intent or per context relation for a 100M to 350M student to retain a given share of the teacher's accuracy.
- No published distillation result exists for a game-command domain with accuracy figures (KRAFTON's write-up gives none).
- "Distilling Step-by-Step" and other rationale-distillation papers were not re-read in this session.
- The workshop paper's exact URL and numbers were seen only through a search summary.

## 8. Running a second model beside ONNX Runtime in a game helper process, runtime licenses, and shipped experience

### Takeaway
Every shipped on-device small-LLM game feature found runs on an NVIDIA RTX GPU: PUBG Ally (2B model) requires an RTX GPU with at least 8 GB of VRAM and disables the mode otherwise, and Mecha BREAK's 4B model needs about 2 GB of VRAM. NVIDIA's SDK lists a CPU path for its language plugin and even bundles Qwen3-0.6B, but no published account of a commercial PC game shipping an LLM on CPU with measured latency was found, and the anecdotal CPU reports are in the range of many seconds.

### Cited Findings
- PUBG Ally runs entirely on-device with speech recognition, Mistral-NeMo-Minitron-2B (further quantized) and an in-house TTS; the quantized model fits in the VRAM left after PUBG, allowing GPUs with as little as 8 GB of total VRAM. — [NVIDIA developer blog](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- KRAFTON's minimum for the mode is an RTX 2080 Ti or RTX 3060 with at least 8 GB VRAM and 16 GB RAM; recommended RTX 4070, 12 GB VRAM, 24 GB RAM; the mode is available only on PCs with a GeForce RTX card and the Play button is disabled otherwise. — [tbreak](https://tbreak.com/pubg-ally-ai-teammate-rtx-requirements/)
- Architecture of PUBG Ally: a behaviour tree ("System 1") executes movement, aiming and immediate combat at game tick rate; the language model ("System 2") handles intent interpretation, coordination and speech; game state reaches the model through observation tools returning plain-text slices of authoritative engine data, declared in the system prompt to be "the only ground truth for the current match"; short-term memory holds recent player speech and events. Deciding the boundary between the two systems "was a major engineering effort". No latency figures are published. — [NVIDIA developer blog](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- Mecha BREAK's ACE character uses a Minitron 4B-class model needing about 2 GB of VRAM and runs locally on RTX GPUs from the RTX 2060 up; the developers did not say how it behaves without an RTX GPU. — [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidias-first-ai-npc-debuts-in-mecha-break-minitron-4b-model-only-requires-2gb-of-vram)
- NVIDIA In-Game Inferencing SDK (NVIGI) runs models in-process through C++ with backends including TensorRT, ONNX Runtime and llama.cpp; the language plugin ("GPT Local GGML") runs on a CUDA GPU or on the CPU and currently lists Nemotron 3 Nano 4B, Nemotron 2 Nano 9B, Qwen3-0.6B, Qwen3.5-4B and Qwen3.5-8B; the speech recognition and TTS plugins are CUDA-GPU only. The SDK is described as open source; license terms are not stated on the page. — [NVIDIA NVIGI page](https://developer.nvidia.com/rtx/in-game-inferencing)
- NVIDIA's ACE model archive describes its on-device models (Llama 3.2 3B, Minitron 2B / 4B / 8B, Qwen3 8B Q4_K_M, Whisper) as "compatible with multi-vendor GPUs and CPUs" and gives no CPU performance figures. — [NVIDIA ACE model archive](https://forums.developer.nvidia.com/t/nvidia-ace-model-archive/362682)
- CPU anecdotes: a player report of a 3B model running CPU-only on a 12-core machine taking about 14 s for one response, causing a time-out; a development build bundling a llama.cpp runtime with Qwen3 8B Q4 for 16 GB RAM, no-GPU machines recorded a 15.8 s JSON-schema smoke test (unshipped). — [itch.io comment](https://sgthale.itch.io/myrobot/comments?after=152); [llm-ttrpg issue](https://github.com/herringvoices/llm-ttrpg/issues/38)
- A 2026 developer guide states that small quantized models run on CPU "slowly" and calls a mid-range GPU the practical floor for responsive dialogue in a shipping game. — [Eposyne guide](https://www.eposyne.com/insights/run-local-llm-game-npcs)
- Memory in use for the small candidates: FunctionGemma 270M int8 288 MB file and 551 MB peak RSS; LFM2.5-350M under 1 GB; LFM2.5-1.2B Q4_0 719 to 856 MB; Qwen3-1.7B Q4_0 1,306 to 1,465 MB; Qwen3.5-0.8B and 2B under 2 GB at about 4 bits, 4B about 3 GB; BitNet 2B 0.4 GB non-embedding. — [FunctionGemma card](https://huggingface.co/google/functiongemma-270m-it); [LFM2.5-350M card](https://huggingface.co/LiquidAI/LFM2.5-350M); [Liquid AI blog](https://www.liquid.ai/blog/introducing-lfm2-5-the-next-generation-of-on-device-ai); [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models); [BitNet card](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T)
- llama.cpp exposes separate thread counts for generation and for prompt processing (`--threads`, `--threads-batch`), CPU affinity (`--cpu-mask`, `--cpu-range`), process priority (`--prio` from low to realtime) and a load mode that locks the model in RAM (`mlock`). — [llama.cpp server README](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md)
- Thread over-subscription lowers throughput: gains flatten or reverse beyond 4 threads on an edge CPU. — [edge-cpu-inference repo](https://github.com/nandan2003/edge-cpu-inference)
- BitNet's efficiency requires its own runtime: "you MUST use the dedicated C++ implementation" (bitnet.cpp); weights and code are MIT. — [BitNet card](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T)
- Granite 4.0's hybrid-SSM variants lack optimised support in llama.cpp, which is why IBM ships plain transformer variants of the Nano models. — [IBM Granite Nano blog](https://huggingface.co/blog/ibm-granite/granite-4-nano)
- ONNX Runtime GenAI ships INT4 CPU builds of Phi models under MIT (model card), showing the same vendor stack the team already uses can host a decoder. — [Phi-3 ONNX card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-onnx)

### Inferences
- A generative stage adds, on top of the present 2.3 GB, about 0.3 to 0.6 GB for a 270M to 350M model and about 0.8 to 1.5 GB for a 1.2B to 1.7B model at 4 bits, plus a second runtime in the helper process unless ONNX Runtime GenAI is used. An extra encoder head adds essentially nothing; an extra encoder model adds a few hundred megabytes.
- The industry's shipped designs put the language model on the GPU and keep the fast loop deterministic. The team's constraint (CPU only, game using most of the machine) is outside what any published shipped title does, which is itself evidence that a CPU-hosted decoder in the per-utterance path is unproven.
- PUBG Ally's split (deterministic layer executes, language model only interprets and coordinates, state arrives as authoritative text, prompt kept stable for the KV cache) is the same shape as the team's planner plus a possible interpreter stage; it transfers directly whether the interpreter is a decoder or an encoder head.
- If a decoder is tried, the lowest-friction integration is sequential execution (classifier first, then decoder, never concurrently), a fixed small thread count with affinity away from the game's main threads, low-but-not-idle priority, the model locked in RAM, and a warm KV cache holding the fixed prefix.
- Runtime licenses named in the brief (llama.cpp MIT, ONNX Runtime MIT, OpenVINO Apache-2.0) were not re-verified in this session; none of the pages read contradicts them.

### Gaps
- No published account of a commercial PC game shipping an LLM on CPU with measured per-response latency was found.
- No NVIDIA-published CPU performance or minimum CPU requirement for the NVIGI GGML CPU path was found; NVIGI's license text was not read.
- No published measurement of memory-bandwidth or cache contention between a game and a concurrently running small LLM on the same CPU was found.
- No published load-time figures for sub-2B GGUF or ONNX decoders on desktop SSDs were found.
- Licenses of NVIDIA's Minitron and Nemotron Nano models were not checked.
