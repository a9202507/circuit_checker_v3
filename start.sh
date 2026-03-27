#!/bin/bash

# Circuit Checker V3 - One-click startup script
# Starts both frontend (Vue dev server) and backend (FastAPI)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "🚀 Circuit Checker V3 - Starting System"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}ℹ macOS detected - opening new terminal windows${NC}"

    # Start backend in new terminal window
    osascript <<EOF
tell app "Terminal"
    do script "cd '$BACKEND_DIR' && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
end tell
EOF

    sleep 2

    # Start frontend in new terminal window
    osascript <<EOF
tell app "Terminal"
    do script "cd '$FRONTEND_DIR' && npm run dev"
end tell
EOF

    echo -e "${GREEN}✓ Backend started on http://localhost:8000${NC}"
    echo -e "${GREEN}✓ Frontend started on http://localhost:5173${NC}"
    echo ""
    echo -e "${YELLOW}📝 Next steps:${NC}"
    echo "  1. Open http://localhost:5173 in your browser"
    echo "  2. Upload your .asc, .BOM, and .yaml files"
    echo "  3. Run the circuit check"

else
    echo -e "${BLUE}ℹ Non-macOS system detected - running in current terminal${NC}"
    echo -e "${YELLOW}⚠ Note: You'll need to run backend and frontend separately${NC}"
    echo ""
    echo "Backend:"
    echo "  cd $BACKEND_DIR"
    echo "  uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    echo ""
    echo "Frontend (in another terminal):"
    echo "  cd $FRONTEND_DIR"
    echo "  npm run dev"
fi
