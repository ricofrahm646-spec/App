#!/usr/bin/env bash
# J.A.R.V.I.S. V300 - SYSTEM IGNITION (Linux/macOS)
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}  ==================================================="
echo "   J.A.R.V.I.S. V300 - OMNIPOTENCE PROTOCOL"
echo "   SYSTEM IGNITION SEQUENCE"
echo -e "  ===================================================${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python3 not found. Install Python 3.10+ first.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Python detected: $(python3 --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
fi
echo -e "${GREEN}[OK]${NC} Virtual environment ready"

# Activate
source venv/bin/activate
echo -e "${GREEN}[OK]${NC} Environment activated"

# Install dependencies
echo "[*] Installing core dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo -e "${GREEN}[OK]${NC} Core packages installed"

# Playwright
echo "[*] Setting up Playwright..."
python -m playwright install chromium 2>/dev/null && \
    echo -e "${GREEN}[OK]${NC} Playwright configured" || \
    echo -e "${YELLOW}[WARN]${NC} Playwright setup failed - news scraping may be limited"

# Directories
mkdir -p apps logs data
echo -e "${GREEN}[OK]${NC} Directories created"

echo ""
echo -e "${CYAN}  ==================================================="
echo "   ALL SYSTEMS GO"
echo -e "  ===================================================${NC}"
echo ""
echo "  [1] Launch J.A.R.V.I.S. (Full System)"
echo "  [2] Launch Dashboard Only"
echo "  [3] Launch J.A.R.V.I.S. (No Voice)"
echo "  [4] Exit"
echo ""
read -p "Select mode: " choice

case $choice in
    1)
        echo "[*] Starting J.A.R.V.I.S. V300..."
        python jarvis.py
        ;;
    2)
        echo "[*] Starting War Room Dashboard..."
        streamlit run core/ui.py --server.port 8501 --theme.base dark
        ;;
    3)
        echo "[*] Starting J.A.R.V.I.S. (silent mode)..."
        python jarvis.py --no-voice
        ;;
    *)
        echo "Exiting."
        ;;
esac
