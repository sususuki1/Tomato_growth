"""
模型参数配置模块
所有参数均来自校准报告和数据集，适配秋季8米单棚环境
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ModelConfig:
    """番茄生长模型全局参数配置"""
    
    # ========== 温度与积温参数 ==========
    T_base: float = 10.0  # 生长基点温度 (℃)
    T_opt_day: float = 23.0  # 最优白天温度 (℃)
    T_opt_night: float = 17.0  # 最优夜间温度 (℃)
    T_min_night: float = 14.0  # 最低夜间温度 (℃)
    T_max_night: float = 19.0  # 最高夜间温度 (℃)
    
    # 积温修正系数（不同生育期）
    GDD_corr_flowering: float = 0.92  # 开花期
    GDD_corr_fruiting: float = 0.95  # 果实期
    GDD_corr_harvest: float = 0.98  # 采收期
    
    # 积温需求（度日）
    GDD_seedling: float = 350.0  # 幼苗期积温需求
    GDD_flowering: float = 450.0  # 开花期积温需求
    GDD_fruiting: float = 800.0  # 果实期积温需求
    GDD_total: float = 1600.0  # 总积温需求
    
    # ========== 光合作用参数 ==========
    phi: float = 0.037  # 光合量子效率 (mol CO₂/mol PAR)
    Rd: float = 0.023  # 暗呼吸速率 (g 干物质/g·h)
    CO2_opt: float = 750.0  # 最优CO₂浓度 (ppm)
    CO2_base: float = 400.0  # 基础CO₂浓度 (ppm)
    CO2_max: float = 800.0  # 最大有效CO₂浓度 (ppm)
    
    # 光饱和点
    PAR_saturation: float = 1200.0  # 光饱和点 (μmol/m²/s)
    PAR_compensation: float = 50.0  # 光补偿点 (μmol/m²/s)
    # 冠层光衰减（Beer–Lambert）
    light_extinction_coeff: float = 0.55  # k，作物群体消光系数（冠层光截获）
    
    # ========== 水肥参数 ==========
    # EC值阈值
    EC_min: float = 1.8  # 最小EC值 (mS/cm)
    EC_max: float = 2.3  # 最大EC值 (mS/cm)
    EC_opt: float = 2.15  # 最优EC值 (mS/cm)
    
    # 钾吸收参数（Michaelis-Menten动力学）
    K_uptake_Vmax: float = 7.5  # 最大吸收速率 (g/株·周)
    K_uptake_Km: float = 2.0  # 半饱和常数
    K_uptake_peak: float = 1.0  # 峰值吸收量 (g/株·d)
    
    # 土壤含水量
    SWC_opt_min: float = 0.65  # 最优含水量下限 (FC)
    SWC_opt_max: float = 0.70  # 最优含水量上限 (FC)
    SWC_min: float = 0.50  # 最小含水量 (FC)
    SWC_max: float = 0.75  # 最大含水量 (FC)
    
    # 根系吸水效率
    root_water_uptake_base: float = 0.85  # 基础根系吸水效率
    root_water_uptake_EC_penalty: float = 0.20  # EC过高时的效率下降比例
    
    # ========== 病虫害参数 ==========
    # 灰霉病
    gray_mold_humidity_threshold: float = 80.0  # 触发湿度阈值 (%)
    gray_mold_temp_min: float = 14.0  # 适宜温度下限 (℃)
    gray_mold_temp_max: float = 18.0  # 适宜温度上限 (℃)
    gray_mold_risk_base: float = 0.1  # 基础风险值
    gray_mold_risk_growth_rate: float = 0.15  # 风险增长速率
    
    # 白粉虱
    whitefly_temp_opt_min: float = 20.0  # 最适温度下限 (℃)
    whitefly_temp_opt_max: float = 25.0  # 最适温度上限 (℃)
    whitefly_generation_cycle: float = 12.0  # 世代周期 (天)
    whitefly_base_population: float = 10.0  # 基础种群数量
    
    # ========== 生长参数 ==========
    # LAI参数
    LAI_max: float = 4.5  # 最大LAI
    LAI_initial: float = 0.1  # 初始LAI
    LAI_growth_rate: float = 0.08  # LAI增长率 (1/天)
    area_per_plant: float = 0.5  # 每株占地面积 (m²/株)
    
    # 干物质分配（结果期）
    DM_leaf_ratio: float = 0.25  # 叶片干物质分配比例
    DM_stem_ratio: float = 0.15  # 茎干物质分配比例
    DM_fruit_ratio: float = 0.50  # 果实干物质分配比例（结果期）
    DM_root_ratio: float = 0.10  # 根系干物质分配比例

    # CO2矩形双曲响应参数（Pn = Pmax * (Ci - C0) / (Km + (Ci - C0))）
    CO2_compensation: float = 50.0   # C0，CO2补偿点 (ppm)
    CO2_Km: float = 300.0            # Km，米氏常数 (ppm)
    Pn_max_CO2: float = 2.2          # 叶片最大净光合（mol CO2/m²/d 的近似上限，用于缩放）

    # 叶片基础暗呼吸速率（冠层面积尺度）
    leaf_resp_rate_base: float = 0.5  # g 干物质/m²/h（基础值，Q10修正）
    
    # 坐果率
    fruit_set_rate_opt: float = 0.82  # 最优坐果率
    fruit_set_rate_min: float = 0.50  # 最低坐果率
    
    # ========== 生育期参数 ==========
    growth_stages: Dict[str, Dict] = None
    
    def __post_init__(self):
        """初始化生育期参数"""
        if self.growth_stages is None:
            self.growth_stages = {
                'seedling': {
                    'name': '幼苗期',
                    'duration': 30,  # 天
                    'GDD_required': self.GDD_seedling,
                    'GDD_corr': 0.92
                },
                'flowering': {
                    'name': '开花期',
                    'duration': 20,
                    'GDD_required': self.GDD_flowering,
                    'GDD_corr': self.GDD_corr_flowering
                },
                'fruiting': {
                    'name': '结果期',
                    'duration': 60,
                    'GDD_required': self.GDD_fruiting,
                    'GDD_corr': self.GDD_corr_fruiting
                },
                'harvest': {
                    'name': '采收期',
                    'duration': 30,
                    'GDD_required': self.GDD_total - self.GDD_seedling - 
                                   self.GDD_flowering - self.GDD_fruiting,
                    'GDD_corr': self.GDD_corr_harvest
                }
            }
    
    def get_GDD_correction(self, stage: str) -> float:
        """获取指定生育期的积温修正系数"""
        if stage in self.growth_stages:
            return self.growth_stages[stage]['GDD_corr']
        return 1.0
    
    def validate_config(self) -> List[str]:
        """验证配置参数的有效性"""
        errors = []
        
        if self.T_base < 0:
            errors.append("基点温度不能为负")
        if self.EC_min >= self.EC_max:
            errors.append("EC最小值应小于最大值")
        if self.SWC_opt_min >= self.SWC_opt_max:
            errors.append("最优土壤含水量下限应小于上限")
        if self.gray_mold_temp_min >= self.gray_mold_temp_max:
            errors.append("灰霉病温度范围无效")
        
        return errors


# 全局配置实例
GLOBAL_CONFIG = ModelConfig()







