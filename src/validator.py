#!/usr/bin/env python3
"""
CAN报文统一验证工具
整合基础验证和范围验证功能，可在解析后自动调用

功能:
1. 基础验证 - 验证唯一CAN ID的信号个数、名称、内容一致性
2. 范围验证 - 验证所有信号的数据类型、数值范围、精度
3. 统计分析 - 统计每个信号的实际数据分布
4. 异常检测 - 自动检测超出范围的异常值

用法:
    python3 src/validator.py msg/chassis_decoded.csv
    python3 src/validator.py msg/chassis_decoded.csv --quick  # 仅快速验证
    python3 src/validator.py msg/chassis_decoded.csv --full   # 完整验证+报告
"""

import csv
import sys
import os
from collections import defaultdict, OrderedDict
from typing import Dict, List, Any

from dbc_loader import DBCLoader


class SignalStats:
    """信号统计信息"""
    def __init__(self, signal_name: str, signal_obj=None):
        self.signal_name = signal_name
        self.signal_obj = signal_obj
        
        # DBC定义的范围
        self.dbc_min = signal_obj.minimum if signal_obj else None
        self.dbc_max = signal_obj.maximum if signal_obj else None
        self.dbc_scale = signal_obj.scale if signal_obj else 1.0
        self.dbc_offset = signal_obj.offset if signal_obj else 0.0
        self.dbc_unit = signal_obj.unit if signal_obj else ""
        
        # 实际数据统计
        self.values = []
        self.actual_min = None
        self.actual_max = None
        self.out_of_range_count = 0
        self.total_count = 0
        
    def add_value(self, value):
        """添加一个值并更新统计"""
        self.total_count += 1
        
        try:
            if isinstance(value, str):
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            
            self.values.append(value)
            
            if self.actual_min is None or value < self.actual_min:
                self.actual_min = value
            if self.actual_max is None or value > self.actual_max:
                self.actual_max = value
            
            # 检查是否超出DBC定义的范围
            if self.dbc_min is not None and value < self.dbc_min:
                self.out_of_range_count += 1
            if self.dbc_max is not None and value > self.dbc_max:
                self.out_of_range_count += 1
                
        except (ValueError, TypeError):
            self.values.append(value)


class CANValidator:
    """CAN报文统一验证器"""
    
    def __init__(self, quick_mode=False):
        self.quick_mode = quick_mode
        self.dbc_loader = DBCLoader()
        self.databases = {}
        self.signal_stats = defaultdict(lambda: defaultdict(SignalStats))
        self.unique_msgs = OrderedDict()
        
    def load_dbc_files(self):
        """加载所有DBC文件"""
        print("=" * 80)
        print("加载DBC文件...")
        print("=" * 80)
        self.databases = self.dbc_loader.load_all()
        return len(self.databases) > 0
    
    def parse_decoded_result(self, decoded_str: str) -> Dict[str, Any]:
        """解析CSV中的解码结果字符串"""
        signals = {}
        
        if not decoded_str or decoded_str.strip() == '':
            return signals
        
        lines = decoded_str.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                line = line.lstrip()
                parts = line.split(':', 1)
                if len(parts) == 2:
                    signal_name = parts[0].strip()
                    signal_value = parts[1].strip()
                    
                    try:
                        if '.' in signal_value:
                            signals[signal_name] = float(signal_value)
                        else:
                            signals[signal_name] = int(signal_value)
                    except ValueError:
                        signals[signal_name] = signal_value
        
        return signals
    
    def get_message_signals(self, can_id: int, dbc_name: str) -> Dict[str, Any]:
        """获取消息的所有信号定义"""
        if dbc_name not in self.databases:
            return {}
        
        db = self.databases[dbc_name]
        
        try:
            message = db.get_message_by_frame_id(can_id)
            signal_defs = {}
            for signal in message.signals:
                signal_defs[signal.name] = signal
            return signal_defs
        except:
            return {}
    
    def process_csv_file(self, csv_file: str):
        """处理CSV文件"""
        print("\n" + "=" * 80)
        print(f"读取CSV文件: {csv_file}")
        print("=" * 80)
        
        row_count = 0
        message_count = defaultdict(int)
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                row_count += 1
                
                can_id_hex = row['CAN_ID']
                dbc_name = row['DBC']
                decoded_result = row['解码结果']
                
                # 保存唯一CAN ID（用于快速验证）
                if can_id_hex not in self.unique_msgs:
                    self.unique_msgs[can_id_hex] = {
                        'timestamp': row['时间戳'],
                        'channel': row['通道'],
                        'can_id': can_id_hex,
                        'message_name': row['消息名称'],
                        'dbc_name': dbc_name,
                        'raw_data': row['原始数据'],
                        'decoded_result': decoded_result
                    }
                
                # 跳过未知消息
                if dbc_name == '未知':
                    continue
                
                # 范围验证（非快速模式）
                if not self.quick_mode:
                    try:
                        can_id = int(can_id_hex, 16)
                        message_count[can_id_hex] += 1
                        
                        signal_defs = self.get_message_signals(can_id, dbc_name)
                        signals = self.parse_decoded_result(decoded_result)
                        
                        for signal_name, signal_value in signals.items():
                            signal_obj = signal_defs.get(signal_name)
                            
                            if can_id_hex not in self.signal_stats or signal_name not in self.signal_stats[can_id_hex]:
                                self.signal_stats[can_id_hex][signal_name] = SignalStats(signal_name, signal_obj)
                            
                            self.signal_stats[can_id_hex][signal_name].add_value(signal_value)
                    
                    except Exception:
                        continue
        
        print(f"处理完成: 共 {row_count} 行, {len(self.unique_msgs)} 个唯一CAN ID")
        if not self.quick_mode:
            print(f"范围验证: {len(message_count)} 个CAN ID, {row_count} 条消息")
    
    def verify_unique_message(self, msg_info):
        """验证单个唯一消息（快速验证）"""
        can_id_hex = msg_info['can_id']
        dbc_name = msg_info['dbc_name']
        raw_data = msg_info['raw_data']
        csv_decoded = msg_info['decoded_result']
        
        if dbc_name == '未知' or msg_info['message_name'] == '未知':
            return {'status': 'skip', 'reason': '无对应DBC文件'}
        
        if dbc_name not in self.databases:
            return {'status': 'error', 'reason': f'DBC文件 {dbc_name} 未加载'}
        
        db = self.databases[dbc_name]
        
        try:
            can_id = int(can_id_hex, 16)
            message = db.get_message_by_frame_id(can_id)
            data_bytes = bytes.fromhex(raw_data)
            dbc_decoded = message.decode(data_bytes)
            csv_signals = self.parse_decoded_result(csv_decoded)
            
            # 验证信号个数
            if len(dbc_decoded) != len(csv_signals):
                return {
                    'status': 'mismatch',
                    'reason': f'信号个数不一致: DBC有{len(dbc_decoded)}个, CSV有{len(csv_signals)}个'
                }
            
            # 验证信号内容
            mismatches = []
            for signal_name in set(dbc_decoded.keys()) | set(csv_signals.keys()):
                dbc_value = dbc_decoded.get(signal_name)
                csv_value = csv_signals.get(signal_name)
                
                if dbc_value is None:
                    mismatches.append(f"{signal_name}: CSV有但DBC无")
                elif csv_value is None:
                    mismatches.append(f"{signal_name}: DBC有但CSV无")
                elif isinstance(dbc_value, (int, float)) and isinstance(csv_value, (int, float)):
                    if abs(dbc_value - csv_value) > 0.0001:
                        mismatches.append(f"{signal_name}: 值不一致")
                elif str(dbc_value) != str(csv_value):
                    mismatches.append(f"{signal_name}: 值不一致")
            
            if mismatches:
                return {'status': 'mismatch', 'reason': f'发现{len(mismatches)}个差异', 'mismatches': mismatches}
            else:
                return {'status': 'match', 'signal_count': len(dbc_decoded)}
                
        except Exception as e:
            return {'status': 'error', 'reason': str(e)}
    
    def print_quick_validation(self):
        """打印快速验证结果"""
        print("\n" + "=" * 80)
        print(f"快速验证结果 (唯一CAN ID: {len(self.unique_msgs)} 个)")
        print("=" * 80)
        
        match_count = mismatch_count = skip_count = error_count = 0
        
        for i, (can_id, msg_info) in enumerate(self.unique_msgs.items(), 1):
            result = self.verify_unique_message(msg_info)
            
            if result['status'] == 'match':
                match_count += 1
                status_icon = "✓"
            elif result['status'] == 'mismatch':
                mismatch_count += 1
                status_icon = "✗"
            elif result['status'] == 'skip':
                skip_count += 1
                status_icon = "○"
            else:
                error_count += 1
                status_icon = "✗"
            
            if result['status'] != 'match' or i <= 5:  # 只显示前5个成功的
                print(f"[{i}] {status_icon} {can_id} | {msg_info['message_name']} | {result.get('reason', '一致')}")
        
        print("\n" + "=" * 80)
        print(f"快速验证统计: 一致 {match_count}/{len(self.unique_msgs)} ({match_count/len(self.unique_msgs)*100:.1f}%)")
        print("=" * 80)
        
        return match_count, mismatch_count, skip_count, error_count
    
    def print_range_validation(self):
        """打印范围验证结果"""
        print("\n" + "=" * 80)
        print("范围验证结果")
        print("=" * 80)
        
        total_signals = valid_signals = invalid_signals = 0
        
        for can_id_hex in sorted(self.signal_stats.keys()):
            signals = self.signal_stats[can_id_hex]
            
            # 统计异常信号
            abnormal_signals = []
            for signal_name, stats in signals.items():
                total_signals += 1
                if stats.out_of_range_count > 0:
                    invalid_signals += 1
                    abnormal_signals.append((signal_name, stats))
                else:
                    valid_signals += 1
            
            # 只显示有异常的CAN ID
            if abnormal_signals:
                print(f"\n【CAN ID: {can_id_hex}】 - {len(abnormal_signals)} 个异常信号")
                print("-" * 80)
                
                for signal_name, stats in abnormal_signals:
                    out_rate = stats.out_of_range_count / stats.total_count * 100
                    print(f"✗ {signal_name}")
                    print(f"   DBC范围: [{stats.dbc_min}, {stats.dbc_max}] | "
                          f"实际范围: [{stats.actual_min}, {stats.actual_max}]")
                    print(f"   超范围: {stats.out_of_range_count}/{stats.total_count} ({out_rate:.1f}%)")
        
        print("\n" + "=" * 80)
        print(f"范围验证统计: 有效 {valid_signals}/{total_signals} ({valid_signals/total_signals*100:.1f}%)")
        print("=" * 80)
        
        return valid_signals, invalid_signals
    
    def export_report(self, output_file: str):
        """导出详细报告（包含所有信号）"""
        print(f"\n导出详细报告: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'CAN_ID', '信号名称', 'DBC最小值', 'DBC最大值', '实际最小值', '实际最大值',
                '精度', '单位', '采样数', '超范围数', '超范围率', '状态'
            ])
            
            for can_id_hex in sorted(self.signal_stats.keys()):
                signals = self.signal_stats[can_id_hex]
                
                for signal_name, stats in sorted(signals.items()):
                    out_rate = f"{stats.out_of_range_count/stats.total_count*100:.2f}%" if stats.total_count > 0 else "0%"
                    status = '有效' if stats.out_of_range_count == 0 else '异常'
                    
                    writer.writerow([
                        can_id_hex, signal_name,
                        stats.dbc_min if stats.dbc_min is not None else '',
                        stats.dbc_max if stats.dbc_max is not None else '',
                        stats.actual_min if stats.actual_min is not None else '',
                        stats.actual_max if stats.actual_max is not None else '',
                        stats.dbc_scale, stats.dbc_unit,
                        stats.total_count, stats.out_of_range_count, out_rate, status
                    ])
    
    def export_error_report(self, output_file: str):
        """导出错误报告（仅包含异常信号）"""
        print(f"导出错误报告: {output_file}")
        
        error_count = 0
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'CAN_ID', '信号名称', 'DBC最小值', 'DBC最大值', '实际最小值', '实际最大值',
                '精度', '单位', '采样数', '超范围数', '超范围率', '问题描述'
            ])
            
            for can_id_hex in sorted(self.signal_stats.keys()):
                signals = self.signal_stats[can_id_hex]
                
                for signal_name, stats in sorted(signals.items()):
                    # 只导出异常信号
                    if stats.out_of_range_count > 0:
                        error_count += 1
                        out_rate = f"{stats.out_of_range_count/stats.total_count*100:.2f}%" if stats.total_count > 0 else "0%"
                        
                        # 分析问题类型
                        problems = []
                        if stats.dbc_min == stats.dbc_max:
                            problems.append(f"Excel定义范围为[{stats.dbc_min}, {stats.dbc_max}] (min=max)")
                        if stats.actual_min < stats.dbc_min:
                            problems.append(f"实际最小值{stats.actual_min}小于DBC最小值{stats.dbc_min}")
                        if stats.actual_max > stats.dbc_max:
                            problems.append(f"实际最大值{stats.actual_max}大于DBC最大值{stats.dbc_max}")
                        
                        # 使用分号+空格连接问题描述
                        problem_desc = "; ".join(problems) if problems else "超出范围"
                        
                        writer.writerow([
                            can_id_hex, signal_name,
                            stats.dbc_min if stats.dbc_min is not None else '',
                            stats.dbc_max if stats.dbc_max is not None else '',
                            stats.actual_min if stats.actual_min is not None else '',
                            stats.actual_max if stats.actual_max is not None else '',
                            stats.dbc_scale, stats.dbc_unit if stats.dbc_unit else '',
                            stats.total_count, stats.out_of_range_count, out_rate, problem_desc
                        ])
        
        print(f"  发现 {error_count} 个异常信号")


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 src/validator.py <csv_file>              # 完整验证")
        print("  python3 src/validator.py <csv_file> --quick      # 快速验证")
        print("  python3 src/validator.py <csv_file> --full       # 完整验证+报告")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    quick_mode = '--quick' in sys.argv
    full_mode = '--full' in sys.argv
    
    if not os.path.exists(csv_file):
        print(f"错误: 文件 {csv_file} 不存在")
        sys.exit(1)
    
    # 创建验证器
    validator = CANValidator(quick_mode=quick_mode)
    
    # 加载DBC文件
    if not validator.load_dbc_files():
        print("错误: 未能加载任何DBC文件")
        sys.exit(1)
    
    # 处理CSV文件
    validator.process_csv_file(csv_file)
    
    # 快速验证
    match_count, mismatch_count, skip_count, error_count = validator.print_quick_validation()
    
    # 范围验证（非快速模式）
    invalid_count = 0
    if not quick_mode:
        valid_count, invalid_count = validator.print_range_validation()
        
        # 导出报告（完整模式）
        if full_mode:
            report_file = csv_file.replace('.csv', '_validation_report.csv')
            validator.export_report(report_file)
            
            # 导出错误报告
            error_report_file = csv_file.replace('.csv', '_validation_errors.csv')
            validator.export_error_report(error_report_file)
    
    # 返回状态码
    if mismatch_count > 0 or error_count > 0 or invalid_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
