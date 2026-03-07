#!/bin/bash
# 验证解析结果
# 用法: 
#   bash docs/validate.sh <csv_file>              # 完整验证
#   bash docs/validate.sh <csv_file> --quick      # 快速验证
#   bash docs/validate.sh <csv_file> --full       # 完整验证+生成报告

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 默认输入文件
CSV_FILE="${1:-$PROJECT_ROOT/msg/chassis_decoded.csv}"

echo "=================================================="
echo "CAN报文验证工具"
echo "=================================================="
echo "输入文件: $CSV_FILE"
echo ""

# 执行验证
python3 "$PROJECT_ROOT/src/validator.py" "$@"

echo ""
echo "验证完成！"
