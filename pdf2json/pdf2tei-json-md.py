# 文件：pdf2tei-json-md.py

import json
import os
import sys
import argparse
from pathlib import Path
from grobid_client.grobid_client import GrobidClient


def validate_input_directory(pdf_dir: str) -> Path:
    """
    验证输入目录是否存在且包含PDF文件
    
    Args:
        pdf_dir: PDF输入目录路径
    
    Returns:
        Path对象（绝对路径）
    
    Raises:
        FileNotFoundError: 目录不存在
        ValueError: 目录中没有PDF文件
    """
    pdf_path = Path(pdf_dir).resolve()
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"❌ 输入目录不存在: {pdf_path}")
    
    if not pdf_path.is_dir():
        raise NotADirectoryError(f"❌ 路径不是目录: {pdf_path}")
    
    # 检查是否存在PDF文件
    pdf_files = list(pdf_path.glob("*.pdf"))
    if not pdf_files:
        raise ValueError(f"❌ 输入目录中没有找到PDF文件: {pdf_path}")
    
    print(f"✅ 输入目录验证成功，找到 {len(pdf_files)} 个PDF文件")
    return pdf_path


def create_output_directory(output_dir: str) -> Path:
    """
    创建输出目录
    
    Args:
        output_dir: 输出目录路径
    
    Returns:
        Path对象（绝对路径）
    """
    output_path = Path(output_dir).resolve()
    
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 输出目录已准备: {output_path}")
        return output_path
    except OSError as e:
        raise OSError(f"❌ 无法创建输出目录 {output_path}: {str(e)}")


def extract_hash_from_json(json_file_path: str) -> str:
    """
    从JSON文件中提取hash值
    
    Args:
        json_file_path: JSON文件路径
    
    Returns:
        hash值，如果不存在则返回None
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 从 biblio.hash 中获取
        if 'biblio' in data and 'hash' in data['biblio']:
            return data['biblio']['hash']
        
        return None
    except Exception as e:
        print(f"   ⚠️  无法从JSON提取hash: {str(e)}")
        return None


def organize_files_by_extracted_hash(
    output_temp_dir: str,
    output_base_dir: str,
    pdf_names: list = None
) -> dict:
    """
    根据JSON中的hash值重新组织文件到对应的子目录
    
    Args:
        output_temp_dir: 临时输出目录（处理后的文件所在位置）
        output_base_dir: 最终输出基础目录
        pdf_names: PDF文件名列表（可选，用于确定要处理的文件）
    
    Returns:
        {pdf_name: hash_value} 的映射字典
    """
    temp_path = Path(output_temp_dir).resolve()
    output_base_path = Path(output_base_dir).resolve()
    output_base_path.mkdir(parents=True, exist_ok=True)
    
    file_hash_map = {}
    
    # 找到所有生成的JSON文件
    json_files = list(temp_path.glob("*.json"))
    
    if not json_files:
        print("⚠️  没有找到JSON文件！")
        return file_hash_map
    
    print(f"找到 {len(json_files)} 个JSON文件")
    print()
    
    for json_file in json_files:
        pdf_name = json_file.stem.replace('.json', '')
        
        # 从JSON中提取hash
        file_hash = extract_hash_from_json(str(json_file))
        
        if not file_hash:
            print(f"⚠️  {pdf_name}: 无法提取hash，使用默认值")
            # 使用默认值（可选）
            file_hash = f"unknown_{len(file_hash_map)}"
        
        file_hash_map[pdf_name] = file_hash
        
        # 创建hash子目录
        hash_dir = output_base_path / file_hash
        hash_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📄 {pdf_name}")
        print(f"   Hash: {file_hash}")
        print(f"   输出目录: {hash_dir.name}/")
        
        # 移动三个文件到hash子目录
        files_to_move = [
            (json_file, 'json'),
            (json_file.parent / f"{pdf_name}.grobid.tei.xml", 'tei'),
            (json_file.parent / f"{pdf_name}.md", 'md')
        ]
        
        for src_file, file_type in files_to_move:
            if src_file.exists():
                dst_file = hash_dir / src_file.name
                src_file.rename(dst_file)
                print(f"      ✅ {file_type.upper()}: {src_file.name}")
            else:
                print(f"      ⚠️  {file_type.upper()}: 文件不存在")
        
        print()
    
    return file_hash_map
    
    return file_hash_map


def process_pdfs_to_all_formats(
    pdf_dir: str,
    output_base_dir: str,
    server: str = "http://localhost:8070",
    concurrency: int = 4,
    verbose: bool = True
):
    """
    将PDF转换为TEI XML、JSON和Markdown三种格式
    并按JSON中的hash值组织输出目录
    
    Args:
        pdf_dir: PDF输入目录
        output_base_dir: 输出基础目录
        server: GROBID服务地址
        concurrency: 并发数
        verbose: 是否显示详细日志
    """
    # 验证和规范化路径
    pdf_path = validate_input_directory(pdf_dir)
    output_path = create_output_directory(output_base_dir)
    
    client = GrobidClient(grobid_server=server)
    
    print(f"📁 输入目录: {pdf_path}")
    print(f"📁 输出目录: {output_path}")
    print(f"🔧 GROBID服务: {server}")
    print(f"⚙️  并发数: {concurrency}")
    print()
    
    # 第一步：处理PDF生成三种格式文件
    print("=" * 60)
    print("🔄 第一步：处理PDF文件 → TEI XML / JSON / Markdown")
    print("=" * 60)
    print()
    
    client.process(
        service="processFulltextDocument",
        input_path=str(pdf_path),
        output=str(output_path),
        n=concurrency,
        json_output=True,
        markdown_output=True,
        verbose=verbose
    )
    
    print()
    
    # 第二步：根据JSON中的hash重新组织文件
    print("=" * 60)
    print("📊 第二步：根据JSON中的hash值重新组织文件")
    print("=" * 60)
    print()
    
    file_hash_map = organize_files_by_extracted_hash(str(output_path), str(output_path))
    
    # 统计结果
    hash_dirs = [d for d in output_path.iterdir() if d.is_dir()]
    total_tei = len(list(output_path.glob("**/*.grobid.tei.xml")))
    total_json = len(list(output_path.glob("**/*.json")))
    total_md = len(list(output_path.glob("**/*.md")))
    
    print()
    print("=" * 60)
    print("✅ 处理完成！")
    print("=" * 60)
    print(f"📊 生成的文件：")
    print(f"   ├─ TEI XML 文件: {total_tei} 个")
    print(f"   ├─ JSON 文件: {total_json} 个")
    print(f"   └─ Markdown 文件: {total_md} 个")
    print()
    print(f"📁 按hash分组的目录: {len(hash_dirs)} 个")
    print()
    
    # 显示目录结构示例
    if hash_dirs:
        print(f"📁 输出目录结构示例：")
        print(f"output/")
        for i, hash_dir in enumerate(hash_dirs[:3]):
            files = list(hash_dir.glob("*"))
            print(f"├── {hash_dir.name}/  ({len(files)} 个文件)")
            for f in files[:3]:
                print(f"│   ├── {f.name}")
            if len(files) > 3:
                print(f"│   └── ... ({len(files) - 3} 个其他文件)")
        
        if len(hash_dirs) > 3:
            print(f"└── ... ({len(hash_dirs) - 3} 个其他目录)")
    
    print()
    print(f"📁 所有结果保存在: {output_path}")


def create_hash_index(output_base_dir: str, output_file: str = "hash_index.json"):
    """
    创建hash索引文件，记录每个hash对应的文件
    
    Args:
        output_base_dir: 输出基础目录
        output_file: 索引文件名
    """
    output_base_path = Path(output_base_dir).resolve()
    hash_index = {}
    
    if not output_base_path.exists():
        print(f"⚠️  输出目录不存在: {output_base_path}")
        return hash_index
    
    # 遍历所有hash子目录
    for item in output_base_path.iterdir():
        if not item.is_dir():
            continue
        
        # 跳过隐藏目录
        if item.name.startswith('.'):
            continue
            
        hash_value = item.name
        
        # 获取该目录下的所有文件
        tei_files = list(item.glob("*.grobid.tei.xml"))
        json_files = list(item.glob("*.json"))
        md_files = list(item.glob("*.md"))
        
        # 从JSON文件中提取PDF名称和其他信息
        pdf_info = {}
        if json_files:
            json_file = json_files[0]
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                pdf_info = {
                    'title': data.get('biblio', {}).get('title'),
                    'authors': data.get('biblio', {}).get('authors', []),
                    'doi': data.get('biblio', {}).get('doi'),
                    'publication_year': data.get('biblio', {}).get('publication_year')
                }
            except Exception as e:
                print(f"   ⚠️  无法读取JSON信息: {str(e)}")
        
        hash_index[hash_value] = {
            'directory': str(item.relative_to(output_base_path)),
            'files': {
                'tei_xml': [f.name for f in tei_files],
                'json': [f.name for f in json_files],
                'markdown': [f.name for f in md_files]
            },
            'pdf_info': pdf_info
        }
    
    # 保存索引文件到输出根目录
    index_path = output_base_path / output_file
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(hash_index, f, indent=2, ensure_ascii=False)
        
        print()
        print("=" * 60)
        print("📋 创建哈希索引")
        print("=" * 60)
        print(f"✅ 哈希索引已保存到: {index_path.name}")
        print(f"   共 {len(hash_index)} 个PDF")
        print(f"   路径: {index_path}")
        return hash_index
    except IOError as e:
        print(f"❌ 无法保存索引文件: {str(e)}")
        return hash_index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PDF批量处理工具 - 转换为TEI XML、JSON和Markdown格式，并按hash值分组",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认目录（相对于脚本位置）
  python pdf2tei-json-md.py
  
  # 指定自定义目录
  python pdf2tei-json-md.py -i /path/to/pdfs -o /path/to/output
  
  # 使用绝对路径
  python pdf2tei-json-md.py -i /home/user/pdfs -o /home/user/output
  
  # 自定义GROBID服务地址和并发数
  python pdf2tei-json-md.py -i ./pdfs -o ./output -s http://grobid:8070 -c 8
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='/home/yzl/Desktop/projects/citation-eva/pdf2json/input/pdfs',
        help='PDF输入目录（默认: ./input/pdfs）'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='/home/yzl/Desktop/projects/citation-eva/pdf2json/output',
        help='处理结果输出目录（默认: ./output）'
    )
    
    parser.add_argument(
        '-s', '--server',
        type=str,
        default='http://localhost:8070',
        help='GROBID服务地址（默认: http://localhost:8070）'
    )
    
    parser.add_argument(
        '-c', '--concurrency',
        type=int,
        default=4,
        help='并发处理数量（默认: 4）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 PDF 批量处理工具 - 按JSON Hash分组")
    print("=" * 60)
    print()
    
    try:
        # 运行处理
        process_pdfs_to_all_formats(
            pdf_dir=args.input,
            output_base_dir=args.output,
            server=args.server,
            concurrency=args.concurrency,
            verbose=args.verbose
        )
        
        # 创建哈希索引
        hash_index = create_hash_index(args.output)
        
        print()
        print("=" * 60)
        print("🎉 所有操作完成！")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n{e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n{e}")
        sys.exit(1)
    except OSError as e:
        print(f"\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)