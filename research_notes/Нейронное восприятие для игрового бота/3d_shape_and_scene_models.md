# Neural models that read 3D data directly (meshes, point clouds, scenes): what is ready-made for labelling game-level objects, as of October 2026

Conventions used below. "O-LVIS" = Objaverse-LVIS zero-shot classification (1,156 categories, 46,832 shapes). "MN40" = ModelNet40. "SONN" = ScanObjectNN. Zero-shot numbers are top-1 / top-3 / top-5 in percent unless noted. Every number carries the year and version of the paper or repository it came from. "FP32 size" figures marked "(computed)" are my arithmetic (parameters x 4 bytes), not published file sizes. Research date: 2026-10-10.

## 1. Zero-shot / open-vocabulary 3D shape classification aligned with CLIP-like encoders (ULIP, ULIP-2, OpenShape, Uni3D, TAMM, MixCon3D, ViT-Lens, Duoduo CLIP, newer 2025-2026)

### Takeaway
The published ceiling on Objaverse-LVIS has stayed at about 55% top-1 since 2023-2024 (Uni3D-g 55.3, Duoduo CLIP 12 views 55.2); I found no verified 2025-2026 result that moves it materially, and the 2026 papers I could confirm (3D-MRL, BMVC 2026) report lower numbers. The practically interesting models are the small ones: Uni3D-Ti (6.2M parameters) already reaches 46.5% O-LVIS / 85.9% MN40, and plain CLIP on 12 rendered views with no 3D training at all reaches 43.5%; code licenses are permissive (MIT / Apache-2.0 / BSD-3) but none of the weight repositories carries an explicit license, and the training data includes non-commercially licensed objects.

### Cited Findings

Benchmark definition
- Objaverse-LVIS is a long-tail benchmark with 1,156 categories; one paper describes it as an annotated subset of Objaverse with 46,832 shapes, evaluated with 64 prompts per class following ULIP — [OpenDlign, arXiv 2404.16538](https://arxiv.org/pdf/2404.16538)
- The BlendCLIP authors (arXiv Oct 2025, WACV 2026) state that strong Objaverse-LVIS performance "alone is insufficient to claim zero-shot robustness in real-world settings" — [BlendCLIP, arXiv 2510.18244](https://arxiv.org/pdf/2510.18244)

Uni3D (BAAI, ICLR 2024 spotlight; paper Oct 2023)
- Variants and parameter counts: Uni3D-Ti 6.2M, Uni3D-S 22.6M, Uni3D-B 88.4M, Uni3D-L 306.7M, Uni3D-g 1016.5M (ViT depth/width 12/192, 12/384, 12/768, 24/1024, 40/1408) — [Uni3D paper, Table 5](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Per-variant zero-shot top-1, trained with LVIS shapes ("Ensembled"): Ti 46.5 O-LVIS / 85.9 MN40; S 50.6 / 86.0; B 51.6 / 86.5; L 53.2 / 86.6; g 55.3 / 88.2. Trained without LVIS shapes: Ti 43.5 / 85.8; S 44.8 / 86.0; B 45.8 / 86.2; L 46.2 / 86.6; g 47.2 / 86.8 — [Uni3D paper, Table 5](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Main model (Uni3D-g), top-1/top-3/top-5: Ensembled-no-LVIS: O-LVIS 47.2/68.8/76.1, MN40 86.8/97.3/98.4, SONN 66.5/83.5/90.1. Ensembled: O-LVIS 53.5/75.5/82.0, MN40 87.3/98.1/99.2, SONN 63.9/84.9/91.7. Best-per-benchmark checkpoint: O-LVIS 55.3/76.7/82.9, MN40 88.2/98.4/99.3, SONN 65.3/85.5/92.7 — [Uni3D paper, Table 1](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Repository model zoo (top-1, top-5 in brackets): Uni3d-B Ensembled 51.7 (80.8) O-LVIS, 86.3 (97.9) MN40, 63.8 (90.2) SONN; Uni3d-L 53.1 (81.5) / 86.3 (98.3) / 58.2 (89.4); Uni3d-g 53.5 (82.0) / 87.3 (99.2) / 63.9 (91.7) — [Uni3D GitHub](https://github.com/baaivision/Uni3D)
- Inputs used in evaluation: O-LVIS 10,000 points with RGB; MN40 10,000 points without colour; SONN 2,048 points without colour (OBJ_ONLY). Tokenisation follows PointBERT: farthest point sampling + kNN grouping + a tiny PointNet per patch, then a standard ViT — [Uni3D paper](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Teacher/text side: EVA-CLIP-E/14+ (LAION-2B, listed as 5.0B parameters); the README tells users to download `timm/eva02_enormous_patch14_plus_clip_224.laion2b_s9b_b144k` for evaluation — [Uni3D paper, Table 6](https://ar5iv.labs.arxiv.org/html/2310.06773); [Uni3D GitHub](https://github.com/baaivision/Uni3D)
- Training cost: Uni3D-g converges in about 20 hours on 24 x A100-40GB. Inference speed is not reported. Freezing the EVA ViT instead of fine-tuning drops O-LVIS to 15.7 — [Uni3D paper](https://ar5iv.labs.arxiv.org/html/2310.06773)
- License: code is MIT; no separate weights license is stated in the README; the Hugging Face repository `BAAI/Uni3D` has no model card and no license field — [Uni3D GitHub](https://github.com/baaivision/Uni3D); [HF BAAI/Uni3D](https://huggingface.co/BAAI/Uni3D)
- File sizes: the `modelzoo` folder on Hugging Face totals 11.9 GB across ten sub-folders (ti, s, b, l, g, each with and without LVIS); individual `model.pt` sizes were not visible — [HF BAAI/Uni3D modelzoo](https://huggingface.co/BAAI/Uni3D/tree/main/modelzoo)
- Uni3D's zero-shot ScanNet object table shows very low per-category scores for some classes (cabinet 3.7, counter 1.9, shower curtain 10.7) — [Uni3D paper, Table 2](https://ar5iv.labs.arxiv.org/html/2310.06773)

OpenShape (NeurIPS 2023; paper May 2023)
- Checkpoints and zero-shot top-1 (top-5): pointbert-vitg14-rgb (four datasets) 46.8 (77.0) O-LVIS, 84.4 (98.0) MN40; pointbert-no-lvis 39.1 (68.9) / 85.3 (97.4); pointbert-shapenet-only 10.8 (25.0) / 70.3 (91.3); spconv-all 42.7 (72.8) / 83.7 (98.4); spconv-all-no-lvis 38.1 (68.2) / 84.0 (97.3); spconv-shapenet-only 12.1 (27.1) / 74.1 (89.5). Text/image space: OpenCLIP ViT-bigG-14 (laion2b_s39b_b160k) — [OpenShape GitHub](https://github.com/Colin97/OpenShape_code)
- Top-3 for the main PointBERT checkpoint: 46.8 / 69.1 / 77.0 (Ensembled) and 39.1 / 60.8 / 68.9 (no LVIS) — [Duoduo CLIP paper, Table 2](https://arxiv.org/html/2406.11579v1)
- SONN zero-shot: OpenShape-SparseConv 56.7 / 78.9 / 88.6; OpenShape-PointBERT 52.2 / 79.7 / 88.7 — [OpenShape paper](https://arxiv.org/html/2305.10764)
- Input: 10,000 points, xyz in [-1, 1], RGB in [0, 1]; the gravity axis must match the checkpoint (z-up for the main ones, y-up for the two demo checkpoints) — [OpenShape GitHub](https://github.com/Colin97/OpenShape_code)
- Parameter counts from the scaling study: PointBERT 5.1M, 13.3M, 32.3M, 72.1M (72.1M overfit and was worse than 32.3M); SparseConv 5.3M, 29.0M, 33.7M, 41.3M — [OpenShape paper, Tables 6-7](https://arxiv.org/html/2305.10764)
- Published file size: `model.pt` of `openshape-pointbert-vitg14-rgb` is 388 MB — [HF OpenShape/openshape-pointbert-vitg14-rgb](https://huggingface.co/OpenShape/openshape-pointbert-vitg14-rgb/tree/main)
- Inference speed: forward pass for a 10,000-point cloud on an A100 takes about 0.9 ms (SparseConv) and 3.8 ms (PointBERT). Training took about 300 A100-hours on one A100 — [OpenShape paper](https://arxiv.org/html/2305.10764)
- Colour ablation: xyz-only input gave 39.6 O-LVIS / 83.6 MN40 against 42.0 / 83.1 with colour (ablation-size model) — [OpenShape paper](https://arxiv.org/html/2305.10764)
- Stated limitations: 876k training shapes is small; no part-level information (embeddings capture global semantics and appearance); sim-to-real gap. Objaverse shapes are user uploads, not expert-verified, of uneven quality, with highly unbalanced categories; GPT-4 filtered about 30% of the raw user texts as uninformative — [OpenShape paper](https://arxiv.org/html/2305.10764)
- License: code Apache-2.0; no weights license stated in the README or on the checked Hugging Face file page. Dependencies include MinkowskiEngine and DGL — [OpenShape GitHub](https://github.com/Colin97/OpenShape_code); [HF OpenShape checkpoint](https://huggingface.co/OpenShape/openshape-pointbert-vitg14-rgb/tree/main)

ULIP / ULIP-2 (Salesforce; CVPR 2023 / CVPR 2024)
- ULIP-1 zero-shot MN40 top-1 (top-5) with 8k points: PointNet++ (ssg) 57.7 (78.9), PointMLP 60.0 (79.4), PointBERT 60.3 (84.0), PointNeXt 56.2 (77.0) — [Salesforce ULIP GitHub](https://github.com/salesforce/ULIP)
- ULIP-2 PointBERT, 10k xyzrgb points, ensembled Objaverse + ShapeNet triplets: "Objaverse" 50.6 (79.1), MN40 84.7 (97.1), compared in the same table with OpenShape PointBERT 46.8 (77.0) / 84.4 (98.0) — [Salesforce ULIP GitHub](https://github.com/salesforce/ULIP)
- ULIP-PointBERT trained on ShapeNet only: O-LVIS 6.2 / 13.6 / 17.9, MN40 60.4 / 79.0 / 84.4, SONN 51.5 / 71.1 / 80.2 — [OpenDlign paper, Table 1](https://arxiv.org/html/2404.16538v3)
- License: code BSD-3-Clause; ULIP-Objaverse triplets under ODC-By 1.0; ULIP-ShapeNet triplets under ShapeNet's terms of use; no separate license statement for the pretrained models. Since 2025-05-23 all ULIP data and models live at `huggingface.co/datasets/SFXX/ulip`, whose dataset card is empty (no license shown) — [Salesforce ULIP GitHub](https://github.com/salesforce/ULIP); [HF SFXX/ulip](https://huggingface.co/datasets/SFXX/ulip)

TAMM (CVPR 2024), ViT-Lens (CVPR 2024), ShapeLLM / ReCon++ (ECCV 2024), MixCon3D (CVPR 2024)
- TAMM-PointBERT: O-LVIS 50.7 / 73.2 / 80.6 (Ensembled) and 42.0 / 63.6 / 71.7 (no LVIS) — [Duoduo CLIP paper, Table 2](https://arxiv.org/html/2406.11579v1)
- TAMM trained on ShapeNet only: PointBERT MN40 73.1 / 88.5 / 91.9, SONN 54.8 / 74.5 / 83.3, O-LVIS 13.7 / 24.2 / 29.2; SparseConv MN40 74.6 / 88.2 / 94.0, SONN 57.9 / 75.3 / 83.1 — [OpenDlign paper, Table 1](https://arxiv.org/html/2404.16538v3)
- ViT-Lens-G: O-LVIS 52.0 / 73.3 / 79.9 (Ensembled), 50.1 / 71.3 / 78.1 (no LVIS) — [Duoduo CLIP paper, Table 2](https://arxiv.org/html/2406.11579v1); the ViT-Lens paper reports 52.0 O-LVIS, 87.4 MN40, 60.6 SONN — [ViT-Lens, arXiv 2308.10185](https://arxiv.org/pdf/2308.10185)
- ShapeLLM (ReCon++ encoder): O-LVIS 53.7 / 75.8 / 82.0; trained 1 day on 8 x A800-80GB — [Duoduo CLIP paper, Tables 1-2](https://arxiv.org/html/2406.11579v1)
- MixCon3D: the repository says it uses the same data as OpenShape and a PointBERT backbone; the README shows no numbers, no checkpoint links and no license file — [MixCon3D GitHub](https://github.com/UCSC-VLAA/MixCon3D)

Multi-view image route (covered here because it competes directly with point encoders)
- Plain zero-shot CLIP on 12 rendered views with averaged embeddings, no 3D training: CLIP ViT-B/32 35.7 / 54.8 / 62.1 on O-LVIS; OpenCLIP ViT-bigG-14 43.5 / 64.2 / 71.3 — [Duoduo CLIP paper, Table 2](https://arxiv.org/html/2406.11579v1)
- Duoduo CLIP (2024): O-LVIS 55.2 / 77.1 / 83.4 with 12 views and 54.1 / 76.0 / 82.4 with 5 views (Ensembled); 52.7 / 74.5 / 81.3 and 51.3 / 73.1 / 79.9 without LVIS — [Duoduo CLIP paper, Table 2](https://arxiv.org/html/2406.11579v1)
- Duoduo CLIP has 87 million parameters, takes (F, H, W, 3) images (example: 12 views at 224x224; a single view is accepted), is built on OpenCLIP, and was trained in 14.3 hours on 4 x A5000-24GB with only the multi-view attention layers of the last 6 of 12 layers trainable. The default checkpoint is `Four_1to6F_bs1600_LT6.ckpt` — [Duoduo CLIP GitHub](https://github.com/3dlg-hcvc/DuoduoCLIP); [Duoduo CLIP paper](https://arxiv.org/html/2406.11579v1)
- No license is shown for the Duoduo CLIP code or weights on the pages checked — [Duoduo CLIP GitHub](https://github.com/3dlg-hcvc/DuoduoCLIP); [HF 3dlg-hcvc/DuoduoCLIP](https://huggingface.co/3dlg-hcvc/DuoduoCLIP)
- Duoduo CLIP failure modes stated by its authors: it "sometimes fails in cases requiring geometric understanding" (a "round back" query favoured point-cloud methods; a soccer-ball query retrieved ladybugs with red wings and black dots, where OpenShape was more robust). On real multi-view images (MVPNet) the model without real-image training scored 49.16% top-1, below zero-shot CLIP B/32 at 52.68%; OpenShape on reconstructed MVPNet point clouds scored 3.55% — [Duoduo CLIP paper, Table 5 and limitations](https://arxiv.org/html/2406.11579v1)
- OpenDlign (2024) classifies from 10 depth maps projected from the point cloud, using a fine-tuned plus a frozen CLIP image encoder. Trained on ShapeNet only, OpenDlign-H (OpenCLIP ViT-H-14): MN40 82.6 / 96.2 / 98.4, SONN 59.5 / 76.8 / 83.7, OmniObject3D 31.3 / 46.7 / 53.2, O-LVIS 35.0 / 53.1 / 60.0; OpenDlign-B32: 68.4 MN40, 46.7 SONN, 22.0 O-LVIS — [OpenDlign paper, Table 1](https://arxiv.org/html/2404.16538v3)
- Projection-only baselines with no 3D training: PointCLIP 19.3 MN40 / 10.5 SONN / 1.9 O-LVIS; PointCLIP V2 63.6 / 42.2 / 4.7; CLIP2Point 49.5 / 25.5 / 2.7 — [OpenDlign paper, Table 1](https://arxiv.org/html/2404.16538v3)

2025-2026 work
- 3D-MRL (arXiv 2608.29285, submitted 2026-08-29, accepted at BMVC 2026) aligns point clouds with frozen CLIP embeddings using Matryoshka (nested-dimension) contrastive supervision; its abstract reports O-LVIS top-1 improving from 46.8% to 50.9%. Code and weight availability is not stated on the abstract page — [3D-MRL, arXiv 2608.29285](https://arxiv.org/abs/2608.29285)
- 3DAlign-DAER (arXiv 2511.13211, Nov 2025, revised 2026-04-24) is reported in a search extract of the paper as reaching 55.8% top-1 on O-LVIS against 53.1% for ReCon++-L, and 88.5% on MN40; the abstract page itself gives no numbers and says code, models and the Align3D-2M dataset "will" be released — [3DAlign-DAER PDF](https://arxiv.org/pdf/2511.13211); [3DAlign-DAER abstract](https://arxiv.org/abs/2511.13211)
- BlendCLIP (arXiv Oct 2025, WACV 2026) targets zero-shot classification of real outdoor LiDAR objects (nuScenes, TruckScenes) by mixing CAD triplets with driving data — [BlendCLIP, arXiv 2510.18244](https://arxiv.org/pdf/2510.18244)

Training-data licenses that bear on the weights
- Objaverse as a whole is ODC-By v1.0; individual objects carry Creative Commons licenses: CC-BY 4.0 721K objects, CC-BY-NC 4.0 25K, CC-BY-NC-SA 4.0 52K, CC-BY-SA 4.0 16K, CC0 1.0 3.5K — [HF allenai/objaverse](https://huggingface.co/datasets/allenai/objaverse)
- ShapeNet access requires accepting a separate Terms of Use document — [HF ShapeNet](https://huggingface.co/ShapeNet)

### Inferences
- For a fixed game vocabulary ("door", "car", "chair", "staircase", "pole", "table", ...) the text encoder is needed only once, offline: the class-prompt embeddings are a constant matrix, and classification at inference is one 3D-encoder forward pass plus a dot product. The billion-parameter CLIP text tower therefore does not have to ship.
- The team has exact meshes offline, so labelling static level objects is a build-time job: any model in this section can run once on a GPU workstation and the result is stored as a tag. The CPU-only runtime budget only matters for objects that do not exist at build time.
- If a runtime model is wanted, the Uni3D small variants are the natural candidates: Uni3D-Ti at 6.2M parameters is about 25 MB FP32 (computed) and Uni3D-S at 22.6M about 90 MB (computed). The Hugging Face total of 11.9 GB for ten checkpoints is consistent with plain FP32 storage (computed sum of the published parameter counts x 2 x 4 bytes is about 11.5 GB).
- Uni3D's network after tokenisation is a standard ViT, so the transformer part should export to ONNX with stock operators if farthest-point sampling and kNN grouping are done in C++ before the graph. This is an architectural inference; I found no published ONNX export of Uni3D or OpenShape.
- The 388 MB OpenShape checkpoint is about three times what 32.3M FP32 parameters would occupy (about 129 MB, computed); the difference is unexplained by the sources (the file may contain additional state).
- Accuracy saturates quickly with size: going from 6.2M to 1016.5M parameters buys 8.8 points on O-LVIS and 2.3 points on MN40 (Uni3D Table 5). For a vocabulary of a few dozen coarse game categories, MN40-style accuracy in the mid-80s is the more relevant reference than the 1,156-way number.
- The numbers that matter for a commercial product are the "no LVIS" rows (43.5-47.2% for Uni3D), since the "Ensembled" rows trained on the evaluation shapes.
- Weights of every model here inherit an unclear commercial status: code licenses are permissive, weight licenses are unstated, and the Objaverse training pool contains about 77K objects under NC licenses out of roughly 818K listed. This needs a legal reading before shipping weights inside a product; using a model only as an offline tool and shipping just the resulting text labels is a different and lighter question.

### Gaps
- No source states top-3 for ULIP-2 or any numbers for MixCon3D in the pages I could open; the MixCon3D README has no results and no license.
- The composition of OpenShape's "four datasets" and the licenses of each (beyond Objaverse and ShapeNet) were not verified in this session.
- The exact text of the ShapeNet Terms of Use (commercial restriction) could not be opened; `shapenet.org/terms` now redirects to Hugging Face.
- No model in this group has a published CPU latency or an official ONNX export that I could find.
- 3DAlign-DAER's 55.8% claim comes from a search extract of the PDF, weights are not confirmed released, and I could not confirm the number on the abstract page. No other 2026 claim above 55.3% was found; I cannot rule out one existing.
- TAMM, ViT-Lens, ShapeLLM/ReCon++ and OpenDlign code and weight licenses were not checked.

## 2. Supervised point-cloud classifiers small enough for CPU (PointNet, PointNet++, DGCNN, PointMLP, PointNeXt, Point-MAE / Point-BERT, PTv2 / PTv3, Mamba-based) and ONNX export experience

### Takeaway
The classic supervised classifiers are tiny (0.6M-13M parameters for the non-pretrained ones, 12M-44M for masked-autoencoder and Mamba backbones) and reach 93-94% on ModelNet40 and 85-90% on ScanObjectNN PB_T50_RS, but published speed is almost always GPU throughput, not CPU latency. ONNX export is routine only for PointNet; anything using farthest point sampling, ball query, torch-scatter or sparse convolution relies on custom compiled operators and needs either a pure-tensor rewrite or vendor plugins (the one production PTv3 ONNX path found targets TensorRT on GPU).

### Cited Findings

Accuracy, size and GPU throughput (1,024 points, no voting; throughput at batch 128 on a Tesla V100-32GB with a 32-core Xeon 2.80GHz)

| Model | Params (M) | FLOPs (G) | MN40 OA % | SONN PB_T50_RS OA % | Throughput (inst./s) | Source |
|---|---|---|---|---|---|---|
| PointNet | 3.5 | 0.9 | 89.2 | 68.2 | 4212 | [PointNeXt paper, Table 2](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| PointNet++ (original) | 1.5 | 1.7 | 91.9 | 77.9 | 1872 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| PointNet++ (improved training only) | 1.5 | 1.7 | 92.8 ± 0.1 | 86.1 ± 0.7 | 1872 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| PointNeXt-S | 1.4 | 1.6 | 93.2 ± 0.1 | 87.7 ± 0.4 | 2040 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| DGCNN | 1.8 | 4.8 | 92.9 | 78.1 | 402 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| PointCNN | 0.6 | – | 92.2 | 78.5 | 44 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| PointMLP | 13.2 | 31.3 | 94.1 | 85.4 ± 1.3 | 191 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| CurveNet | 2.0 | – | 93.8 | – | 22 | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| SimpleView (multi-view projection) | 0.8 | – | 93.0 ± 0.4 | 80.5 ± 0.3 | – | [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670) |
| PCT | 2.9 | 2.3 | 93.2 | – | – | [PointMamba paper, Table 2](https://arxiv.org/html/2402.10739) |
| Point-BERT (pretrained) | 22.1 | 4.8 | 92.7 | 83.07 | – | [PointMamba paper, Tables 1-2](https://arxiv.org/html/2402.10739) |
| Point-MAE (pretrained) | 22.1 | 4.8 | 93.2 | 85.18 (89.04 with rotation augmentation) | – | [PointMamba paper](https://arxiv.org/html/2402.10739) |
| Point-M2AE (pretrained) | 15.3 | 3.6 | 93.4 | 86.43 | – | [PointMamba paper](https://arxiv.org/html/2402.10739) |
| PointGPT-S (pretrained) | 29.2 | 5.7 | 93.3 | 89.17 | – | [PointMamba paper](https://arxiv.org/html/2402.10739) |
| ACT (cross-modal pretrained) | 22.1 | 4.8 | 93.6 | 88.21 | – | [PointMamba paper](https://arxiv.org/html/2402.10739) |
| ReCon (cross-modal pretrained) | 43.6 | 5.3 | – | 90.63 | – | [PointMamba paper](https://arxiv.org/html/2402.10739) |
| PointMamba (pretrained, 2024) | 12.3 | 3.1 (1.5 on MN40) | 93.6 | 89.31 | – | [PointMamba paper](https://arxiv.org/html/2402.10739) |

- PointNeXt's abstract: 87.7 OA on ScanObjectNN, 2.3 points above PointMLP while "10x faster in inference"; improved training alone lifts PointNet++ from 77.9% to 86.1% on ScanObjectNN with no architecture change — [PointNeXt, arXiv 2206.04670](https://arxiv.org/abs/2206.04670)
- Point Transformer V3 (CVPR 2024): 46.2M parameters; on ScanNet scenes at batch 1 on one RTX 4090 inference takes 61 ms and 5.2 GB, against 191 ms / 18.2 GB for PTv2 (12.8M), 90 ms / 4.7 GB for MinkUNet (37.9M), 86 ms / 12.5 GB for OctFormer (44.0M), 456 ms / 8.8 GB for Swin3D (71.1M). The paper reports no object classification results. It depends on space-filling-curve serialisation, a sparse-convolution positional encoding (xCPE) and optionally flash attention — [PTv3 paper](https://ar5iv.labs.arxiv.org/html/2312.10035)
- LitePT (ETH Zurich / Oxford / Zurich, CVPR 2026): LitePT-S 12.7M parameters, LitePT-B 45.1M, LitePT-L 85.9M; LitePT-S runs ScanNet inference in 21 ms / 2.0 GB against PTv3's 51 ms / 4.1 GB in the authors' benchmark, with 76.5 mIoU on ScanNet val. Code is MIT; checkpoints are on Hugging Face (`prs-eth/LitePT`) with no separate weights license stated. Dependencies: spconv, flash-attention and a CUDA PointROPE extension with a slower pure-PyTorch fallback — [LitePT GitHub](https://github.com/prs-eth/LitePT); [LitePT paper](https://arxiv.org/pdf/2512.13689)
- Utonia (March 2026, 137M parameters, PTv3-based) reports object classification of 92.4 (fine-tuned) / 88.2 (linear probe) on ModelNet40 and 95.0 / 86.9 on ScanObjectNN, given as mAcc — [Utonia paper](https://arxiv.org/html/2603.03283)

CPU latency evidence (sparse)
- A lookup-table method paper reports 1.5 ms inference on an Intel i7-8700 in single-core mode and describes this as a 32x speedup over PointNet — [Justlookup, arXiv 1908.08996](https://arxiv.org/pdf/1908.08996)
- A 2026 edge-deployment paper profiles PointNet on CPU and finds latency roughly flat at about 21 ms from 16 to 128 points; it does not use ONNX — [arXiv 2608.07106](https://arxiv.org/pdf/2608.07106)

ONNX export experience
- PointNet is distributed as an ONNX model by Qualcomm AI Hub: input 1x3x1024, 13.2 MB, ONNX Runtime 1.30.0, 0.255-0.724 ms on Snapdragon NPUs (not CPU figures); the deployment package is Apache-2.0 and is exported from the `nikitakaraevv/pointnet` implementation — [HF qualcomm/PointNet](https://huggingface.co/qualcomm/PointNet)
- PointNet++ implementations route farthest point sampling and grouping through compiled CUDA extensions (example: Kaolin's PointNet2), which have no standard ONNX operator — [Kaolin PointNet2 source](https://kaolin-jfl.readthedocs.io/en/latest/_modules/models/PointNet2.html)
- A 2026 Huawei Ascend ModelZoo port replaces the CUDA op with a loop-based farthest point sampling written with standard tensor operations (argmax/min) to make the model exportable — [Ascend ModelZoo pointnet2_ops.py](https://gitcode.com/ascend/ModelZoo-PyTorch/blob/master/ACL_PyTorch/built-in/embodied_ai/GenPosePlus/pointnet2_ops.py)
- A PyTorch forum thread on exporting PointNet++ to ONNX shows tracer warnings from the random start index (`torch.randint`) and Python-side conditionals, and an export that hung — [PyTorch forums](https://discuss.pytorch.org/t/there-was-a-problem-converting-the-model-to-onnx-format/151356)
- MMDeploy's supported 3D models are only CenterPoint, PointPillars (ONNX Runtime, OpenVINO, TensorRT) and SMOKE; voxelisation pre- and post-processing are not converted to ONNX and must be supplied by the caller. No PointNet++, ball-query or sparse-convolution model is listed — [MMDeploy mmdet3d docs](https://mmdeploy.readthedocs.io/en/latest/04-supported-codebases/mmdet3d.html)
- Autoware Foundation ships Point Transformer V3 as three ONNX sub-models (`ptv3_encoder.onnx`, `ptv3_det3d_head.onnx`, `ptv3_seg3d_head.onnx`) with voxelisation outside the graphs; the runtime is TensorRT (FP16) with sparse-convolution plugins from `autoware_tensorrt_plugins` / spconv_cpp; license Apache-2.0. CPU execution is not mentioned — [HF AutowareFoundation/ptv3](https://huggingface.co/AutowareFoundation/ptv3)
- A deployment report states spconv's SparseConv2d/SubMConv2d layers are not natively supported by ONNX/TensorRT; replacing them with dense convolutions took latency from about 23 ms (PyTorch + spconv) to about 50 ms (TensorRT FP16 dense) — [NVIDIA developer forum](https://forums.developer.nvidia.com/t/deploying-spconv-based-3d-detection-model-pillarnet-with-tensorrt-on-aarch64-gb10-libspconv-sm120-missing/362588)
- A GitHub issue reports noticeable output differences for a sparse-convolution CenterPoint model after ONNX export with spconv 2.3.3 — [Lidar_AI_Solution issue 217](https://github.com/NVIDIA-AI-IOT/Lidar_AI_Solution/issues/217)

### Inferences
- GPU throughput converts to per-object GPU time of about 0.24 ms (PointNet), 0.49 ms (PointNeXt-S), 0.53 ms (PointNet++), 2.5 ms (DGCNN) and 5.2 ms (PointMLP) at batch 128 (computed from the instances/s column). CPU numbers will be one to two orders of magnitude higher; the two CPU data points found put PointNet at roughly 20-50 ms on a single desktop core.
- FP32 sizes (computed): PointNeXt-S about 5.6 MB, PointNet++ 6 MB, DGCNN 7.2 MB, PointNet 14 MB (matches Qualcomm's 13.2 MB ONNX), PointMamba 49 MB, PointMLP 53 MB, Point-MAE/Point-BERT 88 MB.
- For ONNX Runtime on CPU the safe set is: PointNet (pure MLP + max-pool), DGCNN if kNN is expressed with `TopK` on a pairwise-distance matrix, and ViT-style encoders (Point-MAE, Point-BERT, Uni3D) with sampling/grouping moved outside the graph. PTv3-family models (PTv3, LitePT, Sonata, Concerto, Utonia) and MinkowskiEngine/spconv models (OpenShape SparseConv, Mask3D, OpenScene, Mosaic3D) are not practical on stock ONNX Runtime CPU: I found no evidence of anyone running them there.
- Because the team can pick the sampling itself (deterministic surface sampling of a known mesh), farthest point sampling and ball query can be precomputed in engine code and passed in as index tensors, which removes the main export obstacle for PointNet++-style networks.
- A supervised classifier trained on the team's own labelled assets (a few dozen categories) is likely to beat zero-shot models on those categories at 1-2M parameters; zero-shot models are more useful for bootstrapping the labels.

### Gaps
- No published ONNX Runtime CPU latency for PointNet++, DGCNN, PointNeXt, PointMLP, Point-MAE or PointMamba was found.
- Point Transformer V2 classification accuracy, Mamba3D and other Mamba variants, and PointMLP-elite were not verified from primary sources in this session.
- Code and weight licenses of PointNet, PointNet++, DGCNN, PointMLP, PointNeXt, Point-MAE, Point-BERT and PointMamba repositories were not checked. ModelNet40 and ScanObjectNN dataset terms (which govern published checkpoints) were not checked.
- Mamba's selective-scan operator and its ONNX exportability were not researched.

## 3. Mesh-native and multi-view alternatives (MeshCNN, MeshNet, MeshMAE, MVCNN-style rendering plus an image backbone)

### Takeaway
Mesh-native networks trail point and multi-view methods on ModelNet40 (88-92.5%) and impose heavy preprocessing (manifold repair, simplification to a few hundred faces, remeshing) that typical game meshes violate; DiffusionNet is the exception on input assumptions. Multi-view rendering is the stronger alternative: with no 3D training, CLIP on 12 views already gives 43.5% on Objaverse-LVIS, and a tuned multi-view model (Duoduo CLIP, 87M parameters) ties the 1B-parameter Uni3D at about 55%.

### Cited Findings
- ModelNet40 accuracy of mesh methods as tabulated by MeshMAE (2022): MeshNet 88.4, MeshWalker 90.5, SubdivNet 91.4, mesh transformer without pretraining 91.5, MeshMAE pretrained on ModelNet40 91.7, MeshMAE pretrained on ShapeNet 92.5; point-based PCT is listed at 92.4 for reference. MeshMAE's encoder is ViT-Base-like (12 layers) — [MeshMAE paper, Table 1](https://ar5iv.labs.arxiv.org/html/2207.10228)
- Other tables give MeshNet 91.9 and MeshWalker 92.3 on the original ModelNet40 — [SubdivNet, arXiv 2106.02285](https://arxiv.org/pdf/2106.02285)
- MeshMAE preprocessing: most meshes "are not watertight or 2-manifold", so shapes are first reconstructed into manifold meshes, simplified uniformly to 500 faces, remeshed with MAPS to a base mesh of 96-256 faces, then subdivided three times (x64 faces); each input gets 10 remeshed variants — [MeshMAE paper](https://ar5iv.labs.arxiv.org/html/2207.10228)
- SubdivNet's authors built Manifold40, a closed-manifold reconstruction of ModelNet40, because most ModelNet40 shapes are not watertight or 2-manifold and remeshing fails; all tested methods score lower on Manifold40. ModelNet40 objects often contain multiple components and are not necessarily watertight, "making this dataset prohibitive for some mesh-based methods" — [SubdivNet, arXiv 2106.02285](https://arxiv.org/pdf/2106.02285); [MeshWalker, arXiv 2006.05353](https://arxiv.org/pdf/2006.05353)
- MeshWalker copes with non-watertight, multi-component meshes because a random walk that reaches a dead end jumps to a new random location — [MeshWalker, arXiv 2006.05353](https://arxiv.org/pdf/2006.05353)
- SHREC11 classification: MeshCNN 98.6% (16 per class) / 91.0% (10 per class); MeshWalker 98.6% / 97.1%; DiffusionNet 99.5% (10 per class) — [Task-driven mesh network, arXiv 2306.05246](https://arxiv.org/pdf/2306.05246)
- MeshCNN: edge-based network for triangular meshes, PyTorch 1.2, MIT license — [MeshCNN GitHub](https://github.com/ranahanocka/MeshCNN)
- DiffusionNet: accepts triangle meshes and point clouds, "does not impose any assumptions such as manifoldness", is robust to triangulation and resolution, but needs a per-shape CPU precomputation of Laplacian operators and eigendecompositions (a few seconds at about 20k vertices, about a minute at about 200k vertices, cacheable); MIT license — [DiffusionNet GitHub](https://github.com/nmwsharp/diffusion-net)
- Supervised multi-view methods: MVTN reports 93.8% on ModelNet40 and up to 6% improvement on ScanObjectNN; PointNeXt's comparison lists MVTN at 93.5 MN40 / 82.8 SONN with 3.5M parameters, 1.8G FLOPs and 236 instances/s — [MVTN, arXiv 2011.13244](https://arxiv.org/pdf/2011.13244); [PointNeXt paper](https://ar5iv.labs.arxiv.org/html/2206.04670)
- RotationNet with a ResNet-50 backbone reaches 94.77 ± 1.10 mean accuracy on ModelNet40 over random view subsets — [RotationNet, arXiv 1603.06208](https://arxiv.org/pdf/1603.06208)
- MVTN's authors note ViewGCN gets higher accuracy by relying on higher-quality images from a non-differentiable OpenGL renderer, i.e. render quality is part of the result — [MVTN extended, arXiv 2212.13462](https://arxiv.org/pdf/2212.13462)
- Zero-shot multi-view vs point-based on the same benchmark (O-LVIS, Ensembled): CLIP bigG-14 12 views 43.5; OpenShape-PointBERT 46.8; TAMM 50.7; ViT-Lens-G 52.0; ShapeLLM/ReCon++ 53.7; Duoduo CLIP 5 views 54.1, 12 views 55.2; Uni3D-g 55.3 — [Duoduo CLIP paper, Table 2](https://arxiv.org/html/2406.11579v1)
- Cost comparison stated by the Duoduo CLIP authors: 87M parameters and 14.3 h on 4 x A5000 against Uni3D's 1B parameters and 20 h on 24 x A100 — [Duoduo CLIP paper, Table 1](https://arxiv.org/html/2406.11579v1)
- Multi-view images "represent textures better than point clouds", while point clouds encode 3D coordinates directly, which the same authors call an inherent advantage for geometric queries — [Duoduo CLIP paper](https://arxiv.org/html/2406.11579v1)
- For untextured meshes, the MeshSegmenter authors state that 2D foundation models are trained on texture-rich images and there is a domain gap when they are applied to untextured renders; their workaround is to synthesise textures first — [MeshSegmenter, arXiv 2407.13675](https://arxiv.org/html/2407.13675v2)

### Inferences
- Mesh-native classifiers are a poor fit for game assets: level meshes are usually non-manifold, multi-component, with intersecting shells and widely varying triangle counts, which is exactly the input the remeshing pipelines of MeshCNN, SubdivNet and MeshMAE cannot take without repair. Sampling points from the surface discards the topology problem entirely, which is why the point route is more robust for this use.
- Multi-view rendering costs the game team almost nothing extra offline (the engine is the renderer and materials are available), and the image backbone is a standard ViT with a well-trodden ONNX path; the price is N image-encoder passes per object (5-12), each far heavier than a small point network.
- For untextured or grey-box assets the multi-view route loses its main advantage (texture) and the point route's geometry advantage grows; a combination (point embedding plus a few rendered views) hedges both failure modes.

### Gaps
- No ModelNet40 number for MVCNN or View-GCN was retrieved from a primary source in this session, and no study using DINOv2 or SigLIP features on rendered views for 3D classification was found.
- Parameter counts and code licenses for MeshNet, MeshWalker, SubdivNet and MeshMAE were not verified.
- No CPU latency is published for any mesh-native network.

## 4. Self-supervised 3D backbones released in 2025 and 2026 (Sonata, Concerto, Utonia, PTv3 successors)

### Takeaway
The Pointcept line (Sonata, CVPR 2025; Concerto, NeurIPS 2025; Utonia, March 2026) gives strong frozen per-point features for scenes (linear probing 72.5, 77.3 and 77.7 mIoU on ScanNet respectively), but all three ship weights under CC-BY-NC 4.0 because of non-commercial training data, need sparse convolution on GPU, and are not text-aligned out of the box. LitePT (CVPR 2026, MIT code) is the only new backbone found with a permissive code license and a much smaller footprint, but it is a supervised scene backbone, not a pretrained universal encoder.

### Cited Findings
- Sonata: self-supervised Point Transformer V3; input dictionary `coord` (N,3), `color` (N,3), `normal` (N,3); depends on spconv, torch-scatter and (optionally) flash attention; code Apache 2.0, weights CC-BY-NC 4.0, "restricted by NC of datasets like HM3D, ArkitScenes"; one checkpoint `facebook/sonata` — [Sonata GitHub](https://github.com/facebookresearch/sonata)
- Sonata numbers (2025): backbone given as 108M parameters in text and 124.8M in result tables; about 140k training point clouds; linear probing 72.5 mIoU ScanNet, 29.3 ScanNet200, 72.3 S3DIS Area 5; full fine-tuning 79.4 ScanNet, 36.8 ScanNet200, 43.7 ScanNet++, 76.0 S3DIS Area 5; with 1% of ScanNet scenes, linear probing reaches 43.6 against 25.8 from scratch — [Sonata paper](https://arxiv.org/html/2503.16429)
- Sonata's "geometric shortcut" diagnosis: earlier point self-supervised models collapse onto low-level cues such as normals or height; previous methods reached only 5.6% (PC) and 21.8% (MSC) ScanNet linear-probing mIoU against 63.1% for DINOv2 features lifted to 3D — [Sonata paper](https://arxiv.org/html/2503.16429)
- Concerto: joint 2D-3D self-supervised PTv3; checkpoints `concerto_small` 39M, `concerto_base` 108M, `concerto_large` 208M on `Pointcept/Concerto`; code Apache-2.0, weights CC-BY-NC 4.0 (same NC-data reason); the repository also lists a SigLIP-based weight `concerto_base_siglip.pth` with an entry dated August 2026 — [Concerto GitHub](https://github.com/Pointcept/Concerto)
- Concerto numbers (Oct 2025): linear probing 77.3 ScanNet, 37.4 ScanNet200, 45.6 ScanNet++, 73.5 S3DIS; full fine-tuning 80.7 / 39.2 / 50.7 / 77.4; beats DINOv2 lifted to 3D (63.09 ScanNet) and Sonata+DINOv2 concatenation (75.91). A tiny 5M variant exists in the scaling table. A language-probing translator into CLIP space gives zero-shot ScanNet 44.56 mIoU (mAcc 64.76) against 41.71 for Sonata. Concerto-L uses 50k extra point clouds lifted from video with VGGT — [Concerto paper](https://arxiv.org/html/2510.23607)
- Utonia (HKU / CUHK / Xiaomi, arXiv 2603.03283, March 2026): one encoder trained across indoor scans, outdoor LiDAR, remote sensing, object CAD and video-lifted point clouds (about 250k point clouds plus about 1M Cap3D object assets); RoPE-enhanced PTv3, 137M parameters (38M ablation model). ScanNet 81.1 fine-tuned / 77.7 linear; ScanNet200 39.6 / 36.4; S3DIS Area 5 78.1 / 74.7; ModelNet40 92.4 / 88.2; ScanObjectNN 95.0 / 86.9 (mAcc); ShapeNetPart 86.3 / 82.5 instance mIoU; PartNetE 62.7 / 39.8 — [Utonia paper](https://arxiv.org/html/2603.03283)
- Utonia treats colour and normals as optional (set to zeros when missing); ScanNet fine-tuning without colour gives 78.5 mIoU against 77.5 for Concerto. It has no text alignment. The authors note sparse convolution can be memory-heavy — [Utonia paper](https://arxiv.org/html/2603.03283); [HF Pointcept/Utonia](https://huggingface.co/Pointcept/Utonia)
- Utonia weights are tagged cc-by-nc-4.0 on Hugging Face (`utonia.pth` for inference) — [HF Pointcept/Utonia](https://huggingface.co/Pointcept/Utonia)
- LitePT (CVPR 2026): convolution in early stages, attention in late stages; 3.6x fewer parameters, 2x faster and 2x less memory than PTv3; S/B/L at 12.7M / 45.1M / 85.9M; code MIT — [LitePT GitHub](https://github.com/prs-eth/LitePT); [LitePT paper](https://arxiv.org/pdf/2512.13689)
- Downstream reuse: P3-SAM (Tencent, Sept 2025) uses pretrained Sonata as its feature extractor; Find3D and SAMPart3D use PTv3 backbones — [P3-SAM paper](https://arxiv.org/html/2509.06784v2); [Find3D paper](https://arxiv.org/html/2411.13550); [SAMPart3D GitHub](https://github.com/Pointcept/SAMPart3D)

### Inferences
- None of Sonata, Concerto or Utonia can be shipped in a commercial product as weights under their stated license (CC-BY-NC 4.0); the restriction comes from the training datasets, so it would also apply to derivatives fine-tuned from them.
- They are scene-scale encoders trained mostly on indoor scans; Utonia is the first to include object CAD data and to publish object-classification numbers, but only with a trained head (linear probe 88.2 on MN40), not zero-shot naming.
- Their value for the game use case is indirect: frozen features plus a linear layer trained on a handful of labelled game objects. Concerto's language probe shows the features can be mapped into CLIP space, but the published result is indoor-scan-specific.
- FP32 sizes (computed): Concerto-S about 156 MB, Concerto-B / Sonata about 430-500 MB, Utonia about 548 MB, LitePT-S about 51 MB.

### Gaps
- Checkpoint file sizes, inference latency and memory for Sonata, Concerto and Utonia are not published in the pages read.
- License of the Utonia code repository and of LitePT weights is not stated in what I read.
- I did not find a 2026 "Point Transformer V4"; Utonia and LitePT are the closest successors found. Other 2026 3D foundation encoders may exist that these searches did not surface.

## 5. Open-vocabulary 3D scene understanding and scene graphs (OpenScene, OpenMask3D, Open3DIS, SAI3D, Mask3D, ConceptGraphs, HOV-SG, Clio, OpenGraph, Hydra, newer and feed-forward work); which can label a scene from geometry alone

### Takeaway
The accurate open-vocabulary scene methods all need posed RGB(-D) frames in addition to geometry and take from about 20 seconds to several minutes per scene on a GPU (best published ScanNet200: OpenTrack3D 26.0 mAP, Open-YOLO 3D 24.7 mAP at 21.8 s); methods that work from a point cloud alone exist (OpenScene 3D-distill, RegionPLC, Mosaic3D, SpaCeFormer, OpenIns3D) but are far weaker on fine vocabularies (ScanNet200 3.9-11.8 mAP, 15.7% f-mIoU) and are trained on indoor scan datasets with restrictive terms. Scene-graph systems (ConceptGraphs, HOV-SG, Clio, Hydra) are robotics pipelines over RGB-D streams built on SAM, CLIP and, for ConceptGraphs, LLaVA and GPT-4.

### Cited Findings

ScanNet200 validation, open-vocabulary 3D instance segmentation (as tabulated by Open-YOLO 3D, ICLR 2025; all experiments on one A100-40GB)

| Method | Proposals | mAP | mAP50 | mAP25 | Head / Common / Tail | s per scene |
|---|---|---|---|---|---|---|
| Mask3D (closed vocabulary, supervised) | 3D network | 26.9 | 36.2 | 41.4 | 39.8 / 21.7 / 17.9 | 13.41 |
| SAM3D | 2D masks | 6.1 | 14.2 | 21.3 | 7.0 / 6.2 / 4.6 | 482.60 |
| OVIR-3D | 2D masks | 13.0 | 24.9 | 32.3 | 14.4 / 12.7 / 11.7 | 466.80 |
| OpenScene (2D fusion) | – | 11.7 | 15.2 | 17.8 | 13.4 / 11.6 / 9.9 | 46.45 |
| OpenScene (3D distill) | – | 4.8 | 6.2 | 7.2 | 10.6 / 2.6 / 0.7 | 0.26 |
| OpenMask3D | Mask3D | 15.4 | 19.9 | 23.1 | 17.1 / 14.1 / 14.9 | 553.87 |
| Open3DIS (3D only) | 3D network | 18.6 | 23.1 | 27.3 | 24.7 / 16.9 / 13.3 | 57.68 |
| Open3DIS (2D + 3D) | 3D + 2D masks | 23.7 | 29.4 | 32.8 | 27.8 / 21.2 / 21.8 | 360.12 |
| Open-YOLO 3D | Mask3D | 24.7 | 31.7 | 36.2 | 27.8 / 24.3 / 21.6 | 21.8 |

Source for the whole table: [Open-YOLO 3D paper, Table 1](https://arxiv.org/html/2406.02548v3)

- Replica (same paper): Open-YOLO 3D 23.7 mAP at 16.6 s; Open3DIS (2D+3D) 18.5 at 187.97 s; OpenMask3D 13.1 at 547.32 s; OpenScene 3D distill 8.2 at 4.29 s; OVIR-3D 11.1 at 52.74 s — [Open-YOLO 3D paper, Table 2](https://arxiv.org/html/2406.02548v3)
- Open-YOLO 3D inputs: posed RGB-D frames plus the reconstructed point cloud; "we assume that the poses and camera parameters are available"; depth is used for the occlusion check; every 10th ScanNet frame is processed. It replaces SAM and CLIP with a 2D open-vocabulary detector — [Open-YOLO 3D paper](https://arxiv.org/html/2406.02548v3)
- Mask3D official numbers: ScanNet val 55.2 AP / 73.7 AP50 / 83.5 AP25; ScanNet200 val 27.4 / 37.0 / 42.3; built on MinkowskiEngine; code MIT; no license stated for checkpoints — [Mask3D GitHub](https://github.com/JonasSchult/Mask3D)
- ScanNet: "The data is released under the ScanNet Terms of Use, and the code is released under the MIT license"; download requires signing the terms with an institutional email — [ScanNet GitHub](https://github.com/ScanNet/ScanNet)
- OpenMask3D: needs a `.ply` point cloud (z-up), `color`/`depth`/`pose` folders of posed RGB-D frames and a 4x4 intrinsics file; uses a mask module trained on ScanNet200, SAM ViT-H and CLIP image embeddings; MIT license; no license note for checkpoints — [OpenMask3D GitHub](https://github.com/OpenMask3D/openmask3d)
- OpenScene: three modes (2D `fusion` from posed RGB-D with OpenSeg or LSeg, 3D `distill` on point clouds only, `ensemble`); 3D weights provided for ScanNet and Matterport3D; code Apache-2.0; no weights license stated — [OpenScene GitHub](https://github.com/pengsongyou/openscene)
- Open3DIS: 3D segmenter ISBNet plus 2D segmenters (RAM++, Grounding DINO, SAM, YOLO-World); BSD-3-Clause, "Copyright (c) 2024 VinAI" — [Open3DIS GitHub](https://github.com/VinAIResearch/Open3DIS)
- OpenIns3D (ECCV 2024): "2D-input-free 3D open-world scene understanding"; takes a coloured point cloud, proposes masks with a Mask3D-derived model, renders synthetic views ("snap") and labels them with 2D open-vocabulary models (ODISE, YOLO-World, CLIP). AP (paper to updated code): Replica 13.6 to 15.4, ScanNet 19.9 to 23.3, S3DIS 21.1 to 22.9, STPLS3D 11.4 to 15.3; with real RGB-D on Replica 21.1 against Open3DIS 18.5 and OpenMask3D 13.1. MIT license — [OpenIns3D GitHub](https://github.com/Pointcept/OpenIns3D)

3D-only inference (no images at test time)
- Mosaic3D (NVIDIA / POSTECH, CVPR 2025): SparseUNet34C encoder, 43.7M trainable parameters, aligned to Recap-CLIP text; trained on Mosaic3D-5.6M (ScanNet, ARKitScenes, ScanNet++, Matterport3D, Structured3D: 29,197 scenes, 5.6M captions). Annotation-free open-vocabulary semantic segmentation f-mIoU / f-mAcc: ScanNet20 68.1 / 84.4; ScanNet200 15.7 / 28.3; Matterport3D-160 13.1 / 27.7; ScanNet++-100 18.0 / 29.0. Baselines: OpenScene-3D 57.5 ScanNet20 and 6.4 ScanNet200; RegionPLC 59.6 and 9.1; OV3D 64.0 and 8.7 — [Mosaic3D paper](https://arxiv.org/html/2502.02548v2)
- Mosaic3D instance segmentation on ScanNet200 with 3D-only input: 11.8 mAP at 1.0 s per scene using Mask3D proposals; 3.9 mAP at 1.2 s with its own decoder (no external proposals); 2.7 mAP with Segment3D proposals. Same table: OpenIns3D 8.8 mAP at 285.2 s, RegionPLC 6.3 at 1.0 s, OpenScene-3D 4.8 at 1.1 s; with 2D input, Open3DIS 23.7 at 33.5 s and OpenMask3D 15.4 at 47.3 s — [Mosaic3D paper](https://arxiv.org/html/2502.02548v2)
- Mosaic3D release: code Apache-2.0 in `NVlabs/Mosaic3D`; checkpoints on Hugging Face (`junhalee/Mosaic3D`, 2.74 GB each, ScanNet200 f-mIoU 13.0-15.7%); backbones SparseUNet-14A/18A/34C/50/101; no license stated for checkpoints or dataset; documented inference is the dataset evaluation script only — [Mosaic3D GitHub](https://github.com/NVlabs/Mosaic3D)
- SpaCeFormer (NVIDIA / POSTECH, arXiv 2604.20395, April 2026): proposal-free, 3D-only open-vocabulary instance segmentation in 0.14 s per scene on one H100 (plus about 0.02 s for one-time CLIP text encoding). Zero-shot mAP: Replica 24.1, ScanNet++ (100 classes) 22.9, ScanNet200 11.1. Trained on SpaCeFormer-3M (604,127 instances, 7,361 scenes, about 3.0M captions from ScanNet, ScanNet++, ARKitScenes, Matterport3D) on 32 H100s for about 1.5 days. The paper states it is 2.8x the next best in the proposal-free, 3D-only, no-GT-3D-annotation regime (Mosaic3D + decoder 3.9), and that methods scoring higher on ScanNet200 rely on GT-trained proposals or 2D inputs — [SpaCeFormer paper](https://arxiv.org/html/2604.20395v1)
- Concerto with a language probe: zero-shot ScanNet semantic segmentation 44.56 mIoU from point input — [Concerto paper](https://arxiv.org/html/2510.23607)

2025-2026 RGB-D methods
- OpenTrack3D (arXiv 2512.03532, v3 May 2026): builds proposals online from an RGB-D stream, "entirely mesh-free" core with optional superpoint refinement when a mesh exists, uses a 2D open-vocabulary segmenter, DINO features and a multimodal LLM as classifier instead of CLIP — [OpenTrack3D abstract](https://arxiv.org/abs/2512.03532)
- OpenTrack3D numbers as tabulated by SpaCeFormer: ScanNet200 26.0 mAP at about 356 s (YOLO-World + SAM2 proposals); ScanNet++ 20.6 mAP at about 320 s; Replica 23.9 at about 62 s. Same tables: Any3DIS 12.9 mAP on ScanNet++ at about 36 s; MaskClustering 7.8 at 600 s; BoxOVIS 24.0 on Replica at 43.7 s; SOLE 24.7 on Replica with ScanNet200 ground-truth mask supervision — [SpaCeFormer paper](https://arxiv.org/html/2604.20395v1)
- Timing conflict: OpenMask3D is 553.87 s per ScanNet200 scene in the Open-YOLO 3D and SpaCeFormer tables but 47.3 s in the Mosaic3D table; Open3DIS is 360.12 s in the former and 33.5 s in the latter — [Open-YOLO 3D paper](https://arxiv.org/html/2406.02548v3); contradicted by [Mosaic3D paper](https://arxiv.org/html/2502.02548v2)

Scene graphs
- ConceptGraphs (ICRA 2024): "takes posed RGB-D images as input"; uses SAM (ViT-H; FastSAM/MobileSAM optional), CLIP via open_clip, optionally GroundingDINO + RAM, LLaVA-7B for captions and GPT-4 through the OpenAI API for caption refinement and edges ("GPT-3.5 often produces inconsistent results"); MIT license — [ConceptGraphs GitHub](https://github.com/concept-graphs/concept-graphs)
- HOV-SG (RSS 2024): posed RGB-D sequences; OpenCLIP ViT-H-14 (laion2B) and SAM ViT-H; builds floor / room / object hierarchy; recommends 128 GB RAM for preparing its HM3D dataset; claims about 75% smaller representation than dense open-vocabulary maps. License: "For academic usage, the code is released under the MIT license. For any commercial purpose, please contact the authors" — [HOV-SG GitHub](https://github.com/hovsg/HOV-SG)
- HOV-SG reports 0.231 mIoU / 0.386 F-mIoU on Replica (ViT-H-14) against ConceptGraphs 0.18 / 0.23 — [HOV-SG paper, RSS 2024](https://www.roboticsproceedings.org/rss20/p077.pdf)
- Clio (MIT SPARK): real-time task-driven scene graphs with open-set semantics, clustering objects and regions relevant to a list of natural-language tasks; ROS pipeline over RGB + depth + poses, CLIP ViT-L/14 (OpenCLIP ViT-H-14 alternative), integrated with Hydra and Khronos; BSD-2-Clause. The README notes the released version's real-time performance is below the paper's — [Clio GitHub](https://github.com/MIT-SPARK/Clio)
- Hydra (MIT SPARK): incremental real-time 3D scene graph construction, ROS 2 Jazzy on Ubuntu 24.04, open-set semantic capabilities added in the January 2025 release; BSD-2-Clause — [Hydra GitHub](https://github.com/MIT-SPARK/Hydra)
- OVIP-SG (arXiv 2608.17633, August 2026) on six Replica scenes with 52 classes, mAcc / F-mIoU: ConceptFusion 35.63 / 47.95, HOV-SG 40.98 / 58.73, ConceptGraphs 45.00 / 56.30, OVIP-SG 51.31 / 61.45; class-agnostic instance PQ 0.398 against 0.338 (ConceptGraphs) and 0.163 (HOV-SG) — [OVIP-SG paper](https://arxiv.org/html/2608.17633)
- Other 2025-2026 scene-graph papers surfaced by title only: KeySG (hierarchical keyframe-based, Oct 2025) and FOUND-IT (task-driven, May 2026) — [KeySG, arXiv 2510.01049](https://arxiv.org/pdf/2510.01049); [FOUND-IT, arXiv 2605.25371](https://arxiv.org/pdf/2605.25371)

Feed-forward reconstruction-based methods (images in, labelled 3D out)
- EPS3D (arXiv 2606.08980, June 2026): end-to-end feed-forward open-vocabulary 3D panoptic segmentation from unposed multi-view images, about 1 s per scene, +13% semantic mIoU on Replica under the LSM protocol — [EPS3D paper](https://arxiv.org/html/2606.08980)
- IGGT (Oct 2025): instance-grounded geometry transformer, reports +8.34% mIoU on ScanNet++ — [IGGT, arXiv 2510.22706](https://arxiv.org/pdf/2510.22706)
- Uni3R (Aug 2025): VGGT-style cross-view transformer predicting Gaussians with semantic feature fields from unposed views — [Uni3R, arXiv 2508.03643](https://arxiv.org/pdf/2508.03643)
- Unified Semantic Transformer (Dec 2025) evaluates on ScanNet, ScanNet200 and ScanNet++ and reports large margins over PanSt3R on ScanNet20/ScanNet200 and over IGGT on ScanNet — [UST, arXiv 2512.14364](https://arxiv.org/pdf/2512.14364)
- SegSplat (Nov 2025) acknowledges a gap to per-scene-optimised methods; RelationVGGT (listed for NeurIPS 2026) segments 3D spatial relations feed-forward — [SegSplat, arXiv 2511.18386](https://arxiv.org/pdf/2511.18386); [RelationVGGT, arXiv 2610.00970](https://arxiv.org/html/2610.00970)

### Inferences
- "Needs posed RGB-D frames" is not a real constraint for a game team: the engine can render colour and depth from arbitrary known poses of the finished level, so the 2D-lifting pipelines (OpenMask3D, Open3DIS, Open-YOLO 3D, ConceptGraphs, HOV-SG) are applicable offline. The real issues are domain gap (all proposal networks are trained on ScanNet-style indoor scans) and runtime weight (SAM ViT-H, CLIP ViT-H/L, sometimes a VLM), which rules them out for CPU runtime but not for an offline bake.
- A game level already contains the instance segmentation that these pipelines work hardest to recover: every placed actor or static mesh is a known instance with a transform and bounds. The class-agnostic proposal stage (Mask3D, ISBNet, SAM lifting) is therefore redundant; the problem reduces to classifying known instances (questions 1-3) plus computing relations from transforms. The remaining use for scene-level methods is merged or monolithic geometry (BSP, landscape, baked level chunks) where instances are not separate.
- Methods that can label a scene from geometry alone, with what I could confirm: OpenScene 3D-distill, RegionPLC, Mosaic3D, SpaCeFormer, Concerto with a language probe, and OpenIns3D (which synthesises its own views from the coloured point cloud). All were evaluated with coloured indoor scans; none reports results on colourless geometry or synthetic game levels.
- Fine-vocabulary quality from geometry alone is low: ScanNet200 f-mIoU 15.7% (Mosaic3D) and 11.1-11.8 mAP for instance segmentation, against 68.1% f-mIoU on the 20 coarse ScanNet classes. Coarse categories (wall, floor, chair, table, door) are where these models are usable.
- Weights for the whole group are trained on ScanNet / ScanNet200 / ScanNet++ / ARKitScenes / Matterport3D; the Sonata authors explicitly name ARKitScenes and HM3D as non-commercial sources, and ScanNet has its own terms of use. Permissive code licenses (MIT, Apache-2.0, BSD) do not settle whether the checkpoints can be used commercially.
- Feed-forward image-to-labelled-3D models solve a problem this team does not have (they reconstruct geometry from images); their relevance is that the 2D feature backbones they use (DINO, CLIP, SAM-style) are the same ones a render-and-classify bake would use.

### Gaps
- OpenGraph and SAI3D were not found in the sources read; no numbers or licenses for them are reported here.
- Open-YOLO 3D, OpenTrack3D, SpaCeFormer, EPS3D, IGGT, PanSt3R, LSM and Uni3R code and weight licenses were not checked; SpaCeFormer parameter count and release status were not visible in the part of the paper read.
- The ScanNet Terms of Use text (non-commercial clause) could not be opened; ARKitScenes, Matterport3D, ScanNet++ and HM3D terms were not checked directly.
- Conflicting per-scene timings for OpenMask3D and Open3DIS between papers are unresolved (different frame subsampling or hardware is likely but not stated).
- No evaluation of any of these methods on synthetic game levels, on colourless geometry, or on CPU was found.

## 6. 3D part segmentation and structural understanding (PartNet, PartSLIP, PartField, SAMPart3D, Find3D, P3-SAM and newer)

### Takeaway
By 2025-2026 class-agnostic part decomposition of an arbitrary mesh is fast and good (P3-SAM 81.1 and PartField 79.2 mIoU on PartObjaverse-Tiny with mesh connectivity, about 8-10 s per shape), but these models output unnamed parts; the only feed-forward model that names parts from free text, Find3D (46.2M parameters, about 0.9 s per object on an A100), scores far lower (21.3-28.4 mIoU). The strongest models carry restrictive licenses: PartField is under the non-commercial NVIDIA License and P3-SAM under the Tencent Hunyuan 3D-Part Community License, which excludes the EU, UK and South Korea.

### Cited Findings

Class-agnostic part segmentation, mIoU (as tabulated by PartField, April 2025)

| Method | PartObjaverse-Tiny | PartNetE | Time per shape |
|---|---|---|---|
| PartSLIP (text-based) | 31.54 | 34.94 | about 4 min |
| Find3D (text-based) | 21.28 | 21.69 | about 10 s |
| Ultrametric | 46.39 | – | about 1.5 h |
| SAMesh | 56.86 | 26.66 | about 7 min |
| SAMPart3D | 53.47 | 56.17 | about 15 min |
| PartField | 79.18 | 59.10 | about 10 s (forward pass under 1 s, rest is clustering) |

Source: [PartField paper, Tables 1-2](https://arxiv.org/html/2504.11451)

- PartField (NVIDIA, ICCV 2025): feed-forward feature field (PVCNN encoder, triplane 512² x 128 channels, 6-layer transformer, 448-d features); input `.obj` / `.glb` meshes, `.ply` Gaussian splats or point clouds; mesh output is a hierarchical part tree from agglomerative clustering, point clouds use K-Means. Trained on about 340k Objaverse shapes (SAM2 masks on 6 RGB + 6 normal renders) plus about 30k PartNet shapes, 8 A100s for 2 weeks — [PartField paper](https://arxiv.org/html/2504.11451); [PartField GitHub](https://github.com/nv-tlabs/PartField)
- PartField public checkpoint is trained on Objaverse only: "Due to licensing restrictions, we are unable to release the model that was also trained on PartNet" — [PartField GitHub](https://github.com/nv-tlabs/PartField)
- PartField license is the "NVIDIA License": "The Work and any derivative works thereof only may be used or intended for use non-commercially" (NVIDIA and affiliates exempt) — [PartField LICENSE](https://raw.githubusercontent.com/nv-tlabs/PartField/main/LICENSE)
- PartField limitations: it "does not predict part semantics"; granularity is not selected automatically (evaluation picks the best of 20 scales); features are only weakly position-invariant, so cross-shape use needs consistently oriented shapes; agglomerative clustering wants one connected component, and the default bridging "can lead to poor results when the mesh is poorly connected and fragmented". It was tested on AI-generated assets, Gaussian-splat scans and ABC CAD mechanical parts — [PartField paper](https://arxiv.org/html/2504.11451); [PartField GitHub](https://github.com/nv-tlabs/PartField)
- P3-SAM (Tencent Hunyuan, Sept 2025): Sonata (PTv3) feature extractor, about 112M parameters; input 100,000 points with normals sampled from the mesh plus point prompts; trained on about 3.7M objects (Objaverse, Objaverse-XL, ShapeNet, PartNet, others) with part labels derived from artist-made connected components; about 8 s for full automatic segmentation, about 3 ms per interactive prompt; output is "instance-specific but class-agnostic" — [P3-SAM paper](https://arxiv.org/html/2509.06784v2)
- P3-SAM results: PartObjaverse-Tiny full segmentation without connectivity 59.88 (PartField 53.93, SAMPart3D 53.47, Find3D 21.28); with connectivity 81.14 (PartField 79.18, SAMesh 56.86); watertight variant 58.10 (PartField 51.54, SAMPart3D 48.79); PartNetE point clouds 65.39 (PartField 59.1, SAMPart3D 56.17, SAMesh 26.66); interactive 51.23 against Point-SAM 27.91. SAMesh could not process the watertight meshes because of their face count. Stated limitation: relies on surface geometry, no understanding of part volume — [P3-SAM paper](https://arxiv.org/html/2509.06784v2)
- P3-SAM and X-Part are released as Hunyuan3D-Part; P3-SAM "can handle any input mesh" and outputs features, part masks and part bounding boxes; X-Part generates completed parts (released as a "light version") — [Hunyuan3D-Part GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-Part)
- Hunyuan3D-Part license: "Tencent Hunyuan 3D-Part Community License Agreement"; territory is defined "excluding the territory of the European Union, United Kingdom and South Korea" and use outside it is "unlicensed and unauthorized"; products with more than 1 million monthly active users must request a separate license; an acceptable-use exhibit bans, among others, military use — [Hunyuan3D-Part LICENSE](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-Part/main/LICENSE)
- Find3D (Caltech, Nov 2024; ICCV 2025): open-world part segmentation by free-text query on a point cloud; PTv3-based, 46.2M parameters, 768-d per-point features compared by cosine similarity with SigLIP-style text embeddings; input per point xyz + normal + RGB. Trained on about 30K Objaverse objects from 761 categories, 2.1M parts, 124,615 unique part types, auto-labelled (about 76% of annotations judged high quality on a 50-object check) — [Find3D paper](https://arxiv.org/html/2411.13550)
- Find3D speed and accuracy: about 0.9 s per object on an A100; PointCLIPV2 about 5.4 s, PartSLIP++ about 174 s, OpenMask3D about 297 s. ShapeNet-Part 28.39 mIoU zero-shot against PointCLIPV2 16.91; PartNet-E 16.86 with "{part} of a {object}" prompts against PartSLIP++ 5.12 (PartSLIP++ reaches 32.71 with bare "{part}" prompts, an 84% swing); under random rotation PointCLIPV2 drops about 46% while Find3D is stable — [Find3D paper](https://arxiv.org/html/2411.13550)
- Find3D limitations: points are sampled at 0.02 resolution, so small or geometrically flat parts such as buttons are hard; rotation equivariance makes symmetric parts receive the same label — [Find3D paper](https://arxiv.org/html/2411.13550)
- Find3D code is MIT; checkpoint `ziqima/find3d-checkpt0` on Hugging Face has no stated weights license; requires a CUDA GPU, Pointcept and FlashAttention — [Find3D GitHub](https://github.com/ziqi-ma/Find3D)
- SAMPart3D (Nov 2024): takes a `.glb` mesh, renders 16 views with Blender, and trains an MLP per object on top of a PTv3-object backbone (per-object optimisation; about 15 min per shape per PartField's table); code MIT, no weights license stated — [SAMPart3D GitHub](https://github.com/Pointcept/SAMPart3D); [PartField paper](https://arxiv.org/html/2504.11451)
- PartSAM (Sept 2025): promptable part segmentation trained on native 3D data; PartObjaverse-Tiny IoU 56.1 with one prompt point and 87.6 with ten — [PartSAM, arXiv 2509.21965](https://arxiv.org/pdf/2509.21965)
- GeoSAM2 (Aug 2025): SAM2-based, 84.06 class-agnostic mIoU on PartObjaverse-Tiny against 62.59 for vanilla SAM2; PartObjaverse-Tiny has 200 meshes with human part labels — [GeoSAM2, arXiv 2508.14036](https://arxiv.org/pdf/2508.14036)
- 2026 titles surfaced but not read: SAM3D-Part (interactive part selection and generation, Sept 2026), UniPart (zero-shot language-grounded part segmentation for embodied interaction, Sept 2026), Hi-TOPS (hierarchical topology-aware scoring prior, Aug 2026), S2AM3D (scale-controllable part segmentation, Dec 2025) — [SAM3D-Part](https://arxiv.org/pdf/2609.15639); [UniPart](https://arxiv.org/pdf/2609.12898); [Hi-TOPS](https://arxiv.org/pdf/2608.00767); [S2AM3D](https://arxiv.org/html/2512.00995)
- Self-supervised backbones on part benchmarks: Utonia reaches 86.3 instance mIoU on ShapeNetPart and 62.7 mIoU on PartNetE after fine-tuning (82.5 / 39.8 with a linear probe) — [Utonia paper](https://arxiv.org/html/2603.03283)

### Inferences
- "The door of a car" or "the seat of a chair" needs two things the current models provide separately: a good decomposition (PartField, P3-SAM: class-agnostic, 80% mIoU with connectivity) and a name for each piece (Find3D: text-queryable but about 20-28% mIoU). A two-stage bake (decompose, then name each part by text similarity or by rendering it) is the obvious combination; I found no published system evaluated in exactly that configuration.
- Game assets often already encode the decomposition for free: separate mesh sections, material slots, sockets, skeletal bones or sub-actors. P3-SAM's own training labels are derived from artist-made connected components, which is the same signal. Where that structure exists, only the naming step is needed.
- Licensing blocks the two best decomposers for a commercial product as shipped weights: PartField is non-commercial outright; Hunyuan3D-Part cannot be used from the EU, UK or South Korea at all. Find3D (MIT code, unstated weights license, Objaverse-derived training data) and SAMPart3D (MIT code) are the least encumbered but weakest or slowest.
- All of these need a GPU and PTv3 / sparse-convolution stacks; none is a CPU runtime candidate. They are offline bake tools only.

### Gaps
- PartNet, PartSLIP, Point-SAM, SAMesh, PartSAM and GeoSAM2 code / weight licenses were not checked. PartNet's dataset license is only indirectly evidenced by NVIDIA's statement that it could not release the PartNet-trained PartField model.
- Checkpoint sizes for PartField, P3-SAM, Find3D and SAMPart3D are not published in the pages read; inference hardware for the PartField and P3-SAM timings is not stated.
- No benchmark measures named-part accuracy on game assets (vehicle doors, weapon parts, interactable handles). The 2026 papers listed by title were not read, so I cannot say whether they close the naming gap.
- SceneFun3D / functional-element scene graphs (handles, buttons, switches) were not researched beyond OpenTrack3D's mention of SceneFun3D as a benchmark.

## 7. Applications to game assets or CAD assets (low-poly, non-watertight, untextured meshes) and reported failure modes

### Takeaway
I found no published study that applies these classifiers to a game studio's asset library or to engine levels; the evidence is indirect. It points consistently one way: models trained on Objaverse (user-uploaded, Sketchfab-style assets, which include game-like content) tolerate arbitrary meshes when fed as surface-sampled points, lose only a few points without colour, and fail on fine geometry-versus-texture distinctions, small parts, symmetric parts, fragmented meshes and anything outside the web-asset distribution.

### Cited Findings
- No studio or engine case study: a targeted search for automatic semantic labelling of game assets and engine asset libraries returned only patents on tagging whole games and unrelated mesh-classification papers — [search result example: task-driven mesh network, arXiv 2306.05246](https://arxiv.org/html/2306.05246)
- Training distribution: Objaverse shapes "were uploaded by web users", are not expert-verified, have uneven quality and highly unbalanced categories, and their raw names are often noisy (about 30% filtered) — [OpenShape paper](https://arxiv.org/html/2305.10764)
- Untextured input, point route: OpenShape with xyz only reaches 39.6% on O-LVIS and 83.6% on MN40 against 42.0% / 83.1% with colour; MN40 and ScanObjectNN are evaluated without colour in both OpenShape and Uni3D (Uni3D-g 88.2% MN40 without colour) — [OpenShape paper](https://arxiv.org/html/2305.10764); [Uni3D paper](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Untextured input, image route: 2D foundation models are trained on texture-rich images and show a domain gap on untextured mesh renders; shape-only cues are sensitive to lighting and viewpoint; the MeshSegmenter authors add a texture-synthesis step to compensate — [MeshSegmenter, arXiv 2407.13675](https://arxiv.org/html/2407.13675v2)
- Diff3F is a class-agnostic feature descriptor designed specifically for untextured meshes or point clouds, distilled from diffusion features — [Diff3F, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Dutt_Diffusion_3D_Features_Diff3F_Decorating_Untextured_Shapes_with_Distilled_Semantic_CVPR_2024_paper.pdf)
- Missing colour/normal handling in newer encoders: Utonia accepts zeros for colour and normals and still fine-tunes to 78.5 mIoU on ScanNet without colour; the PartField authors fed Find3D a dummy white colour for untextured shapes — [Utonia paper](https://arxiv.org/html/2603.03283); [PartField paper](https://arxiv.org/html/2504.11451)
- Orientation matters: OpenShape checkpoints are tied to an up axis (z for the main ones, y for demo ones) and the README says to align the gravity axis; PartField's cross-shape features need consistently oriented shapes; PointCLIPV2 loses about 46% under random rotation — [OpenShape GitHub](https://github.com/Colin97/OpenShape_code); [PartField paper](https://arxiv.org/html/2504.11451); [Find3D paper](https://arxiv.org/html/2411.13550)
- Non-watertight and multi-component meshes: most ModelNet40 shapes are not watertight or 2-manifold and break remeshing-based mesh networks; MeshMAE reconstructs manifold meshes and reduces them to 500 faces before use — [SubdivNet, arXiv 2106.02285](https://arxiv.org/pdf/2106.02285); [MeshMAE paper](https://ar5iv.labs.arxiv.org/html/2207.10228)
- Low-poly and poor topology: SAMesh needed modified hyperparameters on PartNetE "because of low-poly, poor-topology meshes" and could not process high-face-count watertight meshes at all; PartField's clustering degrades on fragmented, poorly connected meshes and "certain cases still do not produce satisfactory segmentations" — [PartField paper](https://arxiv.org/html/2504.11451); [P3-SAM paper](https://arxiv.org/html/2509.06784v2); [PartField GitHub](https://github.com/nv-tlabs/PartField)
- Artist-made assets as training signal: P3-SAM derives part labels for about 3.7M objects from the connected components of artist-made meshes, with watertight versions for about 2.3M of them — [P3-SAM paper](https://arxiv.org/html/2509.06784v2)
- CAD: PartField reports good generalisation to ABC CAD mechanical parts and to AI-generated assets (Trellis, Edify3D); Utonia includes object CAD data in pretraining — [PartField paper](https://arxiv.org/html/2504.11451); [Utonia paper](https://arxiv.org/html/2603.03283)
- Game-asset pipelines on the generation side: Tencent's "Hunyuan3D Studio: End-to-End AI Pipeline for Game-Ready 3D Asset Generation" (Sept 2025) is the pipeline P3-SAM / X-Part belong to — [Hunyuan3D Studio, arXiv 2509.12815](https://arxiv.org/pdf/2509.12815); [Hunyuan3D-Part GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-Part)
- Category-level weakness: Uni3D's zero-shot results on ScanNet objects drop to 3.7 for cabinet, 1.9 for counter and 10.7 for shower curtain — [Uni3D paper, Table 2](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Geometry vs appearance confusions in multi-view models: a soccer-ball query retrieving red-and-black ladybugs; "round back" queries favouring point models — [Duoduo CLIP paper](https://arxiv.org/html/2406.11579v1)
- Sim-to-real is the commonly reported gap, in the opposite direction from the game case: OpenShape lists it as a limitation; Duoduo CLIP without real-image training underperforms plain CLIP on real multi-view data; OpenShape scores 3.55% on noisy reconstructed MVPNet clouds — [OpenShape paper](https://arxiv.org/html/2305.10764); [Duoduo CLIP paper](https://arxiv.org/html/2406.11579v1)
- Small and symmetric parts: Find3D misses small, non-prominent parts at its 0.02 sampling resolution and gives symmetric parts the same label — [Find3D paper](https://arxiv.org/html/2411.13550)
- No part-level information in global shape embeddings is an explicit OpenShape limitation — [OpenShape paper](https://arxiv.org/html/2305.10764)

### Inferences
- The game case is the favourable direction of the domain gap: clean synthetic meshes are what Objaverse-trained encoders saw in training, whereas most reported failures concern real scans. The benchmarks say nothing direct about stylised, low-poly or modular kit-bashed assets, which should be tested on the team's own data before any choice is made.
- Expected trouble spots for level objects, from the failure modes above: (1) functionally defined categories with generic shape ("cabinet", "counter", "cover", "pole" vs "pipe" vs "column") where geometry underdetermines the label; (2) modular pieces that are fragments of an object (a wall segment with a door hole, half a staircase); (3) scale-dependent categories, since all encoders normalise the object to a unit box and discard absolute size, which the engine knows and should add as a separate feature; (4) orientation, which must be canonicalised to the checkpoint's up axis (cheap, since the engine knows world up); (5) open or one-sided geometry seen from behind in rendered views.
- Surface point sampling is insensitive to triangle count, non-manifold edges and missing watertightness, so the point route sidesteps the mesh-quality problems that break mesh-native networks; what it loses on low-poly assets is fine detail, because large flat triangles carry little signal beyond silhouette.
- Because labels are produced offline and the asset list is finite, zero-shot output can be treated as a proposal reviewed per unique mesh (not per placed instance); top-3 / top-5 accuracy (75-83% on O-LVIS, 98-99% on MN40 for the best models) is then the relevant figure for how often the right label is on the shortlist.

### Gaps
- No quantitative evaluation of any model in these notes on game assets, low-poly meshes, modular level kits or stylised art was found; this is the largest gap relative to the reader's question.
- No report of Unreal Engine or Unity integration of a 3D classifier, and no report of ONNX Runtime CPU deployment of a zero-shot 3D encoder, was found.
- Roblox's and other vendors' 3D foundation models and commercial asset-tagging services were not researched.
- The effect of polygon count or sampling density on zero-shot accuracy is not quantified in the sources read.
