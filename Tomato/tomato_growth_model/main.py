"""
番茄生长模型主运行模块
整合三大子模型，实现完整的生长模拟系统
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import json

try:
    from .config import ModelConfig, GLOBAL_CONFIG
    from .growth_model import GrowthModel
    from .water_fertilizer_model import WaterFertilizerModel
    from .pest_disease_model import PestDiseaseModel
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tomato_growth_model.config import ModelConfig, GLOBAL_CONFIG
    from tomato_growth_model.growth_model import GrowthModel
    from tomato_growth_model.water_fertilizer_model import WaterFertilizerModel
    from tomato_growth_model.pest_disease_model import PestDiseaseModel


class TomatoGrowthSimulator:
    """番茄生长模拟器主类"""
    
    def __init__(self, config: ModelConfig = None, planting_date: str = None):
        """
        初始化模拟器
        
        Args:
            config: 模型配置对象，默认使用全局配置
            planting_date: 定植日期，格式 'YYYY-MM-DD'，默认今天
        """
        self.config = config or GLOBAL_CONFIG
        
        # 初始化三个子模型
        self.growth_model = GrowthModel(self.config)
        self.water_fertilizer_model = WaterFertilizerModel(self.config)
        self.pest_disease_model = PestDiseaseModel(self.config)
        
        # 设置定植日期
        if planting_date:
            self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        else:
            self.planting_date = datetime.now()
        
        # 模拟结果
        self.simulation_results = []
        self.daily_results = []
    
    def load_weather_data(
        self,
        data: Union[str, pd.DataFrame],
        date_col: str = 'date',
        day_temp_col: str = 'day_temp',
        night_temp_col: str = 'night_temp',
        humidity_col: str = 'humidity',
        PAR_col: str = 'PAR',
        CO2_col: str = 'CO2'
    ) -> pd.DataFrame:
        """
        加载气象数据
        
        Args:
            data: 数据文件路径或DataFrame
            date_col: 日期列名
            day_temp_col: 白天温度列名
            night_temp_col: 夜间温度列名
            humidity_col: 湿度列名
            PAR_col: 光合有效辐射列名
            CO2_col: CO₂浓度列名
            
        Returns:
            处理后的DataFrame
        """
        if isinstance(data, str):
            df = pd.read_csv(data)
        else:
            df = data.copy()
        
        # 确保日期列为datetime类型
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
        
        # 检查必需列
        required_cols = [day_temp_col, night_temp_col, humidity_col, PAR_col, CO2_col]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需的列: {missing_cols}")
        
        return df
    
    def generate_default_weather_data(
        self,
        start_date: str,
        days: int = 120
    ) -> pd.DataFrame:
        """
        生成默认气象数据（用于测试）
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            days: 天数
            
        Returns:
            气象数据DataFrame
        """
        dates = pd.date_range(start=start_date, periods=days, freq='D')
        
        # 秋季典型气象数据
        np.random.seed(42)
        
        # 白天温度：18-25℃，有波动
        day_temp = 21.5 + 3.5 * np.sin(np.arange(days) * 2 * np.pi / 30) + \
                   np.random.normal(0, 1.5, days)
        
        # 夜间温度：14-18℃
        night_temp = 16.0 + 2.0 * np.sin(np.arange(days) * 2 * np.pi / 30) + \
                    np.random.normal(0, 1.0, days)
        
        # 湿度：60-85%，有波动
        humidity = 72.5 + 12.5 * np.sin(np.arange(days) * 2 * np.pi / 7) + \
                  np.random.normal(0, 5, days)
        humidity = np.clip(humidity, 50, 95)
        
        # PAR：800-1200 μmol/m²/s
        PAR = 1000 + 200 * np.sin(np.arange(days) * 2 * np.pi / 30) + \
              np.random.normal(0, 100, days)
        PAR = np.clip(PAR, 500, 1500)
        
        # CO₂：400-750 ppm（部分时间增施）
        CO2 = np.where(np.random.random(days) > 0.3, 750, 400) + \
              np.random.normal(0, 20, days)
        CO2 = np.clip(CO2, 380, 800)
        
        df = pd.DataFrame({
            'date': dates,
            'day_temp': day_temp,
            'night_temp': night_temp,
            'humidity': humidity,
            'PAR': PAR,
            'CO2': CO2
        })
        
        return df
    
    def simulate(
        self,
        weather_data: pd.DataFrame,
        irrigation_frequency: int = 2,
        irrigation_amount: float = 5.0,
        fertilizer_EC: float = 2.15,
        date_col: str = 'date',
        day_temp_col: str = 'day_temp',
        night_temp_col: str = 'night_temp',
        humidity_col: str = 'humidity',
        PAR_col: str = 'PAR',
        CO2_col: str = 'CO2'
    ) -> pd.DataFrame:
        """
        执行模拟
        
        Args:
            weather_data: 气象数据DataFrame
            irrigation_frequency: 灌溉频率 (次/天)
            irrigation_amount: 单次灌溉量 (mm)
            fertilizer_EC: 施肥EC值 (mS/cm)
            date_col: 日期列名
            day_temp_col: 白天温度列名
            night_temp_col: 夜间温度列名
            humidity_col: 湿度列名
            PAR_col: 光合有效辐射列名
            CO2_col: CO₂浓度列名
            
        Returns:
            模拟结果DataFrame
        """
        # 重置模型
        self.growth_model.reset()
        self.water_fertilizer_model.reset()
        self.pest_disease_model.reset()
        self.simulation_results = []
        self.daily_results = []
        
        # 遍历每一天
        for idx, row in weather_data.iterrows():
            day_temp = row[day_temp_col]
            night_temp = row[night_temp_col]
            humidity = row[humidity_col]
            PAR = row[PAR_col]
            CO2 = row[CO2_col]
            
            # 更新生长发育模型
            growth_result = self.growth_model.daily_update(
                day_temp, night_temp, PAR, CO2
            )
            
            # 更新水肥模型
            water_fertilizer_result = self.water_fertilizer_model.daily_update(
                irrigation_frequency,
                irrigation_amount,
                fertilizer_EC,
                growth_result['stage'],
                growth_result['LAI'],
                day_temp,
                PAR,
                growth_result['dry_matter_fruit']
            )
            
            # 更新病虫害模型
            pest_disease_result = self.pest_disease_model.daily_update(
                humidity,
                day_temp,
                night_temp,
                growth_result['LAI']
            )
            
            # 合并结果
            result = {
                'date': row[date_col] if date_col in row else idx,
                'day': growth_result['day'],
                'stage': growth_result['stage'],
                'GDD': growth_result['GDD'],
                'daily_GDD': growth_result['daily_GDD'],
                'LAI': growth_result['LAI'],
                'dry_matter_total': growth_result['dry_matter_total'],
                'dry_matter_leaf': growth_result['dry_matter_leaf'],
                'dry_matter_stem': growth_result['dry_matter_stem'],
                'dry_matter_fruit': growth_result['dry_matter_fruit'],
                'dry_matter_root': growth_result['dry_matter_root'],
                'fruit_set_rate': growth_result['fruit_set_rate'],
                'soil_EC': water_fertilizer_result['soil_EC'],
                'soil_water_content': water_fertilizer_result['soil_water_content'],
                'water_uptake': water_fertilizer_result['water_uptake'],
                'daily_K_uptake': water_fertilizer_result['daily_K_uptake'],
                'accumulated_K': water_fertilizer_result['accumulated_K'],
                'gray_mold_risk': pest_disease_result['gray_mold_risk'],
                'whitefly_population': pest_disease_result['whitefly_population'],
                'alerts': pest_disease_result['alerts']
            }
            
            self.simulation_results.append(result)
            self.daily_results.append(result)
        
        # 转换为DataFrame
        results_df = pd.DataFrame(self.simulation_results)
        
        return results_df
    
    def get_summary(self) -> Dict:
        """获取模拟摘要"""
        if not self.simulation_results:
            return {}
        
        df = pd.DataFrame(self.simulation_results)
        
        # 生育期统计
        stage_summary = df.groupby('stage').agg({
            'day': ['min', 'max', 'count']
        }).to_dict()
        
        # 关键指标统计
        summary = {
            'total_days': len(df),
            'final_GDD': df['GDD'].iloc[-1],
            'final_LAI': df['LAI'].iloc[-1],
            'final_dry_matter_total': df['dry_matter_total'].iloc[-1],
            'final_dry_matter_fruit': df['dry_matter_fruit'].iloc[-1],
            'max_LAI': df['LAI'].max(),
            'max_dry_matter_fruit': df['dry_matter_fruit'].max(),
            'total_K_uptake': df['accumulated_K'].iloc[-1],
            'avg_soil_EC': df['soil_EC'].mean(),
            'avg_soil_water': df['soil_water_content'].mean(),
            'max_gray_mold_risk': df['gray_mold_risk'].max(),
            'avg_gray_mold_risk': df['gray_mold_risk'].mean(),
            'final_whitefly_population': df['whitefly_population'].iloc[-1],
            'stages': {}
        }
        
        # 生育期详情
        for stage in df['stage'].unique():
            stage_df = df[df['stage'] == stage]
            summary['stages'][stage] = {
                'start_day': int(stage_df['day'].min()),
                'end_day': int(stage_df['day'].max()),
                'duration': int(stage_df['day'].max() - stage_df['day'].min() + 1),
                'avg_LAI': float(stage_df['LAI'].mean()),
                'avg_dry_matter': float(stage_df['dry_matter_total'].mean())
            }
        
        # 预警统计
        total_alerts = sum([len(r.get('alerts', [])) for r in self.simulation_results])
        summary['total_alerts'] = total_alerts
        
        return summary
    
    def export_results(self, filepath: str, format: str = 'csv'):
        """
        导出模拟结果
        
        Args:
            filepath: 输出文件路径
            format: 输出格式 ('csv' 或 'json')
        """
        if not self.simulation_results:
            raise ValueError("没有模拟结果可导出，请先运行simulate()")
        
        df = pd.DataFrame(self.simulation_results)
        
        # 处理alerts列（转换为字符串）
        if 'alerts' in df.columns:
            df['alerts'] = df['alerts'].apply(lambda x: json.dumps(x, ensure_ascii=False))
        
        if format.lower() == 'csv':
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        elif format.lower() == 'json':
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def get_management_suggestions(self, day: int = None) -> List[Dict]:
        """
        获取管理建议
        
        Args:
            day: 指定天数，如果为None则返回当前所有建议
            
        Returns:
            管理建议列表
        """
        suggestions = []
        
        if day is None:
            # 返回所有建议
            for result in self.simulation_results:
                # 水肥建议
                water_fert_suggestions = result.get('suggestions', [])
                if water_fert_suggestions:
                    suggestions.extend(water_fert_suggestions)
                
                # 病虫害预警
                alerts = result.get('alerts', [])
                if alerts:
                    suggestions.extend(alerts)
        else:
            # 返回指定天数的建议
            if 0 < day <= len(self.simulation_results):
                result = self.simulation_results[day - 1]
                water_fert_suggestions = result.get('suggestions', [])
                if water_fert_suggestions:
                    suggestions.extend(water_fert_suggestions)
                alerts = result.get('alerts', [])
                if alerts:
                    suggestions.extend(alerts)
        
        return suggestions

