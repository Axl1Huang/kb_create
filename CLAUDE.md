# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a knowledge graph construction system that processes academic papers and stores them in a PostgreSQL database. The system follows a pipeline approach:

1. PDF processing using MinerU to convert PDFs to Markdown
2. LLM-based parsing to extract paper metadata
3. Data transformation to match database schema
4. Database insertion with proper foreign key relationships

The system is optimized for dual-GPU parallel processing and high-memory environments (96GB+ RAM), with dedicated GPU allocation:
- GPU 0: PDF to Markdown conversion (MinerU)
- GPU 1: Markdown to JSON parsing (LLM)

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
│   │   ├── pipeline.py    # Main pipeline orchestration
│   │   └── dual_gpu_pipeline.py # Dual-GPU parallel processing pipeline
│   ├── database_connector/ # Database connector (legacy)
│   ├── llm_parsers/       # LLM parsers (legacy)
│   ├── pdf_processor/     # PDF processor (legacy)
│   ├── utils/             # Utility functions
│   │   ├── __init__.py
│   │   ├── helpers.py
│   │   └── memory_manager.py # Memory management utilities
│   └── __init__.py
├── logs/                   # Log files
├── docs/                   # Documentation
├── input/                  # Input directory (alternative to data/input)
├── output/                 # Output directory (alternative to data/output)
├── processed/              # Processed files directory (alternative to data/processed)
├── temp/                   # Temporary files
├── main.py                # Main entry point
├── requirements.txt        # Python dependencies
├── unified_batch_processor.py # Unified batch processing entry point
├── setup_and_process.py   # Setup and processing script
└── 数据库.sql             # Database schema (in Chinese)
```

## Key Components

### 1. Core Pipeline (`src/core/`)
The core pipeline orchestrates the entire knowledge graph construction process:

- `config.py`: Centralized configuration management using environment variables with unified config support
- `pipeline.py`: Main pipeline orchestration with modular stages
- `pdf_processor.py`: PDF processing using MinerU
- `llm_parser.py`: LLM-based parsing of Markdown files with GPU device support
- `data_importer.py`: Database insertion with proper relationships
- `database.py`: Database connection and operations
- `dual_gpu_pipeline.py`: Dual-GPU parallel processing pipeline with dedicated GPU allocation

### 2. PDF Processing
- Uses MinerU to convert PDF files to Markdown format
- Processes PDFs in batch mode
- Handles file organization and error recovery

### 3. LLM Parsing
- Uses Ollama models to parse paper metadata from Markdown
- Extracts structured data including title, authors, abstract, keywords, etc.
- Handles experimental data extraction (HRT conditions, pollutants, etc.)
- Supports GPU device configuration for dedicated GPU allocation

### 4. Dual-GPU Parallel Processing
- Dedicated GPU allocation for optimal performance
- GPU 0: PDF to Markdown conversion (MinerU)
- GPU 1: Markdown to JSON parsing (LLM)
- Multi-threaded processing with queue-based pipeline
- Memory optimization for high-memory environments (96GB+ RAM)

### 5. Database Operations
- PostgreSQL database with hierarchical schema
- Uses text-based UUIDs for primary keys
- Implements proper foreign key relationships
- Handles upsert operations to avoid duplicates

### 6. Data Insertion
- Follows dependency order (research_field → keyword → paper)
- Manages author-paper and keyword-paper relationships
- Handles metadata storage

## Common Development Tasks

### Installing Dependencies
```bash
pip install -r requirements.txt
```

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

# Process only first N PDFs
python main.py --limit-pdfs 10

# Import only first N Markdown files
python main.py --limit-md 10
```

### Running High-Performance Dual-GPU Pipeline
```bash
# Run high-performance dual-GPU pipeline
python scripts/high_performance_batch.py

# Run with specific configuration
python scripts/high_performance_batch.py --limit 100 --log-level DEBUG

# Run unified batch processor
python unified_batch_processor.py --mode full --workers 4
```

### Running Tests
```bash
# Run a specific test
python tests/unit/test_pdf_processor.py

# Run all tests in a directory
python -m pytest tests/
```

### Configuration
The system uses environment variables from `config/config.env`:
- `INPUT_DIR`: Directory containing input PDF files
- `OUTPUT_DIR`: Directory for processed Markdown files
- `PROCESSED_DIR`: Directory tracking processed files
- `LOGS_DIR`: Directory for log files
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Database connection parameters
- `OLLAMA_URL`: URL for Ollama LLM service
- `LLM_MODEL`: Model to use for LLM parsing
- `LLM_DEVICE`: Device to use for LLM parsing (e.g., "cuda:1" for GPU 1)

## Database Schema

The database uses a hierarchical structure with 10 tables:

1. `venue` - Journal/conference information
2. `research_field` - Top-level research domains
3. `keyword` - Research keywords linked to fields
4. `paper` - Paper metadata
5. `paper_metadata` - Extended paper metadata
6. `paper_keyword` - Many-to-many relationship between papers and keywords
7. `author` - Author information
8. `paper_author` - Many-to-many relationship between papers and authors
9. `paper_citation` - Citation relationships between papers
10. `user_selection` - User configuration for field visibility

## Architecture Notes

1. **Modular Design**: Core components are separated into distinct modules for maintainability
2. **Configuration Management**: Centralized configuration using dataclasses and environment variables with unified config support
3. **Error Handling**: Comprehensive try-catch blocks with logging for error recovery
4. **Data Consistency**: Uses database transactions and upsert operations
5. **Logging**: Unified logging configuration for debugging and monitoring
6. **ID Generation**: Uses UUID5 with DNS namespace for consistent ID generation across runs
7. **Dual-GPU Parallel Processing**: Dedicated GPU allocation for optimal performance with GPU 0 for PDF processing and GPU 1 for LLM parsing
8. **Memory Optimization**: Dynamic memory management for high-memory environments (96GB+ RAM)

## Development Guidelines

1. Maintain the hierarchical insertion order (research_field → keyword → paper)
2. Use consistent ID generation strategy (UUID5 with appropriate namespace)
3. Handle database foreign key constraints properly
4. Follow existing code patterns for new functionality
5. Ensure proper error handling and logging
6. Keep modules focused and cohesive
7. When adding new LLM functionality, consider GPU device configuration for dual-GPU optimization
8. Use the unified configuration management system for new configuration options
9. Implement memory optimization strategies for high-memory environments