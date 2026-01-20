#!/bin/bash
# =============================================================================
# IFoA Model Fitting Wrapper Script
# =============================================================================
#
# This script runs the model fitting with caffeinate to prevent sleep.
#
# Usage:
#   cd /Users/JonMinton/repos/economic_inactivity
#   ./reports/ifoa/run_models.sh
#
# Prerequisites:
#   - Laptop plugged in to power
#   - Lid open (or external display connected)
#
# =============================================================================

# Change to project root
cd "$(dirname "$0")/../.." || exit 1

echo "=============================================="
echo "IFoA Model Fitting"
echo "=============================================="
echo ""
echo "Start time: $(date)"
echo "Working directory: $(pwd)"
echo ""
echo "This script will:"
echo "  1. Prevent system sleep while running (caffeinate)"
echo "  2. Fit 8 multinomial logistic regression models"
echo "  3. Save all models to reports/ifoa/models/"
echo "  4. Log output to reports/ifoa/logs/model_fit.log"
echo ""
echo "Estimated duration: 2-6 hours depending on data size"
echo ""
echo "To monitor progress, open another terminal and run:"
echo "  tail -f reports/ifoa/logs/model_fit.log"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Create log directory if needed
mkdir -p reports/ifoa/logs

# Run with caffeinate
# -d: prevent display sleep
# -i: prevent idle sleep
# -m: prevent disk sleep
# -s: prevent system sleep (only on AC power)
echo ""
echo "Starting model fitting with sleep prevention..."
echo ""

caffeinate -dims Rscript reports/ifoa/_fit_models.R 2>&1 | tee reports/ifoa/logs/model_fit.log

echo ""
echo "=============================================="
echo "Model fitting complete!"
echo "End time: $(date)"
echo "=============================================="
echo ""
echo "Results saved to: reports/ifoa/models/"
echo "Log saved to: reports/ifoa/logs/model_fit.log"
