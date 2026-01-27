#!/usr/bin/env python3
"""
Start the OpenAxis backend server

Usage:
    python scripts/start_backend.py [--port PORT] [--host HOST]
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backend.server import run_server


def main():
    parser = argparse.ArgumentParser(
        description='Start OpenAxis backend server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Host to bind to (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to bind to (default: 8080)'
    )

    args = parser.parse_args()

    print(f"Starting OpenAxis backend server on {args.host}:{args.port}")
    run_server(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
