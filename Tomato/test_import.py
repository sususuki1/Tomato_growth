"""
测试导入是否正常
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 60)
print("测试番茄生长模型导入")
print("=" * 60)

try:
    print("\n1. 测试导入配置模块...")
    from tomato_growth_model.config import ModelConfig, GLOBAL_CONFIG
    print("   [OK] 配置模块导入成功")
    
    print("\n2. 测试导入生长发育模型...")
    from tomato_growth_model.growth_model import GrowthModel
    print("   [OK] 生长发育模型导入成功")
    
    print("\n3. 测试导入水肥运输模型...")
    from tomato_growth_model.water_fertilizer_model import WaterFertilizerModel
    print("   [OK] 水肥运输模型导入成功")
    
    print("\n4. 测试导入病虫害预警模型...")
    from tomato_growth_model.pest_disease_model import PestDiseaseModel
    print("   [OK] 病虫害预警模型导入成功")
    
    print("\n5. 测试导入主运行模块...")
    from tomato_growth_model.main import TomatoGrowthSimulator
    print("   [OK] 主运行模块导入成功")
    
    print("\n6. 测试从包导入...")
    from tomato_growth_model import (
        ModelConfig,
        GrowthModel,
        WaterFertilizerModel,
        PestDiseaseModel,
        TomatoGrowthSimulator
    )
    print("   [OK] 从包导入成功")
    
    print("\n7. 测试创建模型实例...")
    config = ModelConfig()
    growth_model = GrowthModel(config)
    water_fertilizer_model = WaterFertilizerModel(config)
    pest_disease_model = PestDiseaseModel(config)
    simulator = TomatoGrowthSimulator(config)
    print("   [OK] 模型实例创建成功")
    
    print("\n" + "=" * 60)
    print("所有测试通过！模型可以正常使用。")
    print("=" * 60)
    
except ImportError as e:
    print(f"\n[错误] 导入错误: {e}")
    print("\n请确保:")
    print("1. 在项目根目录运行此脚本")
    print("2. 已安装所有依赖包 (pip install -r requirements.txt)")
    print("3. 项目结构完整")
    sys.exit(1)
except Exception as e:
    print(f"\n[错误] 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

