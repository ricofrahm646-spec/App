#!/usr/bin/env bash
# J.A.R.V.I.S. V300 OMNIPOTENCE — SYSTEM IGNITION (Linux/macOS)

set -e

BLUE='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================================"
echo "  J.A.R.V.I.S. V300 OMNIPOTENCE — SYSTEM IGNITION"
echo "  Sir, initializing all systems..."
echo -e "========================================================${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] Python3 not found. Install Python 3.10+ first.${NC}"
    exit 1
fi

PYTHON=$(command -v python3)
PIP="$PYTHON -m pip"

echo -e "${BLUE}[1/5]${NC} Installing Python dependencies..."
$PIP install --upgrade pip
$PIP install -r requirements.txt || echo -e "${YELLOW}[WARN] Some packages may have failed.${NC}"

echo ""
echo -e "${BLUE}[2/5]${NC} Installing Playwright browsers..."
$PYTHON -m playwright install chromium 2>/dev/null || echo -e "${YELLOW}[WARN] Playwright install skipped.${NC}"

echo ""
echo -e "${BLUE}[3/5]${NC} Creating directory structure..."
mkdir -p apps logs config

echo ""
echo -e "${BLUE}[4/5]${NC} Creating .env template..."
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# J.A.R.V.I.S. V300 Configuration
MT5_LOGIN=0
MT5_PASSWORD=
MT5_SERVER=
MT5_PATH=/opt/MetaTrader5/terminal64.exe
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
TRADE_SYMBOL=EURUSD
ENVEOF
    echo -e "${GREEN}[INFO] .env file created — edit it with your credentials.${NC}"
else
    echo -e "${GREEN}[INFO] .env already exists — skipping.${NC}"
fi

echo ""
echo -e "${BLUE}[5/5]${NC} Running initial security scan..."
$PYTHON -c "from ghost_security import SecurityScanner; s = SecurityScanner(); print(f'Scan: {s.get_summary()}')" 2>/dev/null || echo -e "${YELLOW}[WARN] Security scan skipped.${NC}"

echo ""
echo -e "${GREEN}========================================================"
echo "  IGNITION COMPLETE — All systems ready"
echo -e "========================================================${NC}"
echo ""
echo "  Launch options:"
echo "    1. Dashboard:   streamlit run ui.py"
echo "    2. Jarvis CLI:  python3 jarvis.py"
echo "    3. Auto Mode:   python3 jarvis.py --auto"
echo "    4. Voice Mode:  python3 jarvis.py --voice"
echo "    5. Trader Only: python3 trader_ultimate.py"
echo ""

read -p "  Select mode (1-5) or press Enter for Dashboard: " choice

case "$choice" in
    2) echo -e "\n${BLUE}  Launching J.A.R.V.I.S. Interactive Mode...${NC}"; $PYTHON jarvis.py ;;
    3) echo -e "\n${BLUE}  Launching J.A.R.V.I.S. Full Autonomous Mode...${NC}"; $PYTHON jarvis.py --auto ;;
    4) echo -e "\n${BLUE}  Launching J.A.R.V.I.S. Voice Control Mode...${NC}"; $PYTHON jarvis.py --voice ;;
    5) echo -e "\n${BLUE}  Launching Trading Engine...${NC}"; $PYTHON trader_ultimate.py ;;
    *) echo -e "\n${BLUE}  Launching War Room Dashboard...${NC}"; streamlit run ui.py --server.port 8501 --theme.base dark ;;
esac
