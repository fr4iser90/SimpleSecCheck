{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    # Essential dependencies
    fastapi
    uvicorn
    sqlalchemy
    aiosqlite
    python-dotenv
    pydantic
    
    # Development tools
    black
    mypy
    pylint
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
    pkgs.nodejs_20
    pkgs.nodePackages.npm
    pkgs.nodePackages.typescript
    pkgs.nodePackages.typescript-language-server
    pkgs.docker
    pkgs.docker-compose
    pkgs.figlet
    pkgs.lolcat
  ];
  
  shellHook = ''
    # Set PYTHONPATH to include the project root
    export PYTHONPATH="$PWD:$PYTHONPATH"
    
    # --- Clean All Function ---
    clean-all() {
      echo "🧹 Cleaning everything..." | figlet | lolcat
      
      # Stop any running processes
      pkill -f "uvicorn" || true
      pkill -f "npm run dev" || true
      
      # Remove frontend and backend directories
      rm -rf frontend backend
      
      # Clean caches
      find . -type d -name "__pycache__" -exec rm -rf {} +
      find . -type d -name "node_modules" -exec rm -rf {} +
      find . -type d -name ".pytest_cache" -exec rm -rf {} +
      find . -type d -name ".coverage" -exec rm -rf {} +
      find . -type d -name "dist" -exec rm -rf {} +
      find . -type d -name "build" -exec rm -rf {} +
      
      # Clean Docker
      docker-compose down -v --remove-orphans || true
      
      echo "✨ Everything cleaned!" | figlet | lolcat
      echo "Use 'quick-start' to set up the project again"
    }
    
    # --- VibeJam Session Management ---
    vibe-timer() {
      local duration=$1
      local message=$2
      echo "⏰ Starting timer for $duration minutes: $message" | figlet | lolcat
      (
        sleep $((duration * 60))
        echo "🔔 Time's up! $message" | figlet | lolcat
        # Visual notification instead of sound
        for i in {1..3}; do
          echo "🔔 🔔 🔔"
          sleep 0.5
        done
      ) &
    }

    vibe-check() {
      echo "🎵 Vibe Check!" | figlet | lolcat
      echo "Current Status:"
      
      if [ $# -eq 4 ]; then
        echo "   Progress: $1"
        echo "  💪 Energy: $2"
        echo "  🎯 Focus: $3"
        echo "  🎨 Creativity: $4"
      else
        echo "   Progress: Not set"
        echo "  💪 Energy: Not set"
        echo "  🎯 Focus: Not set"
        echo "  🎨 Creativity: Not set"
        echo ""
        echo "Usage: vibe-check <progress> <energy> <focus> <creativity>"
        echo "Example: vibe-check '25%' 'High' 'Focused' 'Creative'"
      fi
    }

    vibe-session() {
      echo "🎮 Starting VibeJam Session #1" | figlet | lolcat
      
      # Prompt for hackathon task
      echo "📝 Please enter the hackathon task:"
      read -p "> " hackathon_task
      
      # Update hackathon.md with the task
      sed -i "s/\[ENTER TASK HERE]/$hackathon_task/" hackathon.md
      
      echo "Workflow:"
      echo "1. Preparation Phase (No Timer)"
      echo "  - AI analyzes the task"
      echo "  - AI selects the tech stack"
      echo "  - AI plans the project structure"
      echo "  - Setup project with 'quick-start'"
      echo ""
      echo "2. Coding Phase (60 minutes)"
      echo "  - AI writes the code"
      echo "  - AI runs tests"
      echo "  - AI optimizes and refactors"
      echo ""
      echo "Use 'vibe-check' to update your status"
      echo "Use 'vibe-progress' to show progress"
      echo ""
      echo "📋 Hackathon.md has been updated with the task!"
      echo ""
      
      # Start coding phase timer when ready
      echo "⏰ Timer will start when you run 'quick-start'"
    }

    vibe-progress() {
      local progress=$1
      local width=50
      local completed=$((progress * width / 100))
      local remaining=$((width - completed))
      
      echo "Progress: [$progress%]"
      printf "["
      for ((i=0; i<completed; i++)); do
        printf "█"
      done
      for ((i=0; i<remaining; i++)); do
        printf "░"
      done
      printf "]\n"
    }
    
    # --- Development Aliases ---
    alias dev-fe="cd frontend && npm run dev"
    alias dev-be="cd backend && uvicorn main:app --reload --port 8000"
    alias dev-all="tmux new-session -d -s vibejam 'cd frontend && npm run dev' \; split-window -h 'cd backend && uvicorn main:app --reload --port 8000' \; attach"
    
    # --- Frontend Aliases ---
    alias fe-install="cd frontend && npm install"
    alias fe-dev="cd frontend && npm run dev"
    alias fe-build="cd frontend && npm run build"
    alias fe-lint="cd frontend && npm run lint"
    
    # --- Backend Aliases ---
    alias be-install="cd backend && pip install -r requirements.txt"
    alias be-dev="cd backend && uvicorn main:app --reload"
    alias be-test="cd backend && pytest"
    alias be-lint="cd backend && pylint **/*.py"
    
    # --- Docker Aliases ---
    alias d-up="docker-compose up"
    alias d-upd="docker-compose up -d"
    alias d-down="docker-compose down"
    alias d-build="docker-compose build"
    alias d-logs="docker-compose logs -f"
    alias d-ps="docker-compose ps"
    alias d-restart="docker-compose restart"
    alias d-clean="docker-compose down -v --remove-orphans"
    
    # --- SimpleSecCheck Aliases ---
    alias ssc-cli="./bin/run-docker.sh"
    alias ssc-webui-up="docker-compose --profile webui up -d"
    alias ssc-webui-down="docker-compose --profile webui down"
    alias ssc-webui-logs="docker-compose --profile webui logs -f webui"
    alias ssc-webui-restart="docker-compose --profile webui restart webui"
    alias ssc-webui-build="docker-compose --profile webui build webui"
    alias ssc-webui-stop="docker-compose --profile webui stop webui"
    alias ssc-scan-code="./bin/run-docker.sh"
    alias ssc-scan-website="./bin/run-docker.sh"
    alias ssc-scan-network="./bin/run-docker.sh network"
    
    # --- Hot Reload Aliases ---
    alias hot-fe="cd frontend && npm run dev -- --host"
    alias hot-be="cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    alias hot-all="tmux new-session -d -s vibejam 'cd frontend && npm run dev -- --host' \; split-window -h 'cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000' \; attach"
    
    # --- Git Aliases ---
    alias gs="git status"
    alias ga="git add"
    alias gc="git commit"
    alias gp="git push"
    alias gl="git pull"
    
    # --- Cache Cleaning Function ---
    clean-caches() {
      echo "Cleaning caches..."
      find . -type d -name "__pycache__" -exec rm -rf {} +
      find . -type d -name "node_modules" -exec rm -rf {} +
      find . -type d -name ".pytest_cache" -exec rm -rf {} +
      echo "Cache cleaning complete."
    }
    
    # --- Quick Start Function ---
    quick-start() {
      echo " Setting up VibeJam project..."
      
      # Create frontend
      if [ ! -d "frontend" ]; then
        echo "Creating frontend..."
        mkdir frontend
        cd frontend
        npm create vite@latest . -- --template react-ts
        npm install
        cd ..
      fi
      
      # Create backend
      if [ ! -d "backend" ]; then
        echo "Creating backend..."
        mkdir backend
        cd backend
        
        # Create minimal requirements.txt with placeholders
        echo "Creating requirements.txt..."
        cat > requirements.txt << EOL
# Core dependencies
fastapi>=0.110.0
uvicorn>=0.27.1
python-dotenv>=1.0.1
pydantic>=2.6.3

# Database
# sqlalchemy>=2.0.28
# aiosqlite>=0.20.0

# Testing
# pytest>=8.0.2
# pytest-asyncio>=0.23.5
# httpx>=0.27.0

# Add your project-specific dependencies below:
# package-name>=version
EOL
        
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
      fi
      
      echo "✨ Setup complete! Use 'dev-all' to start both servers"
      echo "📝 Edit backend/requirements.txt to add your project dependencies"
      
      echo " Starting Coding Phase Timer!" | figlet | lolcat
      vibe-timer 60 "Coding phase complete!" &
    }
    
    echo " VibeJam Development Environment"
    echo "Available commands:"
    echo "  quick-start   - Set up frontend and backend"
    echo "  dev-all      - Start both servers in tmux"
    echo "  dev-fe       - Start frontend server"
    echo "  dev-be       - Start backend server"
    echo "  fe-install   - Install frontend dependencies"
    echo "  be-install   - Install backend dependencies"
    echo "  clean-caches - Clean all caches"
    echo ""
    echo "Docker commands:"
    echo "  d-up        - Start containers"
    echo "  d-upd       - Start containers in background"
    echo "  d-down      - Stop containers"
    echo "  d-build     - Build containers"
    echo "  d-logs      - Show container logs"
    echo "  d-ps        - Show container status"
    echo "  d-restart   - Restart containers"
    echo "  d-clean     - Clean up containers and volumes"
    echo ""
    echo "SimpleSecCheck commands:"
    echo "  ssc-cli           - Run CLI scan (./bin/run-docker.sh)"
    echo "  ssc-webui-up      - Start WebUI (docker-compose --profile webui up -d)"
    echo "  ssc-webui-down    - Stop WebUI"
    echo "  ssc-webui-logs    - Show WebUI logs"
    echo "  ssc-webui-restart - Restart WebUI"
    echo "  ssc-webui-build   - Build WebUI"
    echo "  ssc-webui-stop    - Stop WebUI"
    echo "  ssc-scan-network  - Run network scan"
    echo ""
    echo "Hot reload commands:"
    echo "  hot-fe      - Start frontend with hot reload"
    echo "  hot-be      - Start backend with hot reload"
    echo "  hot-all     - Start both with hot reload in tmux"
    echo ""
    echo "VibeJam Session Tools:"
    echo "  vibe-session   - Start a new VibeJam session"
    echo "  vibe-timer     - Set a timer (minutes)"
    echo "  vibe-check     - Do a vibe check"
    echo "  vibe-progress  - Show progress bar"
  '';
} 