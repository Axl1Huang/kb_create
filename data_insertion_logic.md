# 数据插入逻辑分析

## 1. 插入顺序要求

由于数据库表之间存在外键约束，数据插入需要遵循特定顺序以避免违反约束：

### 第一阶段：插入一级表数据
1. venue (期刊/会议表)
2. research_field (研究领域表)

### 第二阶段：插入二级表数据
3. keyword (关键词表) - 依赖于 research_field

### 第三阶段：插入三级表数据
4. paper (文献表) - 可能依赖于 venue
5. author (作者表)

### 第四阶段：插入关联表数据
6. paper_keyword (文献-关键词映射表) - 依赖于 paper 和 keyword
7. paper_author (文献-作者关联表) - 依赖于 paper 和 author
8. paper_metadata (文献元数据表) - 依赖于 paper

## 2. 依赖关系分析

### keyword 表插入
- 必须先插入对应的 research_field 记录
- field_id 字段必须引用已存在的 research_field.id

### paper 表插入
- venue_id 字段可以引用已存在的 venue.id，但允许为NULL

### paper_keyword 表插入
- paper_id 必须引用已存在的 paper.id
- keyword_id 必须引用已存在的 keyword.id

### paper_author 表插入
- paper_id 必须引用已存在的 paper.id
- author_id 必须引用已存在的 author.id

## 3. 数据完整性要求

1. 所有主键ID必须唯一
2. 外键字段必须引用有效的父记录
3. UNIQUE约束字段不能重复（如paper.doi）
4. NOT NULL字段必须提供值

## 4. 插入逻辑实现建议

### 方法一：按依赖顺序分批插入
1. 先插入所有一级表数据（venue, research_field）
2. 再插入二级表数据（keyword）
3. 接着插入三级表数据（paper, author）
4. 最后插入关联表数据（paper_keyword, paper_author, paper_metadata）

### 方法二：事务性插入
将相关记录的插入放在一个事务中，确保数据一致性：
1. 开始事务
2. 按顺序插入相关记录
3. 提交事务或回滚（如有错误）

## 5. 错误处理

1. 插入前应检查外键引用的有效性
2. 处理重复记录（如DOI重复）的情况
3. 对于违反约束的插入操作，应提供清晰的错误信息
