"""
病虫害预警模型
实现灰霉病与白粉虱的预警与预测
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

try:
    from .config import ModelConfig, GLOBAL_CONFIG
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tomato_growth_model.config import ModelConfig, GLOBAL_CONFIG


class PestDiseaseModel:
    """病虫害预警模型类"""
    
    def __init__(self, config: ModelConfig = None):
        """
        初始化病虫害预警模型
        
        Args:
            config: 模型配置对象，默认使用全局配置
        """
        self.config = config or GLOBAL_CONFIG
        
        # 状态变量
        self.gray_mold_risk = 0.0  # 灰霉病风险指数 (0-100)
        self.whitefly_population = self.config.whitefly_base_population  # 白粉虱种群数量
        self.whitefly_generation = 1  # 当前世代
        self.days_since_infestation = 0  # 侵染天数
        
        # 历史记录
        self.history = []
        self.alert_history = []
    
    def calculate_gray_mold_risk(
        self,
        humidity: float,
        day_temp: float,
        night_temp: float,
        LAI: float,
        days_high_risk: int = 0
    ) -> float:
        """
        计算灰霉病风险指数
        
        Args:
            humidity: 相对湿度 (%)
            day_temp: 白天温度 (℃)
            night_temp: 夜间温度 (℃)
            LAI: 叶面积指数
            days_high_risk: 连续高风险天数
            
        Returns:
            灰霉病风险指数 (0-100)
        """
        # 基础风险
        risk = self.config.gray_mold_risk_base * 100
        
        # 湿度影响（关键因子）
        if humidity >= self.config.gray_mold_humidity_threshold:
            # 超过阈值，风险指数增长
            humidity_excess = humidity - self.config.gray_mold_humidity_threshold
            humidity_factor = 1.0 + (humidity_excess / 20.0) * 2.0  # 每超过20%，风险翻倍
        else:
            # 低于阈值，风险降低
            humidity_factor = max(0.1, humidity / self.config.gray_mold_humidity_threshold)
        
        # 温度影响
        avg_temp = (day_temp + night_temp) / 2.0
        
        if avg_temp < self.config.gray_mold_temp_min:
            temp_factor = 0.5  # 温度过低，风险降低
        elif avg_temp <= self.config.gray_mold_temp_max:
            # 适宜温度范围，风险最高
            temp_factor = 1.0
        else:
            # 温度过高，风险降低
            temp_factor = max(0.3, 1.0 - (avg_temp - self.config.gray_mold_temp_max) / 10.0)
        
        # LAI影响（LAI高，通风差，风险增加）
        if LAI > 3.0:
            LAI_factor = 1.0 + (LAI - 3.0) / 2.0 * 0.3
        else:
            LAI_factor = 1.0
        
        # 连续高风险天数影响（累积效应）
        cumulative_factor = 1.0 + days_high_risk * 0.1
        
        # 计算风险指数
        risk = risk * humidity_factor * temp_factor * LAI_factor * cumulative_factor
        
        # 限制在0-100范围内
        risk = max(0.0, min(100.0, risk))
        
        return risk
    
    def calculate_whitefly_population(
        self,
        day_temp: float,
        night_temp: float,
        days: int = 1
    ) -> float:
        """
        计算白粉虱种群数量动态
        
        Args:
            day_temp: 白天温度 (℃)
            night_temp: 夜间温度 (℃)
            days: 天数，默认1天
            
        Returns:
            更新后的种群数量
        """
        avg_temp = (day_temp + night_temp) / 2.0
        
        # 温度对繁殖的影响
        if avg_temp < self.config.whitefly_temp_opt_min:
            # 温度过低，繁殖率低
            reproduction_rate = 0.3
        elif avg_temp <= self.config.whitefly_temp_opt_max:
            # 最适温度范围，繁殖率最高
            reproduction_rate = 1.0
        elif avg_temp <= 30.0:
            # 温度稍高，繁殖率下降
            reproduction_rate = 1.0 - (avg_temp - self.config.whitefly_temp_opt_max) / 10.0
        else:
            # 温度过高，繁殖率显著下降
            reproduction_rate = 0.2
        
        # 世代周期影响
        # 假设每个世代周期内，种群数量翻倍
        generation_factor = 2.0 ** (days / self.config.whitefly_generation_cycle)
        
        # 自然死亡率（假设每天5%）
        mortality_rate = 0.05
        
        # 计算种群变化
        # 新种群 = 原种群 × 繁殖率 × 世代因子 × (1 - 死亡率)
        new_population = self.whitefly_population * reproduction_rate * \
                        (generation_factor ** (1.0 / self.config.whitefly_generation_cycle)) * \
                        (1.0 - mortality_rate) ** days
        
        # 更新世代
        self.days_since_infestation += days
        if self.days_since_infestation >= self.config.whitefly_generation_cycle:
            self.whitefly_generation += int(self.days_since_infestation / 
                                          self.config.whitefly_generation_cycle)
            self.days_since_infestation = self.days_since_infestation % \
                                        self.config.whitefly_generation_cycle
        
        return max(0.0, new_population)
    
    def get_gray_mold_alert(self, risk: float) -> Optional[Dict]:
        """
        获取灰霉病预警信息
        
        Args:
            risk: 灰霉病风险指数
            
        Returns:
            预警信息字典，如果无预警则返回None
        """
        if risk < 50:
            return None
        elif risk < 70:
            return {
                'type': 'gray_mold',
                'level': 'warning',
                'risk': risk,
                'message': f'灰霉病风险中等 (风险指数: {risk:.1f})',
                'suggestions': [
                    '加强通风，降低湿度',
                    '控制灌溉，避免叶面结露',
                    '适当提高温度至18-20℃',
                    '定期检查植株，发现病叶及时摘除'
                ]
            }
        else:
            return {
                'type': 'gray_mold',
                'level': 'high',
                'risk': risk,
                'message': f'灰霉病高风险 (风险指数: {risk:.1f})',
                'suggestions': [
                    '立即加强通风，开启排风扇',
                    '减少或停止灌溉',
                    '提高温度至20-22℃',
                    '使用杀菌剂预防（如百菌清、多菌灵）',
                    '摘除病叶、病果，集中销毁',
                    '降低LAI，适当疏叶'
                ]
            }
    
    def get_whitefly_alert(self, population: float) -> Optional[Dict]:
        """
        获取白粉虱预警信息
        
        Args:
            population: 白粉虱种群数量
            
        Returns:
            预警信息字典，如果无预警则返回None
        """
        # 阈值设定
        warning_threshold = 50.0
        high_threshold = 200.0
        
        if population < warning_threshold:
            return None
        elif population < high_threshold:
            return {
                'type': 'whitefly',
                'level': 'warning',
                'population': population,
                'generation': self.whitefly_generation,
                'message': f'白粉虱种群增长 (当前数量: {population:.0f}, 世代: {self.whitefly_generation})',
                'suggestions': [
                    '悬挂黄色粘虫板监测',
                    '加强通风，降低温度',
                    '使用生物防治（如释放丽蚜小蜂）',
                    '定期检查叶片背面'
                ]
            }
        else:
            return {
                'type': 'whitefly',
                'level': 'high',
                'population': population,
                'generation': self.whitefly_generation,
                'message': f'白粉虱严重发生 (当前数量: {population:.0f}, 世代: {self.whitefly_generation})',
                'suggestions': [
                    '立即使用化学防治（如吡虫啉、噻虫嗪）',
                    '结合物理防治（黄板、防虫网）',
                    '释放天敌（丽蚜小蜂、瓢虫）',
                    '清理棚内杂草，减少寄主',
                    '轮换使用不同作用机制的药剂'
                ]
            }
    
    def daily_update(
        self,
        humidity: float,
        day_temp: float,
        night_temp: float,
        LAI: float
    ) -> Dict:
        """
        执行每日更新
        
        Args:
            humidity: 相对湿度 (%)
            day_temp: 白天温度 (℃)
            night_temp: 夜间温度 (℃)
            LAI: 叶面积指数
            
        Returns:
            更新结果字典
        """
        # 计算连续高风险天数
        days_high_risk = 0
        if len(self.history) > 0:
            for i in range(len(self.history) - 1, -1, -1):
                if self.history[i].get('gray_mold_risk', 0) >= 70:
                    days_high_risk += 1
                else:
                    break
        
        # 计算灰霉病风险
        self.gray_mold_risk = self.calculate_gray_mold_risk(
            humidity,
            day_temp,
            night_temp,
            LAI,
            days_high_risk
        )
        
        # 计算白粉虱种群
        self.whitefly_population = self.calculate_whitefly_population(
            day_temp,
            night_temp
        )
        
        # 获取预警信息
        gray_mold_alert = self.get_gray_mold_alert(self.gray_mold_risk)
        whitefly_alert = self.get_whitefly_alert(self.whitefly_population)
        
        alerts = []
        if gray_mold_alert:
            alerts.append(gray_mold_alert)
            self.alert_history.append(gray_mold_alert)
        
        if whitefly_alert:
            alerts.append(whitefly_alert)
            self.alert_history.append(whitefly_alert)
        
        # 记录结果
        result = {
            'gray_mold_risk': self.gray_mold_risk,
            'whitefly_population': self.whitefly_population,
            'whitefly_generation': self.whitefly_generation,
            'days_high_risk': days_high_risk,
            'alerts': alerts
        }
        
        self.history.append(result)
        
        return result
    
    def get_risk_summary(self) -> Dict:
        """获取风险摘要"""
        if not self.history:
            return {
                'gray_mold_risk_level': 'low',
                'whitefly_risk_level': 'low',
                'total_alerts': 0
            }
        
        # 灰霉病风险等级
        avg_gray_mold_risk = np.mean([h['gray_mold_risk'] for h in self.history[-7:]])
        if avg_gray_mold_risk < 50:
            gray_mold_level = 'low'
        elif avg_gray_mold_risk < 70:
            gray_mold_level = 'medium'
        else:
            gray_mold_level = 'high'
        
        # 白粉虱风险等级
        current_population = self.whitefly_population
        if current_population < 50:
            whitefly_level = 'low'
        elif current_population < 200:
            whitefly_level = 'medium'
        else:
            whitefly_level = 'high'
        
        return {
            'gray_mold_risk_level': gray_mold_level,
            'gray_mold_risk_avg': avg_gray_mold_risk,
            'whitefly_risk_level': whitefly_level,
            'whitefly_population': current_population,
            'total_alerts': len(self.alert_history)
        }
    
    def reset(self):
        """重置模型状态"""
        self.gray_mold_risk = 0.0
        self.whitefly_population = self.config.whitefly_base_population
        self.whitefly_generation = 1
        self.days_since_infestation = 0
        self.history = []
        self.alert_history = []

