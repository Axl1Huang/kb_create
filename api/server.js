const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const app = express();
const PORT = process.env.PORT || 3001;

// PostgreSQL连接配置
const pool = new Pool({
  host: process.env.DB_HOST || 'pgm-bp1ksg5v1lo5z2r8eo.rwlb.rds.aliyuncs.com',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || 'nju_art_vis',
  password: process.env.DB_PASSWORD || 'Njukeshihua!',
  database: process.env.DB_NAME || 'Article_Vis',
  ssl: false  // 禁用SSL连接
});

// 配置CORS以允许前端访问
app.use(cors({
  origin: true, // 允许所有来源，解决CORS问题
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));
app.use(express.json());

// 请求日志中间件
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} from ${req.headers.origin || 'unknown'}`);
  next();
});

// 获取研究领域的层次结构数据
app.get('/api/graph', async (req, res) => {
  try {
    const client = await pool.connect();
    
    // 获取研究领域（一级节点）
    const fieldsQuery = `
      SELECT id, field_name as name, display_order, node_size, color
      FROM research_field 
      WHERE is_selected = true 
      ORDER BY display_order, field_name
    `;
    const fieldsResult = await client.query(fieldsQuery);
    
    const fields = fieldsResult.rows;
    const fieldsMap = new Map();
    
    // 获取每个领域的关键词（二级节点）
    for (let field of fields) {
      const keywordsQuery = `
        SELECT k.id, k.keyword_name as name, k.frequency as count, k.weight, k.color
        FROM keyword k
        WHERE k.field_id = $1
        ORDER BY k.frequency DESC, k.keyword_name
        LIMIT 10
      `;
      const keywordsResult = await client.query(keywordsQuery, [field.id]);
      field.keywords = keywordsResult.rows;
      fieldsMap.set(field.id, field);
    }
    
    // 不再获取三级节点（论文）数据，保持两层结构
    // 为每个关键词设置空的papers数组以保持数据结构一致性
    for (let field of fields) {
      for (let keyword of field.keywords) {
        keyword.papers = []; // 空数组，不再查询论文数据
      }
    }
    
    client.release();
    
    // 构建层次结构响应
    const response = {
      fields: fields.map(field => ({
        id: field.id,
        name: field.name,
        count: field.keywords.length,

        color: field.color,
        keywords: field.keywords.map(kw => ({
          id: kw.id,
          name: kw.name,
          count: 0, // 不再统计论文数量
          frequency: kw.count || 0,
          weight: kw.weight || 0.5,

          color: kw.color,
          papers: [] // 空数组，不再返回论文数据
        }))
      }))
    };
    
    res.json(response);
  } catch (error) {
    console.error('数据库查询错误:', error);
    res.status(500).json({ error: '数据库查询失败', details: error.message });
  }
});

// 获取节点详细信息
app.get('/api/node/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { type } = req.query; // field, keyword, paper
    
    const client = await pool.connect();
    let result;
    
    switch (type) {
      case 'field':
        result = await client.query(`
          SELECT rf.*, COUNT(k.id) as keyword_count
          FROM research_field rf
          LEFT JOIN keyword k ON rf.id = k.field_id
          WHERE rf.id = $1
          GROUP BY rf.id
        `, [id]);
        break;
        
      case 'keyword':
        result = await client.query(`
          SELECT k.*, COUNT(pk.paper_id) as paper_count
          FROM keyword k
          LEFT JOIN paper_keyword pk ON k.id = pk.keyword_id
          WHERE k.id = $1
          GROUP BY k.id
        `, [id]);
        break;
        
      case 'paper':
        result = await client.query(`
          SELECT p.*, v.venue_name, v.impact_factor
          FROM paper p
          LEFT JOIN venue v ON p.venue_id = v.id
          WHERE p.id = $1
        `, [id]);
        break;
        
      default:
        result = await client.query(`
          SELECT * FROM research_field WHERE id = $1
          UNION
          SELECT * FROM keyword WHERE id = $1
          UNION
          SELECT * FROM paper WHERE id = $1
        `, [id]);
    }
    
    client.release();
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: '节点未找到' });
    }
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('节点查询错误:', error);
    res.status(500).json({ error: '节点查询失败', details: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`服务器运行在端口 ${PORT}`);
  console.log(`数据库连接: ${process.env.DB_HOST || 'pgm-bp1ksg5v1lo5z2r8eo.rwlb.rds.aliyuncs.com'}`);
});

module.exports = app;
