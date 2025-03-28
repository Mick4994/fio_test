#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import json
import csv
import time
from datetime import datetime
import itertools
import argparse
from concurrent.futures import ProcessPoolExecutor
import matplotlib.pyplot as plt
import numpy as np

# 导入 script.py 中的函数
from script import run_fio_test

plt.rcParams['font.sans-serif'] = ['SimHei'] # 设置字体为黑体
plt.rcParams['axes.unicode_minus'] = False # 解决负号显示为方块的问题


def get_iops_from_results(results):
    """从 FIO 结果中提取 IOPS 值"""
    if not results:
        return 0
    
    jobs = results.get('jobs', [])
    if not jobs:
        return 0
    
    job = jobs[0]
    
    # 根据测试类型获取 IOPS
    read_iops = job.get('read', {}).get('iops', 0)
    write_iops = job.get('write', {}).get('iops', 0)
    
    # 返回总 IOPS (读+写)
    return read_iops + write_iops

def run_parameter_test(device, test_params, result_file='iops_test_results.csv'):
    """
    使用不同参数组合运行测试并记录结果
    
    参数:
        device: 要测试的设备路径
        test_params: 包含测试参数的字典
        result_file: 结果 CSV 文件路径
    """
    # 创建结果文件并写入标题行
    with open(result_file, 'w', newline='') as f:
        fieldnames = ['rw', 'bs', 'iodepth', 'numjobs', 'ioengine', 'iops', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
    
    # 生成所有参数组合
    rw_modes = test_params.get('rw', ['randread'])
    block_sizes = test_params.get('bs', ['4k'])
    io_depths = test_params.get('iodepth', [32])
    num_jobs = test_params.get('numjobs', [4])
    io_engines = test_params.get('ioengine', ['libaio'])
    
    # 计算总测试数
    total_tests = len(rw_modes) * len(block_sizes) * len(io_depths) * len(num_jobs) * len(io_engines)
    print(f"将执行 {total_tests} 个测试组合")
    
    # 记录最佳结果
    best_iops = 0
    best_params = {}
    
    # 遍历所有参数组合
    test_count = 0
    for rw, bs, iodepth, numjob, ioengine in itertools.product(
        rw_modes, block_sizes, io_depths, num_jobs, io_engines):
        
        test_count += 1
        print(f"\n测试 {test_count}/{total_tests}:")
        print(f"参数: rw={rw}, bs={bs}, iodepth={iodepth}, numjobs={numjob}, ioengine={ioengine}")
        
        # 运行测试
        test_name = f"iops_test_{rw}_{bs}_{iodepth}_{numjob}_{ioengine}"
        results, _ = run_fio_test(
            test_name=test_name,
            filename=device,
            size='1G',  # 使用固定大小以加快测试
            rw=rw,
            bs=bs,
            iodepth=iodepth,
            numjobs=numjob,
            runtime=30,  # 使用较短的运行时间以加快测试
            ioengine=ioengine
        )
        
        # 提取 IOPS 并记录结果
        iops = get_iops_from_results(results)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 写入 CSV
        with open(result_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow({
                'rw': rw,
                'bs': bs,
                'iodepth': iodepth,
                'numjobs': numjob,
                'ioengine': ioengine,
                'iops': iops,
                'timestamp': timestamp
            })
        
        # 更新最佳结果
        if iops > best_iops:
            best_iops = iops
            best_params = {
                'rw': rw,
                'bs': bs,
                'iodepth': iodepth,
                'numjobs': numjob,
                'ioengine': ioengine,
                'iops': iops
            }
        
        # 显示当前最佳结果
        print(f"当前最佳 IOPS: {best_iops}")
        print(f"最佳参数: {best_params}")
        
        # 短暂休息，避免设备过热
        time.sleep(5)
    
    return best_params

def visualize_results(result_file='iops_test_results.csv'):
    """可视化测试结果"""
    # 读取 CSV 文件
    data = []
    with open(result_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    
    if not data:
        print("没有数据可视化")
        return
    
    # 提取不同参数的唯一值
    rw_modes = set(row['rw'] for row in data)
    block_sizes = sorted(set(row['bs'] for row in data), key=lambda x: int(x[:-1]))
    io_engines = set(row['ioengine'] for row in data)
    io_depths = set(int(row['iodepth']) for row in data)
    # print(f"发现的参数: rw={rw_modes}, bs={block_sizes}, ioengine={io_engines}, iodepth={io_depths}")
    # exit(0)
    
    # 为每种读写模式创建一个图表
    for rw in rw_modes:
        # 为每个 IO 深度创建一个图表
        for iodepth in io_depths:
            plt.figure(figsize=(15, 8))
            
            # 筛选当前读写模式和 IO 深度的数据
            filtered_data = [row for row in data if row['rw'] == rw and int(row['iodepth']) == iodepth]
            if not filtered_data:
                continue
            
            # 准备柱状图数据
            bar_positions = []
            bar_heights = []
            bar_labels = []
            bar_colors = []
            
            # 颜色映射 - 修复 get_cmap 问题
            try:
                # 尝试新版本的方法
                from matplotlib import colormaps
                color_map = colormaps['tab10']
            except (ImportError, AttributeError):
                # 回退到旧版本的方法
                color_map = plt.cm.tab10
            
            # 计算每个块大小的组宽度
            group_width = 0.8
            bar_width = group_width / len(io_engines)
            
            # 按块大小和 IO 引擎分组
            for i, bs in enumerate(block_sizes):
                for j, engine in enumerate(io_engines):
                    # 筛选当前块大小和 IO 引擎的数据
                    bs_engine_data = [row for row in filtered_data if row['bs'] == bs and row['ioengine'] == engine]
                    
                    # 计算该组合的平均 IOPS
                    if bs_engine_data:
                        avg_iops = sum(float(row['iops']) for row in bs_engine_data) / len(bs_engine_data)
                        
                        # 计算柱的位置
                        position = i + (j - len(io_engines)/2 + 0.5) * bar_width
                        
                        bar_positions.append(position)
                        bar_heights.append(avg_iops)
                        bar_labels.append(f"{bs}-{engine}")
                        bar_colors.append(color_map(j % 10))  # 确保索引不超过颜色表范围
            
            # 绘制柱状图
            bars = plt.bar(bar_positions, bar_heights, width=bar_width, color=bar_colors)
            
            # 设置 x 轴标签
            plt.xticks(range(len(block_sizes)), block_sizes)
            
            # 添加图例 - 修复颜色映射问题
            legend_handles = [plt.Rectangle((0,0),1,1, color=color_map(j % 10)) for j in range(len(io_engines))]
            plt.legend(legend_handles, io_engines, title="IO 引擎")
            
            # 在柱上显示数值
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', rotation=0, fontsize=8)
            
            plt.title(f"{rw} 模式下不同块大小和 IO 引擎的 IOPS (IO 深度={iodepth})")
            plt.xlabel("块大小")
            plt.ylabel("IOPS")
            plt.grid(True, axis='y')
            
            # 保存图表
            plt.tight_layout()
            plt.savefig(f"result/iops_{rw}_depth{iodepth}_results.png")
            print(f"已保存图表: iops_{rw}_depth{iodepth}_results.png")
    
    # 创建一个汇总图表，显示不同读写模式的最佳 IOPS
    plt.figure(figsize=(12, 8))
    
    # 为每种读写模式找到最佳 IOPS
    best_iops_by_rw = {}
    best_params_by_rw = {}
    for rw in rw_modes:
        rw_data = [row for row in data if row['rw'] == rw]
        if rw_data:
            best_row = max(rw_data, key=lambda x: float(x['iops']))
            best_iops = float(best_row['iops'])
            best_iops_by_rw[rw] = best_iops
            best_params_by_rw[rw] = f"bs={best_row['bs']}, depth={best_row['iodepth']}, jobs={best_row['numjobs']}, engine={best_row['ioengine']}"
    
    # 绘制条形图
    bars = plt.bar(best_iops_by_rw.keys(), best_iops_by_rw.values(), color='skyblue')
    plt.title("各读写模式的最佳 IOPS")
    plt.xlabel("读写模式")
    plt.ylabel("IOPS")
    plt.grid(True, axis='y')
    
    # 在条形上显示具体数值和最佳参数
    for i, (rw, iops) in enumerate(best_iops_by_rw.items()):
        plt.text(i, iops, f"{int(iops)}", ha='center', va='bottom', fontsize=10)
        plt.text(i, iops/2, best_params_by_rw[rw], ha='center', va='center', fontsize=8, 
                 rotation=90, color='white', fontweight='bold')
    
    # 保存图表
    plt.tight_layout()
    plt.savefig("result/best_iops_by_rw.png")
    print("已保存汇总图表: best_iops_by_rw.png")
    
    # 创建一个热力图，显示不同参数组合的 IOPS
    for rw in rw_modes:
        rw_data = [row for row in data if row['rw'] == rw]
        if not rw_data:
            continue
            
        for engine in io_engines:
            engine_data = [row for row in rw_data if row['ioengine'] == engine]
            if not engine_data:
                continue
                
            # 创建热力图数据
            heatmap_data = np.zeros((len(block_sizes), len(io_depths)))
            
            for i, bs in enumerate(block_sizes):
                for j, depth in enumerate(io_depths):
                    # 筛选当前块大小和 IO 深度的数据
                    filtered = [row for row in engine_data if row['bs'] == bs and int(row['iodepth']) == depth]
                    if filtered:
                        # 计算平均 IOPS
                        avg_iops = sum(float(row['iops']) for row in filtered) / len(filtered)
                        heatmap_data[i, j] = avg_iops
            
            # 绘制热力图
            plt.figure(figsize=(10, 8))
            plt.imshow(heatmap_data, cmap='hot', aspect='auto')
            
            # 添加颜色条
            cbar = plt.colorbar()
            cbar.set_label('IOPS')
            
            # 设置坐标轴标签
            plt.xticks(range(len(io_depths)), io_depths)
            plt.yticks(range(len(block_sizes)), block_sizes)
            
            plt.title(f"{rw} 模式下不同块大小和 IO 深度的 IOPS (引擎={engine})")
            plt.xlabel("IO 深度")
            plt.ylabel("块大小")
            
            # 在每个单元格中显示 IOPS 值
            for i in range(len(block_sizes)):
                for j in range(len(io_depths)):
                    if heatmap_data[i, j] > 0:
                        plt.text(j, i, f"{int(heatmap_data[i, j])}", 
                                ha="center", va="center", color="white" if heatmap_data[i, j] < np.max(heatmap_data)/2 else "black")
            
            # 保存热力图
            plt.tight_layout()
            plt.savefig(f"result/heatmap_{rw}_{engine}.png")
            print(f"已保存热力图: heatmap_{rw}_{engine}.png")

def main():
    parser = argparse.ArgumentParser(description='SSD IOPS 优化测试工具')
    parser.add_argument('--device', type=str, required=True, help='要测试的设备路径 (例如 /dev/sda)')
    parser.add_argument('--quick', action='store_true', help='运行快速测试 (较少的参数组合)')
    parser.add_argument('--visualize', action='store_true', help='仅可视化现有结果，不运行测试')
    
    args = parser.parse_args()
    
    result_file = 'result/iops_test_results.csv'
    
    # 如果只需可视化，则跳过测试
    if args.visualize:
        if os.path.exists(result_file):
            visualize_results(result_file)
        else:
            print(f"错误: 结果文件 {result_file} 不存在")
        return
    
    # 检查设备是否存在
    if not os.path.exists(args.device):
        print(f"错误: 设备 {args.device} 不存在")
        return
    
    # 定义测试参数
    if args.quick:
        # 快速测试使用较少的参数组合
        test_params = {
            'rw': ['randread', 'randwrite'],
            'bs': ['4k', '64k'],
            'iodepth': [1, 16, 64],
            'numjobs': [1, 4],
            'ioengine': ['libaio', 'io_uring']
        }
    else:
        # 完整测试使用更多参数组合
        test_params = {
            'rw': ['randread', 'randwrite', 'read', 'write', 'randrw'],
            'bs': ['4k', '8k', '16k'],
            'iodepth': [16, 32, 64],
            'numjobs': [4, 8, 16],
            'ioengine': ['libaio', 'io_uring', 'sync', 'psync']
        }
    
    # 运行参数测试
    best_params = run_parameter_test(args.device, test_params, result_file)
    
    # 显示最佳结果
    print("\n测试完成!")
    print(f"最佳 IOPS: {best_params['iops']}")
    print("最佳参数组合:")
    for key, value in best_params.items():
        if key != 'iops':
            print(f"  {key}: {value}")
    
    # 可视化结果
    visualize_results(result_file)
    
    # 提供最佳参数的命令行示例
    cmd_example = (f"python script.py --device {args.device} "
                  f"--rw {best_params['rw']} "
                  f"--bs {best_params['bs']} "
                  f"--iodepth {best_params['iodepth']} "
                  f"--numjobs {best_params['numjobs']} "
                  f"--ioengine {best_params['ioengine']}")
    
    print("\n使用最佳参数运行测试的命令:")
    print(cmd_example)

if __name__ == "__main__":
    main() 