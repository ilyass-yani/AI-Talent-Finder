#!/bin/bash
# Test runner script that handles conda activation

# Get conda activation script
CONDA_ACTIVATE="/Users/elhadjibassirousy/miniforge3/etc/profile.d/conda.sh"

# Check if conda exists
if [ ! -f "$CONDA_ACTIVATE" ]; then
    echo "❌ Conda not found at $CONDA_ACTIVATE"
    exit 1
fi

# Activate conda and run tests
source "$CONDA_ACTIVATE"
conda activate ai-tf311

cd /Users/elhadjibassirousy/Desktop/AI-Talent-Finder/backend

echo "✅ Environment: $(python --version 2>&1)"
echo "📍 Location: $(pwd)"
echo ""

# Run tests
python run_representative_tests.py
