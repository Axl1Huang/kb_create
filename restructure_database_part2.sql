-- 继续重构数据库表结构以匹配示例数据

-- 1. 插入keyword数据
INSERT INTO keyword (id, keyword_name, field_id) 
VALUES 
('anaerobic_membrane_bioreactor', 'Anaerobic membrane bioreactor (AnMBR)', 'water_quality_engineering'),
('magnetotactic_bacteria', 'Magnetotactic bacteria (MTB)', 'water_quality_engineering'),
('organic_sulfur_pesticide', 'Organic sulfur pesticide wastewater', 'water_quality_engineering'),
('refractory_pollutants', 'Refractory pollutants', 'water_quality_engineering'),
('enzyme_activities', 'Enzyme activities', 'water_quality_engineering'),
('methane_yield', 'Methane yield', 'water_quality_engineering')
ON CONFLICT (id) DO UPDATE SET 
    keyword_name = EXCLUDED.keyword_name,
    field_id = EXCLUDED.field_id;

-- 2. 插入paper_keyword关联数据
INSERT INTO paper_keyword (paper_id, keyword_id, is_primary, relevance_score) 
VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'anaerobic_membrane_bioreactor', true, 1.0),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'magnetotactic_bacteria', true, 0.9),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'organic_sulfur_pesticide', true, 0.8),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'refractory_pollutants', false, 0.7),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'enzyme_activities', false, 0.7),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'methane_yield', false, 0.6)
ON CONFLICT (paper_id, keyword_id) DO UPDATE SET 
    is_primary = EXCLUDED.is_primary,
    relevance_score = EXCLUDED.relevance_score;

-- 3. 插入作者数据和paper_author关联数据
-- 由于作者数据较多，我们先创建一个临时表来处理作者数据
CREATE TEMP TABLE temp_authors (
    name VARCHAR(500),
    affiliation VARCHAR(1000)
);

-- 插入作者数据到临时表
INSERT INTO temp_authors (name, affiliation) VALUES
('Shiming Cui', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Dongxue Hu', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Zhaobo Chen', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Yifan Wang', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Jitao Yan', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Shuya Zhuang', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Bei Jiang', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Hui Ge', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Zihan Wang', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China'),
('Pengcheng Zhang', 'Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China');

-- 为每个作者生成唯一ID并插入到author表
INSERT INTO author (id, author_name, affiliation)
SELECT 
    LOWER(REPLACE(name, ' ', '_')) as id,
    name as author_name,
    affiliation
FROM temp_authors
ON CONFLICT (id) DO UPDATE SET 
    author_name = EXCLUDED.author_name,
    affiliation = EXCLUDED.affiliation;

-- 插入paper_author关联数据
INSERT INTO paper_author (paper_id, author_id, author_order, is_corresponding)
SELECT 
    'a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical' as paper_id,
    LOWER(REPLACE(name, ' ', '_')) as author_id,
    ROW_NUMBER() OVER() as author_order,
    CASE WHEN name = 'Dongxue Hu' THEN true ELSE false END as is_corresponding
FROM temp_authors
ON CONFLICT (paper_id, author_id) DO UPDATE SET 
    author_order = EXCLUDED.author_order,
    is_corresponding = EXCLUDED.is_corresponding;

-- 删除临时表
DROP TABLE temp_authors;

-- 4. 插入paper_metadata数据
INSERT INTO paper_metadata (paper_id, meta_key, meta_value, meta_type) 
VALUES 
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'cod_removal_efficiency', '75-78%', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'methane_yield_improvement', '1.16 times higher in R2 vs R1', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'hrt_conditions_1', '60 h', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'hrt_conditions_2', '48 h', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'hrt_conditions_3', '36 h', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'hrt_conditions_4', '24 h', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'pollutant_1', 'Mancozeb', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'pollutant_2', 'Ethylenethiourea (ETU)', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'pollutant_3', 'Mn2+', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'pollutant_4', 'Zn2+', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'enzyme_activity_1', 'protease: 205.5% higher in R2 vs R1', 'string'),
('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 'enzyme_activity_2', 'dehydrogenase: 419.6% higher in R2 vs R1', 'string')
ON CONFLICT (paper_id, meta_key) DO UPDATE SET 
    meta_value = EXCLUDED.meta_value,
    meta_type = EXCLUDED.meta_type;