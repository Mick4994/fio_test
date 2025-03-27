#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import argparse
import json
import time
from datetime import datetime

def run_fio_test(test_name, filename, size, rw, bs, iodepth, numjobs, runtime, direct=1, ioengine="libaio"):
    """
    运行单个 FIO 测试并返回结果
    
    参数:
        test_name: 测试名称
        filename: 测试文件路径
        size: 测试文件大小
        rw: 读写模式 (read, write, randread, randwrite, randrw)
        bs: 块大小
        iodepth: IO 队列深度
        numjobs: 并发任务数
        runtime: 测试运行时间(秒)
        direct: 是否使用直接 IO (0 或 1)
        ioengine: IO 引擎类型 (libaio, io_uring, sync 等)
    """
    output_format = "json"
    output_file = f"result/fio_results_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    cmd = [
        "fio",
        f"--name={test_name}",
        f"--filename={filename}",
        f"--size={size}",
        f"--rw={rw}",
        f"--bs={bs}",
        f"--iodepth={iodepth}",
        f"--numjobs={numjobs}",
        f"--runtime={runtime}",
        f"--direct={direct}",
        f"--ioengine={ioengine}",
        "--group_reporting=1",
        f"--output-format={output_format}",
        f"--output={output_file}"
    ]
    
    print(f"执行测试: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"测试完成，结果保存在 {output_file}")
        
        # 读取并解析结果
        with open(output_file, 'r') as f:
            results = json.load(f)
        
        return results, output_file
    except subprocess.CalledProcessError as e:
        print(f"测试执行失败: {e}")
        return None, None

def print_results_summary(results):
    """打印测试结果摘要"""
    if not results:
        return
    
    jobs = results.get('jobs', [])
    if not jobs:
        return
    
    job = jobs[0]
    
    print("\n测试结果摘要:")
    print("-" * 50)
    
    # 读取性能
    read_stats = job.get('read', {})
    if read_stats:
        print(f"读取性能:")
        print(f"  IOPS: {read_stats.get('iops', 0):.2f}")
        print(f"  带宽: {read_stats.get('bw', 0):.2f} KB/s ({read_stats.get('bw', 0)/1024:.2f} MB/s)")
        print(f"  延迟: {read_stats.get('lat_ns', {}).get('mean', 0)/1000000:.2f} ms")
    
    # 写入性能
    write_stats = job.get('write', {})
    if write_stats:
        print(f"写入性能:")
        print(f"  IOPS: {write_stats.get('iops', 0):.2f}")
        print(f"  带宽: {write_stats.get('bw', 0):.2f} KB/s ({write_stats.get('bw', 0)/1024:.2f} MB/s)")
        print(f"  延迟: {write_stats.get('lat_ns', {}).get('mean', 0)/1000000:.2f} ms")
    
    print("-" * 50)

def main():
    parser = argparse.ArgumentParser(description='SSD 性能测试工具')
    parser.add_argument('--device', type=str, required=True, help='要测试的设备路径 (例如 /dev/sda)')
    parser.add_argument('--size', type=str, default='1G', help='测试文件大小 (默认: 1G)')
    parser.add_argument('--rw', type=str, default='randread', 
                        choices=['read', 'write', 'randread', 'randwrite', 'randrw'],
                        help='读写模式 (默认: randread)')
    parser.add_argument('--bs', type=str, default='4k', help='块大小 (默认: 4k)')
    parser.add_argument('--iodepth', type=int, default=32, help='IO 队列深度 (默认: 32)')
    parser.add_argument('--numjobs', type=int, default=4, help='并发任务数 (默认: 4)')
    parser.add_argument('--runtime', type=int, default=60, help='测试运行时间(秒) (默认: 60)')
    parser.add_argument('--ioengine', type=str, default='libaio', 
                        choices=['libaio', 'io_uring', 'sync', 'psync', 'vsync'],
                        help='IO 引擎类型 (默认: libaio)')
    
    args = parser.parse_args()
    
    # 检查设备是否存在
    if not os.path.exists(args.device):
        print(f"错误: 设备 {args.device} 不存在")
        return
    
    test_name = f"ssd_test_{args.rw}"
    
    # 运行测试
    results, output_file = run_fio_test(
        test_name=test_name,
        filename=args.device,
        size=args.size,
        rw=args.rw,
        bs=args.bs,
        iodepth=args.iodepth,
        numjobs=args.numjobs,
        runtime=args.runtime,
        ioengine=args.ioengine
    )
    
    # 打印结果摘要
    if results:
        print_results_summary(results)
        print(f"详细结果已保存到 {output_file}")

if __name__ == "__main__":
    main() 