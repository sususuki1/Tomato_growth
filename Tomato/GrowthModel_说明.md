# 生长发育模型（growth_model.py）实现说明

本文档说明 `tomato_growth_model/growth_model.py` 的设计与实现，标注核心状态量、计算流程、使用的公式与参数来源，并给出当前实现的功能清单与默认假设。

---

## 1. 模块定位与数据流

- 模块职责：按天推进番茄植株的生长发育，输出积温、生育期、LAI、净光合与干物质累积、器官分配与坐果率等结果；供主模拟器 `TomatoGrowthSimulator` 聚合。
- 输入驱动：天气（白天温度、夜温、PAR、CO₂），以及配置参数 `ModelConfig`。
- 输出：每日状态字典（day、stage、GDD、LAI、各器官干物质、坐果率等）。

主要状态变量：
- `day`（定植后天数）、`GDD/ daily_GDD`（积温/日积温）、`stage`（生育期）、`LAI`、
  `dry_matter_*`（总/叶/茎/果/根）与 `fruit_set_rate`（坐果率）。

---

## 2. 参数与来源（统一在 config.py 定义）

- 温度阈值与最适：`T_base=10℃`，`T_opt_day=23℃`，`T_opt_night=17℃`
  - 来源：技术手册 + 原始校准报告（秋季8米棚温控试验）
- 积温阶段修正：`GDD_corr_flowering=0.92`，`GDD_corr_fruiting=0.95`，`GDD_corr_harvest=0.98`
  - 来源：技术手册 + 原始校准报告（生育进程校准）
- 生育期积温阈值（度日）：`GDD_seedling=350`，`GDD_flowering=450`，`GDD_fruiting=800`
  - 来源：技术手册 + 数据集（生育时间序列）
- 光合量子效率：`phi=0.037 mol CO₂ / mol PAR`
  - 来源：技术手册 + 数据集（Pn-光/CO₂曲线）
- 冠层光学参数：`light_extinction_coeff=0.55`（Beer–Lambert 消光系数）
  - 来源：基础模块公式PDF（Beer–Lambert），技术手册建议范围（0.5–0.6）
- PAR 饱和/补偿：`PAR_saturation=1200 μmol m⁻² s⁻¹`，`PAR_compensation=50 μmol m⁻² s⁻¹`
  - 来源：技术手册 + 数据集（秋季光环境）
- CO₂ 响应参数（矩形双曲）：`CO2_compensation=50 ppm`，`CO2_Km=300 ppm`
  - 来源：基础模块公式PDF（直角双曲/矩形双曲）、技术手册（阈值范围）
- 暗呼吸：`leaf_resp_rate_base=0.5 g m⁻² h⁻¹`，`Q10=2.0`（代码内）
  - 来源：基础模块公式PDF（Q10 温度修正），数值经秋季条件下工程化取值
- LAI 相关：`LAI_initial=0.1`，`LAI_max=4.5`，`LAI_growth_rate=0.08 d⁻¹`
  - 来源：技术手册 + 数据集（LAI 时间序列与上限）
- 器官分配（结果期）：叶25%、茎15%、根10%、果50%
  - 来源：技术手册 + 数据集（器官干物质构成，秋季果实优先）
- 坐果率最优：`fruit_set_rate_opt=0.82`（日23℃/夜17℃），最低0.50
  - 来源：原始校准报告（温度梯度坐果实验）
- 单株占地面积：`area_per_plant=0.5 m²/株`
  - 来源：项目假设（8米棚密度经验），可根据密度试验调整

> 注：文献名缩写说明：技术手册=《番茄（秋季）生长模型技术手册》；原始校准报告=《番茄（秋季）生长模型原始校准报告》；数据集=《番茄（秋季）专属数据集报告》；基础模块公式PDF=《基础模块部分相关公式》《核心目标部分的公式》。

---

## 3. 公式与实现对应

### 3.1 积温（GDD）与分期
- 日积温：
  - 公式：`GDD_i = max(0, (T_avg - T_base)) * GDD_corr(stage)`，其中 `T_avg=(T_day+T_night)/2`
  - 代码：`calculate_GDD()`
- 生育期判定：累计 GDD 与阈值比较，按幼苗/开花/结果/采收阶段推进
  - 代码：`determine_growth_stage()`

### 3.2 冠层光截获（Beer–Lambert）
- 冠层截获率：`f_intercept = 1 - exp(-k * LAI)`，`k=light_extinction_coeff`
- 冠层 PAR：`PAR_intercept = PAR * f_intercept`
- 代码位置：`calculate_photosynthesis()` 开头

### 3.3 CO₂ 响应（矩形双曲）
- `f_CO2 = (CO2 - C0) / (Km + (CO2 - C0))`，下限 0
- 代码位置：`calculate_photosynthesis()` 中部

### 3.4 光合日量与换算
- 日 PAR（mol m⁻² d⁻¹）：`PAR_daily = PAR_intercept * 3600 * 12 / 1e6`
- 量子效率：`Gross_CO2 = phi * PAR_daily * f_temp * f_CO2`
- CO₂→干物质：`Gross_DM = Gross_CO2 * 30 (g mol⁻¹)`
- 代码位置：`calculate_photosynthesis()`

### 3.5 温度响应与暗呼吸（Q10）
- 温度响应（f_temp）：最适温度附近上升、超最适缓降（分段线性，技术手册建议）
- 暗呼吸（面积基准）：`R = leaf_resp_rate_base * 24 * Q10^((T - Tref)/10)`，`Tref=20℃`
- 代码位置：`calculate_photosynthesis()`

### 3.6 群体净光合与转株
- 净光合：`Net = Gross_DM - R`（单位：g m⁻² d⁻¹）
- 单株：`Net_plant = Net * area_per_plant`
- 代码位置：`calculate_photosynthesis()` 末尾

### 3.7 LAI 动态
- 幼苗期：指数增长 `LAI = LAI0 * exp(k * day)`（上限约 1.5）
- 开花/结果期：Sigmoid 随积温推进（分别趋于 3.0 与 `LAI_max`）
- 采收期：轻微下降（叶片老化）
- 代码：`calculate_LAI()`

### 3.8 干物质分配（器官）
- 日干物质 `daily_dry_matter` 由净光合给出，按阶段比例分配至叶/茎/根/果
- 代码：`calculate_dry_matter_allocation()` + `daily_update()` 中累加

### 3.9 坐果率（温度驱动）
- 最优：日 23℃ / 夜 17℃ → `0.82`；偏离分段线性降低（<15℃或>28℃显著下降）
- 代码：`calculate_fruit_set_rate()`

---

## 4. 计算流程（每日）
1) `day+=1`  
2) 计算 `daily_GDD` 并累加至 `GDD`  
3) 生育期切换（阈值法）并计算新 `LAI`  
4) 根据 Beer–Lambert 拦截后 PAR、CO₂ 矩形双曲、温度响应与 Q10 呼吸，得到净光合 → 日干物质  
5) 按阶段进行器官分配、累计各器官干物质与总干物质  
6) 根据温度计算坐果率（开花/结果/采收期有效）  
7) 产出当日状态字典

---

## 5. 当前功能清单
- 积温推进 + 生育期判定（含阶段修正系数）
- LAI 动态（幼苗指数 + 阶段 Sigmoid + 采收期老化）
- 冠层光截获（Beer–Lambert）与 CO₂ 矩形双曲响应
- 群体净光合（量子效率、日照时长换算、Q10 暗呼吸）→ 单株日干物质
- 器官分配并累计（叶/茎/根/果），总干物质同步更新
- 温度驱动的坐果率（最优温度范围 + 偏离衰减）
- 对外接口：`daily_update()`、`reset()`、`get_growth_summary()`

---

## 6. 默认假设与可调参数
- 日有效光期 12 小时，可在需要时外部传入更真实的逐日积分 PAR（或扩展为逐小时）
- 单株占地面积 `area_per_plant=0.5 m²`；可与密度试验联动（LAI ~ a×D^b）
- 消光系数 `k=0.55`、CO₂ 参数（C0、Km）与呼吸基准可按品种/棚型微调
- CO₂→干物质换算 30 g mol⁻¹ 为常见工程近似，可按碳含量进一步修正

---

## 7. 与文献/资料的映射
- 《基础模块部分相关公式》《核心目标部分的公式》
  - Beer–Lambert 冠层拦截、CO₂ 直角/矩形双曲响应、Q10 暗呼吸、GDD 定义与阶段模型、LAI 常见函数、产量与能量关系等
- 《番茄（秋季）生长模型技术手册》
  - 秋季 8 米棚参数范围：T_base/T_opt、φ、CO₂ 最优窗口、PAR 饱和/补偿、LAI 上限与阶段划分、器官分配与坐果率阈值
- 《番茄（秋季）生长模型原始校准报告》
  - 温度梯度坐果试验、阶段 GDD 修正系数、部分生育历时
- 《番茄（秋季）专属数据集报告》
  - Pn-光/CO₂ 曲线、LAI/时间序列与取值范围、秋季环境分布统计，用于参数落地校准

