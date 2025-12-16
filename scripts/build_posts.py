import os
import json
import re

# 配置路径
POSTS_DIR = 'posts'
DATA_DIR = 'data'
OUTPUT_FILE = os.path.join(DATA_DIR, 'posts.json')

def parse_metadata(content):
    """
    解析 Markdown 文件开头的 HTML 注释块
    """
    # 正则匹配开头的 <!-- ... --> 块，re.DOTALL 允许匹配换行符
    # 限制只匹配文件开头的注释
    pattern = re.compile(r'^\s*<!--(.*?)-->', re.DOTALL)
    match = pattern.match(content)
    
    metadata = {}
    
    if match:
        # 获取注释内部的内容
        raw_content = match.group(1).strip()
        
        # 按行处理
        lines = raw_content.split('\n')
        
        # 遍历每一行进行解析
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 分割 key 和 value，只分割第一个冒号
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理特殊字段类型
                if key in ['categories', 'tags']:
                    try:
                        # 尝试将 ["A", "B"] 这种字符串解析为列表
                        # 替换单引号为双引号以符合 JSON 标准 (防错处理)
                        if value.startswith('[') and "'" in value:
                            value = value.replace("'", '"')
                        metadata[key] = json.loads(value)
                    except json.JSONDecodeError:
                        # 解析失败则作为普通列表或空列表
                        metadata[key] = []
                        print(f"Warning: Could not parse list for {key}: {value}")
                else:
                    # 处理普通字符串，去除首尾的引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    metadata[key] = value
                    
    return metadata

def extract_date_from_path(file_path, filename):
    """
    尝试从路径和文件名中提取日期
    假设结构: posts/2025/12/22-Building.md -> 2025-12-22
    """
    try:
        # 获取路径部分
        parts = os.path.normpath(file_path).split(os.sep)
        
        # 尝试获取 年、月
        # parts 可能是 ['posts', '2025', '12', '22-Building.md']
        if len(parts) >= 4:
            year = parts[-3] # 2025
            month = parts[-2] # 12
            
            # 尝试从文件名获取 日 (例如 22-Building.md -> 22)
            day_match = re.match(r'^(\d+)-', filename)
            if day_match and year.isdigit() and month.isdigit():
                day = day_match.group(1)
                return f"{year}-{month}-{day}"
    except Exception:
        pass
        
    return "" # 如果无法提取，返回空字符串或使用文件修改时间

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    posts_data = []

    # 遍历 posts 目录
    for root, dirs, files in os.walk(POSTS_DIR):
        for file in files:
            if file.endswith('.md'):
                full_path = os.path.join(root, file)
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 1. 解析元数据
                    meta = parse_metadata(content)
                    
                    # 如果没有 title，可能不是有效的文章，跳过或者仅作为警告
                    if not meta.get('title'):
                        print(f"Skipping {file}: No title found in comment block.")
                        continue

                    # 2. 生成相对路径 (统一使用 / 作为分隔符，方便前端使用)
                    # 例如: posts/2025/12/22-Building.md
                    rel_path = os.path.relpath(full_path, start='.')
                    rel_path = rel_path.replace('\\', '/') 
                    
                    # 3. 提取日期
                    date_str = extract_date_from_path(full_path, file)
                    # 如果元数据里自带了 date，优先使用元数据的，否则使用路径提取的
                    final_date = meta.get('date', date_str)

                    # 4. 构建最终的数据对象
                    post_item = {
                        "path": rel_path,
                        "date": final_date,
                        "title": meta.get('title', 'No Title'),
                        "categories": meta.get('categories', []),
                        "tags": meta.get('tags', []),
                        "cover_image": meta.get('cover_image', ''),
                        "summary": meta.get('summary', '')
                    }
                    
                    posts_data.append(post_item)
                    print(f"Processed: {rel_path}")
                    
                except Exception as e:
                    print(f"Error processing {full_path}: {e}")

    # (可选) 按日期倒序排序
    posts_data.sort(key=lambda x: x['date'], reverse=True)

    # 写入 posts.json
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=4)
        
    print(f"\nSuccess! Saved {len(posts_data)} posts to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()