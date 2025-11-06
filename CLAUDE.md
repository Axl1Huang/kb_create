# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a knowledge graph construction system that processes academic papers and stores them in a PostgreSQL database. The system follows a pipeline approach:

1. PDF processing using MinerU to convert PDFs to Markdown
2. LLM-based parsing to extract paper metadata
3. Data transformation to match database schema
4. Database insertion with proper foreign key relationships

## Directory Structure

```
.
├── config/                 # Configuration files
│   ├── config.env         # Environment configuration
│   └── config.env.example # Configuration example
├── data/                   # Data files
│   ├── input/             # Input PDF files
│   ├── output/            # Processed Markdown files
│   ├── processed/         # Records of processed files
│   └── test/              # Test data
├── src/                    # Source code
│   ├── core/              # Core pipeline components
│   │   ├── __init__.py
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # Database connection utilities
│   │   ├── pdf_processor.py # PDF processing utilities
│   │   ├── llm_parser.py  # LLM-based parsers
│   │   ├── data_importer.py # Data insertion logic
│   │   └── pipeline.py    # Main pipeline orchestration
│   ├── database_connector/ # Database connector (legacy)
│   ├── llm_parsers/       # LLM parsers (legacy)
│   ├── pdf_processor/     # PDF processor (legacy)
│   ├── utils/             # Utility functions
│   │   ├── __init__.py
│   │   └── helpers.py
│   └── __init__.py
├── logs/                   # Log files
├── docs/                   # Documentation
├── input/                  # Input directory (alternative to data/input)
├── output/                 # Output directory (alternative to data/output)
├── processed/              # Processed files directory (alternative to data/processed)
├── temp/                   # Temporary files
├── main.py                # Main entry point
├── requirements.txt        # Python dependencies
└── database.sql           # Database schema
```

## Key Components

### 1. Core Pipeline (`src/core/`)
The core pipeline orchestrates the entire knowledge graph construction process:

- `config.py`: Centralized configuration management using environment variables
- `pipeline.py`: Main pipeline orchestration with modular stages
- `pdf_processor.py`: PDF processing using MinerU
- `llm_parser.py`: LLM-based parsing of Markdown files
- `data_importer.py`: Database insertion with proper relationships
- `database.py`: Database connection and operations

### 2. PDF Processing
- Uses MinerU to convert PDF files to Markdown format
- Processes PDFs in batch mode
- Handles file organization and error recovery

### 3. LLM Parsing
- Uses DashScope Qwen models to parse paper metadata from Markdown
- Extracts structured data including title, authors, abstract, keywords, etc.
- Handles experimental data extraction (HRT conditions, pollutants, etc.)

### 4. Database Operations
- PostgreSQL database with hierarchical schema
- Uses text-based UUIDs for primary keys
- Implements proper foreign key relationships
- Handles upsert operations to avoid duplicates

### 5. Data Insertion
- Follows dependency order (research_field → keyword → paper)
- Manages author-paper and keyword-paper relationships
- Handles metadata storage

## Common Development Tasks

### Running the Complete Pipeline
```bash
python main.py
```

### Running Individual Stages
```bash
# PDF processing only
python main.py --skip-import

# Data import only (from existing Markdown files)
python main.py --skip-pdf

# Debug mode
python main.py --log-level DEBUG
```

### Configuration
The system uses environment variables from `config/config.env`:
- `INPUT_DIR`: Directory containing input PDF files
- `OUTPUT_DIR`: Directory for processed Markdown files
- `PROCESSED_DIR`: Directory tracking processed files
- `LOGS_DIR`: Directory for log files
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Database connection parameters
- `DASHSCOPE_API_KEY`: API key for LLM parsing
- `DASHSCOPE_MODEL`: Model to use for LLM parsing

## Architecture Notes

1. **Modular Design**: Core components are separated into distinct modules for maintainability
2. **Configuration Management**: Centralized configuration using dataclasses and environment variables
3. **Error Handling**: Comprehensive try-catch blocks with logging for error recovery
4. **Data Consistency**: Uses database transactions and upsert operations
5. **Logging**: Unified logging configuration for debugging and monitoring
6. **ID Generation**: Uses UUID5 with DNS namespace for consistent ID generation across runs

## Development Guidelines

1. Maintain the hierarchical insertion order (research_field → keyword → paper)
2. Use consistent ID generation strategy (UUID5 with appropriate namespace)
3. Handle database foreign key constraints properly
4. Follow existing code patterns for new functionality
5. Ensure proper error handling and logging
6. Keep modules focused and cohesive