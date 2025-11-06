# 数据库表结构和关系分析

## 1. 层次结构
根据注释，数据库采用以下层次结构：
根节点(前端写死) -> 研究领域 -> 关键词 -> 文献

## 2. 表结构详解

### 一级表 - 研究领域表 (research_field)
- id: VARCHAR(50) 主键
- field_name: 研究领域名称
- field_code: 领域代码
- category: 所属大类
- description: 描述信息

### 二级表 - 关键词表 (keyword)
- id: VARCHAR(50) 主键
- keyword_name: 关键词名称
- field_id: 外键，关联到 research_field.id
- FOREIGN KEY (field_id) REFERENCES research_field(id) ON DELETE CASCADE

### 三级表 - 文献表 (paper)
- id: VARCHAR(50) 主键
- title: 文献标题
- venue_id: 外键，关联到 venue.id
- FOREIGN KEY (venue_id) REFERENCES venue(id) ON DELETE SET NULL

### 四级关系表 - 文献-关键词映射表 (paper_keyword)
- paper_id: 外键，关联到 paper.id
- keyword_id: 外键，关联到 keyword.id
- is_primary: 是否主要关键词
- relevance_score: 相关度评分
- FOREIGN KEY (paper_id) REFERENCES paper(id) ON DELETE CASCADE
- FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE

### 作者相关表
- author: 存储作者信息
- paper_author: 文献-作者关联表
- paper_id: 外键，关联到 paper.id
- author_id: 外键，关联到 author.id

## 3. 表间关系总结

1. research_field (1) -> keyword (N): 通过 field_id 关联
2. keyword (N) -> paper_keyword (N): 通过 keyword_id 关联
3. paper (N) -> paper_keyword (N): 通过 paper_id 关联
4. paper (N) -> paper_author (N): 通过 paper_id 关联
5. author (N) -> paper_author (N): 通过 author_id 关联
6. venue (1) -> paper (N): 通过 venue_id 关联

## 4. 外键约束特点

- 使用 ON DELETE CASCADE: 当父记录被删除时，子记录也会被自动删除
- 使用 ON DELETE SET NULL: 当父记录被删除时，外键字段被设置为NULL
- 所有外键都建立了索引以提高查询性能

## 5. ID字段特点

- 所有主键ID字段均为VARCHAR(50)类型
- 使用文字ID而非自增数字ID
- 外键字段与对应主键字段类型一致
