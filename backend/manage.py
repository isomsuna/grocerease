#!/usr/bin/env python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


if __name__ == '__main__':
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
