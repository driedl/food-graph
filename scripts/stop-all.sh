#!/bin/bash

# scripts/stop-all.sh
# 
# Stops all processes spawned by the food-graph monorepo
# Usage: ./scripts/stop-all.sh [--force] [--all-ports]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default to graceful kill, use --force for SIGKILL
# Use --all-ports to check all port ranges instead of smart defaults
FORCE=false
ALL_PORTS=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE=true
            ;;
        --all-ports)
            ALL_PORTS=true
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--force] [--all-ports]"
            echo "  --force: Use SIGKILL instead of SIGTERM"
            echo "  --all-ports: Check all port ranges instead of smart defaults"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🛑 Stopping all food-graph monorepo processes...${NC}"

# Function to kill processes with optional force
kill_processes() {
    local pattern="$1"
    local description="$2"
    local signal="${3:-TERM}"
    
    if [[ "$FORCE" == "true" ]]; then
        signal="KILL"
    fi
    
    echo -e "${YELLOW}🔍 Checking $description...${NC}"
    
    # Find processes matching the pattern with detailed info
    local processes=$(ps aux | grep -E "$pattern" | grep -v grep || true)
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    
    if [[ -n "$pids" ]]; then
        echo -e "  ${BLUE}Found $description processes:${NC}"
        echo "$processes" | while read line; do
            local pid=$(echo "$line" | awk '{print $2}')
            local cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ $//')
            local cpu=$(echo "$line" | awk '{print $3}')
            local mem=$(echo "$line" | awk '{print $4}')
            echo -e "    ${RED}PID $pid${NC} | CPU: ${cpu}% | MEM: ${mem}% | ${cmd}"
        done
        
        echo -e "  ${YELLOW}Stopping processes (signal: $signal)...${NC}"
        echo "$pids" | xargs kill -$signal 2>/dev/null || true
        
        # Wait a moment for graceful shutdown
        if [[ "$signal" == "TERM" ]]; then
            sleep 2
            # Check if processes are still running and force kill if needed
            local remaining=$(pgrep -f "$pattern" 2>/dev/null || true)
            if [[ -n "$remaining" ]]; then
                echo -e "  ${YELLOW}⚠️  Some processes still running, force killing...${NC}"
                echo "$remaining" | xargs kill -KILL 2>/dev/null || true
                sleep 1
            fi
        fi
        
        # Verify they're actually stopped
        local still_running=$(pgrep -f "$pattern" 2>/dev/null || true)
        if [[ -n "$still_running" ]]; then
            echo -e "  ${RED}❌ Failed to stop some processes: $still_running${NC}"
        else
            echo -e "  ${GREEN}✅ Successfully stopped $description${NC}"
        fi
    else
        echo -e "  ${GREEN}✓ No $description processes found${NC}"
    fi
}

# Function to free up specific ports
free_port() {
    local port="$1"
    local description="$2"
    
    echo -e "${YELLOW}🔍 Checking port $port ($description)...${NC}"
    
    local port_info=$(lsof -i:$port 2>/dev/null || true)
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    
    if [[ -n "$pids" ]]; then
        echo -e "  ${BLUE}Found processes using port $port:${NC}"
        echo "$port_info" | tail -n +2 | while read line; do
            local pid=$(echo "$line" | awk '{print $2}')
            local user=$(echo "$line" | awk '{print $3}')
            local cmd=$(echo "$line" | awk '{print $1}')
            local name=$(echo "$line" | awk '{print $9}')
            echo -e "    ${RED}PID $pid${NC} | User: $user | Command: $cmd | Name: $name"
        done
        
        echo -e "  ${YELLOW}Killing processes on port $port...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        
        # Verify port is actually free
        local still_using=$(lsof -ti:$port 2>/dev/null || true)
        if [[ -n "$still_using" ]]; then
            echo -e "  ${RED}❌ Failed to free port $port (still in use by: $still_using)${NC}"
        else
            echo -e "  ${GREEN}✅ Successfully freed port $port${NC}"
        fi
    else
        echo -e "  ${GREEN}✓ Port $port is already free${NC}"
    fi
}

# Stop different types of processes

# 1. Package manager processes
kill_processes "pnpm.*dev" "pnpm dev processes"
kill_processes "pnpm.*start" "pnpm start processes"
kill_processes "pnpm.*build" "pnpm build processes"

# 2. Development servers
kill_processes "vite" "Vite dev server"
kill_processes "tsx.*watch" "tsx watch processes"
kill_processes "tsx.*apps/api" "API tsx processes"
kill_processes "tsx.*apps/web" "Web tsx processes"

# 3. Node.js processes related to our apps
kill_processes "node.*apps/api" "API Node processes"
kill_processes "node.*apps/web" "Web Node processes"

# 4. Turbo processes (if using turbo)
kill_processes "turbo" "Turbo processes"

# 5. TypeScript compiler processes
kill_processes "tsc.*watch" "TypeScript watch processes"
kill_processes "tsc.*apps" "TypeScript compiler processes"

# 6. Free up common ports used by the monorepo
# Smart port checking: check defaults first, then expand if needed
check_ports_smart() {
    local api_default=3000
    local vite_default=5173
    local api_plus_one=3001
    local vite_plus_one=5174
    
    echo -e "${YELLOW}🔍 Smart port checking (checking defaults first)...${NC}"
    
    # Check if default ports are in use
    local api_default_in_use=false
    local vite_default_in_use=false
    
    if lsof -ti:$api_default >/dev/null 2>&1; then
        api_default_in_use=true
    fi
    
    if lsof -ti:$vite_default >/dev/null 2>&1; then
        vite_default_in_use=true
    fi
    
    # If defaults are free, we're done
    if [[ "$api_default_in_use" == "false" && "$vite_default_in_use" == "false" ]]; then
        echo -e "  ${GREEN}✓ Default ports (3000, 5173) are free - no need to check additional ports${NC}"
        return
    fi
    
    # Check default ports
    if [[ "$api_default_in_use" == "true" ]]; then
        free_port "$api_default" "API server port $api_default (default)"
    fi
    
    if [[ "$vite_default_in_use" == "true" ]]; then
        free_port "$vite_default" "Vite dev server port $vite_default (default)"
    fi
    
    # Check if default+1 ports are in use
    local api_plus_one_in_use=false
    local vite_plus_one_in_use=false
    
    if lsof -ti:$api_plus_one >/dev/null 2>&1; then
        api_plus_one_in_use=true
    fi
    
    if lsof -ti:$vite_plus_one >/dev/null 2>&1; then
        vite_plus_one_in_use=true
    fi
    
    # If default+1 is also in use, check all ports
    if [[ "$api_plus_one_in_use" == "true" || "$vite_plus_one_in_use" == "true" ]]; then
        echo -e "  ${YELLOW}⚠️  Default+1 ports are also in use - checking all port ranges${NC}"
        check_all_ports
    else
        # Just check default+1 ports
        if [[ "$api_plus_one_in_use" == "true" ]]; then
            free_port "$api_plus_one" "API server port $api_plus_one (default+1)"
        fi
        
        if [[ "$vite_plus_one_in_use" == "true" ]]; then
            free_port "$vite_plus_one" "Vite dev server port $vite_plus_one (default+1)"
        fi
    fi
}

check_all_ports() {
    echo -e "${YELLOW}🔍 Checking all port ranges...${NC}"
    
    # API server ports (3000-3005)
    for port in {3000..3005}; do
        free_port "$port" "API server port $port"
    done

    # Vite dev server ports (5173-5178)
    for port in {5173..5178}; do
        free_port "$port" "Vite dev server port $port"
    done
}

# Use smart port checking unless --all-ports is specified
if [[ "$ALL_PORTS" == "true" ]]; then
    check_all_ports
else
    check_ports_smart
fi

# 7. Kill any remaining processes that might be related to our workspace
echo -e "${YELLOW}Checking for any remaining workspace-related processes...${NC}"

# Look for processes with our workspace path
WORKSPACE_PATH=$(pwd)
WORKSPACE_PROCESSES=$(ps aux | grep "$WORKSPACE_PATH" | grep -v grep | awk '{print $2}' || true)

if [[ -n "$WORKSPACE_PROCESSES" ]]; then
    echo -e "  Found additional workspace processes: $WORKSPACE_PROCESSES"
    echo "$WORKSPACE_PROCESSES" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    # Force kill any remaining
    REMAINING=$(ps aux | grep "$WORKSPACE_PATH" | grep -v grep | awk '{print $2}' || true)
    if [[ -n "$REMAINING" ]]; then
        echo -e "  ${YELLOW}Force killing remaining processes...${NC}"
        echo "$REMAINING" | xargs kill -KILL 2>/dev/null || true
    fi
    echo -e "  ${GREEN}✓ Stopped additional workspace processes${NC}"
else
    echo -e "  ${GREEN}✓ No additional workspace processes found${NC}"
fi

# Final verification and summary
echo -e "\n${BLUE}🔍 Final verification...${NC}"

REMAINING_PROCESSES=$(ps aux | grep -E "(pnpm|vite|tsx|turbo|tsc).*food-graph" | grep -v grep || true)
if [[ -n "$REMAINING_PROCESSES" ]]; then
    echo -e "${RED}⚠️  Some processes may still be running:${NC}"
    echo "$REMAINING_PROCESSES" | while read line; do
        local pid=$(echo "$line" | awk '{print $2}')
        local cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ $//')
        echo -e "  ${RED}PID $pid${NC} | ${cmd}"
    done
    echo -e "\n${YELLOW}Run with --force to force kill all processes:${NC}"
    echo -e "  ${BLUE}./scripts/stop-all.sh --force${NC}"
else
    echo -e "${GREEN}✅ All monorepo processes stopped successfully!${NC}"
fi

# Show summary of what was running before cleanup
echo -e "\n${BLUE}📋 Summary of cleanup:${NC}"
echo -e "${YELLOW}Processes checked and stopped:${NC}"
echo -e "  • pnpm dev/start/build processes"
echo -e "  • Vite development servers"
echo -e "  • tsx watch processes (API/Web/ETL)"
echo -e "  • Node.js processes for apps"
echo -e "  • Turbo build processes"
echo -e "  • TypeScript compiler processes"
echo -e "  • Workspace-related processes"

echo -e "\n${YELLOW}Ports checked and freed:${NC}"
if [[ "$ALL_PORTS" == "true" ]]; then
    echo -e "  • API ports: 3000-3005 (all ports checked)"
    echo -e "  • Vite ports: 5173-5178 (all ports checked)"
else
    echo -e "  • API ports: 3000-3001 (smart checking - defaults first)"
    echo -e "  • Vite ports: 5173-5174 (smart checking - defaults first)"
    echo -e "  • Additional ports checked only if defaults+1 were in use"
fi

echo -e "\n${BLUE}📊 Port status:${NC}"
echo -e "${YELLOW}Default API port (3000):${NC}"
if lsof -ti:3000 >/dev/null 2>&1; then
    echo -e "  Port 3000: ${RED}IN USE${NC}"
else
    echo -e "  Port 3000: ${GREEN}FREE${NC}"
fi

echo -e "\n${YELLOW}Default Vite port (5173):${NC}"
if lsof -ti:5173 >/dev/null 2>&1; then
    echo -e "  Port 5173: ${RED}IN USE${NC}"
else
    echo -e "  Port 5173: ${GREEN}FREE${NC}"
fi

if [[ "$ALL_PORTS" == "true" ]]; then
    echo -e "\n${YELLOW}All API ports (3000-3005):${NC}"
    for port in {3000..3005}; do
        if lsof -ti:$port >/dev/null 2>&1; then
            echo -e "  Port $port: ${RED}IN USE${NC}"
        else
            echo -e "  Port $port: ${GREEN}FREE${NC}"
        fi
    done

    echo -e "\n${YELLOW}All Vite ports (5173-5178):${NC}"
    for port in {5173..5178}; do
        if lsof -ti:$port >/dev/null 2>&1; then
            echo -e "  Port $port: ${RED}IN USE${NC}"
        else
            echo -e "  Port $port: ${GREEN}FREE${NC}"
        fi
    done
fi

# Count total processes stopped
TOTAL_STOPPED=0
for pattern in "pnpm.*dev" "pnpm.*start" "pnpm.*build" "vite" "tsx.*watch" "tsx.*apps" "node.*apps" "turbo" "tsc.*watch" "tsc.*apps"; do
    COUNT=$(ps aux | grep -E "$pattern" | grep -v grep | wc -l)
    TOTAL_STOPPED=$((TOTAL_STOPPED + COUNT))
done

echo -e "\n${GREEN}🎉 Cleanup complete!${NC}"
echo -e "${BLUE}📈 Total processes checked: ${TOTAL_STOPPED}${NC}"
