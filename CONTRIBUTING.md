# Contributing to M-Pesa Real-Time Transaction Streaming Pipeline

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences
- Accept responsibility and apologize for mistakes

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/Victor-Kipruto-Rop/Real_Time_Transaction_Streaming-MPESA-.git
   cd Real_Time_Transaction_Streaming-MPESA-
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/Victor-Kipruto-Rop/Real_Time_Transaction_Streaming-MPESA-.git
   ```

## Development Setup

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- PostgreSQL 15+
- Apache Kafka
- Git

### Setup Instructions

1. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start infrastructure**:
   ```bash
   make infra-up
   ```

5. **Verify setup**:
   ```bash
   make verify
   ```

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Error messages and logs**
- **Screenshots** if applicable

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** and motivation
- **Proposed solution** or implementation approach
- **Alternative solutions** considered
- **Impact** on existing functionality

### Code Contributions

1. **Check existing issues** or create a new one
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following coding standards
4. **Write tests** for new functionality
5. **Update documentation** as needed
6. **Commit your changes**:
   ```bash
   git commit -m "feat: add new feature description"
   ```
7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Create a Pull Request**

## Coding Standards

### Python Style Guide

- Follow **PEP 8** style guide
- Use **type hints** for function parameters and return values
- Maximum line length: **100 characters**
- Use **meaningful variable names**
- Add **docstrings** to all functions and classes

### Code Formatting

We use the following tools:

- **Black** for code formatting
- **Flake8** for linting
- **mypy** for type checking

Run before committing:
```bash
make format  # Format code
make lint    # Check linting
make type-check  # Type checking
```

### Commit Message Convention

Follow the **Conventional Commits** specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(kafka): add dead letter queue support
fix(webhook): handle duplicate transaction IDs
docs(readme): update installation instructions
test(daraja): add OAuth token caching tests
```

## Testing Guidelines

### Writing Tests

- Write tests for **all new features**
- Maintain **test coverage above 80%**
- Use **descriptive test names**
- Follow **AAA pattern** (Arrange, Act, Assert)
- Mock external dependencies

### Test Structure

```python
def test_feature_name_should_expected_behavior():
    """Test description explaining what is being tested"""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
make coverage

# Run integration tests
make test-integration
```

## Pull Request Process

1. **Update documentation** for any changed functionality
2. **Add tests** for new features
3. **Ensure all tests pass**:
   ```bash
   make test
   ```
4. **Update CHANGELOG.md** with your changes
5. **Request review** from maintainers
6. **Address review feedback** promptly
7. **Squash commits** if requested
8. **Wait for approval** before merging

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] CI/CD pipeline passing
- [ ] Reviewed by at least one maintainer

## Documentation

### Code Documentation

- Add **docstrings** to all public functions and classes
- Use **Google-style docstrings**:

```python
def process_transaction(transaction_id: str, amount: float) -> bool:
    """
    Process an M-Pesa transaction.
    
    Args:
        transaction_id: Unique transaction identifier
        amount: Transaction amount in KES
        
    Returns:
        True if processing successful, False otherwise
        
    Raises:
        ValueError: If amount is negative
        TransactionError: If transaction processing fails
    """
    pass
```

### README Updates

Update README.md when:
- Adding new features
- Changing setup instructions
- Modifying configuration options
- Adding new dependencies

### API Documentation

Document all API endpoints with:
- Endpoint URL and method
- Request parameters
- Request body schema
- Response schema
- Example requests/responses
- Error codes

## Project Structure

```
Real_Time_Transaction_Streaming-MPESA-/
├── ingestion/          # Data ingestion components
├── streaming/          # Kafka streaming logic
├── analytics/          # Analytics and reporting
├── ml/                 # Machine learning models
├── dbt/                # Data transformation
├── tests/              # Test suite
├── scripts/            # Utility scripts
├── docs/               # Documentation
└── docker/             # Docker configurations
```

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Email**: kipruto45@github.com

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to making this project better!
