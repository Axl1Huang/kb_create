# 文章内容提取需求分析

## 1. 需要提取的内容分类

### 一级表数据（必须先插入）
1. **研究领域 (research_field)**
   - id: 基于领域名称生成的文字ID
   - field_name: 研究领域名称
   - field_code: 领域代码
   - category: 所属大类
   - description: 领域描述

2. **期刊/会议 (venue)**
   - id: 基于期刊名称生成的文字ID
   - venue_name: 期刊/会议名称
   - venue_type: 类型（journal/conference等）
   - publisher: 出版商
   - impact_factor: 影响因子

### 二级表数据（依赖一级表）
3. **关键词 (keyword)**
   - id: 基于关键词名称生成的文字ID
   - keyword_name: 关键词名称
   - field_id: 关联的研究领域ID
   - description: 关键词描述（可选）

### 三级表数据（独立或依赖venue）
4. **文献 (paper)**
   - id: 基于标题和年份生成的文字ID
   - title: 标题
   - abstract: 摘要
   - publication_year: 发表年份
   - venue_id: 期刊ID
   - doi: DOI编号
   - language: 语言

5. **作者 (author)**
   - id: 基于作者姓名生成的文字ID
   - author_name: 作者姓名
   - affiliation: 所属机构

### 关联表数据（依赖三级表）
6. **文献-关键词映射 (paper_keyword)**
   - paper_id: 文献ID
   - keyword_id: 关键词ID
   - is_primary: 是否为主要关键词
   - relevance_score: 相关性评分

7. **文献-作者关联 (paper_author)**
   - paper_id: 文献ID
   - author_id: 作者ID
   - author_order: 作者顺序
   - is_corresponding: 是否通讯作者

8. **文献元数据 (paper_metadata)**
   - paper_id: 文献ID
   - meta_key: 元数据键
   - meta_value: 元数据值
   - meta_type: 数据类型

## 2. 从文章中需要直接提取的信息

### 基本信息
1. 论文标题
2. 摘要内容
3. 发表年份
4. 期刊/会议名称
5. DOI编号
6. 作者列表及机构信息
7. 关键词列表

### 实验数据（用于元数据）
1. HRT条件
2. 污染物类型及去除率
3. 酶活性数据
4. 其他量化结果

## 3. 需要推断或生成的信息

### ID生成
1. paper.id: 基于标题和年份
2. author.id: 基于作者姓名
3. keyword.id: 基于关键词名称
4. research_field.id: 基于领域名称
5. venue.id: 基于期刊名称

### 分类信息
1. 研究领域分类
2. 关键词与研究领域的关联
3. 期刊类型
4. 作者顺序和通讯作者标识

## 4. 可能需要外部数据补充的信息

1. 期刊影响因子
2. 期刊ISSN号
3. 作者ORCID
4. 作者邮箱
5. 作者h指数
