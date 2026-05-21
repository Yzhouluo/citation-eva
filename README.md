# citation-eva

学术论文引用质量评估系统。给定经 GROBID 处理的学术论文，对每条引用从语义和结构维度进行多维评分，评分结果可作为引用网络（JournalRank）的边权重，支持加权 SpringRank 计算。

## 功能概览

- **PDF 结构化提取**：通过 GROBID 将 PDF 转换为 TEI XML、JSON 和 Markdown
- **引用上下文构建**：提取引用句、上下文窗口、章节标签及被引文献元数据
- **非学术信号检测**：规则识别自引、悬空引用、撤稿、同机构引用
- **多智能体评估流水线**：L1 规则路由 → L2 轻量意图预分类 → L3 评估 Agent + Critic Agent + 置信度门控
- **结构化输出**：每篇论文输出 `citation_eval.json`，可选生成 `report.md`

## 项目结构

```
citation-eva/
├── docker-compose.yml          # GROBID 服务（GPU 加速）
├── pdf2json/                   # PDF → 结构化数据流水线
│   ├── pdf2tei-json-md.py      # 主处理脚本
│   ├── QUICK_REFERENCE.md      # 参数速查
│   ├── input/pdfs/             # 放置待处理 PDF（已 gitignore）
│   └── output/                 # 处理结果（已 gitignore）
│       ├── hash_index.json     # 全局索引
│       └── <MD5_HASH>/         # 每篇论文子目录
│           ├── paper.json
│           ├── paper.grobid.tei.xml
│           └── paper.md
├── scripts/
│   └── md5_hash.py             # 文件 MD5 工具
└── docs/
    └── superpowers/specs/      # 设计规范文档
```

## 快速开始

### 依赖

- Python 3.8+
- Docker + NVIDIA Container Toolkit（GPU 加速 GROBID）
- `grobid_client` Python 包

```bash
pip install grobid-client-python
```

### 第一步：启动 GROBID 服务

```bash
docker compose up -d
```

GROBID 启动后监听 `http://localhost:8070`。

### 第二步：处理 PDF

将 PDF 文件放入 `pdf2json/input/pdfs/`，然后运行：

```bash
cd pdf2json
python pdf2tei-json-md.py
```

**完整参数：**

```bash
python pdf2tei-json-md.py \
    -i ./input/pdfs \      # PDF 输入目录
    -o ./output \          # 结果输出目录
    -s http://localhost:8070 \  # GROBID 服务地址
    -c 8 \                 # 并发数
    -v                     # 详细日志
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-i` / `--input` | `./input/pdfs` | PDF 输入目录 |
| `-o` / `--output` | `./output` | 结果输出目录 |
| `-s` / `--server` | `http://localhost:8070` | GROBID 服务地址 |
| `-c` / `--concurrency` | `4` | 并发处理数量 |
| `-v` / `--verbose` | 关 | 显示详细日志 |

### 工具脚本

```bash
# 计算文件 MD5
python scripts/md5_hash.py <file_path>
```

## 输出格式

每篇论文生成三个文件，存放在以 `biblio.hash`（MD5）命名的子目录中：

| 文件 | 说明 |
|------|------|
| `paper.json` | 结构化元数据（标题、作者、DOI、引用列表等） |
| `paper.grobid.tei.xml` | GROBID 原始 TEI XML |
| `paper.md` | Markdown 版本 |

`hash_index.json` 为全局索引，记录每篇论文的 hash → 元数据映射。

## 数据流

```
PDF 文件
  └─▶ GrobidClient.process()        发送至 GROBID，写入平铺输出文件
        └─▶ organize_files_by_hash() 按 biblio.hash 整理到子目录
              └─▶ create_hash_index() 生成 hash_index.json
```

## 引用评估系统架构（规划中）

```
Context Builder          [纯 Python，无 LLM]
  ├── GROBID JSON 解析器
  ├── 引用上下文提取
  ├── 非学术信号检测
  └── 特征附加 + Token 预算控制
          ↓
LLM 抽象层              [provider 无关]
  ├── AnthropicProvider
  └── OpenAIProvider
          ↓
多智能体评估流水线
  ├── L1 规则路由
  ├── L2 轻量意图预分类
  ├── L3 评估 Agent + Critic Agent
  └── 置信度门控
          ↓
输出：citation_eval.json / report.md
```

> 技术约束：不使用 LangChain / LangGraph / AutoGen，直接调用 Anthropic / OpenAI SDK；结构化输出通过 Pydantic + provider 原生 JSON Schema 实现。

## 注意事项

- `*/output/` 和 `*/input/` 已加入 `.gitignore`，处理结果和源 PDF 不会提交到仓库。
- GROBID 需要 NVIDIA GPU 支持，请确保已安装 NVIDIA Container Toolkit。
- 无法提取 hash 的论文将存入 `unknown_N/` 目录。
