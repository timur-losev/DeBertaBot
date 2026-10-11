# Open-vocabulary 2D perception models and small VLMs: CPU feasibility and licenses (state as of 2026-10-10)

Reader context: game-AI team, Unreal Engine 5.8, C++, ONNX Runtime 1.28, commercial product. Option (a) = runtime on the player's machine (GPU busy, CPU budget near the current text classifier: about 40 ms on 3 cores of an Intel i9-10900K). Option (b) = offline labelling at build time in the editor.

Method caveats that apply to every section:
- Numbers were read from primary pages (GitHub READMEs, Hugging Face cards, arXiv HTML, vendor docs) through an automated page reader. Flattened tables can shift columns. Any number that drives a decision should be re-read at the linked source.
- Benchmarks from different papers use different protocols (AP vs Fixed AP, LVIS minival vs val, F1@0.5 vs mAP). They are listed side by side for orientation, not as a ranking.
- "No CPU figure published" means none was found in the sources searched, not that none exists.
- No measurement in this file was made on an i9-10900K. All CPU figures are from other machines, named where the source names them.

## 1. Open-vocabulary detectors: Grounding DINO family, OWL-ViT / OWLv2, YOLO-World, YOLOE, and 2026 additions

### Takeaway
Transformer open-vocabulary detectors (Grounding DINO, OWLv2) cost 1.5 to 3.4 seconds per image on 10-core desktop CPUs, which is 40 to 85 times the 40 ms budget, and the strongest IDEA models (Grounding DINO 1.5 / 1.6, DINO-X) are hosted-API only. The only family that reaches closed-set YOLO cost on CPU is YOLO-World / YOLOE (vocabulary baked in at export), and it is GPL-3.0 or AGPL-3.0; the permissively licensed open-weight options (Grounding DINO 1.0, MM-Grounding-DINO / LLMDet, OWLv2, OmDet-Turbo) are build-time tools, not runtime ones.

### Cited Findings

#### Grounding DINO 1.0 (open weights)
- Checkpoints: GroundingDINO-T (Swin-T, trained on O365, GoldG, Cap4M) with 48.4 COCO zero-shot AP and 57.2 fine-tuned; GroundingDINO-B (Swin-B) with 56.7 COCO AP, but its training data includes COCO, so that figure is not zero-shot. — [IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)
- The same README states 52.5 COCO zero-shot AP and 63.0 fine-tuned in its highlights (best model), and 48.5 in its evaluation section versus 48.4 in its table; the page is internally inconsistent by 0.1. — [IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)
- GroundingDINO-T has 172M parameters and scores 27.4 AP (APr 18.1) zero-shot on LVIS minival; GLIP-T has 232M and 26.0 AP. — [YOLOE paper, Table 1](https://arxiv.org/html/2503.07465)
- License: the repository is Apache-2.0; no separate license is given for the weights. — [IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO); contradicted by a practitioner guide that calls the 1.0 weights "research-use only" without citing a license text — [Fora Soft, 2026-05-24](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr)
- CPU-only mode is supported by the official code (`--cpu-only`, added 2023-03-27). — [IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)
- ONNX: `onnx-community/grounding-dino-tiny-ONNX` on Hugging Face ships full-precision, fp16, int8, uint8, q4 and other variants, tagged for Transformers.js. — [onnx-community/grounding-dino-tiny-ONNX](https://huggingface.co/onnx-community/grounding-dino-tiny-ONNX/tree/main/onnx)
- An export recipe exists that patches an unsupported `aten::__ior__` operator at opset 16 and wraps the forward pass to return only logits and boxes; it was written against a tiny random test model, not the real checkpoint. — [hf-internal-testing/tiny-random-GroundingDinoForObjectDetection](https://huggingface.co/hf-internal-testing/tiny-random-GroundingDinoForObjectDetection)
- Measured latency, Grounding DINO (variant not named, input 1200×800, prompt "dog"), mean ± std in ms. — [Benchmarking Edge Inference Strategies, arXiv 2607.11356, July 2026](https://arxiv.org/html/2607.11356)

| Device | PyTorch | ONNX Runtime | OpenVINO | TensorRT |
|---|---|---|---|---|
| Intel Core i7-6700 (4C/8T) | 7560 ± 190 | 11373 ± 39 | 6660 ± 100 | n/a |
| Intel Xeon E5-1650 v4 (6C/12T) | 3044 ± 19 | 5330 ± 470 | 2920.3 ± 7.6 | n/a |
| Intel Core i9-9820X (10C/20T) | 2450 ± 170 | 3388 ± 55 | 1479 ± 27 | n/a |
| Jetson AGX Orin, CPU | 24964 ± 305 | 13580 ± 310 | 102720 ± 290 | n/a |
| NVIDIA GTX 1650 | 549.67 ± 0.74 | 1082.34 ± 0.60 | n/a | 878.48 ± 0.34 |
| NVIDIA RTX 2080 Ti | 133.5 ± 1.3 | 250.4 ± 2.9 | n/a | 268 ± 10 |
| Quadro RTX 6000 | 123.0 ± 1.5 | 207.4 ± 2.2 | n/a | 213.2 ± 2.8 |

- In the same paper ONNX Runtime was slower than plain PyTorch for Grounding DINO on every Intel CPU and every desktop GPU, and TensorRT did not beat PyTorch on desktop GPUs; for YOLOv8 (640×640) the i9-9820X took 24.1 ± 1.5 ms in ONNX Runtime and 10.9 ± 1.2 ms in OpenVINO. — [arXiv 2607.11356](https://arxiv.org/html/2607.11356)
- OpenCV's CPU benchmark page (ONNX Runtime 1.25.1, wiki edited 2026-06-05) lists Grounding DINO at 1862 ms on "Intel i9", 4459 ms on "Intel i7", 3941 ms on Apple M1, 2986 ms on "AMD". The page does not give exact CPU models, thread counts, input sizes or model variants. — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- A secondary source gives 100 to 200 ms per image on an A100 for the original family. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr)

#### Grounding DINO 1.5 / 1.6 and DINO-X (hosted API)
- Zero-shot box AP, COCO / LVIS-minival (all, rare) / LVIS-val (all, rare): Grounding DINO 1.5 Pro 54.3 / 55.7, 56.1 / 47.6, 44.6; Grounding DINO 1.6 Pro 55.4 / 57.7, 57.5 / 51.1, 51.5. — [Grounding-DINO-1.5-API](https://github.com/IDEA-Research/Grounding-DINO-1.5-API)
- DINO-X Pro: 56.0 COCO, 59.7 LVIS-minival (63.3 rare), 52.4 LVIS-val (56.5 rare); mask AP 37.9 COCO, 43.8 LVIS-minival, 38.5 LVIS-val. The README highlights say 59.8 for LVIS-minival while its table says 59.7. — [DINO-X-API](https://github.com/IDEA-Research/DINO-X-API)
- Access: both READMEs say the models "are hosted on DeepDataSpace" and require an API token; neither states that weights are released. The repositories themselves (example code) are Apache-2.0. — [Grounding-DINO-1.5-API](https://github.com/IDEA-Research/Grounding-DINO-1.5-API); [DINO-X-API](https://github.com/IDEA-Research/DINO-X-API)
- Grounding DINO 1.5 Edge: 36.2 zero-shot AP on LVIS-minival at 75.2 FPS with TensorRT (speed table measured on an A100), and over 10 FPS on NVIDIA Orin NX at 640×640. — [Grounding DINO 1.5 paper, arXiv 2405.10300](https://arxiv.org/abs/2405.10300)
- A later comparison table lists "G-1.5 Edge" (EfficientViT-L1 backbone) at 33.5 AP on LVIS minival. — [OV-DEIM, Table 2](https://arxiv.org/html/2603.07022)
- No release newer than these was found: the latest news entry in the DINO-X API repo is 2025-07-23 (SDK update), the latest model items are DINO-XSeeK (2025-03-11) and an MCP server (2025-06-18); "Grounding DINO 2" is not mentioned. — [DINO-X-API](https://github.com/IDEA-Research/DINO-X-API)
- Rex-Omni (IDEA, released 2025-10-15, last update 2026-01-10): a 3B-parameter multimodal LLM that does detection, pointing, keypoints, OCR and GUI grounding as next-token prediction; weights are openly downloadable (full and AWQ-quantized); license is "IDEA License 1.0", and the base model Qwen2.5-VL-3B-Instruct is governed by the Qwen Research License Agreement. — [IDEA-Research/Rex-Omni](https://github.com/IDEA-Research/Rex-Omni)

#### MM-Grounding-DINO / LLMDet (open weights, Apache-2.0)
- LLMDet zero-shot LVIS, Fixed AP, minival / val: Swin-T 44.7 / 34.9; Swin-B 48.3 / 38.5; Swin-L 51.1 / 42.0; Swin-L with chunk size 80: 52.4 / 43.2. Rare-class AP on minival: 37.3, 40.8, 45.1. — [iSEE-Laboratory/LLMDet](https://github.com/iSEE-Laboratory/LLMDet)
- Code license Apache 2.0; merged into `transformers` 4.55.0 (2025-08-06) as `AutoModelForZeroShotObjectDetection`. — [iSEE-Laboratory/LLMDet](https://github.com/iSEE-Laboratory/LLMDet)
- The `llmdet_tiny` Hugging Face card lists license apache-2.0 and 0.2B parameters; released checkpoints do not include the LLM used during training, and inference is identical to MM Grounding DINO. — [iSEE-Laboratory/llmdet_tiny](https://huggingface.co/iSEE-Laboratory/llmdet_tiny)

#### OWL-ViT / OWLv2 (Google)
- LVIS AP / APrare from the official evaluator: OWLv1 CLIP B/16 20.8 / 17.1, CLIP L/14 34.6 / 31.2; OWLv2 CLIP B/16 self-trained 26.5 / 29.5, self-trained + fine-tuned 41.4 / 36.2, ensemble 43.9 / 40.5; OWLv2 CLIP L/14 self-trained 32.8 / 34.6, self-trained + fine-tuned 48.8 / 44.0, ensemble 44.6 / 42.6. The fine-tuned variants were fine-tuned on LVIS base classes, so only the "self-trained" rows are fully zero-shot on LVIS. — [scenic OWL-ViT README](https://github.com/google-research/scenic/blob/main/scenic/projects/owl_vit/README.md)
- The same README's introduction cites "44.6% zero-shot LVIS APr" for OWLv2 L/14 while its table lists 44.6 as AP and 42.6 as APr for the ensemble; treat the README as inconsistent. — [scenic OWL-ViT README](https://github.com/google-research/scenic/blob/main/scenic/projects/owl_vit/README.md)
- License: code and checkpoints are Apache 2.0. — [scenic OWL-ViT README](https://github.com/google-research/scenic/blob/main/scenic/projects/owl_vit/README.md)
- Parameter counts: OWLv2 B/16 ensemble 155M, L/14 ensemble 438M (third-party listing). — [PromptLayer B/16](https://www.promptlayer.com/models/owlv2-base-patch16-ensemble); [PromptLayer L/14](https://www.promptlayer.com/models/owlv2-large-patch14-ensemble)
- "Inference speed is dominated by the image and text encoders"; with precomputed text embeddings the cost is nearly that of a plain Vision Transformer. — [scenic OWL-ViT README](https://github.com/google-research/scenic/blob/main/scenic/projects/owl_vit/README.md)
- CPU, ONNX Runtime 1.25.1: "owlv2" (variant unspecified) 1542.6 ms on "Intel i9", 3809 ms on "Intel i7", 1722.6 ms on "AMD". — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- A secondary source gives about 50 to 80 ms on a T4. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr)
- With a SigLIP 2 backbone, an OWL-ViT-style detector reaches COCO AP 42.8 / LVIS AP 34.4 / APr 32.7 (B/16) and 45.2 / 40.5 / 42.3 (So400m/14). — [SigLIP 2 paper, Table 4](https://arxiv.org/html/2502.14786)

#### YOLO-World (Tencent AILab-CVC)
- Zero-shot, V2.1 weights, LVIS minival AP / COCO AP at 640 px: S 23.6 / 36.6; M 30.6 / 43.0; L 33.8 / 44.9; X 35.8 / 46.7. — [AILab-CVC/YOLO-World](https://github.com/AILab-CVC/YOLO-World)
- Parameters and speed as re-measured by the YOLOE authors (T4 TensorRT FPS / iPhone 12 CoreML FPS): YOLO-Worldv2-S 13M, 216.4 / 48.9; M 29M, 117.9 / 34.2; L 48M, 80.0 / 22.1. — [YOLOE paper, Table 1](https://arxiv.org/html/2503.07465)
- License: "YOLO-World is under the GPL-v3 Licence and is supported for commercial usage"; for a commercial license the README directs to the authors (business contact at Tencent). — [AILab-CVC/YOLO-World](https://github.com/AILab-CVC/YOLO-World)
- ONNX export is provided (`docs/deploy`, Gradio demo); the model "re-parameterizes vocabulary embeddings as parameters into the model". — [AILab-CVC/YOLO-World](https://github.com/AILab-CVC/YOLO-World)
- No CPU figure published in the sources searched.

#### YOLOE (THU-MIG, March 2025) and YOLOE-26 (Ultralytics, January 2026)
- Outputs boxes and instance masks; three modes: text prompt, visual prompt, prompt-free (built-in vocabulary). — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- LVIS minival zero-shot, text / visual prompt AP, with parameters (text / visual, in M): YOLOE-26n 24.7 / 21.9 (3.9 / 3.1); 26s 30.8 / 28.6 (10.7 / 11.0); 26m 35.4 / 33.9 (21.3 / 25.1); 26l 37.8 / 36.3 (25.5 / 29.3); 26x 40.6 / 38.5 (55.2 / 65.2). Older: YOLOE-11s 27.5 / 26.3; 11m 33.0 / 31.4; 11l 35.2 / 33.7; YOLOE-v8s 27.9 / 26.2; v8m 32.6 / 31.0; v8l 35.9 / 34.2. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- Rare-class AP (text prompt): 26n 20.5, 26s 23.9, 26m 31.1, 26l 35.1, 26x 37.4. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- Prompt-free LVIS minival AP (end-to-end / non-E2E): 26n 16.6 / 17.7; 26s 21.4 / 22.6; 26m 25.7 / 26.4; 26l 27.2 / 28.0; 26x 29.9 / 31.1. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- The parameter counts above are for the paper's detection configuration; the released segmentation checkpoint `yoloe-26l-seg.pt` has 35.4M parameters and 142.0B FLOPs. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- These are non-end-to-end figures; the NMS-free end-to-end head trails by 1.1 AP (text), 2.3 AP (visual) and 1.2 AP (prompt-free) for YOLOE-26x. — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- Speed in the original paper (T4 TensorRT FPS / iPhone 12 CoreML FPS): YOLOE-v8-S 305.8 / 64.3; v8-M 156.7 / 41.7; v8-L 102.5 / 27.2; YOLOE-11-S 301.2 / 73.3; 11-M 168.3 / 39.2; 11-L 130.5 / 35.1. — [YOLOE paper, Table 1](https://arxiv.org/html/2503.07465)
- A competing paper re-measured YOLOE on T4 TensorRT including NMS at 216 / 145 / 103 FPS for v8-S / M / L. — [OV-DEIM, Table 2](https://arxiv.org/html/2603.07022)
- Zero-shot mask AP on LVIS val: YOLOE-v8-S 17.7, v8-M 20.8, v8-L 23.5, 11-L 22.6. — [YOLOE paper, Table 2](https://arxiv.org/html/2503.07465)
- After re-parameterization YOLOE "can become YOLOs ... with zero inference and transferring overhead", and exports to the same format as YOLOv8 / YOLO11. — [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe)
- ONNX export: call `set_classes()` then `export(format="onnx")`; "Once exported, the model can no longer accept new prompts." Changing the class list requires re-export from the `.pt` checkpoint. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- A `yoloe-26s-seg.pt` forward pass on CPU grows about 19% from 80 to 1,203 classes and about 89% at 4,585 classes. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- Text encoder used to build class embeddings: MobileCLIP2 (`mobileclip2_b.ts`, about 254 MB) for YOLOE-26; MobileCLIP (`mobileclip_blt.ts`) for YOLOE-11 and YOLOE-v8. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- No CPU ONNX figure is published for YOLOE-26 itself. For the closed-set YOLO26 detectors Ultralytics lists CPU ONNX latency (CPU not named in the table) / T4 TensorRT10 latency / COCO mAP50-95: n 38.9 ms / 1.7 ms / 40.9; s 87.2 / 2.5 / 48.6; m 220.0 / 4.7 / 53.1; l 286.2 / 6.2 / 55.0; x 525.8 / 11.8 / 57.5. — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- OpenCV's benchmark (ONNX Runtime 1.25.1, "Intel i9", CPU model and threads unspecified): yolo26n 9.6 ms, yolo26n_seg 15.9 ms, yolo26m_seg 105 ms, YOLOv8 12.98 ms, RT-DETR 99.9 ms. On "Intel i7": yolo26n 19 ms, yolo26n_seg 43.4 ms, yolo26m_seg 391.9 ms. — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- License: THU-MIG YOLOE repository is AGPL-3.0. — [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe). YOLO26 code, models and documentation are "under AGPL-3.0 and Enterprise licenses". — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- Training data that reproduces the published checkpoints: Objects365v1 (609k images), GQA (621k) and Flickr30k (149k) grounding data, about 1.4M samples on 8 RTX 4090. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)

#### Newer in 2026
- OV-DEIM (arXiv, 2026-03-07): DETR-style real-time open-vocabulary detector on DEIMv2. LVIS minival AP / Fixed AP, parameters, T4 TensorRT FPS: S 27.7 / 29.6, 11M, 161 FPS; M 30.6 / 32.6, 20M, 109 FPS; L 33.7 / 35.9, 36M, 91 FPS; rare-class Fixed AP 25.2 / 26.9 / 36.8. Text encoder: frozen MobileCLIP-B(LT). Code at github.com/wleilei/OV-DEIM; the paper states no code license. — [OV-DEIM](https://arxiv.org/html/2603.07022)
- VL-DINO (arXiv 2606.11546, June 2026): claims 38.1 AP and 40.2 Fixed AP zero-shot on LVIS for its large variant. Read only from a search snippet; not verified at the paper. — [VL-DINO](https://arxiv.org/pdf/2606.11546)
- Ultralytics YOLO26 / YOLOE-26: the model card says "released January 2026". — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- OmDet-Turbo (Swin-T): license apache-2.0, 0.1B parameters, available in `transformers`. — [omlab/omdet-turbo-swin-tiny-hf](https://huggingface.co/omlab/omdet-turbo-swin-tiny-hf). The Grounding DINO 1.5 paper lists OmDet-Turbo-T at 30.3 AP on LVIS-minival. — [arXiv 2405.10300](https://arxiv.org/abs/2405.10300)
- RF-DETR (Roboflow) is closed-set, not open-vocabulary; it matters here as a distillation target. COCO AP50:95 / T4 TensorRT FP16 latency / parameters: Nano 48.4 / 2.3 ms / 30.5M; Small 53.0 / 3.5 ms / 32.1M; Medium 54.7 / 4.4 ms / 33.7M; Large 56.5 / 6.8 ms / 33.9M (all Apache 2.0, DINOv2 backbone). Atto, Femto, Pico, XL and 2XL detection models are under "PML 1.0". All segmentation models are Apache 2.0 (Seg Nano 40.3 mask AP, 3.4 ms, 33.6M). — [roboflow/rf-detr](https://github.com/roboflow/rf-detr)
- Florence-2 and SAM 3 also do text-prompted detection; see sections 4 and 2.

#### Summary table (detectors)

| Model | Output | Params | Zero-shot accuracy | CPU latency | GPU latency | ONNX | License |
|---|---|---|---|---|---|---|---|
| GroundingDINO-T | boxes + phrase labels | 172M | COCO 48.4; LVIS minival 27.4 | 1.5 to 3.4 s (i9-9820X, variant unnamed); 1.86 s ("Intel i9", ORT) | 123 to 134 ms (RTX 6000 / 2080 Ti, PyTorch) | community export | Apache-2.0 (repo) |
| LLMDet Swin-T / B / L | boxes | 0.2B (tiny) | LVIS minival 44.7 / 48.3 / 51.1 (Fixed AP) | no CPU figure published | no figure found | none found | Apache-2.0 |
| Grounding DINO 1.6 Pro | boxes | undisclosed | COCO 55.4; LVIS minival 57.7 | n/a (API) | n/a (API) | no | API only |
| DINO-X Pro | boxes, masks, more | undisclosed | COCO 56.0; LVIS minival 59.7 | n/a (API) | n/a (API) | no | API only |
| OWLv2 B/16, L/14 | boxes | 155M, 438M | LVIS AP 26.5, 32.8 (self-trained); 43.9, 44.6 (ensemble) | 1.54 s ("Intel i9", ORT, variant unnamed) | 50 to 80 ms on T4 (secondary) | yes (used in OpenCV benchmark) | Apache-2.0 |
| YOLO-Worldv2 S / M / L | boxes | 13M / 29M / 48M | LVIS minival 24.4 / 32.4 / 35.5 | no CPU figure published | 216 / 118 / 80 FPS on T4 | yes, fixed vocabulary | GPL-3.0 |
| YOLOE-26 n / s / m / l / x | boxes + masks | 3.9M to 55.2M (det config) | LVIS minival 24.7 / 30.8 / 35.4 / 37.8 / 40.6 | none for YOLOE-26; YOLO26n-seg 15.9 ms ("Intel i9") | YOLOE-11-S 301 FPS on T4 | yes, fixed vocabulary | AGPL-3.0 or Enterprise |
| OV-DEIM S / M / L | boxes | 11M / 20M / 36M | LVIS minival 27.7 / 30.6 / 33.7 | no CPU figure published | 161 / 109 / 91 FPS on T4 | not stated | not stated |

Sources for the table are the bullets above.

### Inferences
- Against a 40 ms budget, Grounding DINO at 1479 ms (OpenVINO, 10 cores) is about 37 times over, and at 3388 ms (ONNX Runtime, 10 cores) about 85 times over; OWLv2 at 1543 ms is about 39 times over. On 3 cores of an i9-10900K these would be slower still. They are not runtime candidates on CPU.
- For Grounding DINO specifically, ONNX Runtime was the slowest CPU path in the one controlled comparison (slower than PyTorch, more than 2 times slower than OpenVINO on the i9). A team bound to ONNX Runtime should not assume an ONNX export makes this model faster.
- YOLOE / YOLO-World with a baked vocabulary are the only open-vocabulary detectors whose runtime cost equals a closed-set YOLO. Using the YOLO26n-seg figures as a proxy (15.9 ms on an unspecified i9, 43.4 ms on an unspecified i7, 38.9 ms for YOLO26n detection in Ultralytics' own table), a nano-size model is in the neighbourhood of the 40 ms budget; this must be measured on 3 cores of the target CPU.
- "Open vocabulary" at runtime is partly lost in that setup: the class list is frozen at export. The benefit that remains is that no labelled training data was needed to obtain the class list.
- License is the blocking issue for the fast family in a commercial closed-source game: AGPL-3.0 (YOLOE, YOLO26) and GPL-3.0 (YOLO-World) require either source release under the same license or a paid commercial / Enterprise license. The permissively licensed open-weight detectors (Grounding DINO 1.0, LLMDet, OWLv2, OmDet-Turbo) are all in the seconds-per-image class on CPU.
- YOLOE class embeddings are computed with Apple MobileCLIP / MobileCLIP2 text encoders, whose weights are under a research-only Apple license (section 3). Whether embeddings derived from that encoder and baked into a shipped model are affected is a legal question the sources do not answer.
- For option (b), accuracy matters more than speed: among downloadable Apache-2.0 detectors, LLMDet Swin-L (51.1 Fixed AP on LVIS minival) and OWLv2 L/14 are the strongest found; the API-only models (57.7 to 59.7) are better but send level screenshots to a third-party cloud.

### Gaps
- No CPU latency was found for YOLOE-26, YOLO-World, LLMDet, OmDet-Turbo or OV-DEIM. All figures for them are T4 GPU.
- The OpenCV benchmark page does not name the exact i9 / i7, thread count, input resolution or model variant, so its absolute numbers cannot be mapped to an i9-10900K with 3 cores.
- The edge-inference paper does not name the Grounding DINO variant (Tiny or Base).
- Price and terms of the Ultralytics Enterprise license and the Tencent YOLO-World commercial license were not found.
- The text of "IDEA License 1.0" (Rex-Omni) and "PML 1.0" (RF-DETR XL) was not read; commercial terms unknown.
- OV-DINO, DetCLIPv3, T-Rex2 and Ultralytics releases other than YOLO26 / YOLOE-26 were not researched individually. VL-DINO's numbers come from a search snippet only.
- No source was found confirming or denying a Grounding DINO release after 1.6 or a DINO-X successor in 2026; absence in the IDEA repos is the only evidence.

## 2. Promptable and concept segmentation: SAM, SAM 2, SAM 3 and lightweight derivatives

### Takeaway
SAM 3 (848M parameters, about 3.45 GB) is the first SAM that takes a noun phrase and returns all matching instance masks, but it needs a CUDA GPU officially and its encoder alone takes about 6 seconds on a desktop i9 in ONNX Runtime. Every SAM-family image encoder measured on CPU, including the "mobile" ones, is in the 1 to 8 second range per image; only the mask decoder is cheap (about 11 ms), so these are build-time tools.

### Cited Findings

#### SAM 3 and SAM 3.1 (Meta)
- SAM 3 has 848M parameters, with a shared vision encoder for a detector and a tracker; license is "the SAM License". — [facebookresearch/sam3](https://github.com/facebookresearch/sam3)
- A parameter breakdown from a distillation project: vision 463M, text 354M, transformer 30.3M, other 14.2M, total 861.5M. — [EfficientSAM3 README](https://github.com/SimonZeng7108/efficientsam3)
- Ultralytics lists SAM 3 at 473.6M parameters and 3450 MB; this conflicts with the official 848M and matches roughly the vision part only. — [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)
- Benchmarks in the official README (flattened table; column mapping ambiguous): LVIS AP 48.5 (instance segmentation) and 53.6 (box); SA-Co/Gold cgF1 54.1 (instance segmentation) and 55.7 (box), human baseline 74.0; COCO box AP 56.4. — [facebookresearch/sam3](https://github.com/facebookresearch/sam3)
- Ultralytics' summary of the paper gives different figures: LVIS zero-shot mask AP 47.0 (previous best 38.5), SA-Co/Gold cgF1 65.0 (OWLv2 34.3), COCO zero-shot box AP 53.5, CountBench accuracy 95.6%, PixMo-Count 87.3%, Cityscapes zero-shot semantic mIoU 65.1, ADE-847 mIoU 14.7. The two sources disagree on LVIS, SA-Co and COCO values. — [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)
- Speed: about 30 ms per image with 100+ detected objects on an H200 GPU. — [Roboflow, "What is SAM 3"](https://blog.roboflow.com/what-is-sam3/); [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)
- Requirements: Python 3.12+, PyTorch 2.7+, "CUDA-compatible GPU with CUDA 12.6 or higher"; CPU support is not mentioned. Weights are gated on Hugging Face (access request). ONNX export is not mentioned in the official repo. — [facebookresearch/sam3](https://github.com/facebookresearch/sam3)
- CPU, ONNX Runtime 1.25.1: "SAM3 (Encoder)" 6194 ms on "Intel i9", 15859 ms on "Intel i7", 7223 ms on Apple M1. — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- SAM 3.1 (released 2026-03-27): adds Object Multiplex for joint multi-object video tracking, about 7 times faster at 128 objects on one H100; image-level accuracy essentially unchanged (SA-V J&F 84.4 to 85.1). — [facebookresearch/sam3](https://github.com/facebookresearch/sam3); [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)
- Stated limitations: best for simple noun phrases; long referring expressions need an MLLM in front; "Performance may drop on rare or fine-grained concepts"; larger and slower than YOLO-type detectors. — [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/); [SAM 3 paper](https://arxiv.org/pdf/2511.16719)
- SAM License (last updated 2025-11-19): "non-exclusive, worldwide, non-transferable and royalty-free limited license" to use, reproduce, distribute, create derivative works and modify. It does not restrict the grant to non-commercial use. Redistribution must be under the same agreement with a copy of it. Prohibited: activities subject to ITAR and end uses including "military or warfare purposes", nuclear applications, espionage, and development or use of guns or illegal weapons. Publications must acknowledge use. Meta may terminate on breach, after which the materials must be deleted. — [SAM License](https://github.com/facebookresearch/sam3/blob/main/LICENSE)

#### SAM (2023) and SAM 2 / 2.1
- SAM: three checkpoints (ViT-H, ViT-L, ViT-B); "The model is licensed under the Apache 2.0 license"; only the mask decoder has an official ONNX export. — [facebookresearch/segment-anything](https://github.com/facebookresearch/segment-anything)
- SAM ViT-H: 641.1M parameters, 4.3 FPS on an RTX 2080 Ti. — [EdgeSAM README](https://github.com/chongzhou96/EdgeSAM)
- SAM 2.1 (2024-09-29), size / FPS on an A100 (torch 2.5.1) / SA-V test J&F: hiera_tiny 38.9M / 91.2 / 76.5; hiera_small 46M / 84.8 / 76.6; hiera_base_plus 80.8M / 64.1 / 78.2; hiera_large 224.4M / 39.5 / 79.5. Checkpoints, demo and training code are Apache 2.0. — [facebookresearch/sam2](https://github.com/facebookresearch/sam2)
- CPU, ONNX Runtime 1.25.1, "SAM2 ENCODER" (variant unspecified): 2281 ms on "Intel i9", 7261 ms on "Intel i7"; "SAM2 DECODER": 10.94 ms and 30.29 ms. — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- Ultralytics pipeline timings on CPU ("2025 Apple M4 Air with 16GB", SAM in PyTorch, YOLO in ONNX Runtime 1.24.4): SAM-b 41703 ms, SAM2-b 28867 ms, SAM2-t 23430 ms, MobileSAM 23802 ms, FastSAM-s 58.0 ms, YOLOv8n-seg 24.8 ms, YOLO11n-seg 24.3 ms, YOLO26n-seg 25.2 ms per image. Sizes: SAM-b 375 MB / 93.7M; SAM2-t 78.1 MB / 38.9M; MobileSAM 40.7 MB / 10.1M; FastSAM-s 23.9 MB / 11.8M; YOLO26n-seg 6.7 MB / 2.7M. — [Ultralytics MobileSAM docs](https://docs.ultralytics.com/models/mobile-sam/)
- The same comparison on GPU ("NVIDIA RTX PRO 6000 with 96GB", torch 2.9.1): SAM-b 1306 ms, SAM2-b 857 ms, SAM2-t 668 ms, SAM 3 2921 ms, MobileSAM 605 ms, FastSAM-s 55.9 ms, YOLO26n-seg 8.4 ms. — [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)

#### Lightweight derivatives
- MobileSAM: 9.66M parameters in total (TinyViT image encoder about 5M at 8 ms, mask decoder 3.876M at 4 ms), about 12 ms per image on "a single GPU" (unnamed); "On our own Mac i5 CPU, it takes around 3s"; original SAM pipeline 615M and 456 ms on the same GPU; license Apache-2.0; ONNX export script provided. — [ChaoningZhang/MobileSAM](https://github.com/ChaoningZhang/MobileSAM)
- EdgeSAM: 9.6M parameters; 38.7 FPS on iPhone 14, 164.3 FPS on RTX 2080 Ti; COCO mask mAP 42.2 versus SAM 46.1, MobileSAM 39.4, FastSAM 37.9; ONNX and CoreML export supported. — [chongzhou96/EdgeSAM](https://github.com/chongzhou96/EdgeSAM)
- EdgeSAM license is NTU S-Lab License 1.0: redistribution and use "for non-commercial purpose"; for commercial use "please contact the contributor(s)". — [EdgeSAM LICENSE](https://github.com/chongzhou96/EdgeSAM/blob/master/LICENSE)
- FastSAM (YOLOv8-seg based): 68.2M parameters, 25.0 FPS on an RTX 3090 for the full model. — [EdgeSAM README](https://github.com/chongzhou96/EdgeSAM). FastSAM-s is 23.9 MB / 11.8M and 58 ms on an M4 Air CPU. — [Ultralytics MobileSAM docs](https://docs.ultralytics.com/models/mobile-sam/)
- EfficientSAM (Ti and S variants): Apache-2.0; ONNX export scripts and separate encoder / decoder ONNX models are provided. — [yformer/EfficientSAM](https://github.com/yformer/EfficientSAM)
- EfficientTAM (video, SAM 2 family): checkpoints and code Apache 2.0; "can run >10 frames per second" on iPhone 15. — [yformer/EfficientTAM](https://github.com/yformer/EfficientTAM)
- Colab CPU comparison (runtime per model not clearly stated): SAM 2.1 Hiera-Tiny about 7.2 to 7.7 s per image, MobileSAM about 4.4 to 6.6 s, NanoSAM (ResNet18 encoder) about 1.6 to 2.9 s. — [zenn.dev comparison](https://zenn.dev/piment/articles/ee78e816e1d05b)
- Pre-exported ONNX models exist for MobileSAM, EfficientSAM-Ti, EfficientSAM-S and SAM 2.1 Tiny, checked with ONNX Runtime CPU. — [nrl-ai/samexporter-onnx-models](https://huggingface.co/nrl-ai/samexporter-onnx-models)
- EfficientSAM3 (University of Bristol, paper November 2025): distils SAM 3 into EfficientViT / RepViT / TinyViT students with a MobileCLIP text encoder; totals 89.2M, 92.7M and 95.3M parameters (about 89 to 90% smaller than SAM 3). Stage 3 fine-tuned weights were released on Hugging Face on 2026-06-11; ONNX / TensorRT export was contributed; CoreML pending; repository Apache 2.0, with upstream licenses (SAM 3, MobileCLIP) still applying. The README reports no accuracy or latency numbers. — [EfficientSAM3 README](https://github.com/SimonZeng7108/efficientsam3); [paper](https://arxiv.org/abs/2511.15833)
- SAM3-LiteText (arXiv, February 2026): replaces only SAM 3's text encoder with a MobileCLIP student, cutting text-encoder parameters by up to 88%; totals 550.0M to 631.3M. — [SAM3-LiteText](https://arxiv.org/abs/2602.12173); [EfficientSAM3 README](https://github.com/SimonZeng7108/efficientsam3)

### Inferences
- No SAM-family model can run per frame inside a 40 ms CPU budget. The cheapest measured encoders are seconds per image on desktop CPUs; the iPhone and GPU figures for EdgeSAM and MobileSAM rely on a neural accelerator or GPU that the game cannot spare.
- The Ultralytics tables (23 to 42 s on CPU, 0.6 to 2.9 s on GPU) are far slower than encoder-only figures elsewhere; they most likely time a whole "segment everything" pipeline rather than a single prompted mask. They should not be compared with the 30 ms H200 figure.
- For option (b), SAM 3 is the most direct fit: one text prompt ("door", "staircase") returns all instance masks, which replaces the Grounding DINO + SAM two-stage pipeline. It needs a CUDA GPU on the build machine and acceptance of the SAM License, which does not exclude commercial use but adds field-of-use prohibitions and a same-license redistribution rule. Since build-time labelling does not redistribute weights, the redistribution clause would not be triggered, but that reading needs legal confirmation.
- If a fully permissive stack is required for build time, SAM 2.1 (Apache-2.0) prompted by boxes from an Apache-2.0 detector is the alternative. Because the editor already knows each actor's screen-space bounds, SAM 2.1 can be prompted with engine-provided boxes and needs no detector at all.
- EdgeSAM is the fastest small SAM but its license forbids commercial use without a separate agreement; MobileSAM and EfficientSAM are the permissive small options.

### Gaps
- No published CPU latency for SAM 3 as a whole (encoder + text + detector + decoder), only the encoder figure from the OpenCV page.
- No accuracy or latency numbers for EfficientSAM3 students were found in the README; the paper tables were not read.
- EfficientSAM and EfficientTAM parameter counts and benchmark numbers are not on their README pages and were not retrieved.
- Exact SAM 3 benchmark values conflict between the official README and Ultralytics' summary; the paper's tables were not read directly.
- The OpenCV page does not say which SAM 2 size was benchmarked.

## 3. Vision backbones and image-text embedding models for zero-shot classification of crops or thumbnails

### Takeaway
Classifying a crop or thumbnail against a fixed list of text labels is the one "open-vocabulary" operation that fits a small CPU budget: plain ViT-B/32-class image encoders measure 13 to 35 ms on desktop CPUs in ONNX Runtime and text embeddings can be precomputed offline. The license picture is uneven: SigLIP 2, Perception Encoder, DINOv2 and TinyCLIP-class models are permissive, MobileCLIP / MobileCLIP2 weights are research-only, and DINOv3 has a custom Meta license with field-of-use prohibitions and no native text tower in its base release.

### Cited Findings

#### Zero-shot ImageNet-1k top-1 (image-text models)
- SigLIP 2 (Google, February 2025): B/32 at 256 px 74.0; B/16 at 224 / 256 / 384 / 512 px 78.2 / 79.1 / 80.6 / 81.2; L/16 at 256 / 384 / 512 px 82.5 / 83.1 / 83.5; So400m/14 at 224 / 384 px 83.2 / 84.1; So400m/16 at 256 / 384 / 512 px 83.4 / 84.1 / 84.3; g/16 at 256 / 384 px 84.5 / 85.0. — [SigLIP 2 paper, Table 1](https://arxiv.org/html/2502.14786)
- Baselines in the same table: OpenAI CLIP B/16 68.3 and L/14 75.5; OpenCLIP B/16 70.2 and L/14 74.0; MetaCLIP B/16 72.4, L/14 79.2, H/14 80.5; EVA-CLIP B/16 74.7, L/14 79.8; DFN B/16 76.2, L/14 82.2, H/14 83.4; SigLIP (v1) B/16 76.2, So400m/14 82.2. — [SigLIP 2 paper, Table 1](https://arxiv.org/html/2502.14786)
- SigLIP 2 sizes: ViT-B 86M, L 303M, So400m 400M, g 1B. — [SigLIP 2 abstract](https://arxiv.org/abs/2502.14786)
- SigLIP 2 license: a repackaged So400m checkpoint is described as Apache License 2.0 (secondary source). — [LibreYOLO/LibreSigLIP2so400m-cls](https://huggingface.co/LibreYOLO/LibreSigLIP2so400m-cls)
- Perception Encoder, PE-Core (Meta, 2025): T/16 at 384 px 62.1; S/16 at 384 px 72.7; B/16 at 224 px 78.4; L/14 at 336 px 83.5; G/14 at 448 px 85.4. Code and PE weights are Apache 2.0; the companion Perception Language Model (PLM 1B / 3B / 8B) weights are under the FAIR Research License. Latest update on the page is 2025-12-16. — [facebookresearch/perception_models](https://github.com/facebookresearch/perception_models)
- MobileCLIP2 (Apple), image + text parameters / image + text latency / IN-1k zero-shot: S0 11.4M + 63.4M / 1.5 + 3.3 ms / 71.5; S2 35.7M + 63.4M / 3.6 + 3.3 ms / 77.2; B 86.3M + 63.4M / 10.4 + 3.3 ms / 79.4; S3 125.1M + 123.6M / 8.0 + 6.6 ms / 80.7; L/14 304.3M + 123.6M / 57.9 + 6.6 ms / 81.9; S4 321.6M + 123.6M / 19.6 + 6.6 ms / 81.9. The only device named is an iPhone 12 Pro Max. — [apple/ml-mobileclip](https://github.com/apple/ml-mobileclip)
- MobileCLIP (v1): S0 11.4M + 42.4M / 1.5 + 1.6 ms / 67.8; S1 72.6; S2 74.4; B 76.8; B (LT) 77.2; S3 78.3; S4 79.4. — [apple/ml-mobileclip](https://github.com/apple/ml-mobileclip)
- MobileCLIP licenses: code MIT; models under `LICENSE_MODELS`; data CC-BY-NC-ND. — [apple/ml-mobileclip](https://github.com/apple/ml-mobileclip)
- `LICENSE_MODELS` is the "Apple Machine Learning Research Model License Agreement": the grant is "exclusively for Research Purposes", defined as "non-commercial scientific research and academic development activities", and it excludes "any commercial exploitation, product development" and "use in any commercial product or service". — [LICENSE_MODELS](https://github.com/apple/ml-mobileclip/blob/main/LICENSE_MODELS)
- The Hugging Face card for `apple/MobileCLIP-S0` states "License: apple-amlr". — [apple/MobileCLIP-S0](https://huggingface.co/apple/MobileCLIP-S0); one MobileCLIP2 card carries mixed metadata (apple-amlr with a license name of apple-ascl) — [apple/mobileclip2_coca card](https://huggingface.co/apple/mobileclip2_coca_dfn2b_s13b_context77/blob/main/README.md)
- TinyCLIP (Microsoft), IN-1k zero-shot / MACs / throughput in pairs per second (hardware unnamed): ViT-8M/16 Text-3M 41.1 / 2.0G / 4,150; ViT-39M/16 Text-19M 63.5 / 9.5G / 1,469; ViT-40M/32 Text-19M 59.8 / 3.5G / 4,641; ViT-61M/32 Text-29M 62.4 / 5.3G / 3,191; ViT-63M/32 Text-31M (auto, LAION+YFCC) 64.5 / 5.6G / 2,909. — [wkcn/TinyCLIP](https://github.com/wkcn/TinyCLIP)

#### Self-supervised backbones (no text tower by default)
- DINOv2: ViT-S/14 21M (k-NN 79.0%, linear 81.1% on ImageNet-1k), ViT-B/14 86M (82.1% / 84.5%), ViT-L/14 300M (83.5% / 86.3%), ViT-g/14 1,100M (83.5% / 86.5%). A text-aligned "dino.txt" head exists for ViT-L/14 with registers; its zero-shot ImageNet number is not on the page. "DINOv2 code and model weights are released under the Apache License 2.0." — [facebookresearch/dinov2](https://github.com/facebookresearch/dinov2)
- DINOv3 (Meta, August 2025) sizes: ViT-S/16 21M, S+/16 29M, B/16 86M, L/16 300M, H+/16 840M, 7B/16 6716M; ConvNeXt Tiny 29M, Small 50M, Base 89M, Large 198M; trained on LVD-1689M (1,689M web images). — [DINOv3 model card](https://github.com/facebookresearch/dinov3/blob/main/MODEL_CARD.md)
- DINOv3 frozen-feature results (ADE20k linear segmentation / NYU depth, lower is better): S/16 47.0 / 0.403; B/16 51.8 / 0.373; L/16 54.9 / 0.352; 7B/16 55.9 / 0.309; ConvNeXt Tiny 42.7 / 0.448; ConvNeXt Large 47.8 / 0.403. — [DINOv3 model card](https://github.com/facebookresearch/dinov3/blob/main/MODEL_CARD.md)
- DINOv3 License (dated 2025-08-14): "non-exclusive, worldwide, non-transferable and royalty-free limited license" to use, reproduce, distribute, copy, create derivative works and modify. The text has no non-commercial restriction. Distribution of the materials or derivatives is allowed only under the same agreement with a copy of it. Prohibited: ITAR-controlled activities and end uses including military or warfare purposes, nuclear industries, espionage, and development or use of guns or illegal weapons. Research publications must acknowledge use. On termination the materials must be deleted. — [DINOv3 License](https://ai.meta.com/resources/models-and-libraries/dinov3-license)
- The automated reading of the license page also reported a requirement to display "Built with DINOv3" on distribution; this wording was not double-checked verbatim and should be confirmed in the license text. — [DINOv3 License](https://ai.meta.com/resources/models-and-libraries/dinov3-license)
- DINOv3 weights are gated on Hugging Face with license tag `other` / `dinov3-license`. — [facebook/dinov3-vits16-pretrain-lvd1689m](https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m)

#### CPU latency
- ONNX Runtime 1.25.1 on "Intel i9" / "Intel i7" (exact CPUs, threads and variants unspecified), ms per image: VIT_B_32 12.57 / 33.12; VIT_Base_Patch16_224 35.68 / 69.1; DeiT_Tiny_Patch16_224 4.89 / 7.4; MobileViT_XS 5.39 / 10.32; SigLip 26.28 / 72.51; Dinov2 26.5 / 72.48; Dinov3 14.5 / 27.97. — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- A community ONNX export of MobileCLIP2-S0 reports 112 ms for the FP32 vision model and 10 ms for the INT8 text model on "standard CPU desktops and laptops" (hardware not named), total size 105 MB; the author kept vision in FP32 because dynamic INT8 on the FastViT backbone added overhead. — [felixhrdyn/mobileclip2-s0-onnx](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx)
- CLIP ViT-B/32 image encoder: 335 MB in fp32, 91.2 MB in int8; on a Snapdragon 8+ Gen 1 phone, 500 images at 400 px took about 54 s (fp32) versus about 20 s (int8) single-threaded. — [CLIP-android-demo](https://github.com/greyovo/CLIP-android-demo)
- An ImageNet ViT-B/16 classifier in ONNX Runtime on Apple arm64 CPU: 92.51 ms FP32 versus 37.05 ms INT8. — [vit-base-patch16-224 int8 card](https://huggingface.co/nielsr/vit-base-patch16-224-r3al-int8)

### Inferences
- A ViT-B/32-class image tower at about 13 ms (unspecified i9, full threads) plus a dot product against precomputed text embeddings is the only open-vocabulary operation in this file with a realistic chance of fitting 40 ms on 3 cores. It classifies one crop; it does not localise, so the game must supply the crop (the engine already knows object bounds).
- SigLIP 2 B/32 at 256 px (74.0 zero-shot ImageNet) is 6 to 7 points above OpenAI CLIP B/16 at lower cost, and the Perception Encoder S/16 (72.7) is in the same class; both come with permissive licenses, unlike MobileCLIP2-S0 (71.5), which is research-only.
- The MobileCLIP latency figures (1.5 ms image) are phone neural-engine numbers; the one community desktop CPU figure (112 ms) shows they do not transfer to x86 ONNX Runtime without work.
- DINOv2 / DINOv3 are useful for option (b) as feature extractors for a small trained classifier head or for nearest-neighbour matching of level objects against a labelled reference set, not for text-prompted labels. DINOv3's license is more restrictive than DINOv2's Apache-2.0 while the small-model gains are moderate; for a commercial game DINOv2 or PE is the lower-risk choice.
- For a game, zero-shot ImageNet accuracy overstates what to expect on rendered thumbnails of stylised assets; the list of candidate labels will be short (tens, not 1,000), which helps.

### Gaps
- Zero-shot ImageNet numbers for the DINOv2 dino.txt head and for any DINOv3 text-aligned variant were not found.
- The licenses of OpenAI CLIP, OpenCLIP and TinyCLIP were not confirmed at a primary source in this session (they are widely reported as MIT; verify before relying on it).
- The SigLIP 2 checkpoint license was only confirmed through a secondary repackaging; the big_vision README could not be fetched (HTTP 503).
- No x86 desktop CPU latency was found for SigLIP 2 B/32, PE-Core-T / S, TinyCLIP or MobileCLIP v1; the "SigLip", "Dinov2" and "Dinov3" rows in the OpenCV table do not name the variant.
- Perception Encoder parameter counts per variant are not on the README page.
- No evaluation of any of these encoders on game-rendered thumbnails was found.

## 4. Florence-2 and small vision-language models for local use

### Takeaway
No small VLM has a published desktop-CPU figure that comes near a per-frame budget: the only CPU measurements found are tens of seconds per image on a Raspberry Pi and "1 to 3 seconds" for Florence-2 on a modern Xeon or Ryzen. They are build-time candidates; among them Moondream is the only family that publishes detection and pointing scores as a first-class feature, Florence-2 (MIT, 0.23B) is the smallest multi-task model with an ONNX build, and licenses range from MIT / Apache-2.0 to research-only.

### Cited Findings

#### Florence-2 (Microsoft)
- Sizes: Florence-2-base 0.23B, Florence-2-large 0.77B parameters; license MIT. — [microsoft/Florence-2-base](https://huggingface.co/microsoft/Florence-2-base)
- Tasks through prompt tokens: caption (three lengths), caption-to-phrase grounding, object detection, dense region caption, region proposal, OCR and OCR with regions. — [microsoft/Florence-2-base](https://huggingface.co/microsoft/Florence-2-base)
- Zero-shot (base / large): COCO detection val2017 mAP 34.7 / 37.5; RefCOCO val accuracy 53.9 / 56.3; RefCOCO RES val mIoU 34.6 / 35.8; Flickr30k R@1 83.6 / 84.4; COCO caption CIDEr 133.0 / 135.6. Fine-tuned (base-ft / large-ft): COCO detection 41.4 / 43.4; RefCOCO val 92.6 / 93.4; RefCOCO RES mIoU 78.0 / 80.5. — [microsoft/Florence-2-base](https://huggingface.co/microsoft/Florence-2-base)
- ONNX: `onnx-community/Florence-2-base-ft` provides ONNX weights for Transformers.js, license MIT. — [onnx-community/Florence-2-base-ft](https://huggingface.co/onnx-community/Florence-2-base-ft)
- CPU: a third-party C# / ONNX port gives a rough "1–3 seconds for DETAILED_CAPTION at 768×768" on a modern Xeon or Ryzen and rates object detection at 2 to 5 times the latency of a short caption, with no absolute figure. — [Florence2-Sharp performance notes](https://docs.curiosity.ai/florence2-sharp/advanced/performance)
- GPU (secondary source): about 30 to 60 ms on an RTX A5000 with about 862 MB of VRAM. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr)
- A Roboflow test of `florence-2-base` on cloud CPUs (2024-11-19) found Intel Emerald Rapids fastest, on average 0.55 s faster per image than Sapphire Rapids; absolute times are only in images on the page. — [Roboflow](https://roboflow.com/blog/deploy-florence-2-intel-emerald-rapids)

#### Moondream
- Moondream 2 (latest revision 2025-06-21): 2B parameters, apache-2.0; capabilities caption, query, detect, point. Changelog: COCO object detection 30.5 to 51.2 and CountBenchQA 80 to 86.4 (2025-03-27); ScreenSpot F1@0.5 60.3 to 80.4 and 20 to 40% faster text generation (2025-06-21). — [vikhyatk/moondream2](https://huggingface.co/vikhyatk/moondream2)
- Moondream 2 speed: 184 tokens per second on an RTX 3090. — [moondream.ai models](https://moondream.ai/models)
- Moondream 0.5B: 8-bit build 479 MiB download and about 996 MiB runtime memory; 4-bit build 375 MiB and 816 MiB. — [Introducing Moondream 0.5B](https://moondream.ai/blog/introducing-moondream-0-5b)
- Moondream 0.5B on a Raspberry Pi 4 (4 GB): about 1.9 GB memory, all four cores busy, model load about 19 s, image encoding about 37 s, one answer about 56 s. — [Dexter Industries forum](https://forum.dexterindustries.com/t/moondream-vision-language-assistant-on-gopigo3-robot-kilted-dave/10750)
- Moondream 3 Preview (September 2025): 9B total parameters, about 2B active per token (mixture of experts, 64 experts with 8 active), 32K context, SigLIP-based vision encoder; skills query, caption, point, detect. License: Business Source License 1.1 with an additional use grant; internal and in-product use is allowed, a separate agreement is needed for hosted APIs, managed hosting, paid SDKs that bundle the weights, and B2B computer-vision or data-labelling services that overlap the vendor's paid offering. — [moondream/moondream3-preview](https://huggingface.co/moondream/moondream3-preview)
- Moondream 3 Preview benchmark tables disagree between vendor pages: the docs list RefCOCO 91.1, RefCOCO+ 81.8, RefCOCOg 88.6, CountBenchQA 93.2. — [docs.moondream.ai](https://docs.moondream.ai/); the models page lists COCO mAP 51.2, ScreenSpot F1@0.5 80.4, CountBenchQA 86.4, RefCOCO (segmentation) 83.2 mIoU — [moondream.ai models](https://moondream.ai/p/models)
- Moondream 3.1 (released 2026-07-07, model id `moondream3.1-9B-A2B`): vendor-reported F1@0.5 for open-vocabulary detection COCO 81.46, ODinW-13 93.94, LVIS 67.4 (a "Qwen3.5 9B" scored 71.11 on LVIS in the same table); dense detection Dense200 74.61, SKU-110K 52.77, CrowdHuman 74.5; referring RefCOCO-M 87.1; counting CountBench 90.35, TallyQA 74.86, PixMo-Count 88.68. — [Moondream 3.1 blog](https://moondream.ai/blog/moondream-3-1-beyond-benchmarks)
- Moondream 3.1 speed: 34.2 requests per second on one H100 at batch size 16 with the vendor's Photon engine; on Cloudflare Workers AI, point about 145 ms and detect about 160 ms end to end. No CPU figure. — [Moondream 3.1 blog](https://moondream.ai/blog/moondream-3-1-beyond-benchmarks)
- Moondream 3.1 license: "Moondream Model License 1.0"; commercial use, self-hosting, fine-tuning, quantizing and redistribution are allowed; offering general-purpose Moondream inference or fine-tuning as a hosted service is not. — [Moondream 3.1 blog](https://moondream.ai/blog/moondream-3-1-beyond-benchmarks)

#### Other small VLMs
- SmolVLM2 (Hugging Face): 256M, 500M, 2.2B; Apache 2.0. — [SmolVLM2-2.2B-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct). RAM at batch size 1 in the SmolVLM paper: about 0.8 GB (256M), 1.2 GB (500M), 4.9 GB (2.2B). — [SmolVLM paper](https://arxiv.org/pdf/2504.05299). Its documented tasks are VQA, captioning, OCR and video understanding, not detection or pointing. — [Roboflow SmolVLM2 page](https://roboflow.com/model/smolvlm2)
- Qwen3-VL-2B-Instruct (Alibaba): license apache-2.0, 2B parameters, "stronger 2D grounding" and 3D grounding claimed, native 256K context; grounding results are published only as chart images. — [Qwen/Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct). A q4_0 llama.cpp build is listed by Qualcomm AI Hub. — [qualcomm/Qwen3-VL-2B-Instruct](https://huggingface.co/qualcomm/Qwen3-VL-2B-Instruct)
- Qwen2.5-VL-3B-Instruct is governed by the Qwen Research License Agreement. — [Rex-Omni README](https://github.com/IDEA-Research/Rex-Omni); a Hugging Face thread notes the 3B and 72B LICENSE files are labelled "Qwen" while the 7B is Apache — [Qwen2.5-VL-7B discussion](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/discussions/31); contradicted by third-party listings that label the 3B as Apache-2.0 — [immers.cloud listing](https://en.immers.cloud/ai/Qwen/qwen2.5-vl-3b-instruct/)
- PaliGemma 2 (Google): 3B / 10B / 28B; license "gemma" (Gemma Terms of Use), gated. The `pt` checkpoints are base models meant for fine-tuning; "out-of-the-box or zero-shot performance may lag behind task-specific models". Fine-tuned RefCOCO val: 73.4 at 224 px, 76.3 at 448 px (3B). — [google/paligemma2-3b-pt-224](https://huggingface.co/google/paligemma2-3b-pt-224)
- Gemma 3n (Google, 2025): E2B and E4B, phone-first, audio input, Gemma Terms. — [aiidelist on-device VLM comparison, 2026-09-24](https://aiidelist.com/blog/on-device-vlm-comparison.md)
- Gemma 4 (Google, reported release 2026-04-02): sizes E2B, E4B, 12B, 26B-A4B, 31B; reported as the first Gemma under Apache 2.0. — [The Decoder](https://the-decoder.com/googles-gemma-4-is-now-available-with-apache-2-0-licensing-for-the-first-time/); [aiidelist](https://aiidelist.com/blog/on-device-vlm-comparison.md). E2B is 2.3B effective parameters (5.1B with embeddings), E4B 4.5B effective; outputs JSON bounding boxes. — [Emelia guide](https://emelia.io/hub/gemma-4-open-source-guide). In a hands-on test with E2B under Ollama the box for a bicycle "was not exactly over the object". — [Medium walkthrough](https://medium.com/@gabi.preda/run-gemma-4-e2b-locally-with-ollama-no-cloud-no-limits-7e6c3f6bd860). These are secondary sources; Google's model card was not read.
- Phi-4-multimodal-instruct (Microsoft, February 2025): 5.6B parameters, MIT; text, image and audio in; the card lists no bounding-box or grounding feature; a separate ONNX version exists; tested on A100 / A6000 / H100. — [microsoft/Phi-4-multimodal-instruct](https://huggingface.co/microsoft/Phi-4-multimodal-instruct)
- Others, from a single third-party comparison dated 2026-09-24: FastVLM (Apple, 0.5B / 1.5B / 7B, Apple AMLR license); LFM2.5-VL (Liquid AI, 2026, 450M / 3B, "LFM Open License"); MiniCPM-V 4.5 (OpenBMB, 8B, Apache 2.0 code with separate MiniCPM weights terms). — [aiidelist](https://aiidelist.com/blog/on-device-vlm-comparison.md)
- Rex-Omni (3B, detection and pointing as token prediction): see section 1; IDEA License 1.0 on top of the Qwen Research License. — [IDEA-Research/Rex-Omni](https://github.com/IDEA-Research/Rex-Omni)
- Text-only CPU reference for scale: with llama.cpp on a recent Xeon, Llama-3.2-1B reaches about 120 tokens per second and Qwen2.5-7B about 45. — [CEUR-WS Vol-4164 paper 11](https://ceur-ws.org/Vol-4164/paper11.pdf)

#### Quality on game images
- VideoGameQA-Bench (NeurIPS 2025 Datasets and Benchmarks; 11 proprietary and 5 open-weight VLMs): best scores were 53.0% on visual unit testing (Gemini-2.5-Pro), 40.0% on UI unit testing, 45.2% on visual regression, 82.8% on image glitch detection (GPT-4o), 87.8% on parametric clipping (GPT-4.1), 36.0% on needle-in-a-haystack; best open-weight model Qwen-2.5-VL 72B scored 70.0% on image glitch detection. The authors state VLMs "perform poorly at detecting fine details required for accurate scene understanding" and are "still not ready to be deployed for many video game QA tasks". — [VideoGameQA-Bench](https://arxiv.org/html/2505.15952)

### Inferences
- None of these models belongs in option (a). Even the 0.23B Florence-2 is quoted at seconds per image on server-class CPUs, and autoregressive decoding of boxes scales with the number of objects.
- For option (b), three tiers emerge: Florence-2 (MIT, smallest, ONNX available, weak zero-shot detection at 34.7 to 37.5 COCO mAP); Moondream 3.1 (best published small-model detection and pointing scores, commercial self-hosting allowed, but 9B total weights and vendor-only benchmarks reported as F1@0.5, which is not comparable with mAP); and general small VLMs (Qwen3-VL-2B, Gemma 4 E2B, both Apache-2.0) whose grounding quality is not documented numerically.
- Build-time labelling of the team's own game does not look like the hosted-service or data-labelling-service cases that the Moondream licenses reserve, but "B2B ... data labeling" wording in the Moondream 3 Preview BSL grant is close enough to warrant a legal check before using the Preview; Moondream 3.1's license is clearer.
- Research-only or restricted licenses to avoid in a commercial pipeline unless cleared: Qwen2.5-VL-3B (and Rex-Omni built on it), FastVLM, PLM, PaliGemma 2 and Gemma 3n (Gemma Terms are not a standard open-source license).
- VideoGameQA-Bench tested only frontier and large open models, and they were weak on fine detail in game frames; small models can be expected to be weaker still, so a VLM should be a second opinion on labels, not the sole labeler.

### Gaps
- No desktop-CPU tokens-per-second or seconds-per-image figure was found for SmolVLM2, Qwen3-VL-2B, Gemma 3n, Gemma 4, PaliGemma 2, Phi-4-multimodal, MiniCPM-V or Moondream 2 / 3 / 3.1.
- No absolute CPU latency for Florence-2 object detection was found.
- Grounding, pointing and counting scores for Qwen3-VL small variants, Gemma 3 / 3n / 4, SmolVLM2 and MiniCPM-V were not found in text form.
- Gemma 4's license and release date were confirmed only through secondary press, not Google's model card. "Qwen3.5 9B" appears only as a comparison row in the Moondream 3.1 blog and was not verified.
- Gemma 3 (4B) and the Qwen2-VL-2B model were not researched individually.
- MiniCPM-V, LFM2.5-VL and FastVLM license terms come from one third-party table.

## 5. Monocular depth and geometry (brief)

### Takeaway
Depth Anything is the practical family: the Small / Base tiers are Apache-2.0 and a "depth_anything" ONNX model runs in about 127 ms on a desktop i9, while the larger and multi-view models (VGGT, MapAnything, DA3-Giant) are GPU-only build-time tools with split commercial and non-commercial checkpoints. For a game this whole category is low value, because the engine already has exact depth and geometry.

### Cited Findings
- Depth Anything V2: Small 24.8M (Apache-2.0); Base 97.5M, Large 335.3M, Giant 1.3B (CC-BY-NC-4.0). Community ports exist for ONNX, TensorRT, Core ML, Transformers.js and ncnn. — [DepthAnything/Depth-Anything-V2](https://github.com/DepthAnything/Depth-Anything-V2)
- Depth Anything V2 was trained by "replacing all labeled real images with synthetic images", with a large teacher pseudo-labelling real images for the students; models span about 25M to 1.3B parameters and are more than 10 times faster than Stable-Diffusion-based depth models. — [Depth Anything V2 abstract](https://arxiv.org/abs/2406.09414)
- CPU, ONNX Runtime 1.25.1, "depth_anything" (version and size unspecified): 126.5 ms on "Intel i9", 332.5 ms on "Intel i7", 240.4 ms on "AMD". — [OpenCV 5 DNN Benchmarks](https://github.com/opencv/opencv/wiki/OpenCV-5-DNN-Benchmarks)
- Depth Anything 3 (ByteDance, late 2025): DA3-SMALL 0.08B and DA3-BASE 0.12B (Apache 2.0); DA3METRIC-LARGE 0.35B and DA3MONO-LARGE 0.35B (Apache 2.0); DA3-LARGE(-1.1) 0.35B, DA3-GIANT(-1.1) 1.15B, DA3NESTED-GIANT-LARGE(-1.1) 1.40B (CC BY-NC 4.0). Code Apache-2.0. The "-1.1" models were retrained after a training bug. Any-view models output depth and camera pose; metric depth via `focal * net_output / 300`. — [ByteDance-Seed/Depth-Anything-3](https://github.com/ByteDance-Seed/Depth-Anything-3); a third-party listing labels DA3 Base as CC BY-NC 4.0, contradicting the official table — [Voxel51 model zoo](https://docs.voxel51.com/model_zoo/models/depth_anything_v3_base_torch.html)
- Community DA3 ONNX weights exist. — [SpatialHub/depth-anything-3-onnx](https://huggingface.co/SpatialHub/depth-anything-3-onnx)
- Depth Pro (Apple): metric depth plus focal length; "2.25-megapixel depth map in 0.3 seconds on a standard GPU" (GPU unnamed). — [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro). The GitHub LICENSE is an Apple software license that permits use, modification and redistribution and does not mention weights, while the Hugging Face card states "License: apple-amlr" (Apple research-only model license). — [GitHub LICENSE](https://github.com/apple/ml-depth-pro/blob/main/LICENSE); [apple/DepthPro](https://huggingface.co/apple/DepthPro)
- Metric3D v2: ViT-Small / Large / giant2 (DINOv2-with-registers encoders); metric depth and surface normals; code under a 2-clause BSD License with "For further commercial inquiries, please contact" the authors; ONNX exports for all three sizes. — [YvanYin/Metric3D](https://github.com/YvanYin/Metric3D)
- MoGe (Microsoft): MoGe-1 ViT-L 314M; MoGe-2 ViT-L 326M, ViT-L with normals 331M, ViT-B with normals 104M, ViT-S with normals 35M; outputs point map, depth, normals, camera FoV, metric scale in MoGe-2; "60ms latency per image (A100 or RTX3090, FP16, ViT-L)"; code MIT (bundled DINOv2 code Apache 2.0); ONNX support documented. — [microsoft/MoGe](https://github.com/microsoft/MoGe)
- VGGT (Meta): original `VGGT-1B` checkpoint "remains non-commercial"; `VGGT-1B-Commercial` is licensed for commercial use "excluding military applications" and requires an access application; reconstructs a scene "in less than 1 second" on GPU; single-view depth works but was not evaluated quantitatively by the authors. — [facebookresearch/vggt](https://github.com/facebookresearch/vggt)
- MapAnything (Meta, September 2025, 3DV 2026): `facebook/map-anything` is CC-BY-NC 4.0, `facebook/map-anything-apache` is Apache 2.0; code Apache 2.0; outputs metric point maps, depth, intrinsics and poses from one or many images; runs on CUDA or CPU. — [facebookresearch/map-anything](https://github.com/facebookresearch/map-anything)

### Inferences
- A game engine can read exact depth, normals and object IDs from its own buffers or by ray casts at negligible cost, so predicted depth has no role in option (a) or (b) unless the goal is to simulate what a camera-only agent could perceive.
- If image-only depth is wanted on the player's CPU, Depth Anything V2 Small (24.8M, Apache-2.0) is the only tier near feasibility, and at roughly 127 ms on an unspecified i9 with all threads it is already 3 times the 40 ms budget.
- These models are relevant indirectly: Depth Anything V2 and several others are trained on rendered synthetic data, which is evidence that rendered images are in-distribution for geometry models (see section 6).

### Gaps
- No CPU figures for Depth Pro, Metric3D v2, MoGe, VGGT, MapAnything or DA3; no parameter counts for Depth Pro, VGGT and MapAnything on the pages read.
- MoGe pretrained-weight license is not stated on the README.
- The Depth Pro weight license conflict (GitHub versus Hugging Face) is unresolved.
- The variant behind the OpenCV "depth_anything" row is unknown.

## 6. Synthetic and game-rendered images, and unusual categories (hole, pit, cliff edge, ledge, staircase)

### Takeaway
No study was found that measures an open-vocabulary detector on game-engine frames with per-class AP, and none that evaluates "hole", "pit", "cliff edge" or "ledge" prompts. The indirect evidence is mixed to negative: detectors lose most of their AP on non-photorealistic inserted objects, a game agent that used Grounding DINO + SAM in Red Dead Redemption 2 still failed to locate targets, robotics papers treat negative obstacles as a geometry problem and train dedicated stair models, while feature-level evidence (DINOv2 trained on GTA5 transferring to real streets) says the rendering gap itself is modest for modern backbones.

### Cited Findings

#### Detectors under domain shift
- "Can We Challenge Open-Vocabulary Object Detectors with Generated Content in Street Scenes?" (WACV 2026) tested Grounding DINO, YOLO-World, OmDet-Turbo and MDETR on real LostAndFound road-obstacle images and on versions with objects inpainted by Stable Diffusion. Grounding DINO: AP 0.5488 and AR 0.7352 on real data versus AP 0.1975 and AR 0.3319 on synthetic; YOLO-World AP 0.4914 versus 0.0899; OmDet AP 0.2945 versus 0.1221. — [arXiv 2506.23751](https://arxiv.org/html/2506.23751v1)
- Same paper: Grounding DINO produced 1,888 false positives against 154 true positives on real LostAndFound, and 34,340 false positives against 2,957 true positives on the synthetic set; the authors attribute part of the drop to lack of photorealism, find that "object location and prompt choice" matter more than the object's semantic class, and find fixed "blind spot" regions in the image. — [arXiv 2506.23751](https://arxiv.org/html/2506.23751v1)
- Same paper, control experiment: for inpaintings with empty content (no object, just a patch), Grounding DINO missed 21 of 21; for copied road-texture patches it found 1 and missed 15. — [arXiv 2506.23751](https://arxiv.org/html/2506.23751v1)
- "Do Open-Vocabulary Detectors Transfer to Aerial Imagery?" (arXiv, January 2026): the best of five detectors (OWLv2) reached "only 27.6% F1-score with 69% false positive rate" on an 80-class aerial set; cutting the vocabulary from 80 to 3.2 classes gave a 15 times improvement, so "semantic confusion is the primary bottleneck"; prompt engineering did not help. — [arXiv 2601.22164](https://arxiv.org/abs/2601.22164)
- In the auto-labelling study of section 7, the gap between auto-labelled and human-labelled training was largest on BDD driving footage, attributed to viewpoints atypical of the labelers' training data; the classes "rider", "motor" and "train" were left entirely unlabelled in some configurations. — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)

#### Use on actual game frames
- Cradle (general computer control agent) added Grounding DINO and SAM "to provide additional grounding for object detection and localization" on Red Dead Redemption 2 screenshots. Even with "additional detection tools, like Grounding DINO", success on a night combat task dropped to 20%; the authors report "inability to accurately locate enemies or objects", "poor spatial perception, which finds it difficult to locate target objects" indoors, and trouble recognising out-of-distribution icons in the stylised 2D game Stardew Valley. — [Cradle, arXiv 2403.03186](https://arxiv.org/html/2403.03186)
- VideoGameQA-Bench: frontier VLMs reach 53% at best on visual unit tests over game images and "perform poorly at detecting fine details required for accurate scene understanding", including spatial relationships and borderline object clipping. — [VideoGameQA-Bench](https://arxiv.org/html/2505.15952)

#### Rendered images as training or test data for foundation models
- DINOv2-Large backbones trained only on GTA5 (a game) reach 61.1 to 67.7 average mIoU on real street datasets depending on the adaptation method (frozen backbone 61.1, full fine-tuning 61.7, Vireo 67.7). — [Vireo, arXiv 2506.09881](https://arxiv.org/pdf/2506.09881)
- With EVA02 backbones, GTA5-trained segmentation reaches 62.7 to 64.0 average mIoU on Cityscapes / BDD / Mapillary, against about 36 to 46 for pre-foundation-model baselines. — [Set Pivot Learning, arXiv 2508.01582](https://arxiv.org/pdf/2508.01582)
- Depth Anything V2 was trained with all labelled images synthetic. — [arXiv 2406.09414](https://arxiv.org/abs/2406.09414)
- SAM 3 zero-shot semantic segmentation on real Cityscapes: 65.1 mIoU. — [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)

#### Negative obstacles and stairs
- An open-source LiDAR and monocular off-road navigation stack (arXiv, April 2026) names negative obstacles as a major open challenge because the sensor data lacks information about them, and lists them as future work. — [arXiv 2604.03096](https://arxiv.org/pdf/2604.03096)
- A floor-aware zero-shot object-goal navigation system (2025) uses Grounding DINO for open-vocabulary objects and D-FINE for COCO classes, but handles stairs with a separately fine-tuned RedNet on RGB-D input. — [arXiv 2505.23019](https://arxiv.org/pdf/2505.23019)
- A BMVC 2025 workshop paper on potholes finds RGB-trained detectors do well in their training context but lose a lot on out-of-context roads, and fuses them with a monocular-depth detector built on DINOv2 plus SAM masks. — [BMVC 2025 DIFA workshop paper](https://bmva-archive.org.uk/bmvc/2025/assets/workshops/DIFA/Paper_2/paper.pdf)
- A 2026 paper on adapting vision foundation models to traversability argues that semantic labels cause false positives, because semantically safe terrain such as grass can sit on a steep slope or above the ground plane. — [arXiv 2605.29565](https://www.alphaxiv.org/abs/2605.29565.md)
- The ADE20K 150-class list contains "door", "stairs", "stairway" (stairway, staircase), "screen door" and "pole" as classes. — [ADE20K class list](https://huggingface.co/codyshen/Human_parser/blob/main/head_extractor/src/mmseg/datasets/ade.py)
- SAM 3's stated limitation: performance may drop on rare or fine-grained concepts. — [Ultralytics SAM 3 docs](https://docs.ultralytics.com/models/sam-3/)

### Inferences
- "Hole", "pit", "cliff edge" and "ledge" are not objects with a boundary and texture of their own; they are the absence of support, defined by geometry. The inpainting control (21 of 21 empty patches missed) and the robotics practice of using depth or LiDAR for negative obstacles both point the same way: text-prompted 2D detectors are the wrong tool for them. In a game the navmesh, collision queries and height traces answer this exactly and cheaply.
- "Door", "car", "chair", "pole" and "staircase" are ordinary categories that exist in the training vocabularies (COCO, Objects365, LVIS, ADE20K), so the open question for them is only the rendering style. The GTA5-to-real results suggest photoreal UE5 output is close to in-distribution for DINOv2-class features; stylised art is not (Stardew Valley icons failed).
- Expect high false-positive rates when a long class list is prompted on unusual imagery (69% false positives on aerial; more than 10 false positives per true positive for Grounding DINO on LostAndFound). For build-time labelling, prompting with a short list and validating each detection against engine ground truth (actor bounds, object IDs from a custom stencil pass) would remove most of that noise.
- Because the engine can render ground-truth masks, depth and class IDs for every actor, the team can measure the domain gap on its own levels directly and can also generate unlimited labelled training data without any foundation model; that makes a small closed-set model trained on the game's own renders the natural comparison point for every option in this file.

### Gaps
- No paper was found that reports AP of Grounding DINO, OWLv2, YOLO-World, YOLOE, SAM 3 or Florence-2 on frames from GTA V, CARLA, Unreal Engine or any game engine.
- No evaluation was found of the prompts "hole", "pit", "cliff edge", "ledge" or "staircase" for any open-vocabulary detector or VLM.
- Whether LVIS or Objects365 contain "stairs" or "manhole" classes was not verified; Mapillary Vistas' class list (pothole, manhole, curb) was not retrieved.
- The Cradle paper was read only in its first third; details on how SAM was used were not found.
- The reverse direction (models trained on real photos, tested on synthetic test sets such as Hypersim or Virtual KITTI) was searched for and not found for open-vocabulary detectors.

## 7. Use as automatic labelers, and distillation into small closed-set detectors

### Takeaway
Using an open-vocabulary model as a teacher and shipping a small closed-set student is an established pattern with tooling (Autodistill, X-AnyLabeling, Grounded-SAM) and one controlled study: students trained only on auto-labels reach about 93 to 95% of the human-label mAP50 on common-object datasets (VOC, COCO) at roughly one hundred-thousandth of the labelling cost, but fall to about 62% on driving footage and near zero on rare classes.

### Cited Findings

#### Tooling
- Autodistill (Roboflow, Apache 2.0) uses "large, slow foundation models to train small, fast supervised models" with no human in the loop. Base models include Grounded SAM 2, GroundedSAM, GroundingDINO, OWL-ViT, OWLv2, DETIC, SAM-CLIP, Kosmos-2, LLaVA-1.5, CoDet, CLIP, DINOv2 and cloud APIs; target models include YOLOv8, YOLO-NAS, YOLOv5 and DETR. Each plugin carries the license of its underlying model. — [autodistill/autodistill](https://github.com/autodistill/autodistill)
- X-AnyLabeling v4.0.0 (2026-08-05), GPL-3.0, desktop labelling tool with ONNX Runtime, TensorRT and OpenCV DNN back ends; supports Grounding DINO, YOLO-World, YOLOE, SAM 1 / 2 / 3, MobileSAM, EdgeSAM, EfficientViT-SAM, Florence-2, Rex-Omni, RAM++, Depth Anything, Qwen3-VL and cloud VLMs. — [CVHub520/X-AnyLabeling](https://github.com/CVHub520/X-AnyLabeling)
- Grounded SAM 2 (IDEA) combines Grounding DINO with SAM 2 for open-world detection, segmentation and tracking. — [IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)
- OWLv2 itself was built by self-training on pseudo-labels: its "self-trained" checkpoints learn from OWL-ViT pseudo-boxes at web scale. — [scenic OWL-ViT README](https://github.com/google-research/scenic/blob/main/scenic/projects/owl_vit/README.md)
- EfficientSAM3 is a direct distillation of SAM 3 into students about 89 to 90% smaller. — [EfficientSAM3 README](https://github.com/SimonZeng7108/efficientsam3)

#### Controlled results
- "Auto-Labeling Data for Object Detection" (Voxel51, arXiv 2506.02359): labelers YOLO-World, YOLOE and Grounding DINO-T; students YOLO11 n / s / m / l / x and RT-DETR trained 100 epochs from scratch on VOC, COCO, LVIS and BDD. — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)
- YOLO11n mAP50, human labels versus YOLO-World labels at confidence threshold 0.2: VOC 0.756 versus 0.715; COCO 0.496 versus 0.460; LVIS 0.087 versus 0.059; BDD 0.434 versus 0.271; average 0.443 versus 0.376. — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)
- A larger student on auto-labels beat a smaller student on human labels: YOLO11s with YOLO-World labels reached 0.768 on VOC and 0.538 on COCO, versus 0.756 and 0.496 for YOLO11n with human labels. — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)
- Cost: human labelling of the four datasets was estimated at 6,703 hours and $124,092.54; auto-labelling took 1.27 GPU hours and $1.18 on an NVIDIA L40S. — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)
- Threshold: 0.2 gave the best downstream mAP50 in 9 of 11 settings; 0.8 gave the highest label precision and the worst mAP50 in every setting; "high auto-label recall is the best single predictor of downstream model performance". Grounding DINO labels collapsed at high thresholds (VOC 0.637 at 0.2 to 0.314 at 0.8; BDD 0.000 at 0.8). — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)
- Labels closest to human labels were not the best training labels: Grounding DINO had higher label F1 but trained worse students than YOLO-World. — [arXiv 2506.02359](https://arxiv.org/pdf/2506.02359)
- Grounding DINO ran out of memory on LVIS's 1,203 verbose class prompts; splitting the prompts made labelling about 300 times slower than YOLO-World or YOLOE. — [arXiv 2506.02359](https://arxiv.org/html/2506.02359)
- The vendor summary of the same study: auto-labelling reaches "up to 95%" of human-label accuracy; hybrid pipelines with targeted human annotation are recommended. — [Voxel51 report](https://voxel51.com/reports/auto-labeling-data-for-object-detection)
- An Applied Sciences study with Grounding DINO as teacher and a YOLO student reports that auto-generated labels caused no performance degradation and that mixing auto and manual labels improved results; it also notes Grounding DINO is too slow for real-time use. — [MDPI Applied Sciences 14(6):2232](https://www.mdpi.com/2076-3417/14/6/2232)
- Roboflow's qualitative comparison (2023-06-28, Grounding DINO through Autodistill, 5 datasets): two datasets were judged at human quality; failures included missed items on densely stocked shelves, scaffolding labelled as a ladder, and "empty shelf space" never detected because abstract concepts map poorly to prompts; the authors conclude foundation models cannot yet fully replace human labelling and suggest that a model labelling about half the dataset correctly already saves effort. — [Roboflow blog](https://roboflow.com/blog/ai-vs-human-labeled-data)
- Rule-of-thumb figures from a practitioner guide: open-vocabulary models run 10 to 20 times slower per frame and are 5 to 15 AP less accurate than a closed-set detector on classes the latter was trained on; retraining a closed-set student becomes worthwhile at roughly 500 to 1,000 labelled examples per category. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr)
- Student candidates with permissive licenses: RF-DETR Nano / Small / Medium / Large and all RF-DETR-Seg sizes are Apache 2.0 (Nano 48.4 COCO AP, 2.3 ms on T4, 30.5M parameters). — [roboflow/rf-detr](https://github.com/roboflow/rf-detr)

### Inferences
- The teacher-student pattern resolves the runtime problem (the student is a 10 to 40 ms closed-set model) but not automatically the license problem: the fastest and best-documented students (YOLO11, YOLO26) are AGPL-3.0, and X-AnyLabeling is GPL-3.0 (acceptable as an internal tool, since it is not shipped). A student under Apache-2.0 (RF-DETR Nano to Large) or a custom small network trained in-house avoids the issue; RF-DETR's CPU latency was not found and its smallest Apache model has 30.5M parameters, so its fit to 40 ms on 3 cores is unproven.
- The study's central lesson for teacher settings is to favour recall: a low confidence threshold (0.2) gave the best students, and precise-but-sparse labels gave the worst.
- "Empty shelf space" failing as a prompt is the same failure class as "hole" or "pit": concepts defined by absence do not map to detector prompts.
- For a game team the teacher may be unnecessary. The engine can emit exact boxes, masks and class IDs for every placed actor, so the realistic role of an open-vocabulary teacher is narrower: assigning a semantic class to assets whose class is not already known from metadata (for example, deciding that a mesh named `SM_Prop_047` is a chair). That is a per-asset thumbnail classification problem (section 3) rather than a per-frame detection problem, and it runs once per asset at build time.
- If per-frame visual perception is still wanted at runtime, a student trained on engine-generated labels has no teacher noise at all, which should beat the 93 to 95% ceiling reported for auto-labels.

### Gaps
- No study was found that uses SAM 3, Grounding DINO 1.5 / 1.6, DINO-X, Florence-2 or a VLM as the teacher with measured student accuracy; the one controlled study used YOLO-World, YOLOE and Grounding DINO-T.
- No distillation result was found for game or synthetic imagery.
- The MDPI study's exact mAP numbers and publication date were not read.
- CPU latency of RF-DETR students was not found.
- Whether a model trained on labels produced by an AGPL-3.0 or research-only teacher inherits any license obligation is a legal question not addressed by the sources.
