"""
水肥运输模型
模拟土壤EC值动态、钾元素吸收效率、根系吸水效率
"""

import numpy as np
from typing import Dict, List, Optional

try:
    from .config import ModelConfig, GLOBAL_CONFIG
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tomato_growth_model.config import ModelConfig, GLOBAL_CONFIG


class WaterFertilizerModel:
    """水肥运输模型类"""
    
    def __init__(self, config: ModelConfig = None):
        """
        初始化水肥运输模型
        
        Args:
            config: 模型配置对象，默认使用全局配置
        """
        self.config = config or GLOBAL_CONFIG
        
        # 状态变量
        self.soil_EC = self.config.EC_opt  # 当前土壤EC值 (mS/cm)
        self.soil_water_content = 0.65  # 当前土壤含水量 (FC)
        self.accumulated_K = 0.0  # 累计钾吸收量 (g/株)
        self.daily_K_uptake = 0.0  # 日钾吸收量 (g/株/d)
        self.root_water_uptake_efficiency = self.config.root_water_uptake_base
        
        # 历史记录
        self.history = []
    
    def calculate_EC_dynamics(
        self,
        irrigation_frequency: int,
        fertilizer_EC: float,
        water_uptake: float,
        days: int = 1
    ) -> float:
        """
        计算土壤EC值动态变化
        
        Args:
            irrigation_frequency: 灌溉频率 (次/天)
            fertilizer_EC: 施肥EC值 (mS/cm)
            water_uptake: 根系吸水量 (mm/d)
            days: 天数，默认1天
            
        Returns:
            更新后的土壤EC值 (mS/cm)
        """
        # EC变化速率常数
        EC_decay_rate = 0.05  # EC自然衰减率 (1/天)
        EC_uptake_factor = 0.02  # 根系吸收对EC的影响因子
        
        # 灌溉带来的EC增加
        EC_input = fertilizer_EC * irrigation_frequency * 0.1
        
        # 根系吸收导致的EC下降
        EC_uptake_loss = self.soil_EC * water_uptake * EC_uptake_factor
        
        # 自然衰减
        EC_decay = self.soil_EC * EC_decay_rate
        
        # EC变化 = 输入 - 吸收损失 - 自然衰减
        EC_change = (EC_input - EC_uptake_loss - EC_decay) * days
        
        # 更新EC值
        new_EC = self.soil_EC + EC_change
        
        # 限制在合理范围内
        new_EC = max(0.5, min(3.5, new_EC))
        
        return new_EC
    
    def calculate_K_uptake(
        self,
        soil_EC: float,
        soil_water: float,
        growth_stage: str,
        dry_matter_fruit: float
    ) -> float:
        """
        计算钾吸收量（基于Michaelis-Menten动力学）
        
        Args:
            soil_EC: 土壤EC值 (mS/cm)
            soil_water: 土壤含水量 (FC)
            growth_stage: 当前生育期
            dry_matter_fruit: 果实干物质量 (g/株)
            
        Returns:
            日钾吸收量 (g/株/d)
        """
        # EC对钾吸收的影响
        if soil_EC < self.config.EC_min:
            EC_factor = 0.7  # EC过低，吸收受限
        elif soil_EC <= self.config.EC_max:
            # 最优范围内
            EC_factor = 1.0
        else:
            # EC过高，吸收下降
            EC_factor = max(0.5, 1.0 - (soil_EC - self.config.EC_max) / 1.0)
        
        # 土壤含水量影响
        if soil_water < self.config.SWC_min:
            water_factor = 0.5  # 过干，吸收受限
        elif soil_water < self.config.SWC_opt_min:
            water_factor = 0.7 + 0.3 * (soil_water - self.config.SWC_min) / \
                          (self.config.SWC_opt_min - self.config.SWC_min)
        elif soil_water <= self.config.SWC_opt_max:
            water_factor = 1.0  # 最优范围
        elif soil_water <= self.config.SWC_max:
            water_factor = 1.0 - 0.2 * (soil_water - self.config.SWC_opt_max) / \
                          (self.config.SWC_max - self.config.SWC_opt_max)
        else:
            water_factor = 0.6  # 过湿，吸收受限
        
        # 生育期影响（结果期需求最大）
        if growth_stage == 'fruiting':
            stage_factor = 1.2
        elif growth_stage == 'harvest':
            stage_factor = 1.0
        elif growth_stage == 'flowering':
            stage_factor = 0.8
        else:
            stage_factor = 0.6
        
        # Michaelis-Menten动力学
        # V = Vmax * [S] / (Km + [S])
        # 这里用EC作为底物浓度的代理
        Vmax = self.config.K_uptake_Vmax / 7.0  # 转换为日值
        Km = self.config.K_uptake_Km
        
        # 底物浓度（用EC值表示）
        S = max(0.1, soil_EC)
        
        # 基础吸收速率
        base_uptake = Vmax * S / (Km + S)
        
        # 应用各种因子
        K_uptake = base_uptake * EC_factor * water_factor * stage_factor
        
        # 限制在合理范围内
        K_uptake = max(0.0, min(self.config.K_uptake_peak * 1.5, K_uptake))
        
        return K_uptake
    
    def calculate_water_uptake(
        self,
        soil_water: float,
        soil_EC: float,
        LAI: float,
        day_temp: float,
        PAR: float
    ) -> float:
        """
        计算根系吸水量
        
        Args:
            soil_water: 土壤含水量 (FC)
            soil_EC: 土壤EC值 (mS/cm)
            LAI: 叶面积指数
            day_temp: 白天温度 (℃)
            PAR: 光合有效辐射 (μmol/m²/s)
            
        Returns:
            日吸水量 (mm/d)
        """
        # 基础吸水量（与LAI相关）
        base_uptake = 2.0 * LAI  # mm/d per LAI unit
        
        # 土壤含水量影响
        if soil_water < self.config.SWC_min:
            water_factor = 0.3
        elif soil_water < self.config.SWC_opt_min:
            water_factor = 0.5 + 0.5 * (soil_water - self.config.SWC_min) / \
                          (self.config.SWC_opt_min - self.config.SWC_min)
        elif soil_water <= self.config.SWC_opt_max:
            water_factor = 1.0
        elif soil_water <= self.config.SWC_max:
            water_factor = 1.0 - 0.3 * (soil_water - self.config.SWC_opt_max) / \
                          (self.config.SWC_max - self.config.SWC_opt_max)
        else:
            water_factor = 0.4
        
        # EC影响（高EC降低吸水效率）
        if soil_EC <= self.config.EC_max:
            EC_factor = 1.0
        else:
            # EC过高，效率下降
            EC_penalty = self.config.root_water_uptake_EC_penalty * \
                        (soil_EC - self.config.EC_max) / 1.0
            EC_factor = max(0.5, 1.0 - EC_penalty)
        
        # 温度影响
        if day_temp < self.config.T_base:
            temp_factor = 0.3
        elif day_temp <= self.config.T_opt_day:
            temp_factor = 0.5 + 0.5 * (day_temp - self.config.T_base) / \
                         (self.config.T_opt_day - self.config.T_base)
        else:
            temp_factor = 1.0
        
        # 光照影响（影响蒸腾）
        if PAR < self.config.PAR_compensation:
            light_factor = 0.5
        else:
            light_factor = min(1.0, PAR / self.config.PAR_saturation)
        
        # 计算吸水量
        water_uptake = base_uptake * water_factor * EC_factor * temp_factor * light_factor
        
        # 更新根系吸水效率
        self.root_water_uptake_efficiency = self.config.root_water_uptake_base * \
                                           EC_factor * water_factor
        
        return max(0.0, water_uptake)
    
    def calculate_soil_water_dynamics(
        self,
        irrigation_amount: float,
        water_uptake: float,
        evaporation: float = 0.0
    ) -> float:
        """
        计算土壤含水量动态变化
        
        Args:
            irrigation_amount: 灌溉量 (mm/d)
            water_uptake: 根系吸水量 (mm/d)
            evaporation: 土壤蒸发量 (mm/d)，默认0
            
        Returns:
            更新后的土壤含水量 (FC)
        """
        # 土壤持水能力（假设为100mm）
        field_capacity = 100.0  # mm
        
        # 当前土壤储水量
        current_storage = self.soil_water_content * field_capacity
        
        # 水量变化
        water_change = irrigation_amount - water_uptake - evaporation
        
        # 更新储水量
        new_storage = current_storage + water_change
        
        # 转换为FC
        new_water_content = new_storage / field_capacity
        
        # 限制在合理范围内
        new_water_content = max(0.0, min(1.0, new_water_content))
        
        return new_water_content
    
    def get_management_suggestions(self) -> List[Dict]:
        """
        获取管理建议
        
        Returns:
            管理建议列表
        """
        suggestions = []
        
        # EC值建议
        if self.soil_EC < self.config.EC_min:
            suggestions.append({
                'type': 'fertilizer',
                'priority': 'high',
                'message': f'土壤EC值偏低 ({self.soil_EC:.2f} mS/cm)，建议增加施肥量',
                'action': f'将EC值提升至 {self.config.EC_opt:.2f} mS/cm'
            })
        elif self.soil_EC > self.config.EC_max:
            suggestions.append({
                'type': 'fertilizer',
                'priority': 'high',
                'message': f'土壤EC值偏高 ({self.soil_EC:.2f} mS/cm)，可能影响根系吸收',
                'action': '减少盐分输入，增加灌溉量稀释'
            })
        
        # 土壤含水量建议
        if self.soil_water_content < self.config.SWC_opt_min:
            suggestions.append({
                'type': 'irrigation',
                'priority': 'medium',
                'message': f'土壤含水量偏低 ({self.soil_water_content*100:.1f}% FC)',
                'action': '增加灌溉频率或灌溉量'
            })
        elif self.soil_water_content > self.config.SWC_opt_max:
            suggestions.append({
                'type': 'irrigation',
                'priority': 'medium',
                'message': f'土壤含水量偏高 ({self.soil_water_content*100:.1f}% FC)',
                'action': '减少灌溉，注意排水'
            })
        
        # 根系吸水效率建议
        if self.root_water_uptake_efficiency < 0.7:
            suggestions.append({
                'type': 'root_health',
                'priority': 'medium',
                'message': '根系吸水效率偏低，可能影响养分吸收',
                'action': '检查根系健康，调整EC值和土壤含水量'
            })
        
        return suggestions
    
    def daily_update(
        self,
        irrigation_frequency: int,
        irrigation_amount: float,
        fertilizer_EC: float,
        growth_stage: str,
        LAI: float,
        day_temp: float,
        PAR: float,
        dry_matter_fruit: float = 0.0
    ) -> Dict:
        """
        执行每日更新
        
        Args:
            irrigation_frequency: 灌溉频率 (次/天)
            irrigation_amount: 单次灌溉量 (mm)
            fertilizer_EC: 施肥EC值 (mS/cm)
            growth_stage: 当前生育期
            LAI: 叶面积指数
            day_temp: 白天温度 (℃)
            PAR: 光合有效辐射 (μmol/m²/s)
            dry_matter_fruit: 果实干物质量 (g/株)
            
        Returns:
            更新结果字典
        """
        # 计算根系吸水量
        water_uptake = self.calculate_water_uptake(
            self.soil_water_content,
            self.soil_EC,
            LAI,
            day_temp,
            PAR
        )
        
        # 更新土壤含水量
        total_irrigation = irrigation_amount * irrigation_frequency
        self.soil_water_content = self.calculate_soil_water_dynamics(
            total_irrigation,
            water_uptake
        )
        
        # 更新EC值
        self.soil_EC = self.calculate_EC_dynamics(
            irrigation_frequency,
            fertilizer_EC,
            water_uptake
        )
        
        # 计算钾吸收
        self.daily_K_uptake = self.calculate_K_uptake(
            self.soil_EC,
            self.soil_water_content,
            growth_stage,
            dry_matter_fruit
        )
        self.accumulated_K += self.daily_K_uptake
        
        # 获取管理建议
        suggestions = self.get_management_suggestions()
        
        # 记录结果
        result = {
            'soil_EC': self.soil_EC,
            'soil_water_content': self.soil_water_content,
            'water_uptake': water_uptake,
            'daily_K_uptake': self.daily_K_uptake,
            'accumulated_K': self.accumulated_K,
            'root_water_uptake_efficiency': self.root_water_uptake_efficiency,
            'suggestions': suggestions
        }
        
        self.history.append(result)
        
        return result
    
    def reset(self):
        """重置模型状态"""
        self.soil_EC = self.config.EC_opt
        self.soil_water_content = 0.65
        self.accumulated_K = 0.0
        self.daily_K_uptake = 0.0
        self.root_water_uptake_efficiency = self.config.root_water_uptake_base
        self.history = []

