-- ============================================
-- 层次化知识图谱数据库 - 完整SQL脚本
-- 创建日期: 2025-10-26
-- 说明: 本脚本包含所有数据表的创建语句
-- 层次结构: 根节点(前端写死) -> 研究领域 -> 关键词 -> 文献
-- ============================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. 期刊/会议表 (venue)
-- 说明: 存储期刊和会议的基本信息
-- ============================================
CREATE TABLE venue (
    id VARCHAR(50) PRIMARY KEY,
    venue_name VARCHAR(255) NOT NULL,
    venue_abbr VARCHAR(50) COMMENT '期刊/会议缩写',
    venue_type ENUM('conference', 'journal', 'workshop', 'symposium') NOT NULL,
    issn VARCHAR(20) COMMENT '期刊ISSN号',
    publisher VARCHAR(255) COMMENT '出版商',
    impact_factor DECIMAL(6,3) COMMENT '影响因子',
    ccf_rank ENUM('A', 'B', 'C', 'N') COMMENT 'CCF分级',
    core_rank VARCHAR(20) COMMENT '中文核心等级',
    homepage VARCHAR(500) COMMENT '官方网站',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_venue_name (venue_name),
    INDEX idx_venue_type (venue_type),
    INDEX idx_ccf_rank (ccf_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='期刊会议表';

-- ============================================
-- 2. 研究领域表 (research_field)
-- 说明: 存储研究领域的详细信息（一级节点）
-- ============================================
CREATE TABLE research_field (
    id VARCHAR(50) PRIMARY KEY,
    field_name VARCHAR(255) NOT NULL,
    field_code VARCHAR(50) UNIQUE COMMENT '领域代码',
    frequency INT DEFAULT 0 COMMENT '出现频次',
    is_selected BOOLEAN DEFAULT TRUE COMMENT '是否被选中显示',
    category VARCHAR(100) COMMENT '所属大类',
    description TEXT,
    icon VARCHAR(100) COMMENT '图标URL',
    color VARCHAR(20) COMMENT '节点颜色',
    node_size INT DEFAULT 50 COMMENT '节点大小(用于可视化)',
    display_order INT DEFAULT 0 COMMENT '显示顺序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_frequency (frequency DESC),
    INDEX idx_category (category),
    INDEX idx_field_name (field_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='研究领域表';

-- ============================================
-- 3. 关键词表 (keyword)
-- 说明: 存储具体的研究关键词（二级节点）
-- ============================================
CREATE TABLE keyword (
    id VARCHAR(50) PRIMARY KEY,
    keyword_name VARCHAR(255) NOT NULL,
    field_id VARCHAR(50) NOT NULL COMMENT '所属研究领域ID',
    frequency INT DEFAULT 0 COMMENT '出现频次',
    weight DECIMAL(5,3) DEFAULT 1.0 COMMENT '权重',
    description TEXT,
    color VARCHAR(20) COMMENT '节点颜色',
    node_size INT DEFAULT 40 COMMENT '节点大小(用于可视化)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (field_id) REFERENCES research_field(id) ON DELETE CASCADE,
    INDEX idx_field_id (field_id),
    INDEX idx_frequency (frequency DESC),
    INDEX idx_keyword_name (keyword_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='关键词表';

-- ============================================
-- 4. 文献表 (paper)
-- 说明: 存储文献的基本信息（三级节点）
-- ============================================
CREATE TABLE paper (
    id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL COMMENT '文献标题',
    abstract TEXT COMMENT '摘要',
    publication_year INT COMMENT '发表年份',
    venue_id VARCHAR(50) COMMENT '期刊/会议ID',
    doi VARCHAR(255) UNIQUE COMMENT 'DOI',
    url VARCHAR(500) COMMENT '论文链接',
    pdf_url VARCHAR(500) COMMENT 'PDF链接',
    citations_count INT DEFAULT 0 COMMENT '引用数',
    download_count INT DEFAULT 0 COMMENT '下载数',
    language VARCHAR(20) DEFAULT 'en' COMMENT '语言',
    page_start INT COMMENT '起始页码',
    page_end INT COMMENT '结束页码',
    volume VARCHAR(50) COMMENT '卷号',
    issue VARCHAR(50) COMMENT '期号',
    node_size INT DEFAULT 30 COMMENT '节点大小(用于可视化)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (venue_id) REFERENCES venue(id) ON DELETE SET NULL,
    INDEX idx_publication_year (publication_year),
    INDEX idx_citations_count (citations_count DESC),
    INDEX idx_venue_id (venue_id),
    FULLTEXT idx_title (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文献表';

-- ============================================
-- 5. 文献元数据表 (paper_metadata)
-- 说明: 存储文献的扩展元数据
-- ============================================
CREATE TABLE paper_metadata (
    id INT PRIMARY KEY AUTO_INCREMENT,
    paper_id VARCHAR(50) NOT NULL,
    meta_key VARCHAR(100) NOT NULL COMMENT '元数据键',
    meta_value TEXT COMMENT '元数据值',
    meta_type VARCHAR(50) COMMENT '数据类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES paper(id) ON DELETE CASCADE,
    INDEX idx_paper_id (paper_id),
    INDEX idx_meta_key (meta_key),
    UNIQUE KEY uk_paper_meta (paper_id, meta_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文献元数据表';

-- ============================================
-- 6. 文献-关键词映射表 (paper_keyword)
-- 说明: 处理文献与关键词的多对多关系
-- ============================================
CREATE TABLE paper_keyword (
    id INT PRIMARY KEY AUTO_INCREMENT,
    paper_id VARCHAR(50) NOT NULL,
    keyword_id VARCHAR(50) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE COMMENT '是否主要关键词',
    relevance_score DECIMAL(5,3) DEFAULT 1.0 COMMENT '相关度评分',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES paper(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keyword(id) ON DELETE CASCADE,
    INDEX idx_paper_id (paper_id),
    INDEX idx_keyword_id (keyword_id),
    UNIQUE KEY uk_paper_keyword (paper_id, keyword_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文献关键词映射表';

-- ============================================
-- 7. 作者表 (author)
-- 说明: 存储作者的基本信息
-- ============================================
CREATE TABLE author (
    id VARCHAR(50) PRIMARY KEY,
    author_name VARCHAR(255) NOT NULL,
    author_name_en VARCHAR(255) COMMENT '英文名',
    affiliation VARCHAR(500) COMMENT '所属机构',
    email VARCHAR(255),
    orcid VARCHAR(50) COMMENT 'ORCID标识符',
    homepage VARCHAR(500) COMMENT '个人主页',
    h_index INT DEFAULT 0 COMMENT 'h指数',
    total_citations INT DEFAULT 0 COMMENT '总引用数',
    research_interests TEXT COMMENT '研究兴趣',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_author_name (author_name),
    INDEX idx_affiliation (affiliation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作者表';

-- ============================================
-- 8. 文献-作者关联表 (paper_author)
-- 说明: 处理文献与作者的多对多关系
-- ============================================
CREATE TABLE paper_author (
    id INT PRIMARY KEY AUTO_INCREMENT,
    paper_id VARCHAR(50) NOT NULL,
    author_id VARCHAR(50) NOT NULL,
    author_order INT NOT NULL COMMENT '作者顺序',
    is_corresponding BOOLEAN DEFAULT FALSE COMMENT '是否通讯作者',
    contribution TEXT COMMENT '贡献说明',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES paper(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES author(id) ON DELETE CASCADE,
    INDEX idx_paper_id (paper_id),
    INDEX idx_author_id (author_id),
    UNIQUE KEY uk_paper_author (paper_id, author_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文献作者关联表';

-- ============================================
-- 9. 文献引用关系表 (paper_citation)
-- 说明: 存储文献之间的引用关系
-- ============================================
CREATE TABLE paper_citation (
    id INT PRIMARY KEY AUTO_INCREMENT,
    citing_paper_id VARCHAR(50) NOT NULL COMMENT '引用文献ID',
    cited_paper_id VARCHAR(50) NOT NULL COMMENT '被引文献ID',
    citation_context TEXT COMMENT '引用上下文',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (citing_paper_id) REFERENCES paper(id) ON DELETE CASCADE,
    FOREIGN KEY (cited_paper_id) REFERENCES paper(id) ON DELETE CASCADE,
    INDEX idx_citing_paper (citing_paper_id),
    INDEX idx_cited_paper (cited_paper_id),
    UNIQUE KEY uk_citation (citing_paper_id, cited_paper_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文献引用关系表';

-- ============================================
-- 10. 用户选择配置表 (user_selection)
-- 说明: 存储用户自定义的研究领域选择和配置
-- ============================================
CREATE TABLE user_selection (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(50),
    field_id VARCHAR(50) NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    custom_color VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (field_id) REFERENCES research_field(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    UNIQUE KEY uk_user_field (user_id, field_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户选择配置表';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 数据库表结构创建完成
-- 共10张表，层次结构清晰，表名使用单数形式
-- ============================================
