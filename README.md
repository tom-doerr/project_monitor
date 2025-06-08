# Dev-Monitor

A portable development environment monitoring tool that captures:
- Docker Compose logs
- Pytest output
- Pylint results

## Installation

```bash
pip install dev-monitor
```

## Usage

```bash
dev-monitor [OPTIONS]

Options:
  --log-dir TEXT    Log directory (default: logs)
  --interval INTEGER  Update interval in seconds (default: 15)
  --sections TEXT   Sections to monitor (docker, pytest, pylint)
```

Example:
```bash
dev-monitor --sections docker pytest --interval 30
```

## Features
- Automatic detection of Docker Compose projects
- Configurable monitoring sections
- Rotating log files
- Cross-platform support
