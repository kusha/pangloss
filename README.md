# Pangloss

Pangloss is a language graph analysis and transformation framework. It provides tools for analyzing relationships between natural languages using graph-based algorithms to identify linguistic patterns, generate similarity matrices, and transform language representations.

## Features

- Graph-based language analysis
- NetworkX integration for advanced graph algorithms
- Command-line interface for easy access
- YAML-based configuration support

## Installation

```bash
pip install -e .
```

## Requirements

- Python 3.11 or higher
- networkx - for graph algorithms
- click - for command-line interface
- pyyaml - for configuration files

## Quick Start

```bash
# Show version
pangloss version

# Analyze a dataset
pangloss analyze data.yaml
```

## Project Structure

```
pangloss/
├── __init__.py       # Package initialization
├── __main__.py       # CLI entry point
├── cli.py            # Command definitions
├── data/             # Data handling module
├── graph/            # Graph construction module
├── algo/             # Algorithm implementations
└── output/           # Output formatting module
```

## Development

This is an early MVP release. Contributions are welcome!

## License

MIT
