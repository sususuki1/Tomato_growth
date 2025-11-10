"""
生长发育模型
模拟积温积累、LAI动态、干物质积累与果实分配

基于《番茄（秋季）生长模型技术手册》和公式PDF中的核心公式实现
"""

import numpy as np
from typing import Dict, Optional
from datetime import datetime

try:
    from .config import ModelConfig, GLOBAL_CONFIG
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tomato_growth_model.config import ModelConfig, GLOBAL_CONFIG


class GrowthModel:
    """生长发育模型类"""
    
    def __init__(self, config: ModelConfig = None):
        """
        初始化生长发育模型
        
        Args:
            config: 模型配置对象，默认使用全局配置
        """
        self.config = config or GLOBAL_CONFIG
        
        # 状态变量
        self.day = 0  # 定植后天数
        self.GDD = 0.0  # 累积积温 (度日)
        self.daily_GDD = 0.0  # 日积温
        self.stage = 'seedling'  # 当前生育期
        self.LAI = self.config.LAI_initial  # 叶面积指数
        
        # 干物质状态 (g/株)
        self.dry_matter_total = 0.0  # 总干物质量
        self.dry_matter_leaf = 0.0  # 叶片干物质量
        self.dry_matter_stem = 0.0  # 茎干物质量
        self.dry_matter_fruit = 0.0  # 果实干物质量
        self.dry_matter_root = 0.0  # 根系干物质量
        
        # 坐果率
        self.fruit_set_rate = 0.0
        
        # 历史记录
        self.history = []
        
        # 生育期转换标志
        self.stage_transitions = {
            'seedling': False,
            'flowering': False,
            'fruiting': False,
            'harvest': False
        }
    
    def calculate_GDD(
        self,
        day_temp: float,
        night_temp: float,
        stage: str = None
    ) -> float:
        """
        计算日积温（Growing Degree Days）
        
        公式：GDD = (T_avg - T_base) * GDD_corr
        其中 T_avg = (T_day + T_night) / 2
        
        Args:
            day_temp: 白天温度 (℃)
            night_temp: 夜间温度 (℃)
            stage: 当前生育期，用于获取修正系数
            
        Returns:
            日积温 (度日)
        """
        # 计算平均温度
        avg_temp = (day_temp + night_temp) / 2.0
        
        # 如果平均温度低于基点温度，积温为0
        if avg_temp <= self.config.T_base:
            return 0.0
        
        # 获取积温修正系数
        if stage is None:
            stage = self.stage
        GDD_corr = self.config.get_GDD_correction(stage)
        
        # 计算日积温
        daily_GDD = (avg_temp - self.config.T_base) * GDD_corr
        
        return max(0.0, daily_GDD)
    
    def determine_growth_stage(self, GDD: float) -> str:
        """
        根据累积积温判断当前生育期
        
        Args:
            GDD: 累积积温 (度日)
            
        Returns:
            当前生育期名称
        """
        # 根据积温阈值判断生育期
        if GDD < self.config.GDD_seedling:
            return 'seedling'
        elif GDD < self.config.GDD_seedling + self.config.GDD_flowering:
            return 'flowering'
        elif GDD < self.config.GDD_seedling + self.config.GDD_flowering + self.config.GDD_fruiting:
            return 'fruiting'
        else:
            return 'harvest'
    
    def calculate_LAI(
        self,
        GDD: float,
        stage: str,
        day: int
    ) -> float:
        """
        计算叶面积指数（LAI）动态变化
        
        基于S型增长曲线，考虑积温和生育期的影响
        
        公式参考：LAI = LAI_max / (1 + exp(-k * (GDD - GDD_mid)))
        
        Args:
            GDD: 累积积温 (度日)
            stage: 当前生育期
            day: 定植后天数
            
        Returns:
            当前LAI值
        """
        # 不同生育期的LAI增长模式
        if stage == 'seedling':
            # 幼苗期：指数增长
            growth_rate = self.config.LAI_growth_rate
            LAI = self.config.LAI_initial * np.exp(growth_rate * day)
            LAI = min(LAI, 1.5)  # 幼苗期LAI上限
            
        elif stage == 'flowering':
            # 开花期：快速增长
            # 使用S型曲线
            GDD_mid = self.config.GDD_seedling + self.config.GDD_flowering / 2
            k = 0.01  # 增长速率参数
            LAI_max_stage = 3.0
            LAI_base = 1.5  # 开花期起始LAI
            # 从1.5增长到3.0
            LAI = LAI_base + (LAI_max_stage - LAI_base) / (1 + np.exp(-k * (GDD - GDD_mid)))
            LAI = max(1.5, min(LAI, 3.0))
            
        elif stage == 'fruiting':
            # 结果期：接近最大值
            GDD_mid = (self.config.GDD_seedling + self.config.GDD_flowering + 
                      self.config.GDD_fruiting / 2)
            k = 0.008
            LAI = self.config.LAI_max / (1 + np.exp(-k * (GDD - GDD_mid)))
            LAI = max(3.0, min(LAI, self.config.LAI_max))
            
        else:  # harvest
            # 采收期：LAI略有下降（叶片老化）
            LAI = self.config.LAI_max * 0.95
            LAI = max(3.5, LAI)
        
        return max(self.config.LAI_initial, min(LAI, self.config.LAI_max))
    
    def calculate_photosynthesis(
        self,
        PAR: float,
        CO2: float,
        day_temp: float,
        LAI: float
    ) -> float:
        """
        计算光合作用速率（结合Beer–Lambert冠层光拦截与CO2矩形双曲响应的简化版）
        
        公式参考：
        - 冠层光拦截：f_intercept = 1 - exp(-k * LAI)
        - PPFD≈PAR（μmol m⁻² s⁻¹），日量：PAR_daily = PAR_intercept * 3600*12 / 1e6 (mol m⁻² d⁻¹)
        - 光合：Gross_CO2 = φ * PAR_daily * f_temp * f_CO2
        - CO2矩形双曲：f_CO2 = (CO2 - C0) / (Km + (CO2 - C0))（>=0）
        - 暗呼吸：R = R_base(h⁻¹) * 24 * Q10^((T - Tref)/10)
        - 群体净光合：Net = (Gross_DM - Resp)  [g m⁻² d⁻¹]
        
        其中：
        - phi: 光合量子效率
        - f_CO2: CO2响应函数
        - f_temp: 温度响应函数
        - f_intercept: 冠层光截获率
        
        Args:
            PAR: 光合有效辐射 (μmol/m²/s)
            CO2: CO2浓度 (ppm)
            day_temp: 白天温度 (℃)
            LAI: 叶面积指数
            
        Returns:
            净光合速率 (g 干物质/m²/d)
        """
        # 0) 冠层光拦截（Beer–Lambert）
        k_ext = self.config.light_extinction_coeff
        f_intercept = 1.0 - np.exp(-k_ext * max(0.0, LAI))
        PAR_intercept = max(0.0, PAR) * f_intercept

        # 1) 温度响应（最适温度附近提升，高温衰减）
        if day_temp < self.config.T_base:
            temp_factor = 0.1
        elif day_temp <= self.config.T_opt_day:
            temp_factor = 0.3 + 0.7 * (day_temp - self.config.T_base) / \
                          (self.config.T_opt_day - self.config.T_base)
        elif day_temp <= 30.0:
            temp_factor = 1.0 - 0.02 * (day_temp - self.config.T_opt_day)
        else:
            temp_factor = max(0.3, 1.0 - 0.05 * (day_temp - 30.0))
        
        # 2) CO2矩形双曲响应（归一化到0-1）
        CO2_excess = max(0.0, CO2 - self.config.CO2_compensation)
        CO2_factor = CO2_excess / (self.config.CO2_Km + CO2_excess) if (self.config.CO2_Km + CO2_excess) > 0 else 0.0
        
        # 3) 计算总光合（mol CO2 转 g DM）
        # 单位转换：μmol/m²/s -> mol/m²/d，按12小时有效光期
        PAR_daily = PAR_intercept * 3600 * 12 / 1e6  # mol/m²/d
        
        # φ单位：mol CO2 / mol PAR
        gross_photosynthesis_CO2 = self.config.phi * PAR_daily * temp_factor
        # CO2限制（矩形双曲）：作为效率系数乘上
        gross_photosynthesis_CO2 *= CO2_factor
        
        # CO₂转换为干物质：1 mol CO₂ ≈ 30 g 干物质（CH2O）
        CO2_to_DM = 30.0  # g 干物质/mol CO₂
        gross_photosynthesis = gross_photosynthesis_CO2 * CO2_to_DM  # g 干物质/m²/d
        
        # 4) 呼吸消耗（暗呼吸，考虑温度修正）
        # 呼吸速率随温度指数增长：Q10 = 2.0
        Q10 = 2.0
        T_ref = 20.0  # 参考温度
        resp_temp_factor = Q10 ** ((day_temp - T_ref) / 10.0)
        
        # 基础暗呼吸速率（g/m²/h），来源于PDF与秋季校准
        base_respiration_rate = self.config.leaf_resp_rate_base
        dark_respiration = base_respiration_rate * 24 * resp_temp_factor  # g/m²/d
        
        # 5) 净光合速率（g/m²/d）
        net_photosynthesis = gross_photosynthesis - dark_respiration
        
        # 6) 转株：g/株/d（冠层/地表面积→单株面积）
        area_per_plant = self.config.area_per_plant
        net_photosynthesis_per_plant = max(0.0, net_photosynthesis) * area_per_plant
        
        return max(0.0, net_photosynthesis_per_plant)
    
    def calculate_dry_matter_allocation(
        self,
        daily_dry_matter: float,
        stage: str
    ) -> Dict[str, float]:
        """
        计算干物质分配（根据生育期）
        
        不同生育期的分配比例：
        - 幼苗期：叶片40%，茎30%，根系30%
        - 开花期：叶片35%，茎25%，根系20%，花20%
        - 结果期：叶片25%，茎15%，根系10%，果实50%
        - 采收期：叶片20%，茎10%，根系5%，果实65%
        
        Args:
            daily_dry_matter: 日干物质积累量 (g/株/d)
            stage: 当前生育期
            
        Returns:
            各器官干物质分配量字典
        """
        if stage == 'seedling':
            leaf_ratio = 0.40
            stem_ratio = 0.30
            root_ratio = 0.30
            fruit_ratio = 0.0
            
        elif stage == 'flowering':
            leaf_ratio = 0.35
            stem_ratio = 0.25
            root_ratio = 0.20
            fruit_ratio = 0.20  # 花器官
            
        elif stage == 'fruiting':
            leaf_ratio = self.config.DM_leaf_ratio
            stem_ratio = self.config.DM_stem_ratio
            root_ratio = self.config.DM_root_ratio
            fruit_ratio = self.config.DM_fruit_ratio
            
        else:  # harvest
            leaf_ratio = 0.20
            stem_ratio = 0.10
            root_ratio = 0.05
            fruit_ratio = 0.65
        
        # 计算各器官分配量
        allocation = {
            'leaf': daily_dry_matter * leaf_ratio,
            'stem': daily_dry_matter * stem_ratio,
            'root': daily_dry_matter * root_ratio,
            'fruit': daily_dry_matter * fruit_ratio
        }
        
        return allocation
    
    def calculate_fruit_set_rate(
        self,
        day_temp: float,
        night_temp: float
    ) -> float:
        """
        计算坐果率（基于温度条件）
        
        最优条件：白天23℃，夜间17℃，坐果率82%
        温度偏离时坐果率下降
        
        Args:
            day_temp: 白天温度 (℃)
            night_temp: 夜间温度 (℃)
            
        Returns:
            坐果率 (0-1)
        """
        # 白天温度影响
        if day_temp < 18.0:
            day_factor = 0.5 + 0.3 * (day_temp - 15.0) / 3.0  # 15-18℃
        elif day_temp <= self.config.T_opt_day:
            day_factor = 0.8 + 0.2 * (day_temp - 18.0) / 5.0  # 18-23℃
        elif day_temp <= 28.0:
            day_factor = 1.0 - 0.3 * (day_temp - self.config.T_opt_day) / 5.0  # 23-28℃
        else:
            day_factor = max(0.3, 0.7 - 0.4 * (day_temp - 28.0) / 5.0)  # >28℃
        
        # 夜间温度影响（更关键）
        if night_temp < 14.0:
            night_factor = 0.4 + 0.2 * (night_temp - 12.0) / 2.0  # 12-14℃
        elif night_temp <= self.config.T_opt_night:
            night_factor = 0.6 + 0.4 * (night_temp - 14.0) / 3.0  # 14-17℃
        elif night_temp <= 19.0:
            night_factor = 1.0 - 0.2 * (night_temp - self.config.T_opt_night) / 2.0  # 17-19℃
        else:
            night_factor = max(0.3, 0.8 - 0.5 * (night_temp - 19.0) / 5.0)  # >19℃
        
        # 综合坐果率
        fruit_set_rate = self.config.fruit_set_rate_opt * day_factor * night_factor
        
        # 限制在合理范围内
        fruit_set_rate = max(self.config.fruit_set_rate_min, min(1.0, fruit_set_rate))
        
        return fruit_set_rate
    
    def daily_update(
        self,
        day_temp: float,
        night_temp: float,
        PAR: float,
        CO2: float
    ) -> Dict:
        """
        执行每日更新
        
        Args:
            day_temp: 白天温度 (℃)
            night_temp: 夜间温度 (℃)
            PAR: 光合有效辐射 (μmol/m²/s)
            CO2: CO2浓度 (ppm)
            
        Returns:
            更新结果字典
        """
        # 1. 更新天数
        self.day += 1
        
        # 2. 计算日积温
        self.daily_GDD = self.calculate_GDD(day_temp, night_temp, self.stage)
        self.GDD += self.daily_GDD
        
        # 3. 判断生育期（检查是否转换）
        new_stage = self.determine_growth_stage(self.GDD)
        if new_stage != self.stage:
            # 生育期转换
            self.stage_transitions[self.stage] = True
            self.stage = new_stage
        
        # 4. 计算LAI
        self.LAI = self.calculate_LAI(self.GDD, self.stage, self.day)
        
        # 5. 计算光合作用和干物质积累
        daily_dry_matter = self.calculate_photosynthesis(
            PAR, CO2, day_temp, self.LAI
        )
        
        # 6. 干物质分配
        allocation = self.calculate_dry_matter_allocation(
            daily_dry_matter, self.stage
        )
        
        # 7. 更新各器官干物质量
        self.dry_matter_leaf += allocation['leaf']
        self.dry_matter_stem += allocation['stem']
        self.dry_matter_root += allocation['root']
        self.dry_matter_fruit += allocation['fruit']
        
        # 8. 更新总干物质量
        self.dry_matter_total = (self.dry_matter_leaf + self.dry_matter_stem + 
                                self.dry_matter_fruit + self.dry_matter_root)
        
        # 9. 计算坐果率（开花期和结果期）
        if self.stage in ['flowering', 'fruiting', 'harvest']:
            self.fruit_set_rate = self.calculate_fruit_set_rate(day_temp, night_temp)
        else:
            self.fruit_set_rate = 0.0
        
        # 10. 记录结果
        result = {
            'day': self.day,
            'stage': self.stage,
            'GDD': self.GDD,
            'daily_GDD': self.daily_GDD,
            'LAI': self.LAI,
            'dry_matter_total': self.dry_matter_total,
            'dry_matter_leaf': self.dry_matter_leaf,
            'dry_matter_stem': self.dry_matter_stem,
            'dry_matter_fruit': self.dry_matter_fruit,
            'dry_matter_root': self.dry_matter_root,
            'daily_dry_matter': daily_dry_matter,
            'fruit_set_rate': self.fruit_set_rate,
            'stage_transition': self.stage_transitions.get(self.stage, False)
        }
        
        self.history.append(result)
        
        return result
    
    def reset(self):
        """重置模型状态"""
        self.day = 0
        self.GDD = 0.0
        self.daily_GDD = 0.0
        self.stage = 'seedling'
        self.LAI = self.config.LAI_initial
        
        self.dry_matter_total = 0.0
        self.dry_matter_leaf = 0.0
        self.dry_matter_stem = 0.0
        self.dry_matter_fruit = 0.0
        self.dry_matter_root = 0.0
        
        self.fruit_set_rate = 0.0
        self.history = []
        
        self.stage_transitions = {
            'seedling': False,
            'flowering': False,
            'fruiting': False,
            'harvest': False
        }
    
    def get_growth_summary(self) -> Dict:
        """获取生长摘要"""
        if not self.history:
            return {}
        
        # 计算各生育期持续时间
        stage_durations = {}
        current_stage = None
        stage_start_day = 0
        
        for record in self.history:
            if record['stage'] != current_stage:
                if current_stage is not None:
                    stage_durations[current_stage] = record['day'] - stage_start_day
                current_stage = record['stage']
                stage_start_day = record['day']
        
        # 最后一个生育期
        if current_stage is not None:
            stage_durations[current_stage] = self.day - stage_start_day + 1
        
        return {
            'total_days': self.day,
            'total_GDD': self.GDD,
            'current_stage': self.stage,
            'current_LAI': self.LAI,
            'total_dry_matter': self.dry_matter_total,
            'dry_matter_leaf': self.dry_matter_leaf,
            'dry_matter_stem': self.dry_matter_stem,
            'dry_matter_fruit': self.dry_matter_fruit,
            'dry_matter_root': self.dry_matter_root,
            'fruit_set_rate': self.fruit_set_rate,
            'stage_durations': stage_durations
        }

