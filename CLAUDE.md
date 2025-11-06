# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a knowledge graph construction system that processes academic papers and stores them in a PostgreSQL database. The system follows a pipeline approach:

1. PDF processing using MinerU to convert PDFs to Markdown
2. Markdown parsing to extract paper metadata
3. Data transformation to match database schema
4. Database insertion with proper foreign key relationships

## Directory Structure

```
.
├── config.env                 # Environment configuration
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── 数据库.sql                 # Database schema
├── 目录配置说明.md            # Directory configuration
├── src/                      # Source code
│   ├── main.py               # Main entry point
│   ├── main_controller.py    # Main controller
│   ├── pdf_processor/        # PDF processing utilities
│   ├── md_parser/            # Markdown parsing utilities
│   ├── database_connector/   # Database connection utilities
│   ├── data_inserter.py      # Data insertion logic
│   ├── db_manager.py         # Database management
│   ├── process_pdfs.py       # PDF processing pipeline
│   ├── test_single_pdf.py    # Single PDF testing
│   └── utils/                # Utility functions
├── input/                    # Input PDF files
├── output/                   # Processed Markdown files
├── processed/                # Records of processed files
├── logs/                     # Log files
├── sample_md/                # Sample Markdown files
├── test_data/                # Test data
└── test_output/              # Test output
```

## Key Components

### 1. PDF Processing
- Uses MinerU to convert PDF files to Markdown format
- Processes PDFs in batch mode
- Handles file organization by groups

### 2. Markdown Parsing
- Extracts paper metadata from MinerU-generated Markdown files
- Parses authors, abstract, keywords, references
- Extracts experimental data (HRT conditions, pollutants, etc.)

### 3. Database Operations
- PostgreSQL database with hierarchical schema (research_field → keyword → paper)
- Uses text-based UUIDs for primary keys
- Implements proper foreign key relationships
- Handles upsert operations to avoid duplicates

### 4. Data Insertion
- Follows dependency order (research_field → keyword → paper)
- Manages author-paper and keyword-paper relationships
- Handles metadata storage

## Common Development Tasks

### Running the Complete Pipeline
```bash
python src/main.py
```

### Processing PDF Files
```bash
python src/pdf_processor/pdf_batch_processor.py -i /path/to/pdf/files -o /path/to/output
```

### Parsing Markdown Files
```bash
python src/md_parser/md_parser.py -i /path/to/md/files -o /path/to/output.json
```

### Importing Data to Database
```bash
python src/database_connector/data_importer.py -i /path/to/parsed_data.json
```

## Database Schema

The database follows a hierarchical structure:
- `research_field`: Top-level research domains
- `keyword`: Research keywords linked to fields
- `paper`: Academic papers
- `paper_keyword`: Many-to-many relationship between papers and keywords
- `author`: Paper authors
- `paper_author`: Many-to-many relationship between papers and authors
- `venue`: Journals and conferences
- `paper_metadata`: Additional paper metadata

## Configuration

The system uses environment variables from `config.env`:
- `INPUT_DIR`: Directory containing input PDF files
- `OUTPUT_DIR`: Directory for processed Markdown files
- `PROCESSED_DIR`: Directory tracking processed files
- `LOGS_DIR`: Directory for log files

Database connection parameters are also configured through environment variables.

## Architecture Notes

1. **ID Generation**: Uses UUID5 with DNS namespace for consistent ID generation across runs
2. **Error Handling**: Implements try-catch blocks with logging for error recovery
3. **Data Consistency**: Uses database transactions and upsert operations
4. **Modularity**: Separates concerns into distinct modules (parsing, database, insertion)
5. **Logging**: Comprehensive logging for debugging and monitoring

## Development Guidelines

1. Maintain the hierarchical insertion order (research_field → keyword → paper)
2. Use consistent ID generation strategy (UUID5 with appropriate namespace)
3. Handle database foreign key constraints properly
4. Follow existing code patterns for new functionality
5. Ensure proper error handling and logging