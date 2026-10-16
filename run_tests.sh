#!/bin/bash
# Run GameTrainer middleware tests

echo "🧪 Running GameTrainer middleware tests..."

# Install test dependencies
pip install pytest numpy opencv-python pygame

# Run tests
python -m pytest tests/ -v

echo "✅ Tests completed"
