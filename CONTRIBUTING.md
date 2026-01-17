# Contributing to Flight Sales Dashboard

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and professional in all interactions
- Provide constructive feedback
- Focus on improving the project for everyone

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/flight-sales-dashboard.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Push to your fork: `git push origin feature/your-feature-name`
6. Create a Pull Request

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies including dev tools
pip install -r requirements.txt
pip install pylint pytest black

# Set up pre-commit hooks (optional)
pre-commit install
```

## Code Style Guidelines

- Follow PEP 8 style guide
- Use meaningful variable and function names
- Keep functions small and focused
- Maximum line length: 100 characters
- Use type hints where applicable

### Formatting

Run black for automatic code formatting:
```bash
black *.py
```

### Linting

Check code quality with pylint:
```bash
pylint *.py
```

## Commit Message Guidelines

Format: `[TYPE] Brief description`

Types:
- `[FEAT]`: New feature
- `[FIX]`: Bug fix
- `[DOCS]`: Documentation changes
- `[STYLE]`: Code style changes
- `[REFACTOR]`: Code refactoring
- `[PERF]`: Performance improvements
- `[TEST]`: Adding or updating tests
- `[CHORE]`: Maintenance tasks

Examples:
```
[FEAT] Add export to PDF functionality
[FIX] Fix database connection timeout issue
[DOCS] Update installation instructions
[REFACTOR] Simplify analytics module structure
```

## Pull Request Process

1. Update README.md with any new features or API changes
2. Update CHANGELOG.md with your changes
3. Ensure code follows style guidelines
4. Test your changes thoroughly
5. Add descriptive PR title and description
6. Reference any related issues
7. Request review from maintainers

## Testing

When adding new features:
- Test with various date ranges
- Test with empty datasets
- Test error conditions
- Verify performance impact

## Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions
- Update CHANGELOG.md
- Add inline comments for complex logic
- Include examples in documentation

## Reporting Bugs

Create an issue with:
1. Clear, descriptive title
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Environment details (OS, Python version, etc.)
6. Screenshots if applicable

## Suggesting Enhancements

Create an issue with:
1. Clear description of the enhancement
2. Use case and motivation
3. Proposed implementation (if applicable)
4. Alternative approaches considered

## Questions or Need Help?

- Create a discussion in GitHub Discussions
- Check existing issues for similar questions
- Contact maintainers directly if needed

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

## Recognition

Contributors will be recognized in:
- README.md acknowledgments section
- Release notes

Thank you for making this project better!
