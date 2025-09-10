# Testing Scripts

Scripts for system validation, integration testing, and quality assurance.

## Scripts

### `test_cache_integration.py`
- **Purpose**: Validates the cache system integration with data collection
- **Usage**: `python scripts/testing/test_cache_integration.py`
- **Tests**: Cache directory structure, methods availability, collector integration
- **Output**: Validation report of cache system functionality

## Testing Categories

### Integration Tests
- Cache system integration
- API client connectivity
- Data pipeline validation

### Unit Tests
- Individual component testing
- Function validation
- Error handling verification

## Adding New Test Scripts

When adding new test scripts:

1. **Naming**: Prefix with `test_` (e.g., `test_gex_calculations.py`)
2. **Structure**: Include setup, test execution, and cleanup
3. **Reporting**: Provide clear pass/fail indicators
4. **Coverage**: Test both success and failure scenarios