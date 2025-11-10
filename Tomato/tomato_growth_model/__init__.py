"""
番茄（秋季）生长模型
基于8米单棚试验数据开发的完整生长模拟系统

包含三大核心模块：
1. 生长发育模型：积温、LAI、干物质积累
2. 水肥运输模型：EC值、钾吸收、根系吸水
3. 病虫害预警模型：灰霉病、白粉虱预警
"""

__version__ = "1.0.0"
__author__ = "Tomato Growth Model Team"

try:
    from .config import ModelConfig
    from .growth_model import GrowthModel
    from .water_fertilizer_model import WaterFertilizerModel
    from .pest_disease_model import PestDiseaseModel
    from .main import TomatoGrowthSimulator
except ImportError:
    # 如果相对导入失败（例如直接运行），使用绝对导入
    from tomato_growth_model.config import ModelConfig
    from tomato_growth_model.growth_model import GrowthModel
    from tomato_growth_model.water_fertilizer_model import WaterFertilizerModel
    from tomato_growth_model.pest_disease_model import PestDiseaseModel
    from tomato_growth_model.main import TomatoGrowthSimulator

__all__ = [
    'ModelConfig',
    'GrowthModel',
    'WaterFertilizerModel',
    'PestDiseaseModel',
    'TomatoGrowthSimulator'
]


