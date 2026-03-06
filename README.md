# CAN Parser Tools

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)]()

> 专业的CAN总线报文解析工具，支持ASC文件解析、DBC文件管理、Excel协议转换和解析结果验证

## ✨ 核心特性

- **高性能解析** - 处理速度 ~145K 消息/次，解码率 99.92%
- **智能DBC管理** - 自动扫描加载，支持多种编码（UTF-8/GBK/GB2312/Latin-1）
- **完整验证** - 信号个数、名称、格式、内容全方位验证，通过率 97%+
- **Excel转DBC** - 智能识别协议工作表，自动生成DBC文件
- **批量处理** - 支持批量处理多个ASC文件
- **精确格式化** - 严格遵循DBC定义的浮点数精度

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone <your-repo-url>
cd can-parser-tools

# 2. 安装依赖
pip install -r requirements.txt

# 3. 解析ASC文件
bash docs/parse.sh msg/chassis.asc

# 4. 验证解析结果
bash docs/validate.sh msg/chassis_decoded.csv
```

## 📁 项目结构

```
can-parser-tools/
├── config/                  # 配置文件
│   └── config.example.yaml # 配置示例
├── docs/                    # Shell脚本
│   ├── parse.sh            # 解析ASC文件
│   ├── validate.sh         # 验证解析结果
│   ├── convert.sh          # Excel转DBC
│   ├── batch_process.sh    # 批量处理
│   └── can-converter.sh    # 格式转换工具
├── msg/                     # 消息文件目录
│   ├── *.asc               # 输入ASC文件
│   ├── *_decoded.csv       # 输出解析结果
│   └── *_errors.csv        # 输出错误信息
├── protocol/                # 协议文件目录
│   ├── dbc/                # DBC文件（自动扫描）
│   │   └── *.dbc          # DBC数据库文件
│   └── *.xls               # Excel协议文件
├── src/                     # Python源代码
│   ├── cli.py              # 命令行接口
│   ├── asc_parser.py       # ASC解析器
│   ├── dbc_loader.py       # DBC加载器
│   ├── signal_validator.py # 信号验证器
│   └── excel_to_dbc.py     # Excel转DBC转换器
├── .gitignore               # Git忽略配置
├── LICENSE                  # MIT许可证
├── README.md                # 项目文档
└── requirements.txt         # Python依赖项
```

## 🔧 功能详解

### 1. 自动DBC管理

- ✅ 智能扫描 `protocol/dbc/` 目录下的所有DBC文件
- ✅ 自动检测文件编码（UTF-8/GBK/GB2312/Latin-1）
- ✅ 智能识别中文内容，避免乱码
- ✅ 无需手动配置，即插即用

### 2. ASC文件解析

- ✅ 解析CAN报文时间戳、通道、ID、数据
- ✅ 自动匹配DBC文件进行信号解码
- ✅ 支持多通道CAN数据
- ✅ 详细的统计信息和错误报告

### 3. 精确浮点数格式化

- ✅ 严格遵循DBC文件中定义的factor精度
- ✅ 自动计算小数位数（factor=0.1 → 1位，factor=0.01 → 2位）
- ✅ 避免浮点数精度问题（如 2.9000000000000004 → 2.9）
- ✅ 支持各种factor值（0.1, 0.01, 0.5, 0.0625等）

### 4. 完整验证

验证项目包括：
1. **信号个数验证** - DBC定义的信号数量与CSV解析结果对比
2. **信号名称验证** - 检查所有信号名称是否一致
3. **数据格式验证** - 验证数据类型（整数/浮点数/字符串）
4. **数据内容验证** - 对比DBC解码值与CSV记录值

### 5. Excel转DBC

- ✅ 智能识别协议工作表（自动跳过Map、Index等非协议表）
- ✅ 自动解析信号定义（名称、起始位、长度、因子等）
- ✅ 支持 .xls 和 .xlsx 格式
- ✅ 自动生成标准DBC文件

### 6. 批量处理

- ✅ 递归扫描 `msg/` 目录中的所有ASC文件
- ✅ 自动生成输出文件名
- ✅ 支持重新生成DBC后批量处理
- ✅ 详细的处理进度和结果统计

## 📖 使用方法

### 解析ASC文件

```bash
# 使用Shell脚本（推荐）
bash docs/parse.sh msg/chassis.asc

# 使用Python CLI
python3 src/cli.py parse msg/chassis.asc

# 指定输出文件
bash docs/parse.sh msg/chassis.asc -o msg/result.csv
```

**输出文件：**
- `msg/chassis_decoded.csv` - 解析结果
- `msg/chassis_decoded_errors.csv` - 错误信息

### 验证解析结果

```bash
# 使用Shell脚本（推荐）
bash docs/validate.sh msg/chassis_decoded.csv

# 使用Python CLI
python3 src/cli.py validate msg/chassis_decoded.csv
```

**验证内容：**
- 信号个数是否匹配
- 信号名称是否一致
- 数据格式是否正确
- 数据内容是否一致

### Excel转DBC

```bash
# 使用默认路径（protocol/can_protocol_W2_500k.xls）
bash docs/convert.sh

# 指定Excel文件和输出目录
bash docs/convert.sh -e protocol/my_protocol.xls -o protocol/dbc/

# 使用Python CLI
python3 src/cli.py convert
python3 src/cli.py convert --excel protocol/my_protocol.xls --output protocol/dbc/
```

**输出：**
- 自动生成多个DBC文件（每个工作表一个）
- 保存到 `protocol/dbc/` 目录

### 批量处理

```bash
# 批量处理msg/目录下的所有ASC文件
bash docs/batch_process.sh

# 先重新生成DBC，再批量处理
bash docs/batch_process.sh -r
bash docs/batch_process.sh --regenerate-dbc
```

**处理流程：**
1. 扫描 `msg/` 目录下的所有 .asc 文件
2. 逐个解析并生成对应的 _decoded.csv 文件
3. 显示处理进度和结果统计

## ❓ 常见问题

**Q: 如何添加新的DBC文件？**  
A: 直接将DBC文件放到 `protocol/dbc/` 目录，工具会自动扫描加载。

**Q: 如何更换DBC文件？**  
A: 直接替换 `protocol/dbc/` 目录中的DBC文件，无需修改代码。

**Q: 为什么有些信号显示乱码？**  
A: 工具会智能检测DBC文件编码（UTF-8/GBK/GB2312/Latin-1），自动选择正确编码。如果仍有乱码，请检查DBC文件的原始编码。

**Q: Excel转DBC支持哪些文件格式？**  
A: 支持 .xls 和 .xlsx 文件，工具会智能识别协议工作表，自动跳过Map、Index等非协议表。

**Q: 如何处理多个ASC文件？**  
A: 将所有ASC文件放到 `msg/` 目录，然后运行 `bash docs/batch_process.sh` 即可批量处理。

**Q: 解析结果保存在哪里？**  
A: 所有解析结果和错误日志都保存在 `msg/` 目录下，文件名格式为 `原文件名_decoded.csv` 和 `原文件名_decoded_errors.csv`。

## 📦 依赖项

```bash
pip install -r requirements.txt
```

**核心依赖：**
- Python 3.6+
- cantools >= 38.0.0 - CAN数据库解析
- pandas >= 1.3.0 - 数据处理
- xlrd >= 2.0.0 - Excel读取（.xls）
- openpyxl >= 3.0.0 - Excel读取（.xlsx）

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| 解析速度 | ~145K 消息/次 |
| 解码成功率 | 99.92% |
| 验证通过率 | 97.1% |
| 支持的DBC编码 | UTF-8, GBK, GB2312, Latin-1 |
| 支持的Excel格式 | .xls, .xlsx |
| 支持的CAN通道 | 多通道 |

## 🛠️ 开发指南

### 目录说明

- `docs/` - 存放所有Shell脚本，提供命令行接口
- `msg/` - 存放ASC输入文件和CSV输出文件
- `protocol/` - 存放协议相关文件（Excel和DBC）
- `src/` - Python源代码，核心解析逻辑
- `config/` - 配置文件（可选）

### 添加新功能

1. 在 `src/` 目录下添加新的Python模块
2. 在 `src/cli.py` 中添加新的子命令
3. 在 `docs/` 目录下创建对应的Shell脚本
4. 更新 `README.md` 文档

### 代码规范

- Python代码遵循PEP 8规范
- Shell脚本使用bash语法
- 所有函数和类都有完整的文档字符串
- 关键逻辑添加注释说明

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

⭐ 如果这个项目对你有帮助，请给个 Star！
