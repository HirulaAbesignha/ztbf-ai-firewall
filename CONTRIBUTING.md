# Contributing to AI-Driven Zero-Trust Behavior Firewall (ZTBF)

First off, thank you for considering contributing to ZTBF! 🎉

This project aims to build a **research-grade, enterprise-ready behavioral security system**. We welcome contributions from security researchers, ML engineers, data scientists, and developers of all skill levels.

---

<!-- ## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Testing Guidelines](#testing-guidelines)
- [Issue Labels](#issue-labels)

---
-->
## 📜 Code of Conduct

This project adheres to a **Code of Conduct** that all contributors must follow:

- **Be respectful**: Treat everyone with respect and kindness
- **Be collaborative**: Work together towards common goals
- **Be professional**: Keep discussions focused on technical matters
- **Be inclusive**: Welcome diverse perspectives and backgrounds
- **Be constructive**: Provide helpful, actionable feedback

**Unacceptable behavior** includes harassment, discrimination, trolling, or personal attacks.

---

## 🤝 How Can I Contribute?

### 1. **Reporting Bugs** 🐛

Found a bug? Help us fix it!

- Check if the bug is already reported in [Issues](https://github.com/your-org/ztbf/issues)
- If not, create a new issue using the **Bug Report** template
- Include: steps to reproduce, expected vs actual behavior, logs, screenshots

### 2. **Suggesting Features** 💡

Have an idea to improve ZTBF?

- Check existing [Feature Requests](https://github.com/your-org/ztbf/issues?q=is%3Aissue+label%3Aenhancement)
- Create a new issue using the **Feature Request** template
- Describe: the problem, proposed solution, alternatives considered

### 3. **Writing Code** 💻

Pick an issue and start coding!

- **Good First Issues**: Look for `good first issue` label
- **Help Wanted**: Check `help wanted` label for priority tasks
- **Phase-Specific**: Issues are tagged by phase (Phase 1, Phase 2, etc.)

### 4. **Improving Documentation** 📚

Documentation is crucial!

- Fix typos, clarify explanations, add examples
- Create tutorials, how-to guides, or architecture deep-dives
- Improve code comments and docstrings

### 5. **Creating Test Cases** 🧪

Help us maintain quality!

- Add unit tests for existing code
- Create integration tests for workflows
- Develop adversarial test scenarios (attack simulations)

### 6. **Security Research** 🔒

Contribute to threat modeling!

- Propose new attack scenarios
- Identify detection gaps
- Suggest ML model improvements

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose**
- **Git**
- **4GB RAM minimum**

### Setup Development Environment

```bash
# 1. Fork the repository on GitHub
# Click "Fork" button at https://github.com/your-org/ztbf

# 2. Clone YOUR fork
git clone https://github.com/HirulaAbesignha/ztbf.git
cd ztbf

# 3. Add upstream remote
git remote add upstream https://github.com/your-org/ztbf.git

# 4. Run automated setup
chmod +x scripts/setup_local_env.sh
./scripts/setup_local_env.sh

# 5. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 6. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools

# 7. Start Docker services
docker-compose -f deployment/docker/docker-compose.yml up -d

# 8. Run tests to verify setup
pytest tests/ -v
```

---

## 🔄 Development Workflow

### 1. **Pick an Issue**

- Browse [open issues](https://github.com/your-org/ztbf/issues)
- Comment on the issue to claim it: "I'd like to work on this!"
- Wait for maintainer approval (usually within 24 hours)

### 2. **Create a Branch**

**Branch Naming Convention:**

```
<type>/<issue-number>-<short-description>

Examples:
- feature/42-add-lstm-autoencoder
- bugfix/15-fix-queue-overflow
- docs/23-improve-api-documentation
- test/31-add-normalizer-tests
```

**Types:**
- `feature/` - New functionality
- `bugfix/` - Bug fixes
- `docs/` - Documentation only
- `test/` - Test additions/improvements
- `refactor/` - Code refactoring
- `performance/` - Performance improvements
- `security/` - Security enhancements

**Create and switch to your branch:**

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create your feature branch
git checkout -b feature/42-add-lstm-autoencoder
```

### 3. **Make Your Changes**

- Write clean, well-commented code
- Follow our [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed

### 4. **Test Your Changes**

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_normalizer.py -v

# Check code coverage
pytest tests/ --cov=src --cov-report=html

# Run linters
black src/ tests/
flake8 src/ tests/
mypy src/

# Run type checks
mypy src/data_pipeline/
```

### 5. **Commit Your Changes**

Follow our [commit guidelines](#commit-guidelines):

```bash
git add .
git commit -m "feat(normalizer): add support for VPC Flow Logs

- Add VPC Flow Log schema
- Implement normalization logic
- Add unit tests for VPC events

Closes #42"
```

### 6. **Push to Your Fork**

```bash
git push origin feature/42-add-lstm-autoencoder
```

### 7. **Create a Pull Request**

- Go to your fork on GitHub
- Click "New Pull Request"
- Select your branch
- Fill out the PR template
- Link related issues (e.g., "Closes #42")
- Request review from maintainers

---

## 📝 Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

```python
# Use 4 spaces for indentation (no tabs)
# Maximum line length: 100 characters
# Use double quotes for strings (unless single quotes avoid escaping)

# Good
def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single event through the pipeline.
    
    Args:
        event: Raw event dictionary
    
    Returns:
        Processed event dictionary
    
    Raises:
        ValidationError: If event schema is invalid
    """
    if not event:
        raise ValueError("Event cannot be empty")
    
    return normalized_event
```

### Code Quality Tools

**Mandatory before committing:**

```bash
# Auto-format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Documentation Standards

**All public functions/classes MUST have docstrings:**

```python
def enrich_event(event: Dict[str, Any], context: EnrichmentContext) -> Dict[str, Any]:
    """
    Enrich event with additional contextual data.
    
    Adds GeoIP location, entity metadata, device fingerprint, and
    resource sensitivity classification to the normalized event.
    
    Args:
        event: Normalized event dictionary with required fields:
            - entity_id (str): User or service identifier
            - source_ip (str): Source IP address
            - timestamp (datetime): Event timestamp
        context: Enrichment configuration and cache
    
    Returns:
        Enriched event dictionary with additional fields:
            - location (Dict): GeoIP location data
            - entity_metadata (Dict): User/service metadata
            - device (Dict): Device fingerprint
            - resource_sensitivity (int): Sensitivity level 1-5
    
    Raises:
        EnrichmentError: If enrichment fails critically
    
    Example:
        >>> event = {"entity_id": "alice@company.com", "source_ip": "8.8.8.8"}
        >>> enriched = enrich_event(event, context)
        >>> enriched["location"]["city"]
        'Mountain View'
    
    Note:
        GeoIP lookups are cached for performance. Cache TTL is configurable
        via EnrichmentContext.cache_ttl.
    """
    pass
```

### File Organization

```python
"""
Module docstring explaining purpose and usage.

File: src/data_pipeline/processing/enricher.py

This module implements event enrichment logic for ZTBF.
It adds contextual information to normalized events including
GeoIP location, entity metadata, and device fingerprinting.

Usage:
    enricher = EventEnricher(config)
    enriched_event = await enricher.enrich(normalized_event)
"""

# Standard library imports
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Third-party imports
import pandas as pd
from pydantic import BaseModel

# Local imports
from data_pipeline.schemas.unified_schema import UnifiedEvent

# Module constants
DEFAULT_CACHE_TTL = 3600
MAX_RETRIES = 3

# Logger configuration
logger = logging.getLogger(__name__)
```

---

## 📜 Commit Guidelines

We use **Conventional Commits** for clear commit history:

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding/updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `style`: Code style changes (formatting)
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Scopes

- `api`: Ingestion API
- `queue`: Event queue
- `normalizer`: Event normalization
- `enricher`: Event enrichment
- `processor`: Event processor
- `storage`: Storage layer
- `generator`: Synthetic data generator
- `ml`: Machine learning models
- `tests`: Test infrastructure

### Examples

```bash
# Feature addition
git commit -m "feat(normalizer): add VPC Flow Log support

- Implement VPC Flow Log schema
- Add normalization logic for VPC events
- Include tests for edge cases

Closes #42"

# Bug fix
git commit -m "fix(queue): prevent memory leak in disk buffer

The SQLite connection was not being closed properly,
causing memory accumulation over time.

Fixes #15"

# Documentation
git commit -m "docs(readme): add quick start guide

Added step-by-step setup instructions for new contributors"

# Breaking change
git commit -m "feat(api)!: change event schema to v2

BREAKING CHANGE: Event schema updated from v1 to v2.
All clients must update to new schema format.

Migration guide: docs/migration-v1-to-v2.md"
```

---

## 🔀 Pull Request Process

### Before Submitting

**Checklist:**

- [ ] Code follows style guidelines (black, flake8, mypy pass)
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New features have tests (unit + integration)
- [ ] Documentation is updated
- [ ] Commit messages follow guidelines
- [ ] Branch is up-to-date with `main`

### PR Title Format

Use the same format as commit messages:

```
feat(normalizer): add VPC Flow Log support
fix(queue): prevent memory leak in disk buffer
docs(contributing): improve setup instructions
```

### PR Description Template

When you create a PR, fill out this template:

```markdown
## Description
Brief description of what this PR does.

## Related Issues
Closes #42
Related to #38

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Changes Made
- Added VPC Flow Log schema
- Implemented normalization logic
- Added unit tests
- Updated documentation

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing locally
- [ ] Manual testing completed

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added and passing
```

### Review Process

1. **Automated Checks**: CI/CD runs tests, linters, type checks
2. **Code Review**: At least 1 maintainer approval required
3. **Discussion**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: Squash and merge to `main`

### After Merge

```bash
# Sync your fork with upstream
git checkout main
git fetch upstream
git merge upstream/main
git push origin main

# Delete your feature branch
git branch -d feature/42-add-lstm-autoencoder
git push origin --delete feature/42-add-lstm-autoencoder
```

---

## 📂 Project Structure

Understanding the codebase:

```
ai-zero-trust-behavior-firewall/
├── research/              # Research documents, threat models
├── architecture/          # Architecture diagrams, design docs
├── src/
│   └── data_pipeline/
│       ├── schemas/       # Pydantic models, event schemas
│       ├── ingestion/     # API, queue, collectors
│       ├── processing/    # Normalizer, enricher, processor
│       ├── storage/       # Storage layer implementations
│       ├── ml_models/     # ML models (Phase 2+)
│       ├── risk_engine/   # Risk scoring (Phase 3+)
│       └── utils/         # Shared utilities
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── adversarial/       # Attack simulation tests
├── configs/               # Configuration files
├── deployment/            # Docker, K8s, IaC
├── scripts/               # Utility scripts
└── docs/                  # Additional documentation
```

---

## 🧪 Testing Guidelines

### Test Categories

**1. Unit Tests** (`tests/unit/`)
- Test individual functions/classes
- Mock external dependencies
- Fast execution (<1s per test)

**2. Integration Tests** (`tests/integration/`)
- Test component interactions
- Use real dependencies (Docker services)
- Moderate execution (<10s per test)

**3. Adversarial Tests** (`tests/adversarial/`)
- Simulate attack scenarios
- Validate detection capabilities
- Can be slower (comprehensive)

### Writing Tests

```python
# tests/unit/test_normalizer.py

import pytest
from datetime import datetime
from src.data_pipeline.processing.normalizer import EventNormalizer

@pytest.fixture
def normalizer():
    """Fixture providing a normalizer instance."""
    return EventNormalizer()

@pytest.fixture
def sample_azure_event():
    """Fixture providing a sample Azure AD event."""
    return {
        "source_type": "azure_ad",
        "id": "test-123",
        "createdDateTime": "2025-01-08T10:00:00Z",
        "userPrincipalName": "alice@company.com",
        # ... more fields
    }

class TestEventNormalizer:
    """Test suite for EventNormalizer."""
    
    @pytest.mark.asyncio
    async def test_normalize_azure_ad_success(self, normalizer, sample_azure_event):
        """Test successful Azure AD event normalization."""
        # Act
        result = await normalizer.normalize(sample_azure_event)
        
        # Assert
        assert result["entity_id"] == "alice@company.com"
        assert result["entity_type"] == "user"
        assert result["event_type"] == "authentication"
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_normalize_invalid_source_type(self, normalizer):
        """Test normalization fails with invalid source type."""
        # Arrange
        invalid_event = {"source_type": "invalid"}
        
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown source type"):
            await normalizer.normalize(invalid_event)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/unit/test_normalizer.py -v

# Specific test
pytest tests/unit/test_normalizer.py::TestEventNormalizer::test_normalize_azure_ad_success -v

# With coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Parallel execution
pytest tests/ -n auto

# Stop on first failure
pytest tests/ -x

# Only failed tests from last run
pytest tests/ --lf
```

---

## 🏷️ Issue Labels

We use labels to categorize issues:

### Priority
- `priority: critical` - Must be fixed immediately
- `priority: high` - Important, fix soon
- `priority: medium` - Normal priority
- `priority: low` - Nice to have

### Type
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `question` - Further information is requested
- `performance` - Performance improvements

### Difficulty
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `advanced` - Requires deep knowledge

### Phase
- `phase-1` - Data pipeline
- `phase-2` - Feature engineering
- `phase-3` - ML models
- `phase-4` - Risk engine
- `phase-5` - Dashboard
- `phase-6` - Testing

### Component
- `api` - Ingestion API
- `queue` - Event queue
- `processor` - Event processor
- `ml-model` - Machine learning
- `storage` - Storage layer
- `testing` - Test infrastructure

---

## 🎯 Development Tips

### Debugging

```python
# Use logging instead of print()
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed debug info")
logger.info("Important information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)

# Set log level
export LOG_LEVEL=DEBUG
```

### Performance Profiling

```bash
# Profile code
python -m cProfile -o profile.stats src/data_pipeline/processing/processor.py

# View results
python -m pstats profile.stats
```

### IDE Setup

**VSCode** (`.vscode/settings.json`):
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true
}
```

---

## 📞 Getting Help

- **Questions**: Open a [Discussion](https://github.com/your-org/ztbf/discussions)
- **Bug Reports**: Create an [Issue](https://github.com/your-org/ztbf/issues/new?template=bug_report.md)
- **Feature Requests**: Create an [Issue](https://github.com/your-org/ztbf/issues/new?template=feature_request.md)

---

## 🙏 Thank You!

Every contribution helps make ZTBF better. Whether you're:
- Fixing a typo
- Adding a test
- Implementing a feature
- Improving documentation
- Sharing ideas

**You're making a difference in cybersecurity research!**

Happy coding! 🚀

---

**Project Maintainers:**
- [Hirula Abesignha](https://github.com/HirulaAbesignha)

**License:** MIT - See [LICENSE](LICENSE) for details