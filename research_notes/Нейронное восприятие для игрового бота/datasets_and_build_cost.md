# Datasets and build cost for an in-house neural perception model of structural and object primitives (state: October 2026)

Reading notes for the report writer:

- Scope: three build routes. (A) closed-set classifier over object geometry (point cloud / voxels). (B) classification of rendered views with a pretrained image-text model, optionally distilled. (C) classifier of local terrain structure from a height field / occupancy patch.
- Every item under "Cited Findings" was retrieved in this session (10 Oct 2026) from the linked page. Page contents were read through a summarising fetch tool, so table values should be spot-checked against the original before they go into a budget.
- Everything under "Inferences" is my own reasoning. Numbers there are marked **ESTIMATE** and are not published results.
- Recollections that I could not re-verify in this session are in "Gaps" and are marked as unverified.

## 1. 3D object datasets: size, categories, licenses

### Takeaway
Only a handful of object datasets are clean for a commercial product: the CC-BY / CC0 part of Objaverse (about 725K objects, but only about 47K carry verified category labels), OmniObject3D, Google Scanned Objects and uCO3D (all CC BY 4.0), plus ABO if the website license (CC BY 4.0) rather than the paper's (CC BY-NC 4.0) is the binding one. ShapeNet, PartNet-Mobility, 3D-FUTURE, ScanObjectNN and MVImgNet are research-only or under custom terms, and none of the object datasets covers structural primitives (pit, ramp, ledge, stairs, wall) in a useful way.

### Cited Findings

**Objaverse 1.0**
- 818K 3D objects designed by 160K artists (abstract says "800K+"). — [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051)
- "The use of the dataset as a whole is licensed under the ODC-By v1.0 license." Each object has its own license recorded in the metadata: CC-BY 4.0 721K objects, CC-BY-NC 4.0 25K, CC-BY-NC-SA 4.0 52K, CC-BY-SA 4.0 16K, CC0 1.0 3.5K. — [HF card allenai/objaverse](https://huggingface.co/datasets/allenai/objaverse)
- The HF card makes no statement about commercial use; it only lists the per-object licenses. — [HF card allenai/objaverse](https://huggingface.co/datasets/allenai/objaverse)
- Objects with restricted (objectionable/adult) flags were excluded; the paper says "Objects selected for Objaverse have a distributable Creative Commons license." — [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051)

**Objaverse-LVIS**
- A 47K-object subset "comprised of objects uniquely assigned to one of 1156 LVIS categories". — [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051)
- Exact benchmark size used by later work: 46,832 shapes in 1,156 LVIS categories, long-tailed. — [OpenShape](https://ar5iv.labs.arxiv.org/html/2305.10764)
- Label procedure: 500 candidates per category picked by CLIP classification plus metadata-term matching (250K candidates in total), then filtered and verified by crowdworkers. The paper reports no accuracy or error rate for these labels. — [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051)
- Because only 500 candidates were shown per class, popular categories have many more objects in Objaverse than are labelled in Objaverse-LVIS. — [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051)
- Coverage: vehicles ("animals, humans, and vehicles") are present. Doors and windows are not treated as Objaverse objects: in the paper's procedurally generated homes, "Structural objects, like doors and windows, are inherited from ProcTHOR." Stairs are not mentioned. — [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051)
- Noise in raw Objaverse metadata: OpenShape calls the data "dominated with noisy text descriptions" and used GPT-4 to filter out about 30% of the raw user-uploaded texts. — [OpenShape](https://ar5iv.labs.arxiv.org/html/2305.10764)
- Noise of model-generated labels: the Objaverse-N200 benchmark assigned Objaverse-LVIS category names to about 200K objects with Uni3D; its authors put the noise ratio at about 50%. (Taken from a search-result summary of the DAC paper; not read in full.) — [DAC, arXiv 2407.17779](https://arxiv.org/pdf/2407.17779)

**Objaverse-XL**
- "Over 10 million 3D objects" (10.2M in the datasheet). Approximate shares: GitHub about 56% (5.5M files rendered), Thingiverse about 35% (about 3.5M), Sketchfab about 8% (Objaverse 1.0, about 800K), Polycam under 1% (71K), Smithsonian under 1% (2.4K). — [Objaverse-XL paper](https://ar5iv.labs.arxiv.org/html/2307.05663)
- License: "The use of the dataset as a whole is licensed under the ODC-By v1.0 license. Individual objects in Objaverse-XL are licensed under different licenses." Code is Apache-2.0. Polycam data is available "to academic researchers for non-commercial use upon request and approval from Polycam." — [objaverse-xl GitHub](https://github.com/allenai/objaverse-xl)
- Per source: Smithsonian objects are CC0, Polycam CC-BY 4.0, Sketchfab Creative Commons, GitHub and Thingiverse mostly Creative Commons. — [Objaverse-XL paper](https://ar5iv.labs.arxiv.org/html/2307.05663)
- No category labels. Metadata is source metadata (license, file names, stars), Blender statistics (polygon counts and so on) and CLIP ViT-L/14 embeddings averaged over 12 renders. For Polycam, 38.2% of renders were judged "bad". Deduplication by content hash removed about 23M files; near-duplicates may remain. — [Objaverse-XL paper](https://ar5iv.labs.arxiv.org/html/2307.05663)

**Cap3D (captions for Objaverse)**
- 1,002,422 descriptive captions for objects in Objaverse and a subset of Objaverse-XL; ABO caption pairs are also distributed. The GitHub page states no license and no error rate. — [Cap3D GitHub](https://github.com/crockwell/Cap3D)

**ShapeNet (ShapeNetCore, ShapeNetSem, PartNet)**
- ShapeNetCore: 55 common object categories, about 51,300 unique 3D models; gated access with license acceptance. — [HF ShapeNet/ShapeNetCore](https://huggingface.co/datasets/ShapeNet/ShapeNetCore)
- Terms of use restrict the database to non-commercial research and educational purposes; if the researcher works for a for-profit company, the employer is bound by the terms too; access can be terminated at any time. (From a search-result summary of the terms page; shapenet.org/terms now redirects to Hugging Face, where the terms are in a separate TERMS.md.) — [ShapeNet Terms of Use](https://www.shapenet.org/terms); [HF ShapeNet organisation page](https://huggingface.co/ShapeNet)
- ShapeNetSem and PartNet are hosted in the same gated organisation (ShapeNetSem-archive about 12 GB, PartNet-archive). — [HF ShapeNet organisation page](https://huggingface.co/ShapeNet)

**ModelNet10 / ModelNet40**
- The project site lists 127,915 CAD models in 662 categories overall, with 10-class and 40-class subsets. The page text retrieved contains no license or copyright statement. — [ModelNet site](https://modelnet.cs.princeton.edu/)
- Models were downloaded from 3D Warehouse and through the Yobi3D search engine (261 CAD model websites), plus the Princeton Shape Benchmark; categories were checked by Mechanical Turk workers. — [3D ShapeNets paper](https://arxiv.org/pdf/1406.5670); [ModelNet download page](https://modelnet.cs.princeton.edu/download.html)

**ScanObjectNN**
- About 15,000 objects in 15 categories from 2,902 unique real scanned instances. Categories: bag, bin, box, cabinet, chair, desk, display, door, shelf, table, bed, pillow, sink, sofa, toilet. Download requires agreeing to the "ScanObjectNN Terms of Use" through a form (text not shown on the page). — [ScanObjectNN site](https://hkust-vgd.github.io/scanobjectnn/)
- Objects were cut out of SceneNN and ScanNet scans (700 unique scenes). — [ScanObjectNN paper](https://ar5iv.labs.arxiv.org/html/1908.04616)

**OmniObject3D**
- 6,000 scanned real objects in 190 daily categories; textured meshes, point clouds (1,024 / 4,096 / 16,384 points), multi-view renders, real videos. — [OmniObject3D project page](https://omniobject3d.github.io/); [OmniObject3D GitHub](https://github.com/omniobject3d/OmniObject3D)
- "The OmniObject3D dataset is released under the CC BY 4.0". — [OmniObject3D GitHub](https://github.com/omniobject3d/OmniObject3D)

**ABO (Amazon Berkeley Objects)**
- 147,702 product listings, 398,212 catalog images, 7,953 artist-made 3D models (glTF 2.0) in 63 categories; categories named in the paper: bench, chair, couch, cabinet, lamp, table. — [ABO paper](https://ar5iv.labs.arxiv.org/html/2110.06199)
- License, website: "This work is licensed under the Creative Commons Attribution 4.0 International Public License (CC BY 4.0)." — [ABO website](https://amazon-berkeley-objects.s3.amazonaws.com/index.html)
- License, AWS registry: "Creative Commons Attribution 4.0 (CC BY 4.0)". — [AWS Open Data Registry](https://registry.opendata.aws/amazon-berkeley-objects/)
- License, paper: the dataset is "released under CC BY-NC 4.0 license". — [ABO paper](https://ar5iv.labs.arxiv.org/html/2110.06199); contradicted by [ABO website](https://amazon-berkeley-objects.s3.amazonaws.com/index.html)

**3D-FUTURE**
- 9,992 furniture shapes with textures in the original report; the ABO paper's comparison table lists 3D-FUTURE at 16.6K models in 8 classes. — [3D-FUTURE report](https://arxiv.org/pdf/2009.09633); [ABO paper](https://ar5iv.labs.arxiv.org/html/2110.06199)
- License agreement (Taobao / Alibaba): revocable, non-transferable license "for scientific research purpose only"; no commercialisation of the data or derivatives, no sharing with third parties; the license ends automatically on breach. — [3D-FUTURE Data Sets Use License Agreement](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202004171628_60052.html)

**Google Scanned Objects (GSO)**
- 1,030 scanned household objects, 13 GB, CC-BY 4.0. — [Google Research blog](https://www.research.google/blog/scanned-objects-by-google-research-a-dataset-of-3d-scanned-common-household-items/); [GSO paper](https://arxiv.org/abs/2204.11918v1)

**PartNet-Mobility (SAPIEN)**
- About 2K articulated objects with motion annotations. Terms limit use to non-commercial research and educational purposes; a for-profit employer is bound too; ShapeNet terms also apply because the data builds on ShapeNet. — [HF sapien-sim/PartNetMobility](https://huggingface.co/datasets/sapien-sim/PartNetMobility)

**Toys4K**
- 4,179 object instances in 105 categories, "collected under Creative Commons and royalty-free licenses" (secondary description). — [Low-shot Object Learning paper](https://arxiv.org/pdf/2312.03533)
- Download is by request form; the repository page states no license, and notes that some objects were removed to allow release. — [Toys4K repository](https://github.com/rehg-lab/lowshot-shapebias/tree/main/toys4k)

**MVImgNet**
- 6.5 million frames from 219,188 videos across 238 classes; MVPNet subset: 87,825 point clouds in 180 categories. "The data is released under the MVImgNet Terms of Use"; code is under CC BY-NC 4.0. — [MVImgNet GitHub](https://github.com/GAP-LAB-CUHK-SZ/MVImgNet)

**uCO3D**
- About 170,000 turntable videos of real objects, about 1,000 LVIS categories in 50 super-categories; per video: masks, camera poses, three kinds of point cloud, a 3D Gaussian Splat reconstruction, captions, depth maps. "The data are released under the CC BY 4.0 license." — [uCO3D GitHub](https://github.com/facebookresearch/uco3d)

### Inferences
- Commercial-use reading of the licenses (my interpretation, not legal advice):
  - CC-BY 4.0 and CC0 (721K + 3.5K Objaverse objects, OmniObject3D, GSO, uCO3D, Polycam / Smithsonian parts of Objaverse-XL) allow commercial use; CC-BY requires attribution, which for a training set means keeping a per-object credit list.
  - CC-BY-NC and CC-BY-NC-SA Objaverse objects (25K + 52K) must be filtered out by the metadata license field before any commercial training run.
  - CC-BY-SA (16K) raises a share-alike question for derived artefacts; the cautious choice is to drop them as well.
  - ODC-By on the Objaverse collection adds an attribution duty for the database itself.
  - ShapeNet, PartNet, PartNet-Mobility, 3D-FUTURE, ScanObjectNN and MVImgNet are research-only or under custom terms. A shipped model trained on them is a legal risk even if the weights contain no meshes.
- ABO has two contradictory license statements. The data host and the AWS registry say CC BY 4.0, the paper says CC BY-NC 4.0. Treat it as usable only after reading the LICENSE file inside the actual download.
- The labelled, commercially usable pool for a closed set is much smaller than the headline sizes: about 47K labelled Objaverse objects over 1,156 long-tailed categories (minus NC-licensed ones), 6K OmniObject3D, 1K GSO. For 50 to 200 game-relevant classes, most classes would have tens to low hundreds of labelled public examples, and structural classes would have none.
- Furniture and vehicles (car, chair, table, sofa, crate-like boxes) are well covered by public data. Pit, hole, ramp, ledge, cliff, wall and doorway are not object categories in any of these datasets and have to come from scene datasets (section 2, mostly non-commercial) or from procedural generation (sections 3 and 4).

### Gaps
- ModelNet license text: not found on the pages retrieved. Unverified recollection: the site carries a notice that the CAD models were downloaded from the Internet, that the original authors hold the copyright, and that the dataset is provided for the convenience of academic research only. Whatever the wording, the underlying meshes belong to third-party creators, so commercial terms are unclear at best.
- ModelNet40 class list not retrieved. Unverified recollection: it includes "door" and "stairs" classes next to car, chair, table, sofa, desk and bench.
- ShapeNetSem size (unverified recollection: about 12,000 models in about 270 categories) and the exact ShapeNet TERMS.md text (gated) were not retrieved.
- PartNet-Mobility exact counts (unverified recollection: 2,346 models in 46 categories, including Door and Window) could not be fetched; sapien.ucsd.edu refused the connection.
- Cap3D license and the caption-producing models: the Hugging Face card returned HTTP 401, and the GitHub page states neither.
- No source was found that quantifies the mislabel rate inside Objaverse-LVIS itself.
- Whether the LVIS vocabulary contains each target primitive (barrel, crate, pole, door, ladder and so on) was not checked against the LVIS category list.
- The MVImgNet Terms of Use, ScanObjectNN Terms of Use and Toys4K terms were not retrieved in full.

## 2. Scene datasets with structural labels: which contain stairs, doors, railings, columns; licenses

### Takeaway
Scene datasets are where the structural labels are (ScanNet200 has stairs, stair rail, door, doorframe, column, pillar, ladder, ledge; Matterport3D / HM3DSem have stairs, railing, column, beam, door, window), but every one whose terms could be read is non-commercial or academic-only. They are usable for evaluation and research prototypes, not for training a shipped model.

### Cited Findings
- **ScanNet**: more than 1,500 scans and 2.5 million views. "The data is released under the ScanNet Terms of Use, and the code is released under the MIT license." Access requires a signed agreement sent from an institutional address. — [ScanNet GitHub](https://github.com/ScanNet/ScanNet)
- **ScanNet200** label list (200 classes) contains: wall, floor, ceiling, door, doorframe, closet door, shower door, window, stairs, stair rail, column, pillar, ladder, ledge, structure, table, chair, couch, sofa chair, armchair, crate, box, bin, trash can, counter, cabinet, bookshelf. It does not contain: railing, barrel, car, pole. — [scannet200_constants.py](https://raw.githubusercontent.com/ScanNet/ScanNet/master/BenchmarkScripts/ScanNet200/scannet200_constants.py)
- **ScanNet++**: use only for non-commercial research and educational purposes, commercial use strictly prohibited; data may be shared only with colleagues who signed the terms; a for-profit employer is bound; German law governs. (From a search-result summary of the terms PDF.) — [ScanNet++ Terms of Use](https://scannetpp.mlsg.cit.tum.de/scannetpp/static/scannetpp-terms-of-use.pdf)
- **Matterport3D**: 90 properties. "The data is released under the Matterport3D Terms of Use, and the code is released under the MIT license." — [Matterport GitHub](https://github.com/niessner/Matterport)
- **Matterport3D category set (mpcat40)**: void, wall, floor, chair, door, table, picture, cabinet, cushion, window, sofa, bed, curtain, chest_of_drawers, plant, sink, stairs, ceiling, toilet, stool, towel, mirror, tv_monitor, shower, column, bathtub, counter, fireplace, lighting, beam, railing, shelving, blinds, gym_equipment, seating, board_panel, furniture, appliances, clothes, objects, misc, unlabeled. — [mpcat40.tsv](https://raw.githubusercontent.com/niessner/Matterport/master/metadata/mpcat40.tsv)
- **HM3D**: Matterport's academic end-user license allows non-commercial academic use only, requires the agreement to accompany published derived material, and forbids building an online experience similar to Matterport's products. (From a search-result summary.) — [Matterport EULA for Academic Use of Model Data](https://matterport.com/legal/matterport-end-user-license-agreement-academic-use-model-data)
- **HM3DSem v0.2**: 142,646 object instance annotations across 216 spaces and 3,100 rooms, raw names mapped to the 40 Matterport categories; "free and available for academic, non-commercial research". — [HM3D-Semantics page](https://aihabitat.org/datasets/hm3d-semantics/)
- **Structured3D**: 3,500 synthetic house designs with semantic, albedo, depth, normal and layout ground truth and 3D structure annotations (planes, wireframes, floorplans, 3D boxes). "The data is released under the Structured3D Terms of Use"; code is MIT. — [Structured3D GitHub](https://github.com/bertjiazheng/Structured3D)
- **3D-FRONT**: 6,813 CAD houses, 18,968 furnished rooms, 13,151 furniture objects; described by its authors as freely available "to the academic community and beyond". — [3D-FRONT paper](https://arxiv.org/abs/2011.09127v2)
- **Replica**: 18 scenes with semantic class and instance segmentation; terms are in a LICENSE file not shown on the README. — [Replica GitHub](https://github.com/facebookresearch/Replica-Dataset)
- **ARKitScenes**: 5,047 captures of 1,661 unique scenes with 3D oriented boxes for a furniture taxonomy; license is in a LICENSE file. — [ARKitScenes GitHub](https://github.com/apple/ARKitScenes)
- ARKitScenes is listed by a NeurIPS 2025 supplemental as under an Apple license described as non-commercial. (From a search-result summary.) — [NeurIPS 2025 supplemental](https://papers.nips.cc/paper_files/paper/2025/file/6b9628a5da76f5f1d6ec025f4b493686-Supplemental-Datasets_and_Benchmarks_Track.pdf)
- **Stanford 2D-3D-S**: 6 areas from 3 buildings, over 6,000 m², over 70,000 RGB images; the dataset license is shown only behind the download link; the repository's Apache-2.0 license "covers only the provided software". — [2D-3D-Semantics GitHub](https://github.com/alexsax/2D-3D-Semantics)

### Inferences
- If the team needs labelled real examples of stairs, columns or railings for a held-out sanity check, ScanNet200 and Matterport3D have them, but under terms that bind a for-profit employer to non-commercial use. A safe pattern is to keep them strictly as an offline research benchmark and never put them into the training set of a shipped model.
- Scans differ from game meshes (noise, holes, no clean topology), so even without the license problem their value as training data for an in-engine bot is limited. Their class vocabularies are still a useful checklist for the taxonomy: ScanNet200 separates door / doorframe / closet door and stairs / stair rail / ladder / ledge.
- Structured3D and 3D-FRONT are synthetic and closer to engine geometry than scans, but their terms were not readable in this session; assume research-only until checked.

### Gaps
- ScanNet Terms of Use and Matterport3D Terms of Use PDFs could not be fetched (the host kaldir.vc.in.tum.de refused the connection). Unverified recollection: both restrict use to non-commercial research and educational purposes.
- Structured3D Terms of Use, the 3D-FRONT license, the Replica LICENSE and the S3DIS / 2D-3D-S license texts were not retrieved. Unverified recollection: the S3DIS 13 classes are ceiling, floor, wall, beam, column, window, door, table, chair, sofa, bookcase, board, clutter.
- The ScanNet200 head / common / tail split (66 / 68 / 66 categories by labelled-point frequency) came only from secondary search summaries and was not checked on the benchmark page.

## 3. Terrain and traversability data: stair datasets, off-road sets, procedural terrain generators

### Takeaway
Real terrain datasets (RELLIS-3D, GOOSE, RUGD) label surface type (grass, mud, asphalt), not geometric structure, and are partly non-commercial. The practical source for route C is the procedural terrain code used for legged-robot training: Isaac Lab and legged_gym generate stairs, slopes, pits, gaps, boxes, rails and stepping stones under BSD-3-Clause, with the generating parameters available as free labels.

### Cited Findings

**Procedural generators**
- Isaac Lab height-field sub-terrains: random uniform (rough), pyramid sloped and inverted pyramid sloped, pyramid stairs and inverted pyramid stairs, discrete obstacles, wave, stepping stones. Parameters include `slope_range`, `step_height_range`, `step_width`, `obstacle_height_range`, `stone_distance_range`, `holes_depth`. — [Isaac Lab terrains API](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.terrains.html)
- Isaac Lab trimesh sub-terrains: flat plane, pyramid stairs, inverted pyramid stairs, random grid, rails, pit (`pit_depth_range`, `double_pit`), box (`box_height_range`), gap (`gap_width_range`), floating ring, star, repeated objects (pyramids, boxes, cylinders). — [Isaac Lab terrains API](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.terrains.html)
- License: "The Isaac Lab framework is released under BSD-3 License." Full workflows need Isaac Sim, which "includes components under proprietary licensing terms"; page header shows Isaac Lab 3.0.0. — [Isaac Lab GitHub](https://github.com/isaac-sim/IsaacLab)
- legged_gym `terrain.py` builds eight types by curriculum: smooth slope, rough slope (slope plus uniform noise of ±0.05 m), stairs down, stairs up (step width 0.31 m), discrete obstacles (20 rectangles of 1 to 2 m), stepping stones, gap, pit. Difficulty formulas: slope = 0.4 × d, step height = 0.05 + 0.18 × d, obstacle height = 0.05 + 0.2 × d, stone size = 1.5 × (1.05 − d), gap size = 1.0 × d, pit depth = 1.0 × d (metres, d in 0..1). — [legged_gym terrain.py](https://raw.githubusercontent.com/leggedrobotics/legged_gym/master/legged_gym/utils/terrain.py)
- legged_gym file header: BSD-3-Clause, Copyright (c) 2021 NVIDIA CORPORATION & AFFILIATES and ETH Zurich, Nikita Rudin. — [legged_gym terrain.py](https://raw.githubusercontent.com/leggedrobotics/legged_gym/master/legged_gym/utils/terrain.py)
- Genesis tiles sub-terrains with the same technique as Isaac Gym; built-ins include flat, random uniform, pyramid sloped, discrete obstacles, wave, pyramid stairs, stairs, stepping stones and fractal terrain. — [Genesis terrain docs](https://genesis-world.readthedocs.io/en/v1.2.1/user_guide/getting_started/terrain.html)
- A third-party "terrain_benchmark" repository for legged locomotion is licensed CC BY-NC-SA 4.0, so not every terrain suite is permissive. (From a search-result summary.) — [terrain_benchmark](https://github.com/zita-ch/terrain_benchmark)

**Learning traversability from procedural height maps (closest published analogue of route C)**
- Training terrains were procedural: sums of 2D simplex-noise layers plus holes, steps, bumps and rail-like indentations. 30 training terrains of 512 × 512 px, each a 10 m × 10 m surface (about 2 cm per pixel); 450K training samples; simulation of the training data took about one day. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)
- Model: CNN on a 60 × 60 px patch (1.2 m × 1.2 m) with three 3×3 convolution layers of 5 feature maps, one 2×2 max-pool, a 128-unit dense layer and a 2-way softmax; 100 epochs; about 1 hour on one NVIDIA Tesla K80. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)
- Results (accuracy / AUC), binary traversable vs not: synthetic evaluation 0.926 / 0.970; real-world elevation maps 0.819 / 0.840 (Quarry), 0.858 / 0.884 (Sullens), 0.832 / 0.839 (Gravelpit), 0.887 / 0.921 (ETH-ASL), 0.864 / 0.875 (Slope), 0.961 / 0.980 (Bars). A HOG + Random Forest baseline scored 0.703 to 0.829 accuracy. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)
- Stated limits: only shape is modelled (no friction or soft ground); narrow passages, tight rails and low barriers were under-represented in the procedural training data, which the authors link to lower real-world scores; steep downhill slopes are often labelled traversable. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)

**Stair detection**
- An RGB-D stair detection network reports +5.64% accuracy and +7.97% recall over prior deep methods, and a lightweight version above 300 frames per second; the abstract does not give dataset size or availability. — [RGB-D-based Stair Detection (2022)](https://arxiv.org/abs/2212.01098)
- A 2026 paper projects a robot-centric point cloud into a fixed bird's-eye-view grid and trains a student encoder (supervised by a privileged teacher in simulation) to predict step height, step depth and yaw. (From a search-result summary; no accuracy numbers seen.) — [Explicit Stair Geometry Conditioning (2026)](https://arxiv.org/pdf/2605.09944)
- Non-learned geometric staircase detection on point clouds remains a published approach for robots (ICRA 2023, CMU). — [Fast Staircase Detection and Estimation](https://ri.cmu.edu/?p=137507)

**Off-road datasets with terrain classes**
- RELLIS-3D: annotations for 13,556 LiDAR scans and 6,235 images, 20 classes including void; classes named in benchmarks include grass, tree, bush, concrete, mud, puddle, rubble, barrier, log, fence, vehicle, pole, water, asphalt, building. License: "Creative Commons Attribution-NonCommercial-ShareAlike 3.0 License." — [RELLIS-3D GitHub](https://github.com/unmannedlab/RELLIS-3D)
- GOOSE: 15,000 image and point-cloud frames; "The data is published under the CC BY-SA license"; 64 semantic classes. — [GOOSE site](https://goose-dataset.de/); [GOOSE paper](https://arxiv.org/html/2310.16788v2)
- RUGD: 24 classes, RGB camera only, per the GOOSE paper's comparison table. — [GOOSE paper](https://arxiv.org/html/2310.16788v2)

### Inferences
- The generators give exactly the classes the brief names (stairs up / down, slope or ramp, pit, gap, box or ledge, rough, flat, pillars via repeated cylinders, rails), and each sub-terrain is produced from explicit parameters, so labels cost nothing. The code is BSD-3-Clause, and generated height fields are the team's own output, so there is no dataset license to manage. The team does not need Isaac Sim to reuse the pure-NumPy height-field functions.
- The generators emit whole sub-terrain tiles (8 m × 8 m is typical in these code bases), not labelled local patches. The team must write its own patch sampler and decide what the label of a patch is when it straddles two structures (stairs meeting a flat landing, a ledge next to a wall). That labelling rule is the main design work in route C.
- Real off-road datasets label material and object type, not geometric structure, and RELLIS-3D is non-commercial. They add little to a game bot that reads engine geometry.

### Gaps
- No public benchmark was found for multi-class classification of local structure (pit / stairs / ramp / ledge / gap / wall / flat) from height patches. The published numbers found are for binary traversability.
- No dataset of negative obstacles (pits, drop-offs) with labels was found in this session.
- RUGD and TartanDrive licenses were not found. The GOOSE CC BY-SA version number and the full GOOSE class list were not shown on the page.
- Stair dataset sizes and public availability were not confirmed.

## 4. Synthetic and procedural data as a substitute: how well does it generalise

### Takeaway
Procedural shapes are a proven substitute for curated 3D assets in pretraining (150K shapes built from five primitives match ShapeNet pretraining within 0.3 to 0.8 points), and a tiny CNN trained only on procedural height maps transferred to real terrain at 82 to 96% accuracy. The failure case is crossing domains: models trained on clean CAD drop to 25 to 49% on real scans, and open-set detection drops with them.

### Cited Findings
- Point-MAE-Zero pretrains on 150K procedural shapes (8,192 surface points each) composed from cubes, spheres, cylinders, cones and tori with Boolean differences and wireframe conversion; generating the object and scene data took about 1,400 CPU hours. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)
- Downstream accuracy, from scratch (revised setup) / pretrained on ShapeNet / pretrained on procedural shapes: ModelNet40 93.4 / 93.8 / 93.0; ScanObjectNN OBJ-BG 87.44 / 90.0 / 90.4; OBJ-ONLY 82.03 / 88.3 / 88.6; PB-T50-RS 81.99 / 85.18 / 85.46. ShapeNetPart mIoU 85.1 / 86.1 / 86.1. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)
- More complex procedural shapes help: PB-T50-RS 83.93 with a single primitive, 84.52 with up to 3, 84.73 with up to 9, 85.46 with augmentation. Performance keeps improving as the procedural set grows. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)
- The authors conclude that "current self-supervised learning methods primarily capture geometric structures rather than high-level semantics." — [Point-MAE-Zero project page](https://point-mae-zero.cs.virginia.edu/)
- Scene level: a model pretrained on 4K procedural scenes reached ScanNet mIoU 74.34 and instance AP50 63.12, against 73.85 and 60.51 when pretrained on ScanNet itself. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)
- CAD to real scans without adaptation (train ModelNet40, test ScanObjectNN): OBJ_ONLY 30.9 to 49.3% and PB_T50_RS 24.6 to 36.8% across six architectures, against 73.8 to 86.2% and 63.0 to 78.5% when trained on ScanObjectNN. "Knowledge learned from synthetic objects in ModelNet40 is not well transferable and/or applicable to real-world data." — [ScanObjectNN paper (2019)](https://ar5iv.labs.arxiv.org/html/1908.04616)
- Open-set rejection degrades across domains: average AUROC 72.9 to 89.3 on the synthetic track but 57.9 to 71.6 (DGCNN) and 65.7 to 78.2 (PointNet++) on synthetic-to-real, with FPR95 of 76 to 92%. "Synthetic to Real is the most challenging case." — [3DOS (2022)](https://ar5iv.labs.arxiv.org/html/2207.11554)
- A multi-view model fine-tuned only on synthetic renders overfits them: Duoduo CLIP scored 49.16% top-1 on real MVPNet objects, below zero-shot CLIP B-32 (52.68%); OpenShape trained on synthetic shapes scored 10.80%. On ScanNet objects the best model was zero-shot CLIP B-32 (69.2 average accuracy) against 45.6 to 49.4 for OpenShape, TAMM and Uni3D. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Procedural height maps to real terrain: CNN accuracy 0.926 on synthetic test and 0.819 to 0.961 on six real elevation-map datasets. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)
- Engine-built data: SynLiDAR was created with Unreal Engine 4 (over 19 billion points, 32 classes); its authors needed a translator that aligns appearance and sparsity with real data to make it transfer. — [SynLiDAR paper (2021)](https://arxiv.org/pdf/2107.05399)
- An earlier game-world LiDAR generator reported that adding synthesized data improved segmentation IoU by 9%. (From a search-result summary.) — [A LiDAR Point Cloud Generator: from a Virtual World to Autonomous Driving (2018)](https://arxiv.org/pdf/1804.00103)
- Procedural asset and scene generators: Infinigen is BSD-3-Clause, covers Infinigen Nature, Infinigen Indoors and Infinigen Articulated, and exports to OBJ and OpenUSD. ProcTHOR code is Apache-2.0 and generates "interactive, diverse, and semantically plausible houses" for AI2-THOR. — [Infinigen GitHub](https://github.com/princeton-vl/infinigen); [ProcTHOR GitHub](https://github.com/allenai/procthor)

### Inferences
- The synthetic-to-real gap in these papers is not the gap this team faces. The bot's input is engine geometry, so the test domain is itself synthetic. The relevant gap is between training sources (public meshes, procedural shapes) and the studio's own art style, level-of-detail conventions and collision-mesh simplifications. The cited numbers show how large a mesh-domain gap can be (halving of accuracy), which argues for including the studio's own assets in training and holding out whole asset packs for testing.
- Procedural shapes are a good free pretraining set for an encoder and a good training set for classes that are parametric by nature (stairs, ramp, pillar, wall, crate, barrel, doorway opening). They are not a source of semantics for classes defined by use rather than shape (car, sofa, chair), which still need labelled real assets.
- Structural primitives can be generated in the engine itself with full control of dimensions. Point-MAE-Zero's result that diversity and complexity of composition matter suggests randomising proportions, adding Boolean cut-outs and attaching distractor geometry instead of emitting clean textbook stairs.

### Gaps
- No 2024 to 2026 paper was found that trains a closed-set classifier only on engine-exported game assets and reports held-out accuracy on a different game's assets.
- A secondary aggregator page reports a ProcTHOR-trained 3D detector at 18.9% mAP on ScanNet against 46.3% for an in-domain oracle; the primary paper was not identified. — unverified, see [emergentmind ProcTHOR topic](https://www.emergentmind.com/topics/procthor)
- Infinigen's README does not state whether generated assets may be used commercially beyond the BSD-3-Clause code license, and does not list which structural assets (doors, staircases, windows) the indoor generator emits.
- Generation cost per procedural shape on a workstation was not found beyond the 1,400 CPU-hour total above.

## 5. Reference training costs and data needed per class

### Takeaway
The small classifiers relevant here (1 to 3M-parameter point networks, ResNet-18 on 12 views, a three-layer CNN on height patches) are trained on one V100-class GPU in published work, but papers rarely state wall-clock time. The expensive models are the foundation encoders (300 to 480 A100-hours), which the team would only use frozen. Published learning curves reach 83% top-1 on 1,156 long-tailed classes with 16 examples per class on top of a frozen Uni3D encoder.

### Cited Findings

**Point networks trained from scratch**
- PointNet++: 1.5M parameters, 1.7G FLOPs, 1,872 instances per second; PointNeXt-S: 1.4M parameters, 1.6G FLOPs, 2,040 instances per second (throughput measured at 128 × 1,024 points on a Tesla V100 32 GB). — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Setup: one 32 GB V100, AdamW, label smoothing, cosine decay, batch 32, 1,024 points; 250 epochs on ScanObjectNN, 600 epochs on ModelNet40. Training time is not stated. — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Accuracy: ScanObjectNN PB_T50_RS overall accuracy 77.9 (original PointNet++), 86.1 ± 0.7 (PointNet++ with improved training only), 87.7 ± 0.4 (PointNeXt-S), 85.4 ± 1.3 (PointMLP). ModelNet40: 92.8 ± 0.1 (PointNet++ retrained), 93.2 ± 0.1 (PointNeXt-S), 94.1 (PointMLP). — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Training recipe alone moved PointNet++ by +8.2 points on ScanObjectNN and +0.9 on ModelNet40. — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Backbone sizes used in OpenShape: PointNet 1.3M, DGCNN 2.3M, PointMLP 9.3M, PointNeXt 2.8M, PointBERT 5.1M (scaled to 13.3M / 32.3M / 72.1M), SparseConv 5.3M (scaled up to 41.3M). — [OpenShape (2023)](https://ar5iv.labs.arxiv.org/html/2305.10764)

**Self-supervised pretraining plus fine-tuning (Point-MAE family)**
- Fine-tuned Point-MAE: ModelNet40 93.8 (ShapeNet-pretrained) and 93.0 (procedural-pretrained) against 93.4 from scratch; ScanObjectNN PB-T50-RS 85.18 / 85.46 against 81.99 from scratch. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)
- Few-shot ModelNet40 (5-way 10-shot / 5-way 20-shot / 10-way 10-shot / 10-way 20-shot): from scratch 87.8 / 93.3 / 84.6 / 89.4; ShapeNet-pretrained 96.3 / 97.8 / 92.6 / 95.0; procedural-pretrained 96.6 / 97.6 / 91.9 / 95.2. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)

**3D foundation encoders (to be used frozen, not trained in-house)**
- OpenShape: 876K shapes (ShapeNetCore, 3D-FUTURE, ABO, Objaverse), single A100, batch 200, about 300 A100-hours. — [OpenShape (2023)](https://ar5iv.labs.arxiv.org/html/2305.10764)
- Uni3D: 24 × A100-SXM4-40GB, about 20 hours for Uni3D-g, total batch 1,152; input is 10,000 points. Sizes: Ti 6.2M, S 22.6M, B 88.4M, L 306.7M, g 1,016.5M parameters. — [Uni3D (2023)](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Uni3D zero-shot Objaverse-LVIS top-1 by size, trained without / with the LVIS shapes: Ti 43.5 / 46.5, S 44.8 / 50.6, B 45.8 / 51.6, L 46.2 / 53.2, g 47.2 / 55.3. ModelNet40: 85.8 to 88.2 across sizes. — [Uni3D (2023)](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Duoduo CLIP (multi-view images, 87M parameters): 4 × A5000 for 14.3 hours (57 A5000-hours), compared in the same table with OpenShape at 300 hours on one A100 and Uni3D at 480 A100-hours. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)

**Image models on rendered views**
- MVTN with an ImageNet-pretrained ResNet-18, 12 views at 224 × 224: ModelNet40 93.8% (93.4 ± 0.3 over four runs); MVCNN with 12 fixed views 90.1%. ScanObjectNN: OBJ_BG 92.6, OBJ_ONLY 92.3, PB_T50_RS 82.8. Trained 100 epochs with batch 20 on a V100; total time not given. ResNet-34 gave no gain over ResNet-18. — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)
- View resolution matters little: with 4 views, 160 px / 224 px / 280 px gave 91.0 / 91.6 / 91.9%. — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)

**Small 2.5D CNN on height patches**
- Three 3×3 conv layers with 5 maps each plus a 128-unit dense layer, 450K samples of 60 × 60 px, 100 epochs: about 1 hour on a Tesla K80. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)

**Data per class (published learning curves)**
- Linear probe on frozen features, Objaverse-LVIS top-1 at 1 / 2 / 4 / 8 / 16 shots (mean of 10 seeds): Uni3D 46.5 / 54.1 / 63.3 / 73.6 / 83.1; OpenShape-PointBERT 24.0 / 30.1 / 36.4 / 42.6 / 51.3; OpenShape-SparseConv 21.2 / 25.8 / 31.2 / 37.8 / 47.0. — [Uni3D (2023)](https://ar5iv.labs.arxiv.org/html/2310.06773)
- With a pretrained Point-MAE, 20 examples per class give 95% on a 10-way ModelNet40 task; from scratch the same data gives 89.4%. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)

### Inferences
- **ESTIMATE, training time for a from-scratch point network**: PointNeXt-S infers 2,040 instances per second on a V100. Assuming training throughput of roughly a third of that, 15K objects × 250 epochs (3.75M samples) is on the order of 1.5 to 2 GPU-hours, and 10K objects × 600 epochs about 2.5 to 3 hours. For a studio set of 20K to 50K objects at 250 to 300 epochs this gives roughly 2 to 8 hours per run on one modern workstation GPU. No paper confirms these wall-clock figures. Compared with the team's 10-minute DeBERTa runs, iteration is one to two orders of magnitude slower unless epochs are cut.
- **ESTIMATE, frozen-encoder route**: extracting embeddings with a 6M to 23M-parameter Uni3D-Ti / S for tens of thousands of objects should take minutes to about an hour on one GPU, and fitting a linear or small MLP head takes seconds to minutes. This is the route whose iteration time matches the team's current workflow. The catch is that the frozen encoder then has to run at inference too (see section 7 on latency), and that the published checkpoints were trained on a mix including ShapeNet and 3D-FUTURE (research-only data).
- **ESTIMATE, data per class for above 90%**: the published curves suggest about 20 to 50 labelled objects per class on a pretrained or frozen encoder for well-separated classes (95% at 20 shots on 10-way; 83% at 16 shots on 1,156-way long tail), and a few hundred per class when training a small network from scratch (ModelNet40 and ScanObjectNN reach 86 to 94% with their full training sets). For 50 to 200 classes this means roughly 2K to 10K labelled objects with a pretrained encoder, or 15K to 60K from scratch. Accuracy above 90% is not guaranteed for visually confusable pairs (pole / pillar, crate / box, ramp / wedge, ledge / low wall) whatever the data volume.
- Model size is not where accuracy comes from: Uni3D-Ti (6.2M) is within 3.7 points of the 1B-parameter Uni3D-g when LVIS shapes are excluded, and the training recipe moved PointNet++ by 8 points. Effort should go to data and augmentation, not architecture.

### Gaps
- No paper found states wall-clock training time for PointNet++, PointNeXt, Point-MAE fine-tuning, MVCNN / MVTN or a ViT-S on rendered views. All hours above for these are estimates.
- No published learning curve was found for a closed set of exactly 50 to 200 classes with accuracy as a function of examples per class. The estimates extrapolate from 10-way, 40-way and 1,156-way results.
- ModelNet40 train / test sizes and per-class counts were not retrieved. Unverified recollection: 9,843 training and 2,468 test models, about 246 training models per class, strongly imbalanced.
- The Uni3D few-shot table does not say whether all 1,156 categories are used.
- No training cost was found for a Mac (Apple Silicon / MPS) for any of these models.

## 6. Auto-labelling economics: teacher models, zero-shot accuracy, API cost, label noise

### Takeaway
Zero-shot teachers are weak labellers on large vocabularies (36 to 55% top-1 on 1,156 Objaverse-LVIS classes) but much better on small ones (84 to 88% top-1 and 98% top-5 on 40 ModelNet classes), so a 50 to 200-class studio vocabulary sits between the two and needs human review of low-confidence items. API labelling is cheap: by my estimate $4 to $25 per 10,000 objects with small models at four views, and $60 to $300 with frontier models or twelve high-resolution views.

### Cited Findings

**Zero-shot accuracy of candidate teachers**
- Zero-shot CLIP on 12 rendered views, no 3D training, Objaverse-LVIS top-1 / top-3 / top-5: ViT-B/32 35.7 / 54.8 / 62.1; ViT-bigG/14 43.5 / 64.2 / 71.3. Going from 1 to 12 views adds 7.45 points for B-32. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Multi-view CLIP fine-tuned on 3D data (Duoduo CLIP): 12 views 55.2 / 77.1 / 83.4 (52.7 top-1 when LVIS shapes are excluded from training); 5 views 54.1 / 76.0 / 82.4. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Point-cloud encoders, Objaverse-LVIS top-1: OpenShape-PointBERT 46.8 (39.1 without LVIS shapes), TAMM 50.7 (42.0), MixCon3D 52.5 (47.5), Uni3D-g 55.3 (47.2). — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Smaller vocabularies: OpenShape-PointBERT ModelNet40 84.4 / 96.5 / 98.0 (top-1 / 3 / 5) and ScanObjectNN 52.2 / 79.7 / 88.7; Uni3D-g ModelNet40 86.8 to 88.2 and ScanObjectNN 63.9 to 66.5. — [OpenShape (2023)](https://ar5iv.labs.arxiv.org/html/2305.10764); [Uni3D (2023)](https://ar5iv.labs.arxiv.org/html/2310.06773)
- Depth-projection methods without 3D training are much weaker: PointCLIP 19.3 and PointCLIP v2 63.6 top-1 on ModelNet40; 1.9 and 4.7 on Objaverse-LVIS. — [OpenShape (2023)](https://ar5iv.labs.arxiv.org/html/2305.10764)
- Prompt sets and protocols differ between papers (64 prompts per class in ULIP-style evaluation, nearest class embedding in Duoduo CLIP), so numbers are only roughly comparable. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Pseudo-labelling at scale: assigning 1,156 class names to about 200K Objaverse objects with Uni3D produced labels with a noise ratio of about 50%. (From a search-result summary.) — [DAC, arXiv 2407.17779](https://arxiv.org/pdf/2407.17779)
- SigLIP 2 (`google/siglip2-base-patch16-224`): Apache-2.0, 0.4B parameters for the full dual encoder, usable for zero-shot image classification. — [SigLIP 2 model card](https://huggingface.co/google/siglip2-base-patch16-224)

**API prices, October 2026 (USD per 1M tokens, input / output)**
- Google, page last updated 2026-10-09: Gemini 2.5 Flash-Lite 0.10 / 0.40; Gemini 3.1 Flash-Lite 0.25 / 1.50; Gemini 3.5 Flash-Lite 0.30 / 2.50; Gemini 2.5 Flash 0.30 / 2.50; Gemini 3 Flash Preview 0.50 / 3.00; Gemini 3.6 Flash and 3.8 Flash 0.75 / 3.75; Gemini 2.5 Pro 1.25 / 10.00; Gemini 3.1 Pro Preview 2.00 / 12.00. Batch is half price. Gemini 3.6 / 3.8 Flash rise to 1.50 / 7.50 on 1 January 2027. — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Gemini 3 image input costs 280 tokens at low `media_resolution`, 560 at medium, 1,120 at high (the default) and 2,240 at ultra high. — [Gemini media resolution docs](https://ai.google.dev/gemini-api/docs/media-resolution)
- Anthropic: Claude Haiku 5.5 0.10 / 0.50 (prompts up to 100K tokens); Claude Haiku 4.5 1 / 5; Claude Sonnet 5.5 2 / 10; Claude Opus 5.5 4 / 20. Batch API gives 50% off input and output. — [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)

**Label noise and the student**
- Deep networks tolerate large amounts of random label noise: MNIST test accuracy stays above 90% with 100 randomly labelled examples per clean one; the required training-set size grows with the dilution factor; the finding also held for noise biased toward confusable classes. — [Deep Learning is Robust to Massive Label Noise (2017)](https://arxiv.org/abs/1705.10694)
- A vendor write-up of GPT-4o tagging of game assets reports "over 90% consistency with manual tagging" and about 85% less manual effort, without describing the test set. — [Anchorpoint AI tagging write-up (Feb 2025)](https://app.readytensor.ai/publications/labelling-game-assets-with-ai-in-anchorpoint-Ei281NFx7qia)

### Inferences
- **ESTIMATE, API cost per 10,000 objects.** Assumptions: one request per object, about 500 text tokens for instructions and the class list, about 40 output tokens.
  - 4 views at 560 tokens each (2,740 input tokens): Gemini 3.1 Flash-Lite about $7.5 (batch about $3.7); Gemini 3 Flash Preview about $15; Gemini 3.8 Flash about $22 (about $44 after 1 January 2027); Gemini 3.1 Pro Preview about $60.
  - 12 views at 1,120 tokens each (13,940 input tokens): Gemini 3.1 Flash-Lite about $35; Gemini 3.8 Flash about $106; Gemini 3.1 Pro Preview about $284.
  - Claude, assuming about 1,300 tokens per roughly one-megapixel image (this image-token figure was not verified in this session), 4 views (about 5,800 input tokens): Haiku 5.5 about $6; Haiku 4.5 about $60; Sonnet 5.5 about $120; Opus 5.5 about $240; half of each with the Batch API.
  - Overall range: $4 to $25 per 10,000 objects with small models, $60 to $300 with frontier models or many high-resolution views. Rendering the views locally is extra but small.
- The cost of labelling is therefore negligible next to engineer time. The real cost is verification: at the published zero-shot accuracies a human must review a meaningful share of labels, and the review tool (contact sheet per class, sort by teacher confidence) is the thing to build.
- Teacher errors are not random. They concentrate on confusable classes and on whole styles of asset, so the robustness result for random noise is an upper bound on tolerance. A practical scheme is to accept a label only where two different teachers agree (a multi-view image-text model and a VLM), send disagreements to a human, and keep a human-verified test set that no teacher touched.
- A local zero-shot pass with an open image-text model costs only GPU time and keeps unreleased assets off third-party servers, which may matter more to a studio than the API bill.
- For structural primitives (pit, ramp, ledge, gap) an image-text teacher is the wrong tool: these are not objects with a canonical appearance, and a render of grey collision geometry gives CLIP-style models little to match. Labels for these should come from the generator parameters (route C).

### Gaps
- No published accuracy was found for a large VLM (Gemini, Claude, GPT class) classifying multi-view renders of 3D objects into a closed set on a public benchmark as of 2026.
- No SigLIP 2 result was found for multi-view zero-shot classification of 3D objects; the model card gives no accuracy numbers in text.
- OpenAI prices as of October 2026 were not retrieved. Claude's tokens-per-image rule and Gemini 2.5 tokens-per-image were not retrieved.
- No study was found that measures student accuracy as a function of teacher label noise specifically for 3D asset classification.
- Licenses of OpenAI CLIP / OpenCLIP weights were not checked in this session.

## 7. Engineering cost drivers: ONNX export, quantisation, CPU latency, evaluation practice

### Takeaway
The avoidable engineering risks are known: point networks depend on sampling and grouping operators that ship as compiled extensions and must be rewritten in plain tensor operations for ONNX export; int8 speed-ups on CPU depend on the instruction set; and open-set rejection on 3D data is weak (false-positive rate at 95% recall of 44 to 77% even in-domain). No published CPU latency for these networks was found, so the "few milliseconds per object" requirement is unverified for route A.

### Cited Findings
- Farthest point sampling and gather / ball-query steps in common PointNet++ implementations call compiled extensions (`ext.furthest_point_sampling` in kaolin, `_ext.furthest_point_sampling` in `pointnet2_ops`). — [kaolin PointNet2 source](https://kaolin-jfl.readthedocs.io/en/latest/_modules/models/PointNet2.html)
- Pure-PyTorch versions exist that implement farthest point sampling as a loop of `torch.min` / `torch.argmax` and ball query through squared distances and masking. — [vis4d pointnetpp source](https://vis4d.readthedocs.io/en/latest/_modules/vis4d/op/base/pointnetpp.html); [Ascend ModelZoo pointnet2_ops.py](https://gitcode.com/ascend/ModelZoo-PyTorch/blob/master/ACL_PyTorch/built-in/embodied_ai/GenPosePlus/pointnet2_ops.py)
- ONNX Runtime guidance: static quantisation for CNNs, dynamic quantisation for RNN and transformer models; signed-activation / signed-weight (S8S8) with the QDQ format is the default for CPU; S8S8 with the QOperator format is slow on x86-64 and should be avoided. — [ONNX Runtime quantization docs](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- A 2026 measurement study ran one int8 QDQ ResNet-50 on ONNX Runtime's CPU provider on four CPUs and found that whether int8 is faster than float depends on the CPU's instruction set; it also warns that evaluating on subsets can inflate top-1 by about 9.77 points. (From a search-result summary.) — [Is INT8 Portable? (2026)](https://arxiv.org/pdf/2609.16085)
- An individual blog reports about 2.2× speed-up for int8 static MobileNetV2 on a Raspberry Pi 4 with ONNX Runtime, measured on a 500-image subset. — [zenn.dev ORT INT8 post](https://zenn.dev/ux_xu/articles/ort-int8-ptq-cnn)
- Compute per forward pass: PointNeXt-S 1.6G FLOPs and PointNet++ 1.7G FLOPs at 1,024 points. — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Multi-view inference time reported by MVTN: MVCNN 39.89 ms and ViewGCN 26.06 ms per object (12 views); a PointNet encoder plus view regressor 3.50 ms. — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)
- Pose sensitivity: under random rotation about the vertical axis of ±90° PointNet falls to 42.5%, and at ±180° PointNet and PointNet++ fall to 38.6% and 39.7%, while MVTN holds 90.8% and 91.2%. — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)
- Occlusion: with 50% of the object removed, MVTN 67.1%, PointNet 53.5%, DGCNN 30.1%; at 75% all are below 10%. — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)
- Open-set rejection on 3D (3DOS): in the synthetic track the best average AUROC is 89.3 with FPR95 between 43.6 and 76.6; real-to-real AUROC 67.2 to 78.0; synthetic-to-real 57.9 to 78.2. Simple representation methods (cross-entropy with L2-normalised features, SubArcFace, cosine prototypes) often beat methods ported from 2D; "PointNet++ has proven to be extremely robust in processing real-world data, even across domains." — [3DOS (2022)](https://ar5iv.labs.arxiv.org/html/2207.11554)
- Class imbalance is the norm in the public sets: Objaverse-LVIS is long-tailed, and ScanNet200 is reported in head / common / tail groups. — [OpenShape (2023)](https://ar5iv.labs.arxiv.org/html/2305.10764); [scannet200_constants.py](https://raw.githubusercontent.com/ScanNet/ScanNet/master/BenchmarkScripts/ScanNet200/scannet200_constants.py)

### Inferences
- **ESTIMATE, CPU latency.** A 1.6G-FLOP point network is in the same compute class as ResNet-18 (about 1.8G FLOPs). On a desktop CPU with ONNX Runtime that class typically runs in roughly 10 to 30 ms single-threaded, not "a few milliseconds". To hit a few milliseconds the team would need a lighter design: fewer points (256 to 512), a plain PointNet-style network without neighbourhood grouping, a small voxel CNN (for example 32³ occupancy), or simply caching the label per asset so inference runs once at import time. No published CPU measurement backs these figures.
- Per-asset classification of static geometry does not need to run at query time at all. Labels for meshes can be computed when assets are cooked and stored with the asset; only route C (a query at an arbitrary point in a level) is inherently a runtime call, and its network is tiny.
- ONNX export effort differs sharply by route. A 2.5D CNN or a ResNet-18 exports with no custom work. A PointNet (no grouping) exports cleanly. PointNet++ / PointNeXt need farthest point sampling and ball query rewritten in exportable operations, with fixed point counts, and then verified for parity between PyTorch and ONNX Runtime; budget days, not hours, and expect the sampling loop to dominate CPU time. DGCNN-style k-nearest-neighbour graphs are quadratic in point count.
- Normalising each object to a unit sphere, as all the cited benchmarks do, throws away absolute size, which in a game is one of the strongest cues (pole vs pillar, crate vs container, kerb vs wall). Feeding real-world extents as extra input features is cheap and has no counterpart in the benchmark numbers.
- Evaluation practice that follows from the cited results: split by asset pack or by source, never by random object (near-duplicates and shared styles inflate random-split accuracy); report macro-averaged accuracy and per-class recall because of imbalance; include a held-out set of classes for open-set testing and report AUROC and FPR95, expecting them to be far worse than closed-set accuracy; augment with random yaw (and full rotation if assets are not consistently oriented); test on partial and merged meshes because level geometry is rarely one clean object per mesh.
- An explicit "unknown / other" class trained on diverse negatives, plus a threshold on the top probability calibrated on held-out packs, is the pragmatic combination; the 3DOS numbers say no method makes rejection reliable by itself.

### Gaps
- The search did not return an authoritative statement that specific PointNet++ operators fail in `torch.onnx.export`, nor a reference exported model with measured CPU latency. The export difficulty is inferred from the implementations.
- No published int8 quantisation results (accuracy drop, speed-up) were found for point-cloud classifiers or small voxel networks on CPU.
- No calibration study (expected calibration error and so on) for 3D shape classifiers was found.
- The hardware behind MVTN's millisecond figures was not confirmed (a V100 GPU is mentioned elsewhere in the paper).

## 8. Public write-ups from studios and tool vendors on automatic asset tagging

### Takeaway
Vendors ship automatic tagging of 3D asset libraries (NVIDIA USD Search, Unity Asset Manager, TurboSquid Kraken Pro, Anchorpoint, Project Manager for 3ds Max), all built on image or vision-language models over renders and file metadata, and none publishes a measured accuracy on a described test set. The only number found is a vendor claim of "over 90% consistency with manual tagging". No engineering write-up was found from Epic, Roblox, Adobe or Sketchfab.

### Cited Findings
- NVIDIA SimReady specification: every asset must carry at least one semantic label; NVIDIA uses Wikidata Q-codes as the primary taxonomy for its Omniverse asset libraries; labels are authored with the `SemanticsLabelsAPI` schema (OpenUSD 24.11 and later), and several taxonomies can coexist on one prim; labelling sub-parts "increases the usefulness of the semantic labels for ML training". — [SimReady semantic labels capability](https://nvidia.github.io/simready-foundation/latest/capabilities/semantic_labels/capability-semantic_labels.html)
- Wikidata items bring synonyms, subtrees and translations that can be stored with the asset. — [SimReady semantic labeling docs](https://docs-prod.omniverse.nvidia.com/simready/latest/sim-needs/semantic-labeling.html)
- NVIDIA USD Search API 1.1.0 (February 2025) added automatic captioning and tagging powered by vision language models, with configurable providers (NVIDIA AI Endpoints, OpenAI, Azure OpenAI, Mistral AI, Anthropic). — [USD Search API 1.1.0 release notes](https://docs.omniverse.nvidia.com/services/latest/services/usd-search/release-notes/1_1_0ga.html)
- USD Search is described as indexing 3D asset databases so they can be searched "without manual tagging", and its search model is NVCLIP, NVIDIA's commercial CLIP. No accuracy figure is given. — [NGC catalog USD Search](https://catalog.ngc.nvidia.com/orgs/nvidia/usdsearch/collections/usdsearch/-); [USD Search model card](https://build.nvidia.com/nvidia/usdsearch/modelcard)
- Unity Asset Manager marketing lists "AI-generated tagging" next to custom metadata fields and tags; no accuracy claim. — [Unity: 5 reasons to use Unity Asset Manager](https://unity.com/vn/resources/5-reasons-to-use-unity-asset-manager)
- Anchorpoint plugin (February 2025): GPT-4o through the OpenAI API tags textures, models and sounds from resized previews into `AI-Types`, `AI-Genres` and `AI-Objects`; reports about 85% less manual effort and over 90% consistency with manual tagging; test libraries and the measurement method are not described; token cost is estimated before a run. — [Labelling game assets with AI in Anchorpoint](https://app.readytensor.ai/publications/labelling-game-assets-with-ai-in-anchorpoint-Ei281NFx7qia)
- TurboSquid Kraken Pro (March 2020): cloud service that tags a studio's model library by content category, format and rig / animation state, using "every available source from a model" (image recognition, texture names, object names, materials, layers, file names); trained on content from TurboSquid's roughly 800,000-model marketplace; staff curate categories before delivery; from $599 per month for 10,000 models and 50 users; no quantitative accuracy. — [CG Channel on Kraken Pro](https://www.cgchannel.com/2020/03/kraken-pro-automatically-sorts-your-messy-3d-model-library/)
- Project Manager 4 for 3ds Max advertises AI classification of assets by object type, material composition and style, without accuracy figures. — [3d-kstudio blog](https://3d-kstudio.com/kstudio-blog/the-asset-library-that-organises-itself/)
- Roblox: no engineering post on asset tagging or embedding search was found; a 2025 Marketplace machine-learning job posting describes work on search and recommendation with models that understand text and visual content. — [Roblox ML engineer posting](https://www.themuse.com/jobs/roblox/2025-senior-machine-learning-engineer-marketplace-phd-new-grad)

### Inferences
- The industry pattern is the route B teacher without a student: render or reuse thumbnails, send them with file names and metadata to a general vision-language model, store free-form tags. Nobody publishes a closed-set structural taxonomy for gameplay (pit, ledge, ramp, cover), which suggests that part is not available off the shelf and has to be built.
- File names, material names and folder paths are used by every vendor as extra evidence. A studio's own asset library has these for free, and a text feature (the team already trains DeBERTa-v3 text classifiers) fused with geometry is likely to raise label quality at almost no cost. This is my suggestion, not a published result.
- SimReady's choice of Wikidata Q-codes is a ready-made answer to "a list meant to grow": store an open identifier per asset and map it to the bot's closed gameplay classes in a separate table, so the taxonomy can be extended without relabelling.
- The absence of published accuracy from any vendor means the team cannot benchmark against the market and has to build its own held-out test set before choosing a route.

### Gaps
- No public write-up with measured accuracy was found from Epic (Fab / Quixel), Unity, Roblox, Adobe (Substance 3D), Sketchfab or Shutterstock / TurboSquid for automatic semantic labelling of 3D assets.
- Which VLM is the default captioner in current USD Search releases (1.4 is mentioned in the NGC catalog) was not found.
- Whether any SimReady tooling assigns Q-code labels automatically was not found.

## Route summary: effort and risk for routes A, B and C

### Takeaway
Route C is the cheapest and lowest-risk (free procedural labels, permissive code, a tiny CNN, about an hour of training in the one published analogue). Route B is the fastest way to label a studio's asset library but belongs at asset-import time, not in the runtime path. Route A is the only one with real licensing and export risk, and its public data covers furniture and vehicles but not structural primitives.

### Cited Findings

**Route A: closed-set classifier over object geometry**
- Commercially usable labelled data: Objaverse objects under CC-BY 4.0 (721K) and CC0 (3.5K), of which about 47K have verified labels in 1,156 LVIS categories; OmniObject3D (6,000 objects, 190 categories, CC BY 4.0); Google Scanned Objects (1,030 objects, CC-BY 4.0); uCO3D (about 170K real-object videos with point clouds, CC BY 4.0). — [HF card allenai/objaverse](https://huggingface.co/datasets/allenai/objaverse); [Objaverse paper](https://ar5iv.labs.arxiv.org/html/2212.08051); [OmniObject3D GitHub](https://github.com/omniobject3d/OmniObject3D); [Google Research blog](https://www.research.google/blog/scanned-objects-by-google-research-a-dataset-of-3d-scanned-common-household-items/); [uCO3D GitHub](https://github.com/facebookresearch/uco3d)
- Not usable commercially: ShapeNet (non-commercial research and education), 3D-FUTURE (scientific research only), PartNet-Mobility (non-commercial), ScanNet++ (commercial use strictly prohibited). — [ShapeNet Terms of Use](https://www.shapenet.org/terms); [3D-FUTURE license agreement](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202004171628_60052.html); [HF sapien-sim/PartNetMobility](https://huggingface.co/datasets/sapien-sim/PartNetMobility); [ScanNet++ Terms of Use](https://scannetpp.mlsg.cit.tum.de/scannetpp/static/scannetpp-terms-of-use.pdf)
- Typical model size: 1.3M to 2.8M parameters (PointNet, PointNeXt, DGCNN), 1.6 to 1.7G FLOPs at 1,024 points. — [OpenShape (2023)](https://ar5iv.labs.arxiv.org/html/2305.10764); [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Published training setup: one V100 32 GB, 250 to 600 epochs, batch 32, 1,024 points; wall-clock not stated. — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670)
- Published accuracy: 92.8 to 94.1% on ModelNet40 (40 classes, clean CAD); 86.1 to 87.7% on ScanObjectNN PB_T50_RS (15 classes, real scans); 83.1% on 1,156 Objaverse-LVIS classes with a 16-shot linear probe on frozen Uni3D features; 24.6 to 49.3% when trained on CAD and tested on scans. — [PointNeXt (2022)](https://ar5iv.labs.arxiv.org/html/2206.04670); [Uni3D (2023)](https://ar5iv.labs.arxiv.org/html/2310.06773); [ScanObjectNN paper (2019)](https://ar5iv.labs.arxiv.org/html/1908.04616)
- Procedural pretraining on 150K primitive compositions is worth +3.5 points over training from scratch on ScanObjectNN PB-T50-RS (85.46 against 81.99) and matches ShapeNet pretraining. — [Learning 3D Representations from Procedural 3D Programs (2024)](https://arxiv.org/html/2411.17467)

**Route B: rendered views plus a pretrained image-text model**
- Zero-shot, 12 views, 1,156 classes: CLIP ViT-B/32 35.7% top-1, ViT-bigG/14 43.5% top-1 and 71.3% top-5; fine-tuned multi-view CLIP 55.2%. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Supervised multi-view CNN (ResNet-18, 12 views of 224 px): 93.8% on ModelNet40, 82.8% on ScanObjectNN PB_T50_RS, and robust to rotation where point networks collapse. — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)
- Fine-tuning cost of a multi-view CLIP on about one million shapes: 57 A5000-hours. — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- Fine-tuning on synthetic renders can reduce accuracy on other domains below the zero-shot baseline (49.16% against 52.68% on MVPNet). — [Duoduo CLIP (2024)](https://arxiv.org/html/2406.11579)
- An open teacher with a permissive license exists: SigLIP 2 base is Apache-2.0. — [SigLIP 2 model card](https://huggingface.co/google/siglip2-base-patch16-224)
- Multi-view inference is tens of milliseconds per object in published measurements (MVCNN 39.89 ms for 12 views). — [MVTN (2020)](https://ar5iv.labs.arxiv.org/html/2011.13244)

**Route C: local terrain structure from a height field or occupancy patch**
- Data source: Isaac Lab (BSD-3) and legged_gym (BSD-3-Clause) terrain generators covering slopes, stairs up and down, discrete obstacles, stepping stones, gaps, pits, boxes, rails, random grids and repeated pillars, all parameterised. — [Isaac Lab terrains API](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.terrains.html); [Isaac Lab GitHub](https://github.com/isaac-sim/IsaacLab); [legged_gym terrain.py](https://raw.githubusercontent.com/leggedrobotics/legged_gym/master/legged_gym/utils/terrain.py)
- Published analogue: three small conv layers on 60 × 60 px patches, 450K procedural samples, about 1 hour on a Tesla K80; 92.6% accuracy on synthetic test and 81.9 to 96.1% on real elevation maps for a binary label; a hand-crafted feature baseline reached 70.3 to 82.9%. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)
- Known weak spot of that analogue: structures under-represented in the generator (narrow passages, rails, low barriers) are where real-world accuracy dropped. — [Learning Ground Traversability from Simulations (2017)](https://ar5iv.labs.arxiv.org/html/1709.05368)

### Inferences
All effort figures below are **ESTIMATES** for a team that already has a training and ONNX pipeline for text classifiers. They are not published.

- **Route A**
  - Data work dominates: filter Objaverse by license, map LVIS categories to the game taxonomy, export and label the studio's own assets, generate structural classes procedurally. Estimate 3 to 6 person-weeks before the first credible model.
  - Training: about 2 to 8 GPU-hours per from-scratch run on one workstation GPU for 20K to 50K objects, or minutes per run with a frozen pretrained encoder and a linear head.
  - Expected accuracy on held-out asset packs: 85 to 93% top-1 for 50 to 100 well-defined object classes with a few hundred examples each; noticeably lower (my guess 70 to 85%) on the first try if the test packs differ in style from the training sources.
  - Pitfalls: research-only data leaking into training (including through pretrained checkpoints trained on ShapeNet and 3D-FUTURE); loss of absolute scale through unit-sphere normalisation; pose sensitivity; ONNX export of sampling and grouping; CPU latency above the target unless the network is slimmed or labels are cached per asset; long-tail imbalance; weak open-set rejection; level geometry that is not one object per mesh.
- **Route B**
  - Fastest path to labels: render 4 to 12 views per asset, run an open image-text model locally or a VLM API (estimated $4 to $300 per 10,000 objects depending on model and views), review low-confidence items by hand. Estimate 1 to 2 person-weeks for the pipeline and review tool.
  - As a runtime model it does not meet "CPU-only, a few milliseconds": it needs a renderer in the loop and tens of milliseconds per object. Its natural role is offline labelling at asset import, with the resulting labels either stored per asset or used to train a route A student.
  - Distilling into a small image student (ResNet-18 class on 4 to 12 views) is straightforward to export and quantise but still needs renders at inference; distilling into a geometry student is route A with machine-made labels.
  - Expected accuracy: zero-shot teacher 60 to 90% top-1 on a 50 to 200-class studio vocabulary (interpolated from 36 to 55% on 1,156 classes and 84 to 88% on 40 classes); after human review of disagreements the label set can be as clean as the review budget allows.
  - Pitfalls: untextured or grey-box geometry renders poorly for image-text models; structural primitives have no canonical appearance; prompt wording changes results; overfitting to render style; sending unreleased assets to an external API.
- **Route C**
  - Lowest risk and cost: no dataset license, labels from generator parameters, a network of a few thousand to a few hundred thousand parameters, minutes to about an hour per training run on the workstation or the MacBook, sub-millisecond CPU inference for a 32 to 64 px patch. Estimate 2 to 4 person-weeks including the patch sampler and the labelling rule.
  - Expected accuracy: no published multi-class benchmark exists. In-distribution accuracy on generator output should be high (my guess above 95% for seven classes), and the honest number is accuracy on hand-authored level geometry, which the one published analogue suggests will be 5 to 15 points lower until the generator is extended to cover what levels actually contain.
  - Pitfalls: defining the label of a mixed patch; choosing patch size and resolution (stairs and ramps look alike at coarse resolution, pits and gaps differ only in extent); orientation dependence (decide between a canonical frame aligned to the query direction and rotation augmentation); a height field cannot represent overhangs, doorways, windows or multiple floors, so those need a local occupancy volume or a second model; simple analytic features (slope, step-height histogram, drop depth) are a strong baseline and should be implemented first as both a sanity check and a fallback.
- **Suggested ordering by risk**: C first (self-contained, proves the data and export pipeline on geometry), then B as a labelling tool for the asset library, then A trained on the labels B produced plus licence-clean public data, with A's runtime cost avoided by caching labels per asset.

### Gaps
- All person-week and accuracy-on-own-assets figures above are estimates with no published counterpart; the first two weeks of any route should produce the held-out test set that replaces them with measurements.
- No published end-to-end case was found of a game studio shipping any of the three routes for bot perception, so there is no reference for maintenance cost as the class list grows.
- CPU inference latency for every candidate network on the team's target CPU must be measured; none was found in the literature.
