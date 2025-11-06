# 更新后的SQL数据库插入逻辑

## 1. 概述

根据数据库表结构设计，更新了数据插入逻辑，确保数据能够正确地插入到相应的表中。新的插入逻辑遵循数据库的层次结构和外键约束。

## 2. 表结构层次关系

1. **venue** - 期刊/会议信息
2. **research_field** - 研究领域（一级节点）
3. **keyword** - 关键词（二级节点），关联到研究领域
4. **paper** - 文献信息（三级节点），关联到期刊
5. **paper_metadata** - 文献元数据，关联到文献
6. **author** - 作者信息
7. **paper_author** - 文献与作者的关联关系
8. **paper_keyword** - 文献与关键词的关联关系

## 3. 插入顺序

为确保外键约束不被违反，需要按照以下顺序插入数据：

1. **venue** - 期刊信息
2. **research_field** - 研究领域
3. **keyword** - 关键词
4. **author** - 作者信息
5. **paper** - 文献信息
6. **paper_metadata** - 文献元数据
7. **paper_author** - 文献作者关联
8. **paper_keyword** - 文献关键词关联

## 4. 数据插入示例

### 4.1 插入期刊信息
```sql
INSERT INTO venue (id, venue_name, venue_type, publisher, impact_factor) 
VALUES ('chemical_engineering_journal', 'Chemical Engineering Journal', 'journal', 'Elsevier', 16.744);
```

### 4.2 插入研究领域
```sql
INSERT INTO research_field (id, field_name, field_code, category, description) 
VALUES ('water_quality_engineering', '水处理工程', 'WQE001', '环境工程', '专注于水处理技术、水质改善和水资源管理的研究领域');
```

### 4.3 插入关键词
```sql
INSERT INTO keyword (id, keyword_name, field_id, weight, description) 
VALUES ('anaerobic_membrane_bioreactor', '厌氧膜生物反应器', 'water_quality_engineering', 1.0, '一种结合厌氧消化和膜分离技术的高效污水处理技术');
```

### 4.4 插入作者信息
```sql
INSERT INTO author (id, author_name, affiliation) 
VALUES ('shiming_cui', 'Shiming Cui', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China');
```

### 4.5 插入文献信息
```sql
INSERT INTO paper (id, title, abstract, publication_year, venue_id, doi, language, node_size) 
VALUES ('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'A novel anaerobic membrane bioreactor with magnetotactic bacteria for organic sulfur pesticide wastewater treatment: Improvement of enzyme activities, refractory pollutants removal and methane yield', 'The high refractory pollutant and heavy metal content in organic sulfur pesticide wastewater...', 2025, 'chemical_engineering_journal', '10.1016/j.cej.2025.161397', 'en', 30);
```

### 4.6 插入文献元数据
```sql
INSERT INTO paper_metadata (paper_id, meta_key, meta_value, meta_type) 
VALUES ('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'cod_removal_efficiency', '75-78%', 'string');
```

### 4.7 插入文献作者关联
```sql
INSERT INTO paper_author (paper_id, author_id, author_order, is_corresponding) 
VALUES ('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'shiming_cui', 1, false);
```

### 4.8 插入文献关键词关联
```sql
INSERT INTO paper_keyword (paper_id, keyword_id, is_primary, relevance_score) 
VALUES ('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'anaerobic_membrane_bioreactor', true, 1.0);
```

## 5. JSON数据文件更新

根据新的数据库结构，已更新JSON数据文件格式，包括：
1. 主要实体表数据（venue, research_field, keyword, paper, author）
2. 关联表数据（paper_metadata, paper_author, paper_keyword）

这些文件可以直接用于批量导入数据库。