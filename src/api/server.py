# LEGACY ENTRY POINT DEPRECATED
# The MNIT threat detection platform has been architecturally separated into four fully isolated surfaces:
# 1. Customer Banking App (port 3001 / API port 8001)
# 2. Admin Security Dashboard (port 3002 / API port 8002)
# 3. Attacker Threat Simulator (port 3003 / API port 8003)
# 4. Showcase Research Portal (port 3004 / API port 8004)
#
# Please use 'python run.py' from the project root to start all four services.

if __name__ == "__main__":
    import sys
    print("======================================================================")
    print("WARNING: Legacy server.py entry point is DEPRECATED.")
    print("The codebase has been refactored into four isolated API surfaces.")
    print("Please start the platform by running:")
    print("  python run.py")
    print("======================================================================")
    sys.exit(1)
