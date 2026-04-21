#!/usr/bin/env python3
"""
计算文件的 MD5 哈希值
用法: python md5_hash.py <文件路径>
"""

import hashlib
import sys
import os

def calculate_md5(file_path, buffer_size=8192):
    """
    计算文件的 MD5 哈希值
    
    参数:
        file_path: 文件路径
        buffer_size: 读取文件的缓冲区大小（字节）
    
    返回:
        文件的 MD5 哈希值（十六进制字符串）
    """
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, 'rb') as f:
            # 分块读取文件，避免大文件占用过多内存
            while chunk := f.read(buffer_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 不存在", file=sys.stderr)
        return None
    except PermissionError:
        print(f"错误: 没有权限读取文件 '{file_path}'", file=sys.stderr)
        return None
    except Exception as e:
        print(f"错误: 读取文件时发生异常 - {e}", file=sys.stderr)
        return None

def main():
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("用法: python md5_hash.py <文件路径>", file=sys.stderr)
        print("示例: python md5_hash.py myfile.txt", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在", file=sys.stderr)
        sys.exit(1)
    
    # 计算 MD5
    print(f"正在计算文件 '{file_path}' 的 MD5 值...")
    md5_value = calculate_md5(file_path)
    
    if md5_value:
        print(f"MD5: {md5_value}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()