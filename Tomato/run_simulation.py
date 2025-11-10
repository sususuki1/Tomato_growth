"""
番茄生长模型运行脚本
执行完整的生长模拟并生成结果
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tomato_growth_model import TomatoGrowthSimulator

# 设置matplotlib支持中文
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def main():
    """主函数"""
    print("=" * 60)
    print("番茄（秋季）生长模型 - 模拟运行")
    print("=" * 60)
    
    # 1. 创建模拟器
    print("\n[1/5] 初始化模拟器...")
    planting_date = '2025-09-01'  # 定植日期
    simulator = TomatoGrowthSimulator(planting_date=planting_date)
    print(f"   定植日期: {planting_date}")
    print("   [OK] 模拟器初始化完成")
    
    # 2. 生成示例气象数据
    print("\n[2/5] 生成气象数据...")
    weather_data = simulator.generate_default_weather_data(
        start_date=planting_date,
        days=120  # 模拟120天
    )
    print(f"   生成了 {len(weather_data)} 天的气象数据")
    print(f"   日期范围: {weather_data['date'].min()} 至 {weather_data['date'].max()}")
    print("   [OK] 气象数据生成完成")
    
    # 3. 执行模拟
    print("\n[3/5] 执行生长模拟...")
    print("   参数设置:")
    print("   - 灌溉频率: 2次/天")
    print("   - 单次灌溉量: 5.0 mm")
    print("   - 施肥EC值: 2.15 mS/cm")
    
    results = simulator.simulate(
        weather_data=weather_data,
        irrigation_frequency=2,  # 每日2次灌溉
        irrigation_amount=5.0,    # 每次5mm
        fertilizer_EC=2.15       # EC值2.15 mS/cm
    )
    print(f"   模拟完成，共 {len(results)} 天的数据")
    print("   [OK] 模拟执行完成")
    
    # 4. 获取并显示摘要
    print("\n[4/5] 生成模拟摘要...")
    summary = simulator.get_summary()
    
    print("\n" + "=" * 60)
    print("模拟摘要")
    print("=" * 60)
    print(f"总模拟天数: {summary.get('total_days', 0)} 天")
    print(f"最终积温: {summary.get('final_GDD', 0):.1f} 度日")
    print(f"最终LAI: {summary.get('final_LAI', 0):.2f}")
    print(f"最终总干物质: {summary.get('final_dry_matter_total', 0):.1f} g/株")
    print(f"最终果实干物质: {summary.get('final_dry_matter_fruit', 0):.1f} g/株")
    print(f"最大LAI: {summary.get('max_LAI', 0):.2f}")
    print(f"累计钾吸收: {summary.get('total_K_uptake', 0):.2f} g/株")
    print(f"平均土壤EC: {summary.get('avg_soil_EC', 0):.2f} mS/cm")
    print(f"平均土壤含水量: {summary.get('avg_soil_water', 0):.2%}")
    print(f"最大灰霉病风险: {summary.get('max_gray_mold_risk', 0):.1f}")
    print(f"最终白粉虱种群: {summary.get('final_whitefly_population', 0):.0f}")
    print(f"总预警次数: {summary.get('total_alerts', 0)}")
    
    # 生育期详情
    if 'stages' in summary:
        print("\n生育期详情:")
        for stage, info in summary['stages'].items():
            print(f"  {info.get('name', stage)}: "
                  f"第 {info['start_day']} - {info['end_day']} 天 "
                  f"(持续 {info['duration']} 天), "
                  f"平均LAI: {info['avg_LAI']:.2f}")
    
    print("=" * 60)
    print("   [OK] 摘要生成完成")
    
    # 5. 生成可视化图表
    print("\n[5/5] 生成可视化图表...")
    try:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('番茄生长模拟结果', fontsize=16, fontweight='bold')
        
        # 转换为日期格式
        if 'date' in results.columns:
            dates = pd.to_datetime(results['date'])
        else:
            dates = range(len(results))
        
        # 1. 积温和LAI
        ax1 = axes[0, 0]
        ax1_twin = ax1.twinx()
        line1 = ax1.plot(dates, results['GDD'], 'b-', label='累积积温', linewidth=2)
        line2 = ax1_twin.plot(dates, results['LAI'], 'r-', label='LAI', linewidth=2)
        ax1.set_xlabel('日期')
        ax1.set_ylabel('累积积温 (度日)', color='b')
        ax1_twin.set_ylabel('LAI', color='r')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1_twin.tick_params(axis='y', labelcolor='r')
        ax1.set_title('积温与LAI动态')
        ax1.grid(True, alpha=0.3)
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')
        
        # 2. 干物质积累
        ax2 = axes[0, 1]
        ax2.plot(dates, results['dry_matter_total'], 'g-', label='总干物质', linewidth=2)
        ax2.plot(dates, results['dry_matter_leaf'], 'b--', label='叶片', linewidth=1.5)
        ax2.plot(dates, results['dry_matter_stem'], 'c--', label='茎', linewidth=1.5)
        ax2.plot(dates, results['dry_matter_fruit'], 'r--', label='果实', linewidth=1.5)
        ax2.plot(dates, results['dry_matter_root'], 'm--', label='根系', linewidth=1.5)
        ax2.set_xlabel('日期')
        ax2.set_ylabel('干物质量 (g/株)')
        ax2.set_title('干物质积累动态')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 水肥状态
        ax3 = axes[1, 0]
        ax3_twin = ax3.twinx()
        line3 = ax3.plot(dates, results['soil_EC'], 'b-', label='土壤EC', linewidth=2)
        line4 = ax3_twin.plot(dates, results['soil_water_content'] * 100, 'g-', 
                              label='土壤含水量', linewidth=2)
        ax3.set_xlabel('日期')
        ax3.set_ylabel('土壤EC (mS/cm)', color='b')
        ax3_twin.set_ylabel('土壤含水量 (%)', color='g')
        ax3.tick_params(axis='y', labelcolor='b')
        ax3_twin.tick_params(axis='y', labelcolor='g')
        ax3.set_title('水肥状态动态')
        ax3.grid(True, alpha=0.3)
        lines = line3 + line4
        labels = [l.get_label() for l in lines]
        ax3.legend(lines, labels, loc='upper left')
        
        # 4. 病虫害风险
        ax4 = axes[1, 1]
        ax4_twin = ax4.twinx()
        line5 = ax4.plot(dates, results['gray_mold_risk'], 'r-', label='灰霉病风险', linewidth=2)
        line6 = ax4_twin.plot(dates, results['whitefly_population'], 'orange', 
                              label='白粉虱种群', linewidth=2)
        ax4.set_xlabel('日期')
        ax4.set_ylabel('灰霉病风险指数', color='r')
        ax4_twin.set_ylabel('白粉虱种群数量', color='orange')
        ax4.tick_params(axis='y', labelcolor='r')
        ax4_twin.tick_params(axis='y', labelcolor='orange')
        ax4.set_title('病虫害风险动态')
        ax4.grid(True, alpha=0.3)
        # 添加风险阈值线
        ax4.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='中等风险')
        ax4.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='高风险')
        lines = line5 + line6
        labels = [l.get_label() for l in lines]
        ax4.legend(lines, labels, loc='upper left')
        
        plt.tight_layout()
        
        # 保存图表
        output_file = 'growth_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   图表已保存: {output_file}")
        print("   [OK] 可视化图表生成完成")
        
        # 可选：显示图表（如果在交互式环境中）
        # plt.show()
        
    except Exception as e:
        print(f"   警告: 图表生成失败 - {e}")
        print("   继续执行...")
    
    # 6. 导出结果
    print("\n[6/6] 导出结果...")
    output_csv = 'simulation_results.csv'
    simulator.export_results(output_csv, format='csv')
    print(f"   结果已导出: {output_csv}")
    print("   [OK] 结果导出完成")
    
    # 完成
    print("\n" + "=" * 60)
    print("模拟完成！")
    print("=" * 60)
    print(f"输出文件:")
    print(f"  - {output_csv} (模拟结果数据)")
    if os.path.exists('growth_analysis.png'):
        print(f"  - growth_analysis.png (可视化图表)")
    print("\n提示: 可以使用Excel或其他工具打开CSV文件查看详细数据")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



