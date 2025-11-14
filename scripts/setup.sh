#!/bin/bash

# Setup script for Translation AI System

echo "Setting up Translation AI System..."

# Create necessary directories
mkdir -p models
mkdir -p outputs
mkdir -p data/raw
mkdir -p data/processed
mkdir -p uploads
mkdir -p logs

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Download NLTK data
echo "Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt', quiet=True)"

# Initialize database (if PostgreSQL is running)
echo "To initialize database, run:"
echo "  python database/init_db.py"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up -d db"
echo "  python database/init_db.py"

echo "Setup complete!"

