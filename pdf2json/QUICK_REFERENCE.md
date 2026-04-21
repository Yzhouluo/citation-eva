# 🚀 快速参考 - pdf2tei-json-md.py

## 基本用法

```bash
# 1. 使用默认目录（最简单）
python pdf2tei-json-md.py

# 2. 指定 input 和 output 目录
python pdf2tei-json-md.py -i /path/to/pdfs -o /path/to/output

# 3. 完整参数示例
python pdf2tei-json-md.py \
    -i /home/yzl/Desktop/projects/citation-eva/pdf2json/input/pdfs \
    -o /home/yzl/Desktop/projects/citation-eva/pdf2json/output \
    -s http://localhost:8070 \
    -c 8 \
    -v

# 4. 显示帮助信息
python pdf2tei-json-md.py -h
```

## 参数说明

| 参数 | 长参数 | 类型 | 默认值 | 说明 |
|------|--------|------|--------|------|
| `-i` | `--input` | str | `./input/pdfs` | PDF输入目录 |
| `-o` | `--output` | str | `./output` | 输出目录 |
| `-s` | `--server` | str | `http://localhost:8070` | GROBID服务地址 |
| `-c` | `--concurrency` | int | `4` | 并发处理数量 |
| `-v` | `--verbose` | flag | 无 | 显示详细日志 |

## 示例场景

### 场景1: 从任意目录处理指定的PDF文件夹
```bash
python /home/yzl/Desktop/projects/citation-eva/pdf2json/pdf2tei-json-md.py \
    -i /home/user/my-pdfs \
    -o /home/user/my-output
```

### 场景2: 本地开发（脚本目录执行）
```bash
cd /home/yzl/Desktop/projects/citation-eva/pdf2json
python pdf2tei-json-md.py
```

### 场景3: 提高处理速度（增加并发）
```bash
python pdf2tei-json-md.py -i ./pdfs -o ./output -c 8
```

### 场景4: 连接到远程GROBID服务
```bash
python pdf2tei-json-md.py \
    -i ./pdfs \
    -o ./output \
    -s http://grobid-server:8070
```

### 场景5: 调试（显示详细日志）
```bash
python pdf2tei-json-md.py -v
```

## 输出结构

```
output/
├── hash_index.json          # 📄 哈希索引文件
├── HASH_VALUE_1/            # 📁 按hash分组的目录
│   ├── document.json
│   ├── document.grobid.tei.xml
│   └── document.md
├── HASH_VALUE_2/
│   ├── another.json
│   ├── another.grobid.tei.xml
│   └── another.md
└── unknown_n/               # 📁 无法提取hash的文件
    └── ...
```

## 错误诊断

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `❌ 输入目录不存在` | 指定的input目录不存在 | 检查路径是否正确：`ls -la <path>` |
| `❌ 路径不是目录` | 指定的是文件而不是目录 | 确保 `-i` 参数指向目录 |
| `❌ 输入目录中没有找到PDF文件` | 目录中没有PDF文件 | 将PDF文件放入指定的input目录 |
| `❌ 无法创建输出目录` | 权限问题或磁盘满 | 检查目录权限：`chmod 755 <path>` |
| `❌ 无法保存索引文件` | 磁盘空间不足或权限问题 | 检查磁盘空间和权限 |

## 关键特性

✅ **任意位置运行** - 使用绝对路径，无论在哪里执行都能工作  
✅ **完整参数化** - 所有配置都可通过命令行指定  
✅ **错误处理** - 清晰的错误提示和验证  
✅ **哈希索引** - 自动生成 `hash_index.json` 索引文件  
✅ **向后兼容** - 默认参数与原脚本相同  

## 修复的问题

🔧 **Hash索引输出** - 修复了目录过滤逻辑，确保索引正确生成  
🔧 **路径处理** - 改用 `Path.resolve()` 处理绝对路径  
🔧 **错误检查** - 添加了全面的输入验证和异常处理  

## 下一步建议

1. 运行 `python pdf2tei-json-md.py -h` 查看详细帮助
2. 准备PDF文件放入input目录
3. 启动GROBID服务（如果需要指定地址）
4. 执行脚本开始处理
5. 检查 `output/hash_index.json` 确认索引文件生成

## 常见问题 (FAQ)

**Q: 脚本在哪里创建输出目录？**  
A: 在你指定的 `-o` 参数位置。如果目录不存在会自动创建。

**Q: 可以同时处理多个PDF吗？**  
A: 可以，所有PDF都放在input目录，脚本会批量处理。

**Q: hash值是什么？**  
A: 是从PDF元数据中提取的唯一标识符，用于对文档进行分组。

**Q: 如果无法提取hash怎么办？**  
A: 会自动分配 `unknown_n` 的目录名。

**Q: 并发数设置多少最好？**  
A: 根据服务器性能，通常 4-8 比较合适。过高可能导致服务响应缓慢。
