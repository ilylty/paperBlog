# paperBlog

这是一个基于 Markdown 的轻量级静态博客系统。它不需要复杂的数据库，只需编写 Markdown 文件并运行构建脚本即可发布文章。

## 📁 目录结构

```
paperBlog/
├── assets/          # 静态资源 (CSS, Images)
├── data/            # 数据文件
│   ├── config.json  # 站点配置
│   └── posts.json   # 文章索引 (由脚本生成)
├── posts/           # 博客文章目录 (Markdown 文件)
├── scripts/         # 构建脚本
│   └── build_posts.py # 生成 posts.json 的脚本
├── index.html       # 首页
├── archive.html     # 归档页
├── post.html        # 文章详情页模板
└── README.md        # 项目说明文档
```

## 🚀 快速开始

### 1. 撰写文章

在 `posts/` 目录下创建 Markdown 文件。建议按 `年份/月份/日期-标题.md` 的结构组织，例如 `posts/2025/12/16-Tutorials.md`。

每篇文章的文件头部必须包含以下元数据注释：

```html
<!-- 
title: 文章标题
categories: ["分类"] 
tags: ["标签1", "标签2"]
cover_image: ""
summary: "文章摘要"
-->
```

**注意**：
- `categories` 只能包含**一个**分类。
- 更多写作规范请参考 [博客使用教程](posts/2025/12/16-Tutorials.md)。

### 2. 构建索引

每次添加或修改文章后，都需要运行 Python 脚本来更新文章索引文件 `data/posts.json`。

```bash
python scripts/build_posts.py
```

### 3. 预览博客

构建完成后，直接在浏览器中打开 `index.html` 即可查看博客。

## ⚙️ 配置

你可以在 `data/config.json` 中修改站点配置：

```json
{
  "site_name": "ilylty's Blog"
}
```

## 🛠️ 技术栈

- **前端**: HTML5, CSS3, JavaScript (原生)
- **内容**: Markdown
- **构建**: Python (用于生成 JSON 索引)

## 📝 待办事项

- [ ] 实现封面图片显示 (`cover_image`)
- [ ] 优化移动端适配
