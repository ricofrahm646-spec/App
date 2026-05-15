#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# JARVIS AI Trading OS – Quick Start Script
# ═══════════════════════════════════════════════════════════════
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗"
echo "  ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝"
echo "  ██║███████║██████╔╝██║   ██║██║███████╗"
echo "  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║"
echo "  ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║"
echo "  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝"
echo -e "${NC}"
echo -e "${GREEN}  AI Trading Operating System v1.0.0${NC}"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}[WARN] No .env file found. Copying .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}[ACTION REQUIRED] Edit .env and set your credentials before trading!${NC}"
fi

MODE=${1:-docker}

if [ "$MODE" = "docker" ]; then
    echo -e "${CYAN}Starting JARVIS with Docker Compose...${NC}"
    cd deployment
    docker-compose up -d --build
    echo ""
    echo -e "${GREEN}JARVIS is running!${NC}"
    echo -e "  Dashboard:  ${CYAN}http://localhost:3000${NC}"
    echo -e "  API:        ${CYAN}http://localhost:8000${NC}"
    echo -e "  API Docs:   ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Flower:     ${CYAN}http://localhost:5555${NC}"

elif [ "$MODE" = "dev" ]; then
    echo -e "${CYAN}Starting JARVIS in development mode...${NC}"

    # Start backend
    echo -e "${YELLOW}Starting backend...${NC}"
    cd backend
    pip install -r requirements.txt -q
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..

    # Start frontend
    echo -e "${YELLOW}Starting frontend...${NC}"
    cd frontend
    npm install -q
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo -e "${GREEN}JARVIS development servers running!${NC}"
    echo -e "  Frontend:   ${CYAN}http://localhost:3000${NC}"
    echo -e "  Backend:    ${CYAN}http://localhost:8000${NC}"
    echo -e "  API Docs:   ${CYAN}http://localhost:8000/docs${NC}"
    echo ""
    echo "Press Ctrl+C to stop..."
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait

elif [ "$MODE" = "stop" ]; then
    echo -e "${YELLOW}Stopping JARVIS...${NC}"
    cd deployment
    docker-compose down
    echo -e "${GREEN}JARVIS stopped.${NC}"

else
    echo "Usage: ./start.sh [docker|dev|stop]"
    echo "  docker  - Start with Docker Compose (default)"
    echo "  dev     - Start in development mode (hot reload)"
    echo "  stop    - Stop Docker containers"
fi
