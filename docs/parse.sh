#!/bin/bash
# 解析ASC文件并自动验证
# 用法: bash docs/parse.sh [asc_file]

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 默认输入文件
ASC_FILE="${1:-$PROJECT_ROOT/msg/chassis.asc}"

echo "=================================================="
echo "CAN报文解析工具 - 自动解析并验证"
echo "=================================================="
echo "输入文件: $ASC_FILE"
echo ""

# 执行解析（自动验证）
python3 "$PROJECT_ROOT/src/cli.py" parse "$ASC_FILE" --validate

echo ""
echo "=================================================="
echo "解析完成！生成的文件："
echo "  1. *_decoded.csv - 解码结果"
echo "  2. *_errors.csv - 解析错误"
echo "  3. *_validation_report.csv - 验证报告（所有信号）"
echo "  4. *_validation_errors.csv - 验证错误（仅异常信号）"
echo "=================================================="
