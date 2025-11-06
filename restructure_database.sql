-- 重构数据库表结构以匹配示例数据

-- 1. 更新venue表，添加缺少的字段
ALTER TABLE venue 
ADD COLUMN IF NOT EXISTS venue_abbr VARCHAR(50),
ADD COLUMN IF NOT EXISTS issn VARCHAR(20),
ADD COLUMN IF NOT EXISTS ccf_rank VARCHAR(1) CHECK (ccf_rank IN ('A', 'B', 'C', 'N')),
ADD COLUMN IF NOT EXISTS core_rank VARCHAR(20),
ADD COLUMN IF NOT EXISTS homepage VARCHAR(500);

-- 2. 更新research_field表，确保所有字段都存在
ALTER TABLE research_field 
ADD COLUMN IF NOT EXISTS field_code VARCHAR(50) UNIQUE,
ADD COLUMN IF NOT EXISTS frequency INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_selected BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS category VARCHAR(100),
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS icon VARCHAR(100),
ADD COLUMN IF NOT EXISTS color VARCHAR(20),
ADD COLUMN IF NOT EXISTS node_size INT DEFAULT 50,
ADD COLUMN IF NOT EXISTS display_order INT DEFAULT 0;

-- 3. 更新keyword表，确保所有字段都存在
ALTER TABLE keyword
ADD COLUMN IF NOT EXISTS frequency INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS weight DECIMAL(5,3) DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS color VARCHAR(20),
ADD COLUMN IF NOT EXISTS node_size INT DEFAULT 40;

-- 4. 更新author表，确保所有字段都存在
ALTER TABLE author
ADD COLUMN IF NOT EXISTS author_name_en VARCHAR(500),
ADD COLUMN IF NOT EXISTS email VARCHAR(255),
ADD COLUMN IF NOT EXISTS orcid VARCHAR(50),
ADD COLUMN IF NOT EXISTS homepage VARCHAR(500),
ADD COLUMN IF NOT EXISTS h_index INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_citations INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS research_interests TEXT;

-- 5. 更新paper表，确保所有字段都存在
ALTER TABLE paper
ADD COLUMN IF NOT EXISTS url VARCHAR(500),
ADD COLUMN IF NOT EXISTS pdf_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS citations_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS download_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS page_start INT,
ADD COLUMN IF NOT EXISTS page_end INT,
ADD COLUMN IF NOT EXISTS volume VARCHAR(50),
ADD COLUMN IF NOT EXISTS issue VARCHAR(50);

-- 6. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_venue_ccf_rank ON venue(ccf_rank);
CREATE INDEX IF NOT EXISTS idx_research_field_code ON research_field(field_code);
CREATE INDEX IF NOT EXISTS idx_keyword_weight ON keyword(weight);
CREATE INDEX IF NOT EXISTS idx_author_orcid ON author(orcid);
CREATE INDEX IF NOT EXISTS idx_paper_download_count ON paper(download_count);
CREATE INDEX IF NOT EXISTS idx_paper_page_start ON paper(page_start);
CREATE INDEX IF NOT EXISTS idx_paper_volume ON paper(volume);

-- 7. 插入示例数据的准备SQL

-- 插入research_field数据
INSERT INTO research_field (id, field_name, field_code, category, description) 
VALUES ('water_quality_engineering', '水处理工程', 'WQE001', '环境工程', '专注于水处理技术、水质改善和水资源管理的研究领域')
ON CONFLICT (id) DO UPDATE SET 
    field_name = EXCLUDED.field_name,
    field_code = EXCLUDED.field_code,
    category = EXCLUDED.category,
    description = EXCLUDED.description;

-- 插入venue数据
INSERT INTO venue (id, venue_name, venue_type, publisher, impact_factor) 
VALUES ('chemical_engineering_journal', 'Chem. Eng. J.', 'journal', 'Elsevier', 16.744)
ON CONFLICT (id) DO UPDATE SET 
    venue_name = EXCLUDED.venue_name,
    venue_type = EXCLUDED.venue_type,
    publisher = EXCLUDED.publisher,
    impact_factor = EXCLUDED.impact_factor;

-- 插入paper数据
INSERT INTO paper (id, title, abstract, publication_year, venue_id, doi, language, node_size) 
VALUES ('a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical', 
        'A novel anaerobic membrane bioreactor with magnetotactic bacteria for organic sulfur pesticide wastewater treatment: Improvement of enzyme activities, refractory pollutants removal and methane yield',
        'The high refractory pollutant and heavy metal content in organic sulfur pesticide wastewater limits the removal of chemical oxygen demand (COD) and methane yield of conventional anaerobic membrane bioreactors (cAnMBRs) due to low enzyme activity. The objective of this study was to investigate the impact of magnetotactic bacteria (MTB) with excellent adsorption capabilities on the performance of the AnMBR system at different hydraulic retention times (HRTs). The MTB-assisted AnMBR (R2) showed improved COD removal efficiency (75 %-78 %) over c-AnMBR (R1) by 3 %-7% at HRT of 60, 48, and 36 h. Mancozeb and ethylenethiourea removal efficiencies of R2 were 7.1 %-25.0 % and 25.2 %-28.5 % higher than R1, respectively. The Mn2+ and Zn2+ of R2 were significantly reduced by 16.8 ± 1.9 % and 10.0 ± 0.8 % than that of R1, which were obtained at HRT of 36 h. The activity ratio of protease and dehydrogenase between R1 and R2 was 205.5 % and 419.6 %, respectively. Specific methane yield and specific methane activity of R2 were 1.16 and 1.13 times those of R1, respectively. A mathematical model correlating refractory pollutants, enzyme activity, and COD removal efficiency was established. This study innovatively developed a green MTB-assisted AnMBR technology that successfully removed refractory pollutants and heavy metals while enhancing enzyme activity and methane yield, reducing toxicity threat and improving energy recovery efficiency, along with providing both scientific basis and technical foundation for low-carbon operation of pesticide wastewater treatment.',
        2025,
        'chemical_engineering_journal',
        '10.1016/j.cej.2025.161397',
        'en',
        30)
ON CONFLICT (id) DO UPDATE SET 
    title = EXCLUDED.title,
    abstract = EXCLUDED.abstract,
    publication_year = EXCLUDED.publication_year,
    venue_id = EXCLUDED.venue_id,
    doi = EXCLUDED.doi,
    language = EXCLUDED.language,
    node_size = EXCLUDED.node_size;