---
name: remnote-kb-navigation
description: Template skill for navigating a user's RemNote knowledge base using root and top-level note IDs; customize before use.
---

# RemNote KB navigation template

Use this skill to orient quickly in a user's whole RemNote knowledge base.

## Required customization fields

- User label: `a030110`
- Root headline: `眼科`
- Root rem ID: `Da8SsKWwuA9doqpsp`
- Top-level branch map entries:
  - branch title/headline
  - branch rem ID
  - short routing hint

## Navigation rules

1. Use JSON output (default). Do not use `--text` for navigation.
2. Use ID-first traversal via `read`.
3. Use scoped search via `search <query> --parent-id <parent-rem-id>` to precisely locate subtopics under their resolved parent to prevent collision/false matches on generic subtopic names. Initial top-level searches should target the root ID `Da8SsKWwuA9doqpsp`.
4. Start shallow (`--depth 1`) for orientation.
5. Use high child limit for full branch listings: `--child-limit 500`.
6. Keep operations read-only unless write confirmation policy allows mutating commands.

## Top-level map (customize)
### Example
- `Example branch title` - `example-branch-rem-id` - 範本
  - `Example sub-branch title` - `example-sub-branch-rem-id` - 範本

### Current KB map

- `Basic optics` - `4uE8lPWyfyfMkV0NY` - Covers basic concepts of optics in ophthalmology, including optical axis and refraction. Useful for understanding light pathways and axis alignment. | Optics, optical axis, refraction, light pathway, axis alignment, basic ophthalmic optics
  - `Axis` - `5vhhkndt4Vgu5fSSn` - optical axis | Optical axis, geometric reference line, axis measurement, refraction axis in ophthalmic optics
- `Fundamentals` - `t2RMKcbnchc4jlcbx` - 眼科基礎 | Ocular embryology, development, RPE metabolism, basic anatomy
  - `Development` - `5MNsxs4sYJySC8Hw4` - 發育與胚胎學 | Ocular development, embryology, developmental anatomy
  - `Metabolism` - `JdUtn0RbCUsBTsXVR` - 代謝及生化基礎 (RPE) | RPE (retinal pigment epithelium) metabolism, biochemistry, retinal metabolic processes
  - `Anatomy` - `U85Z8RPqP47VfcAKL` - 基礎解剖 | Basic ocular anatomy, fundamental anatomical structures of the eye
- `Procedure` - `qMErQqVFhEEkLYn2G` - 臨床處議程序 | Clinical procedures: suture removal (cornea, other sites), Mcpherson tweezer, #27 needle, toric SCL fitting (TSCL)
  - `器械` - `A3lZlSz9lHhPXLbNl` - 常用眼科器械 (鑷子、針頭)
  - `cornea拆線` - `v8U7VfcO7C4K9SVoY` - 角膜拆線步驟
  - `其他地方拆線` - `pzhOxlwqLpXygvvET` - 魚尾剪拆線
  - `戴 TSCL` - `U85Z8RPqP47VfcAKL` - 散光隱形眼鏡配戴流程
- `Examination` - `mvIEkYdmzLIKXsPz1` - 眼科各項檢查 | Diagnostic instruments (VA, slit-lamp, CFP, FAF, FAG, ICG, OCT, prism), clinical findings (macular hole, LMH, Roth spot, CWS, MNV, glaukomflecken), tissue biopsy, ERG
  - `Instruments` - `uDrK7VpnP7nKpbyIR` - 診斷儀器
    - `Visual Acuity Testing` - `ggowA35wPnLjqtSDk` - 視力測試
    - `Photostress Test` - `x7ZySWGLZ9Wn9lb8O` - 光調適測試
    - `Worth 4 Dot` - `7KYjwbaq1hcrdSfHU` - 雙眼視功能
    - `CFP` - `HY6BRN0PxkF27T8uH` - 彩色眼底攝影
    - `Infrared` - `GP6fMWudhmcroDnrV` - 紅外線攝影
    - `Red free` - `DVTtlFOQX9tITWlFU` - 綠光濾鏡檢查血管
    - `Cobolt` - `Zv7Qq9psg5UQZVKBr` - 藍光看神經纖維層
    - `Prism` - `NUJllNpHGKKLfSPhS` - 稜鏡檢查
    - `FAF` - `NStJ0YtQx1jk9MbF5` - 自體螢光
    - `FAG` - `A2y33rfDXgGnoJPvL` - 螢光血管造影
    - `ICG` - `Sq0ud6kPAd3g1BKOc` - 吲哚青綠造影
    - `OCT` - `NqAowkwZsWRZtcoNA` - 光學相干斷層掃描
    - `Slit-lamp` - `0OPrdrhZozUYf4g5n` - 裂隙燈
  - `Findings` - `q13MzZLW7qqXI8VoC` - 臨床發現
    - `Macular hole` - `4VsYAVyAYBHSytxr8` - 黃斑裂孔
    - `Lamellar Macular Holes (LMH)` - `aKjD37OVU27lZu4YY` - 板層黃斑裂孔
    - `Roth spot` - `IE7Y40ShOVjWiPSu5` - 羅斯斑 (白心出血)
    - `Cotton wool spot (CWS)` - `NwSIWmO79X3cLyDaM` - 棉絮狀斑
    - `Degenerative lamellar holes (DLH)` - `M4y64gzrBXXVSdRHX` - 退化性板層裂孔
    - `Disorders of the vitreoretinal interface` - `HF97yHRR6gyTw5Pyt` - 玻璃體視網膜介面疾病
    - `Critical Flicker Frequency` - `B8XkfPfbgmyJoD3VF` - 臨界閃爍頻率
    - `Glaukomflecken` - `iHkJMQwC2x3kZGZ5g` - 青光眼斑
    - `Macular Neovascularization (MNV)` - `ZlFDwRLtKE6BtEf1K` - 黃斑部新生血管
  - `Tissue specimen processing` - `ysVQc0seCgvIMlSXY` - 切片處理與病理染色
  - `Retinal examination` - `GQ6xMETJQc5HuoRcG` - 視網膜電生理檢查
- `Common presentation` - `5CwJCcEZY38vm4dtb` - 常見臨床表現 | Leading causes of blindness (cataract, glaucoma, AMD, DR), decreased vision DDx, sudden painless vision loss, optic neuropathy subtypes, photopsias, acutely inflamed orbit
  - `Leading cause of blindness` - `dtNfDVu4ZzdsqiZ5C` - 致盲主因，區分不同呈現
      - `fPIuWD9Gilh7Fncl0`
      - `fR9kuaUXJsv07uqUP`
      - `E3cybGp1J44GaCWxu`
  - `Decreased vision` - `OHUckvVjjEVkNtubv` - 視力下降
    - `Vision loss lasting longer than 24 hrs` - `vyYtJCJb32AhN07Xc`
      - `Sudden, painless` - `6gVTvcz0FYByRDbDL`
        - `Optic neuropathy (ON)` - `hVqvJagr06fyOaTBD` - 視神經病變
          - `Demyelinating ON` - `7vRgAy5lOeONuLqk2`
          - `Ischemic ON (ION)` - `jBj4vND8gEYdemjJ2`
          - `Inflammatory ON` - `3siXnOSW7uYIR6mzV`
          - `Infiltrative ON` - `RF5uwpZHU1tHu6DcH`
          - `Compressive ON` - `BmXeq1WbVPGt0fch3`
          - `Hereditary ON` - `ZD04zNSr8YEb0MWXW`
          - `Toxic-nutritional ON` - `3rLwtB4F91MZ6xEBF`
          - `Radiation ON (RON)` - `hff58m7bI0zo8BDo5`
          - `Traumatic ON` - `xEXJiBZhFCnXuIYcH`
          - `Paraneoplastic ON` - `seJNKjhsqdNbMNLax`
  - `Photopsias` - `HcvFsCZkNbRXnf7ko` - 閃光感
  - `Acutely inflamed orbit` - `qrsV8cDoSs7yiKNmW` - 急性軌道發炎
- `External disease` - `TtzBhK6lHH71f8XQF` - 外眼與軌道疾病 | Orbit & adnexa: 6P's evaluation, TED (Graves), pseudotumor, IOIS, orbital tumors (rhabdomyosarcoma, uveal melanoma, cavernous hemangioma, lymphoma, metastatic), sinusitis-induced ON, hordeolum/chalazion, trauma, conjunctivitis, blepharoplasty, evisceration, enucleation
  - `Evaluation` - `CSiJBnpwFs2Y2kiko` - 6P's 評估
  - `TED` - `dl8odBjfOzd13whpP` - 甲狀腺眼疾
  - `Pseudotumor` - `nMC501IdR2ZC1PBOt` - 假性腫瘤
  - `IOIS` - `cPY33QXwkRNiI5pZo` - 特發性軌道發炎
  - `Orbital tumor` - `MQuRP1pdyFxcjeZHz` - 眼眶腫瘤
    - `Dermatoid and epidermoid cyst` - `8GOXnft1wGb93fjqM` - 皮樣囊腫與表皮樣囊腫
    - `Rhabdomyoscaroma` - `LotsxqQHaGp3TJ776` - 橫紋肌肉瘤
    - `Uveal Melanoma` - `cucxc65xDHABz84zG` - 葡萄膜黑色素瘤
    - `Vascular tumor` - `k96UlivHB74Ev7uKn` - 血管腫瘤
    - `Metastatic tumor` - `2OkUUwbbYkctydqi9` - 轉移性腫瘤
    - `Cavernous hemangioma` - `xI0nhshzdkbRlIfEt` - 海綿狀血管瘤
    - `Orbital adnexal lymphoma` - `t66sbeBX2O1ZJxoSU` - 眼眶附屬器淋巴瘤
    - `Cyberknife Radiotherapy` - `msltpTYbUFcrDvuZ9` - 電腦刀放射治療
  - `Sinusitis-Induced ON` - `StXU9R2BTeuhd8R0V` - 鼻竇炎引發視神經病變
  - `Hordeolum/Chalazion` - `wUbq1MQGALkLEM4Hl` - 針眼與霰粒腫
  - `Trauma` - `tChLljptHhLu7W1vB` - 眼外傷
  - `Conjunctivitis` - `lsd8746ldfqr1GTlk` - 結膜炎
  - `Blepharoplasty` - `OfeAb9z9k8a3aMT4q` - 眼瞼成形術
  - `Eviscleration` - `N2k370V83anJC3jgN` - 眼球內容剜出術
  - `Enucleation` - `rAPaYMUBcTsyO3slp` - 眼球摘除術
- `Cornea` - `W7KYjX2Q6Z722xbS8` - 角膜醫學 | Refraction data (diopter, curvature), astigmatism (WTR/ATR), 5-layer anatomy (540-560μm), topography, pachymetry, specular microscopy, corneal findings, HSV keratitis, corneal dystrophy, transplantation (DALK, DSAEK, PK), LASIK, MSC injection, exosome research
  - `驗光資料` - `48QCw843pG7B5O2Af` - 角膜聚光度與曲率
  - `Astigmatism` - `lybVU44Jay7QWIAjv` - 散光分類 (WTR/ATR)
  - `Anatomy` - `Nemp9tD7cqC0zX79P` - 角膜五層結構與厚度
  - `Examination` - `nc48KPxQgPoz3kQZW` - 下含地形圖、厚度儀、內皮鏡
  - `Corneal findings` - `b4CGkJmF8fmgKZO2f` - 角膜發現病灶
  - `Disease` - `vTniKG4Auouo4KBXz` - 皰疹性眼疾、角膜營養不良
  - `Surgery` - `9yubujiD7SHpjiSAh` - 角膜手術 (Transplantation/LASIK)
  - `MSC` - `WbWeHNnqWHbCENjPN` - 間質幹細胞注射研究
  - `Smartphone diagnosis` - `4oDmv3j4QgGEgTryy` - 智慧型手機診斷研究
  - `DALK rejection` - `gmV2iWCKISsNOQWJo` - 移植排斥研究
  - `Endothelial spots` - `GTqIxGRy3S9FIB4nm` - 內皮黑點研究
  - `Exosome` - `3Cd0RumOpIphFn1mC` - 外泌體應用
- `Lens and Cataract` - `OgQr7FNqhHLU0qlUs` - 水晶體與白內障 | NHI reimbursement criteria (age≥55, VA≤0.5), lens structure, cataract types (age-related, childhood, secondary), slit-lamp grading (NS, CO, PSC), IOL power formulas, phacoemulsification, IOL choices (multifocal, aspheric), complications (TASS, endophthalmitis)
  - `健保給付` - `84DFC5x0FT4EwtNkM` - 健保給付條件
  - `Lens` - `ICWHU3vfJh26W3uqD` - 水晶體結構與疾病
  - `Blindness prevalence` - `ZEGtUP2TjS2BjszDd` - 盲點流行率
  - `Type` - `Vsd2AO397FeC7AUPA` - 白內障分類
  - `Examination` - `IjbDcYJ3djgErhZNR` - 裂隙燈白內障等級
  - `IOL Formula` - `XwYiuzSlFtzHDXezA` - 人工水晶體算式
  - `Surgery` - `ne6xBYNBcxFmeUelR` - Phaco 技術與程序
  - `Choices of IOL` - `m0803hc9kSyUKOxj9` - IOL 選擇 (多焦點、非球面)
  - `Complication` - `G2cb9Qx8N1UOpqqz5` - 術後併發症 (TASS, Endophthalmitis)
- `Glaucoma` - `NG49CdruX4zDzD2Rq` - 青光眼醫學 | IOP & aqueous humor dynamics, ocular hypertension (>21mmHg), NTG, glaucoma types (POAG, PACG, NVG, pseudophakic, aphakic, uveitic), GON, OPP, gonioscopy, visual field, tonometry, acute angle closure emergency, medical/laser/surgical management
  - `IOP` - `0OxAYRxC7CWAiDBFo` - 眼壓與房水循環
  - `Ocular Hypertension` - `J6tCobDYHwxmKoihr` - 高眼壓症
  - `Normal-Tension Glaucoma` - `mGwFn1RvewBJAxsUE` - 正常眼壓性青光眼
  - `Definition` - `6cDSqnAQjQT6sMG9Y` - 青光眼定義
  - `Risk factor` - `u44nLjfhC9JJSTS8g` - 險因素
  - `Epidemiology` - `i59jd65xpjjUI1TvL` - 流行病學
  - `Type` - `pgwcCeXsB2TXT8uRr` - 青光眼分類
  - `NVG` - `MmiFkaUw38rmSEbol` - 新生血管性青光眼
  - `Pseudophakic G` - `Uu8fU95csHi3YiA7A` - 偽水晶體青光眼
  - `Aphakic G` - `SCCgtZ30sFapfyxP8` - 無水晶體青光眼
  - `GON` - `qXca2aXUAprAC74HA` - 視神經病變
  - `Uveitis G` - `D9RDYAOOZhab4YPcp` - 葡萄膜炎性青光眼
  - `OPP` - `O7GYiVwufB18dSIXW` - 眼溢壓相關
  - `Examination` - `7MKyxDX7Ppb4zWRWA` - 診斷與影像 (Gonioscopy, VF)
  - `Emergency` - `SXlTBl08afB5dsinZ` - 急性發作
  - `Management` - `2sB4jtF872mBvPvUt` - 藥物、雷射、手術治療
- `Iris` - `HI4spvrHQIjuw5sua` - 虹膜 | Iris structure (stroma, sphincter/dilator muscle, pigmented epithelium), iris bombe, seclusio pupillae, aniridia
  - `Structure` - `KKiCFORB8IAkIRVef` - 結構
  - `Disease` - `HagcDbCnyOcleFa0H` - 疾病
- `Uveitis` - `kl4ItbmoLAmfqce7L` - 葡萄膜炎 | Patient evaluation, pediatric uveitis, anterior uveitis (AAU, CMV, JIA, Fuchs), panuveitis (bilateral, multi-segment), posterior uveitis (toxoplasmosis), ocular nodules, post-operative uveitis
  - `Patient evaluation` - `A0qAgL6nKhCEIQxik` - 病患評估
  - `Pediatric Uveitis` - `5sq9mBD0IZpnfsLV1` - 兒童葡萄膜炎
  - `Anterior Uveitis` - `hzeM86Lq7RVd8hlMg` - 前葡萄膜炎
  - `Panuveitis` - `qiT6CepzAieLr1Cg1` - 全葡萄膜炎
  - `Posterior Uveitis` - `rqH8FD6wDx0evUqdL` - 後葡萄膜炎
  - `Ocular nodules` - `XRWKTuLMt9D0ueKfB` - 結節
  - `Post-operative uveitis` - `ckuSbqiz3QelHIEUT` - 術後發炎
- `Retina` - `axP0MADOJiMeJBf76` - 視網膜醫學 | Retinal anatomy (vitreous, circulation, blood-retinal barrier, choroid), CSNB, hemorrhage types (subretinal, subRPE, dot-blot, flame, suprachoroidal), vitreous disease (floaters, Terson, asteroid hyalosis, PVD), Purtscher retinopathy, RVO (CRVO/BRVO), amaurosis fugax, OIS, AMD, CSCR, pachychoroid, DR, RD, ERM, macular dystrophy (BVMD), CMV retinitis, ARN, PORN, vitreoretinal surgery
  - `Anatomy` - `QDmOATkudDt3ycjV6` - 解剖結構
  - `CSNB` - `LSQYVZV0SGmDllhx8` - 先天靜止夜盲
  - `Hemorrhage` - `nkDvk6gIjEmCGfqrw` - 急性出血
  - `Vitreous disease` - `e3eKuKuqsrtEpSnAE` - 玻璃體疾病
  - `Purtscher` - `7XTZH6hJvgSfhXpgt` - Purtscher 視網膜病變
  - `Common retinopathy` - `bawUcQC3pFtbLqHKh` - 常見網膜病變
  - `RVO` - `X2ZfjvomoZAMgjnc3` - 視網膜靜脈阻塞
  - `Amaurosis fugax` - `pUNCu7me4AtOGczMI` - 一過性黑矇
  - `OIS` - `tNR2mrtTOXu7vg6R1` - 眼缺血症候群
  - `AMD` - `W8cgUHLD04CXxZsRO` - 老年變性
  - `Cuticular drusen` - `CKNrRljbHsAgGyqyn` - 玻璃疣
  - `CSCR` - `cbSLwe24c6IzRXVJh` - 中心性漿液網膜病變
  - `Pattern dystrophy` - `9WIkaJCnYulBJ5pOv` - 特徵性營養不良
  - `Hypertensive` - `mPkcRyWB6JR9i2GMC` - 壓性網膜病變
  - `RD` - `NDKURLm9BJ1rxP40m` - 網膜剝離
  - `Optic neuritis` - `sLG9u48DKIM2cMqHi` - 視神經炎 (Retina 分支下項目)
  - `Diabetic Retinopathy` - `qJvR6dYYkOFmpi5vl` - 糖尿病網膜病變
  - `PVD` - `y0ksP7MCH0VgebRdw` - 玻璃體後剝離
  - `ERM` - `TL9OzfmvGTJGNarz3` - 黃斑皺褶
  - `Retinal Breaks` - `k9shhk5KLsRuXM2YL` - 網膜裂孔
  - `Macular dystrophy` - `4tloqU6bjXv1mfpHO` - 黃斑營養不良
  - `BVMD` - `Ysd2dY9V4rpmsms1B` - Best 氏症
  - `Infiltration` - `YU01Z1eIAvOG1NjM6` - 浸潤
  - `PNS` - `APSZU5fSvKaj3f6Cq` - 副腫瘤症候群
  - `Pachychoroid` - `ha2F8E1VJnjZdlZ2N` - 厚脈絡膜頻譜
  - `Leukemic` - `zXqDhUJR2YVdopFSb` - 白血病病變
  - `CMV Retinitis` - `q6TT91BqZau7UnpOY` - 巨細胞病毒
  - `ARN` - `YVvJV7wXiOqLDHyGv` - 急性網膜壞死
  - `PORN` - `8Z0vGo6MO86qN9AZ0` - 進行性外網膜壞死
  - `Candidiasis` - `A1vKzBdplv4kF4SCO` - 念珠菌感染
  - `Radiation` - `KJCfWYQ70BG1B0CdJ` - 放射線病變
  - `Vitreoretinal surgery` - `5fPulWTSwO6XgTZIl` - 網膜玻璃體手術
- `Neuro-ophthalmology` - `JC3yhtfC24Gv1sMCY` - 神經眼科 | Visual pathway & field defects, optic neuropathy (ethambutol, gaze-evoked amaurosis), Tolosa-Hunt syndrome, CN III/IV/VII palsy, oculosympathetic pathway (Horner), CN VII overactivity (BEB, hemifacial spasm), cavernous sinus & orbital apex syndromes, TVL, diplopia, ptosis, CIDP, Miller Fisher, dorsal midbrain, NMO, MS, INO, one-and-a-half, reflexes, migraine, papilledema, ophthalmoplegia
  - `Visual Pathway` - `mqflesMq7Kdc1RMCD` - 視神經路徑
  - `Optic nerve abnormality` - `gmgjVGvmSsvR5YhpY` - 視神經異常
  - `Tolosa-Hunt` - `HGjJMbjXfCwWNX47H` - Tolosa-Hunt 症候群
  - `CN III palsy` - `FmoqlKBukwBlfRIWU` - 動眼神經麻痺
  - `Oculosympathetic` - `qJQCjC7PzoY6iA8Bb` - 交感神經路徑 (Horner)
  - `CN IV palsy` - `1mP4d7lQOGaeebcot` - 滑車神經麻痺
  - `CN VII palsy` - `o3ywldToxOUl5Dlhu` - 顏面神經麻痺 (Bell)
  - `CN VII overactivity` - `pRylO0npDUmF9fXKM` - 顏面神經過度活躍
  - `Cavernous Sinus` - `6kXFUc4JPdRR572wL` - 海綿竇症候群
  - `Orbital Apex` - `l21AVYx2IbrwQFDWd` - 視神經尖症候群
  - `TVL` - `U6nFEGK2mJBMvUeVk` - 一過性黑矇
  - `Diplopia` - `in8OgDATbvBXeND43` - 複視
  - `Ptosis` - `k3wIv4wq7wdeW03VL` - 下垂
  - `CIDP` - `aPu7szfx1lI5nYp7z` - 慢性脫髓鞘多神經病變
  - `Miller Fisher` - `PRvEgLjwBv4wsakYL` - Miller Fisher 症候群
  - `Dorsal Midbrain` - `ZTKfRAaeHtX9GNLA0` - 背側中腦症候群
  - `Synkinesis` - `77UGrrrKOE4wpMNOx` - 異常再聯動
  - `NMO` - `byjnIo6ZrAcoFzkEN` - 視神經脊髓炎
  - `MS` - `FbaGpFR1Ak5gCppCq` - 多發性硬化症
  - `INO` - `5GvBvKcwQAAQzSbTn` - 核間性眼肌麻痺
  - `One-and-a-half` - `J059o7Qv7LujZbZfk` - 一個半症候群
  - `Reflexes` - `5MrLLgWmMjvrFLDOf` - 各類反射 (瞳孔、角膜)
  - `Migraine` - `C19lRnwpAHl4fCcm3` - 偏頭痛
  - `Papilledema` - `jEsPADSaZD8xZGzhE` - 視乳頭水腫
  - `Pseudopapilledema` - `Tcxt5Acw3u67JXwFC` - 假性水腫
  - `Optic disc edema` - `pGwzhJpjVe6jnzVXu` - 視盤水腫 (無 IICP)
  - `Ophthalmoplegia` - `4qWojdwOmwK2u61UF` - 眼肌麻痺
  - `Binocular diplopia` - `XddNgrjAbDBD95JgJ` - 雙眼複視
- `Systematic` - `rGexWin57k2Yp7LxY` - 系統性眼科表現 | Systemic diseases with ocular manifestation: immunotherapy irAE (uveitis, vitritis, retinal vasculitis), Kikuchi-Fujimoto disease, phakomatoses
  - `Immunotherapy irAE` - `WxlDBqi5SREzgVD0E` - 免疫治療副作用
  - `Kikuchi-Fujimoto` - `f2NJkFwNR0aJqg31t` - 菊池病
  - `Phakomatoses` - `vx75LRBPJQ3wrmQyc` - 母斑症
- `Pediatric ophthalmology` - `bI7e9zIlyeyoPzBDV` - 小兒眼科 | Pediatric red eye, strabismus, tearing (congenital glaucoma, epiblepharon), amblyopia (visual development, critical period), leukocoria, congenital corneal opacities, inherited eye diseases, fetal vessels (PFV), pediatric trauma/glaucoma, hyperopia, nanophthalmos, malignancy, albinism, DM, Marfan, nystagmus
  - `Red eye/swelling` - `Cjl76LiUzpewPBahD` - 紅腫
  - `Strabismus` - `c2NDZR6Wfy9bsBiXM` - 斜視
  - `Tearing` - `mENsrhGSkmqzX2h2h` - 流淚
  - `Amblyopia` - `SsWWksaakpmWMLlM1` - 弱視
  - `Leukocoria` - `FHhDDsL9NSwZ56az7` - 白瞳症
  - `Congenital Corneal Opacities` - `RcIgE14SNPqqViyqB` - 先天角膜白斑
  - `Inherited eye diseases` - `pcpsWZTJWxjtpWWEg` - 遺傳性疾病
  - `Fetal vessels` - `tGUm0rLX7droQjHne` - 胎兒血管殘留
  - `Trauma` - `rlMuq6pLjGc1GG8rM` - 兒童外傷
  - `Glaucoma` - `6NlQdNvbM8hlXOpXe` - 兒童青光眼
  - `Hyperopia` - `Qq8q6p1sp2xrkjjAb` - 遠視
  - `Nanophthalmos` - `KCGGXnySV4wzOY0Gi` - 納米眼
  - `Malignancy` - `oB1Lsmh0VKkFzBiSd` - 惡性腫瘤
  - `Albinism` - `aQ81e78UKiTRG5D5p` - 白化症
  - `Diabetes` - `CV6hBHg9VzMU7N45K` - 糖尿病
  - `Infection` - `3xbGos8qJz8A2mmvM` - 感染
  - `Marfan` - `FNw8z8v8JTyujkbIC` - 馬凡氏症候群
  - `Nystagmus` - `SDhm6L73QmFm7CrHA` - 眼球震顫
- `Ophthamlology medication` - `9o9I65kDVTQpu32Ob` - 眼科藥物 | Blood-ocular barrier, glaucoma meds (combination, inflow/outflow), mydriatics & cycloplegics (phenylephrine, tropicamide, atropine, cyclopentolate), allergic disease, anti-inflammation, uveitis meds, antibiotics, antiviral, antifungal, artificial tears, diagnostic agents (Alcaine), drug side effects/toxicity
  - `Blood-ocular barrier` - `feM7ebDxKOG9GipA2` - 血眼屏障
  - `Glaucoma Medication` - `q4n8fH8ZJsU4o0gUB` - 青光眼用藥
  - `Mydriatics & cycloplegics` - `AIfOkXDcBWWzaPC87` - 散瞳藥物
  - `Allergic disease` - `dmWXEs9yVYIRL9pSI` - 過敏藥物
  - `Anti-inflammation` - `EO3Xt4uWYz1j9L7bn` - 抗發炎
  - `Uveitis Medication` - `geOefWc6yNtbMOP9F` - 葡萄膜炎藥物
  - `Anti-bacterial` - `c69TlSzDv9JHO2ivJ` - 抗生素
  - `Antiviral` - `d91kZ2nazfi3oK3MG` - 抗病毒
  - `Anti-fungal` - `ZGILqJhEKHJC7c09D` - 抗黴菌
  - `Artificial tear` - `PaHnaSh1XCBqEh1ZD` - 人工淚液
  - `Other` - `RLPCBten3CJtLonDS` - 診斷用藥 (Alcaine 等)
  - `Side effect` - `yBcLZXfaHSVTrQLSb` - 藥物副作用 (毒性)
- `GVHD` - `2KIH8sENSdJ4x3jKk` - GVHD | Graft-versus-host disease ocular involvement (cornea, conjunctiva, lacrimal gland, meibomian gland), onset 6-9mo post-BMT, chronic GVHD, treatment (artificial tears, autologous serum, cyclosporin, tacrolimus)
- `Case discussion` - `re3th39xJtgK9Z42Y` - 案例討論 | Morning & subspecialty case rounds: real clinical cases with CC/PI/impression/management, covering diplopia, orbital cellulitis, keratitis (HSV, microsporidia), ACG, RD, chemical burns, CSCR, VKH, Tolosa-Hunt, cavernous sinus syndrome, ERM, perimetry
- `Meta-analysis` - `t70gU6mbwxvCe23N8` - 薈萃分析入口 | Entry point for meta-analysis methodology and evidence-based ophthalmology references

## Recommended workflow

1. Read root for global orientation:
   a. while using remnote-cli `remnote-cli read Da8SsKWwuA9doqpsp --include-content structured --depth 1 --child-limit 500`
   b. while using remnote-mcp `call remnote_search Da8SsKWwuA9doqpsp include-content structured depth 1 child-limit 500`
2. Pick the best top-level branch ID from the map.
3. Read that branch shallowly first:
   a. while using remnote-cli `remnote-cli read <branch-id> --depth 1 --child-limit 500`
   b. while using remnote-mcp `call remnote_search <branch-id> include-content structured depth 1 child-limit 500`
   c. if searching for a specific sub-topic by title under a resolved parent ID: `remnote-cli search "Subtopic Title" --parent-id <parent-id>`
4. Descend deeper only in the selected subtree.
5. If multiple branches seem relevant, read 2-3 candidate branches shallowly, then ask a focused clarification.
6. **Map Update Rule**: If a new topic is written and its `parentID` already exists in the Top-level map, and sub-items are already listed under that ID (indicating it's an important annotated branch), you must synchronize this new topic (Title, ID, Hint) into the `SKILL.md` map for future navigation reference.