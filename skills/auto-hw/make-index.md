# make-index（auto-hw 子流程）

> 不是独立 skill。由 `auto-hw/SKILL.md` 在 index.md 缺失或用户要求重建时调起。**不要触发**：用户在写作业 / 给了具体作业题 / 让你读特定文件 / 不在 KB root / index 已存在且没说更新。

1. `find . -maxdepth 3 -type f -not -path '*/\.*' -not -name 'index.md'`
2. 每个文件起一句话摘要：PDF/DOCX → Read 多模态读前 1-3 页；MD/IPYNB → 直读头几行；二进制 / >10MB → 只标 size 不读
3. 渲染 ASCII 管道树，写到 `<KB root>/index.md`：

```
# <文件夹名>

├── file1.pdf — 摘要
└── subdir/
    ├── file2.pdf — 摘要
    └── file3.md — 摘要
```

4. 摘要不确定就空 `— ?`，告诉用户补
5. 不替用户编内容——存疑就标出来
