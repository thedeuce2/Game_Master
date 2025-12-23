
#!/bin/bash
# --------------------------------------------
# Life Simulation Backend v6 - Render Startup Script
# --------------------------------------------
# Ensures proper initialization of static folders and scene state
# before launching the FastAPI application.

# Create persistent directories if missing
mkdir -p static/logs

# Initialize empty scene state if missing
if [ ! -f static/logs/scene_state.json ]; then
  echo '{"date": "January 1, 2000", "time": "12:00 AM", "location": "Unknown", "funds": "$0.00"}' > static/logs/scene_state.json
fi

# Start FastAPI app using uvicorn
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
