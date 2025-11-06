# SQL数据库表结构设计建议

## 1. 主表 - papers
| 字段名 | 数据类型 | 描述 |
|--------|---------|------|
| id | VARCHAR(255) | 主键，文献唯一标识符 |
| title | TEXT | 文献标题 |
| abstract | TEXT | 摘要 |
| publication_year | INT | 发表年份 |
| venue | VARCHAR(255) | 期刊/会议名称 |
| cod_removal_efficiency | VARCHAR(50) | COD去除效率 |
| methane_yield_improvement | VARCHAR(100) | 甲烷产量改善 |
| file_path | VARCHAR(500) | 文件路径 |

## 2. 关联表设计

### authors表
| 字段名 | 数据类型 | 描述 |
|--------|---------|------|
| id | INT | 主键，自增 |
| paper_id | VARCHAR(255) | 外键，关联papers表 |
| name | VARCHAR(255) | 作者姓名 |
| affiliation | TEXT | 作者机构 |

### keywords表
| 字段名 | 数据类型 | 描述 |
|--------|---------|------|
| id | INT | 主键，自增 |
| paper_id | VARCHAR(255) | 外键，关联papers表 |
| keyword | VARCHAR(255) | 关键词 |

### hrt_conditions表
| 字段名 | 数据类型 | 描述 |
|--------|---------|------|
| id | INT | 主键，自增 |
| paper_id | VARCHAR(255) | 外键，关联papers表 |
| condition | VARCHAR(50) | HRT条件 |

### pollutants_studied表
| 字段名 | 数据类型 | 描述 |
|--------|---------|------|
| id | INT | 主键，自增 |
| paper_id | VARCHAR(255) | 外键，关联papers表 |
| pollutant | VARCHAR(100) | 研究的污染物 |

### enzyme_activities表
| 字段名 | 数据类型 | 描述 |
|--------|---------|------|
| id | INT | 主键，自增 |
| paper_id | VARCHAR(255) | 外键，关联papers表 |
| enzyme | VARCHAR(100) | 酶名称 |
| activity | VARCHAR(100) | 酶活性描述 |

## 3. 数据插入示例

### 插入主表数据
INSERT INTO papers (id, title, abstract, publication_year, venue, cod_removal_efficiency, methane_yield_improvement, file_path) VALUES ('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'A novel anaerobic membrane bioreactor with magnetotactic bacteria for organic sulfur pesticide wastewater treatment: Improvement of enzyme activities, refractory pollutants removal and methane yield', 'The high refractory pollutant and heavy metal content in organic sulfur pesticide wastewater limits the removal of chemical oxygen demand (COD) and methane yield of conventional anaerobic membrane bioreactors (cAnMBRs) due to low enzyme activity...', 2025, 'Chemical Engineering Journal', '75-78%', '1.16 times higher in R2 vs R1', '/home/axlhuang/kb_create/test_output/markdown_only/A-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical.md');

### 插入作者数据
INSERT INTO authors (paper_id, name, affiliation) VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'Shiming Cui', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'Dongxue Hu', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
... (其他作者)

### 插入关键词数据
INSERT INTO keywords (paper_id, keyword) VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'Anaerobic membrane bioreactor (AnMBR)'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'Magnetotactic bacteria (MTB)'),
... (其他关键词)

### 插入HRT条件数据
INSERT INTO hrt_conditions (paper_id, condition) VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', '60 h'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', '48 h'),
... (其他条件)

### 插入污染物数据
INSERT INTO pollutants_studied (paper_id, pollutant) VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'Mancozeb'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'Ethylenethiourea (ETU)'),
... (其他污染物)

### 插入酶活性数据
INSERT INTO enzyme_activities (paper_id, enzyme, activity) VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'protease', '205.5% higher in R2 vs R1'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'dehydrogenase', '419.6% higher in R2 vs R1');