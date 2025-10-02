# Tetra Demo Site

A demonstration project showcasing the capabilities of the Tetra framework for building reactive Django web applications.

## Overview

This demo site demonstrates various Tetra features including reactive components, real-time WebSocket communication, and interactive UI elements. It serves as both a testing ground for Tetra development and a reference implementation for developers.

## Features Demonstrated

- **Component updates**: without full page reloading
- **News Ticker**: Server data updates pushed to all connected clients simultaneously
- **Reactive Components**: Interactive components that update automatically based on server-side changes
- **Alpine.js Integration**: Smooth transitions and interactive UI elements

## Getting Started

### Prerequisites

- Python 3.11+
- Django 5.0+
- Redis (for WebSocket channel layer)

### Installation

1. Install dependencies:
```bash
pip install .[demo]
```

2. setup a crontab to purge old session data

```bash
crontrab -e
```

```
0 2 * * * /path/to/venv/bin/python /path/to/tetra/demosite/manage.py purge_old_sessions >> /var/log/django_purge.log 2>&1
```