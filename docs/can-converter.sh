#!/usr/bin/env python3
import re
import sys

with open('chassis.asc', 'r') as f_in, open('chassis_candump.asc', 'w') as f_out:
    for line in f_in:
        line = line.strip()
        # 跳过注释行和元数据行
        if not line or line.startswith('//') or line.startswith('date') or line.startswith('base'):
            continue
        
        parts = line.split()
        if len(parts) < 14:
            continue
        
        timestamp = parts[0]
        can_id = parts[2]
        data_bytes = parts[6:14]  # 8个数据字节
        
        # 转换为 candump 格式
        candump_line = f"({timestamp}) can0 {can_id.upper()}#{''.join(data_bytes)}\n"
        f_out.write(candump_line)

print("转换完成！使用：sudo canplayer -I chassis_candump.asc -v")


