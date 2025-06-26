# SynthDB Documentation

This directory contains the source files for SynthDB's comprehensive documentation system, built with both Sphinx and MkDocs Material for different use cases.

## Documentation Structure

```
docs/
├── index.md                    # Main documentation homepage
├── getting-started/            # Installation and quickstart guides
├── user-guide/                # Detailed user documentation
├── api/                       # API reference documentation
├── examples/                  # Code examples and tutorials
├── advanced/                  # Advanced topics and troubleshooting
├── development/               # Contributor and developer docs
│   └── feature-proposals/     # Feature proposals and planning
├── conf.py                    # Sphinx configuration
├── stylesheets/              # Custom CSS styling
└── README.md                 # This file
```

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
# With uv (recommended)
uv sync --extra docs

# With pip
pip install "synthdb[docs]"

# Or install individual packages
pip install sphinx furo myst-parser sphinx-copybutton sphinx-design mkdocs mkdocs-material mkdocstrings[python] mike
```

### Build Commands

```bash
# Check if dependencies are installed
make docs-check
# or
python scripts/build_docs.py check

# Build all documentation
make docs-build
# or
python scripts/build_docs.py build

# Serve for development (auto-reload)
make docs-serve
# or
python scripts/build_docs.py serve

# Build only specific format
make docs-mkdocs      # MkDocs only
make docs-sphinx      # Sphinx only

# Clean build directories
make docs-clean

# Deploy to GitHub Pages
make docs-deploy
```

### Development Server

Start the development server for live editing:

```bash
make docs-serve
```

This will start MkDocs Material on http://localhost:8000 with automatic reloading when files change.

## Documentation Systems

### MkDocs Material (Primary)
- **Purpose**: User-facing documentation, guides, tutorials
- **URL**: http://localhost:8000 (development)
- **Features**: 
  - Beautiful Material Design theme
  - Fast search and navigation
  - Mobile-responsive
  - Syntax highlighting
  - Mermaid diagrams

### Sphinx (API Reference)
- **Purpose**: API documentation generated from docstrings
- **URL**: http://localhost:8001 (development)
- **Features**:
  - Automatic API documentation from code
  - Cross-references and linking
  - Advanced reStructuredText features
  - PDF generation capability

## Writing Documentation

### Adding New Pages

1. Create a new Markdown file in the appropriate directory
2. Add the page to `mkdocs.yml` navigation
3. Use proper heading structure (start with `#`)
4. Include code examples where helpful

### Markdown Features

SynthDB documentation supports:

```markdown
# Standard Markdown
**Bold text**, *italic text*, `inline code`

# Code blocks with syntax highlighting
```python
import synthdb
db = synthdb.connect('app.db')
```

# Admonitions
!!! note "Important Note"
    This is a note admonition.

!!! warning "Warning"
    This is a warning admonition.

# Tables
| Feature | Status |
|---------|--------|
| Joins   | Planned |

# Links
[Connection API](api/connection.md)
```

### Feature Proposals

New feature proposals should:

1. Use the feature proposal template
2. Be placed in `docs/development/feature-proposals/`
3. Include proper status badges
4. Follow the established format

Example status badges:
```html
<div class="status-badge status-proposed">Proposed</div>
<div class="status-badge status-in-progress">In Progress</div>
<div class="status-badge status-implemented">Implemented</div>
```

### API Documentation

API documentation is automatically generated from Python docstrings using mkdocstrings:

```markdown
# Include full class documentation
::: synthdb.Connection
    options:
      show_source: true

# Include specific method
::: synthdb.Connection.insert
    options:
      show_source: false
```

## Styling and Customization

### Custom CSS
Add custom styles to `docs/stylesheets/extra.css`:

```css
/* Custom theme colors */
:root {
  --md-primary-fg-color: #336790;
  --md-accent-fg-color: #4A9EE0;
}

/* Custom component styles */
.feature-proposal {
  border-left: 4px solid var(--md-accent-fg-color);
  padding-left: 1rem;
}
```

### Material Theme Configuration
Customize the theme in `mkdocs.yml`:

```yaml
theme:
  name: material
  palette:
    primary: blue
    accent: blue
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate
```

## Deployment

### GitHub Pages
Documentation is automatically deployed to GitHub Pages using Mike for versioning:

```bash
# Deploy current version
make docs-deploy

# Deploy specific version
mike deploy v1.0.0 latest --update-aliases --push

# Set default version
mike set-default latest --push
```

### Manual Deployment
For other hosting platforms:

```bash
# Build static site
make docs-build

# Upload contents of site/ directory to your hosting provider
```

## Contributing to Documentation

### Guidelines
1. **Clarity**: Write for your intended audience (beginners vs advanced users)
2. **Examples**: Include working code examples
3. **Accuracy**: Test all code examples before submitting
4. **Consistency**: Follow existing style and structure
5. **Completeness**: Cover edge cases and error scenarios

### Review Process
1. Create a feature branch for documentation changes
2. Write/update documentation
3. Test locally with `make docs-serve`
4. Submit pull request for review
5. Address review feedback
6. Merge and deploy

### Documentation Types
- **Tutorials**: Step-by-step learning experiences
- **How-to guides**: Problem-focused instructions
- **Reference**: Information-oriented documentation
- **Explanation**: Understanding-oriented content

## Troubleshooting

### Common Issues

#### Dependencies not found
```bash
# Install documentation dependencies
uv sync --extra docs
```

#### Port already in use
```bash
# Use different port
python scripts/build_docs.py serve --port 8080
```

#### Build failures
```bash
# Clean and rebuild
make docs-clean
make docs-build
```

#### Missing API documentation
Ensure docstrings are properly formatted:

```python
def example_function(param: str) -> str:
    """
    Brief description of the function.
    
    Args:
        param: Description of parameter.
        
    Returns:
        Description of return value.
        
    Examples:
        >>> example_function("test")
        "result"
    """
    pass
```

## Resources

- [MkDocs Material Documentation](https://squidfunk.github.io/mkdocs-material/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [MyST Parser](https://myst-parser.readthedocs.io/) - Markdown in Sphinx
- [mkdocstrings](https://mkdocstrings.github.io/) - API docs in MkDocs