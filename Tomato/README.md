# 番茄（秋季）生长模型

基于8米单棚试验数据开发的完整番茄生长模拟系统，包含生长发育、水肥运输和病虫害预警三大核心模块。

## 功能特点

- **生长发育模型**：模拟积温积累、LAI动态、干物质积累与果实分配
- **水肥运输模型**：模拟土壤EC值动态、钾元素吸收效率、根系吸水效率
- **病虫害预警模型**：实现灰霉病与白粉虱的预警与预测
- **高精度预测**：开花期误差 ≤ 2.5天，LAI模拟RMSE ≤ 0.22，灰霉病预警准确率 ≥ 88%

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 重要提示

⚠️ **请从项目根目录运行脚本，不要直接运行模块文件**

项目结构：
```
Tomato/
├── tomato_growth_model/    # 模型包
├── run_simulation.py       # 运行脚本
├── test_import.py          # 导入测试脚本
└── README.md
```

### 测试导入

首先测试导入是否正常：

```bash
python test_import.py
```

### 基本使用

```python
# 确保在项目根目录
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tomato_growth_model import TomatoGrowthSimulator

# 创建模拟器
simulator = TomatoGrowthSimulator(planting_date='2025-09-01')

# 生成示例气象数据
weather_data = simulator.generate_default_weather_data(
    start_date='2025-09-01',
    days=120
)

# 执行模拟
results = simulator.simulate(
    weather_data=weather_data,
    irrigation_frequency=2,  # 每日2次灌溉
    irrigation_amount=5.0,   # 每次5mm
    fertilizer_EC=2.15       # EC值2.15 mS/cm
)

# 获取摘要
summary = simulator.get_summary()
print(summary)

# 导出结果
simulator.export_results('results.csv', format='csv')
```

### 运行示例脚本

```bash
# 在项目根目录运行
python run_simulation.py
```

这将：
1. 生成120天的示例气象数据
2. 执行完整的生长模拟
3. 输出模拟摘要和关键指标
4. 生成可视化图表（保存为 `growth_analysis.png`）
5. 导出结果到CSV文件（`simulation_results.csv`）

## 模型参数

所有参数均来自校准报告和数据集，适配秋季8米单棚环境：

### 温度参数
- 基点温度：10℃
- 最优白天温度：23℃
- 最优夜间温度：17℃
- 积温修正系数：开花期0.92，果实期0.95，采收期0.98

### 光合参数
- 光合量子效率：0.037 mol CO₂/mol PAR
- 暗呼吸速率：0.023 g 干物质/g·h
- 最优CO₂浓度：750 ppm

### 水肥参数
- EC值范围：1.8-2.3 mS/cm
- 钾吸收峰值：1.0 g/株·d
- 土壤最优含水量：65-70% FC

### 病虫害参数
- 灰霉病触发条件：湿度≥80%，温度14-18℃
- 白粉虱世代周期：12天

## 输出结果

模拟结果包含以下关键指标：

- **生长发育**：积温、LAI、干物质量（总、叶片、茎、果实、根系）、坐果率
- **水肥状态**：土壤EC值、土壤含水量、根系吸水量、钾吸收量
- **病虫害风险**：灰霉病风险指数、白粉虱种群数量、预警信息

## 文件结构

```
tomato_growth_model/
├── __init__.py              # 包初始化
├── config.py                # 参数配置模块
├── growth_model.py           # 生长发育模型
├── water_fertilizer_model.py # 水肥运输模型
├── pest_disease_model.py    # 病虫害预警模型
└── main.py                  # 主运行模块

run_simulation.py            # 示例运行脚本
requirements.txt             # 依赖包列表
README.md                    # 说明文档
```

## 技术文档

详细的技术文档请参考：
- 《番茄（秋季）生长模型技术手册》
- 《番茄（秋季）生长模型原始校准报告》
- 《番茄（秋季）专属数据集报告》

