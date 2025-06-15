#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to include src directory
export PYTHONPATH=src

# Run the development server
python -m emojismith.dev_server