# Documentation Organization Guidelines

## Purpose

This documentation system provides comprehensive guidance for the GEX-LLM Pattern Analysis project. It is organized into logical categories to help future contributors, researchers, and AI assistants understand how to structure, format, and maintain project documentation.

## Directory Structure

```bash
docs/
├── README.md                  # This file - organization guidelines
├── architecture/              # System design and component interactions
├── agents/                    # LLM agent frameworks and workflows
├── technical/                 # Implementation details and technical specs
├── research/                  # Research methodology and academic standards
├── api/                       # API documentation and integration guides
├── CACHE_AUDIT_REPORT.md      # Cache system analysis and problems
└── CACHE_CLEANUP_SUMMARY.md   # Cache cleanup actions and results
```

## Folder Guidelines

### `architecture/`

**Purpose**: High-level system design, component relationships, and overall project structure.

**Contents Should Include**:

- System architecture diagrams and explanations
- Component interaction flows
- Directory structure documentation
- Design principles and patterns
- Integration points between major components

**Naming Convention**: `{component}_overview.md`, `{system}_architecture.md`

**Example Files**:

- `architecture_overview.md` - Main system architecture
- `caching_architecture.md` - Cache system design
- `data_flow_architecture.md` - Data processing flows

### `agents/`

**Purpose**: Documentation for LLM agent systems, multi-agent workflows, and AI integration.

**Contents Should Include**:

- Agent role definitions and responsibilities
- Multi-agent conversation patterns
- Prompt engineering guidelines
- Agent configuration and setup
- Cost optimization strategies

**Naming Convention**: `{framework}_integration.md`, `{agent_type}_workflows.md`

**Example Files**:

- `agent_framework.md` - Autogen multi-agent setup
- `prompt_engineering.md` - Prompt design patterns
- `conversation_flows.md` - Agent interaction patterns

### `technical/`

**Purpose**: Implementation details, technical specifications, and developer-focused documentation.

**Contents Should Include**:

- API integration guides
- Mathematical implementations
- Data processing pipelines
- Utility functions and tools
- Performance optimization guides
- Testing strategies

**Naming Convention**: `{component}_implementation.md`, `{feature}_technical_spec.md`

**Example Files**:

- `gex_calculations.md` - Mathematical GEX implementation
- `data_pipeline.md` - Data collection and processing
- `tools_and_utils.md` - Utility functions reference
- `caching_strategy.md` - Cache implementation details
- `performance_optimization.md` - Speed and memory optimization

### `research/`

**Purpose**: Academic methodology, statistical approaches, and research standards.

**Contents Should Include**:

- Research methodology and experimental design
- Statistical validation approaches
- Bias prevention strategies
- Ethical considerations
- Publication standards
- Reproducibility requirements

**Naming Convention**: `{topic}_methodology.md`, `{approach}_validation.md`

**Example Files**:

- `research_methodology.md` - Overall research approach
- `statistical_validation.md` - Statistical testing methods
- `bias_prevention.md` - Controls for research bias
- `ethics_and_standards.md` - Ethical research guidelines

### `api/`

**Purpose**: External API documentation, integration guides, and reference materials.

**Contents Should Include**:

- Third-party API integration guides
- Internal API documentation
- Authentication and security
- Rate limiting and error handling
- API response formats and examples

**Naming Convention**: `{service}_api.md`, `{endpoint}_reference.md`

**Example Files**:

- `alpha_vantage_integration.md` - Alpha Vantage API guide
- `openai_api_usage.md` - OpenAI/LLM API integration
- `internal_api_reference.md` - Project's internal APIs

## Critical System Documentation

### Cache System Analysis (September 2025)

**⚠️ CRITICAL INFRASTRUCTURE DOCUMENTATION**

The project underwent a major cache system audit and cleanup in September 2025 due to critical organizational issues:

#### Key Documents
- **`CACHE_AUDIT_REPORT.md`** - Complete analysis of cache system chaos
  - 8 databases reduced to 1 source of truth
  - Directory structure and usage patterns documented  
  - Data flow mapping (API → Pickle → Database)
  - Identified existing `UnifiedCacheManager` infrastructure

- **`CACHE_CLEANUP_SUMMARY.md`** - Cleanup actions and results
  - 400K+ storage recovered by removing test files
  - Emergency cleanup phase completed
  - Architecture recommendations for unified system
  - Next steps for proper cache-first implementation

#### Critical Findings
- **Database consolidation**: `consolidated_historical.db` is source of truth (13 records)
- **Data storage**: 34M options data, 1.4M market data in organized pickle files
- **Missing data**: Need complete 2015-2024 historical data for statistical validity
- **Architecture issue**: Existing `UnifiedCacheManager` should be used instead of hardcoded paths

#### GitHub Issues
- **Issue #44**: Cache System Organization and Documentation Overhaul
- **Issue #45**: Design: Unified Data Storage and Retrieval System

#### Branch Status
- **`dbreorg` branch**: Contains cache cleanup and documentation
- **Status**: Cleanup phase complete, ready for unified system implementation

**⚠️ DO NOT bypass the `UnifiedCacheManager` - use existing cache infrastructure!**

## File Naming Conventions

### General Rules

- **Use snake_case**: `file_name.md` (not `fileName.md` or `file-name.md`)
- **Be descriptive**: Name should clearly indicate content
- **Use consistent suffixes**: `_overview.md`, `_implementation.md`, `_methodology.md`
- **Avoid special characters**: No `@`, `#`, `%`, spaces, or punctuation except `_` and `-`

### Recommended Patterns

```
{component}_overview.md        # High-level component description
{feature}_implementation.md    # Technical implementation details
{process}_workflow.md         # Step-by-step processes
{system}_architecture.md      # System design documentation
{topic}_methodology.md        # Research or analytical methods
{service}_integration.md      # External service integration
{tool}_reference.md           # Reference documentation
{concept}_explanation.md      # Conceptual explanations
```

## Document Formatting Standards

### Markdown Structure

```markdown
# Document Title (H1 - Only one per document)

## Major Section (H2)

### Subsection (H3)

#### Minor Subsection (H4 - Use sparingly)

## Another Major Section
```

### Required Sections

Every documentation file should include:

1. **Purpose/Overview** - What this document covers
2. **Main Content** - Organized with clear headings
3. **Examples** - Code examples where applicable
4. **Integration Points** - How this connects to other components
5. **References** - Links to related documentation

### Code Blocks

```python
# Always specify language for syntax highlighting
def example_function():
    """Include docstrings for functions"""
    return "formatted code"
```

### Cross-References

- Use relative paths: `../technical/gex_calculations.md`
- Link to specific sections: `[GEX Formula](../technical/gex_calculations.md#gamma-exposure-formula)`
- Reference other components: See `agents/agent_framework.md` for details

### Tables and Lists

- Use tables for structured data comparisons
- Use bullet points for feature lists
- Use numbered lists for step-by-step processes

## Content Guidelines

### Writing Style

- **Clear and Concise**: Avoid unnecessary complexity
- **Technical but Accessible**: Assume reader has programming knowledge
- **Complete**: Include all necessary context
- **Updated**: Keep documentation current with code changes

### Code Examples

- **Working Examples**: All code should be functional
- **Context**: Provide enough context to understand usage
- **Comments**: Explain complex logic
- **Imports**: Include necessary import statements

### Diagrams and Visuals

- Use ASCII art for simple diagrams
- Include system flow diagrams where helpful
- Keep visuals simple and focused
- Update diagrams when architecture changes

## Maintenance Guidelines

### When to Update Documentation

1. **Code Changes**: Update docs when functionality changes
2. **New Features**: Document new components immediately
3. **API Changes**: Update integration guides for API changes
4. **Research Updates**: Modify methodology docs for approach changes

### Version Control

- Commit documentation with related code changes
- Use descriptive commit messages for doc updates
- Review documentation in pull requests
- Keep documentation in sync with code versions

### Quality Checks

Before committing documentation:

- [ ] All links work (internal and external)
- [ ] Code examples are tested and functional
- [ ] Formatting is consistent with guidelines
- [ ] Content is up-to-date with current implementation
- [ ] Cross-references are accurate

## Guidelines for AI Assistants

### When Adding New Documentation

1. **Determine Category**: Choose appropriate subfolder based on content type
2. **Follow Naming**: Use snake_case and descriptive names
3. **Check Existing**: Avoid duplicating existing documentation
4. **Cross-Reference**: Link to related documentation appropriately
5. **Update Index**: Add references in relevant overview documents

### When Updating Documentation

1. **Preserve Structure**: Maintain existing organization patterns
2. **Update Cross-References**: Fix any broken links
3. **Maintain Consistency**: Follow established formatting
4. **Document Changes**: Note what was modified and why

### Integration with Main README

- Main project README should reference key documentation
- Keep docs/README.md focused on organization, not content
- Update main README when adding major documentation sections

## Current Documentation Map

### Architecture

- `architecture/architecture_overview.md` - Complete system design

### Agents  

- `agents/agent_framework.md` - Autogen multi-agent workflows

### Technical

- `technical/data_pipeline.md` - Data collection and processing
- `technical/gex_calculations.md` - Mathematical GEX framework
- `technical/tools_and_utils.md` - Utility functions and tools

### Research

- `research/research_methodology.md` - Statistical and ethical standards

### API

- *Ready for Alpha Vantage and OpenAI integration guides*

This organization ensures comprehensive, maintainable documentation that grows logically with the project while remaining accessible to both human researchers and AI assistants.
