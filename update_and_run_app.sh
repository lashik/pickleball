#!/bin/bash

# --- Configuration ---
# !!! IMPORTANT: SET THESE VARIABLES !!!
PROJECT_DIR="/path/to/your/project/folder" # e.g., /Users/yourname/projects/my-node-app
GIT_BRANCH="main"                          # Or "master", or your default branch name
LOG_FILE="/tmp/app_update_$(date +%Y%m%d).log" # Log file for this script's run
APP_NAME="my-node-app"                     # A unique name for PM2 to manage your app

# --- Helper Function for Logging ---
log_message() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# --- Ensure PATH includes Node/NPM/Git directories ---
# Common locations for Homebrew installations on macOS
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
# You can find paths using: which npm, which git, which node

# --- Main Script ---
log_message "Script started."

# 1. Navigate to the project directory
cd "$PROJECT_DIR" || { log_message "ERROR: Could not navigate to $PROJECT_DIR. Exiting."; exit 1; }
log_message "Successfully navigated to $PROJECT_DIR."

# 2. Check current Git status and fetch updates
log_message "Fetching remote changes for branch '$GIT_BRANCH'..."
git fetch origin "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
FETCH_STATUS=$?

if [ $FETCH_STATUS -ne 0 ]; then
  log_message "ERROR: git fetch failed. Check network or Git configuration."
  # Decide if you want to exit or try to start the app anyway
  # For now, we'll try to proceed to start the app if it's not running
else
  log_message "Git fetch successful."
fi

# Compare local HEAD with remote HEAD
LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse "origin/$GIT_BRANCH")

NEEDS_UPDATE=false
if [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
  # Check if local is behind remote (can be pulled)
  MERGE_BASE=$(git merge-base HEAD "origin/$GIT_BRANCH")
  if [ "$LOCAL_HEAD" = "$MERGE_BASE" ]; then
    log_message "New commits found on remote. Local branch is behind."
    NEEDS_UPDATE=true
  elif [ "$REMOTE_HEAD" = "$MERGE_BASE" ]; then
    log_message "Local branch is ahead of remote. No pull needed from this script."
  else
    log_message "Branches have diverged. Manual intervention required. Will not pull."
  fi
else
  log_message "Local branch is already up-to-date with origin/$GIT_BRANCH."
fi

APP_RESTARTED_OR_STARTED=false

# 3. If new commits, pull changes and rebuild/restart
if [ "$NEEDS_UPDATE" = true ]; then
  log_message "Pulling changes from origin/$GIT_BRANCH..."
  git pull origin "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
  PULL_STATUS=$?
  if [ $PULL_STATUS -ne 0 ]; then
    log_message "ERROR: git pull failed. Manual intervention may be needed."
    # Decide if you want to exit or try to start/restart the app with old code
  else
    log_message "Git pull successful."

    log_message "Running 'npm init -y' as requested..."
    # WARNING: This can overwrite parts of an existing package.json with defaults.
    # It's typically used for initial project setup, not for updates.
    npm init -y >> "$LOG_FILE" 2>&1

    log_message "Installing/updating npm dependencies..."
    npm install >> "$LOG_FILE" 2>&1
    INSTALL_STATUS=$?
    if [ $INSTALL_STATUS -ne 0 ]; then
      log_message "ERROR: npm install failed."
    else
      log_message "NPM dependencies installed/updated."
    fi

    log_message "Attempting to restart application '$APP_NAME' with PM2..."
    # Assumes PM2 is installed and you want to use it (recommended)
    if command -v pm2 &> /dev/null; then
      pm2 restart "$APP_NAME" >> "$LOG_FILE" 2>&1 || {
        log_message "PM2 restart failed (app might not be running). Attempting to start..."
        pm2 start npm --name "$APP_NAME" -- start >> "$LOG_FILE" 2>&1
        START_STATUS=$?
        if [ $START_STATUS -ne 0 ]; then
            log_message "ERROR: PM2 failed to start '$APP_NAME'."
        else
            log_message "Application '$APP_NAME' started with PM2."
            APP_RESTARTED_OR_STARTED=true
        fi
      }
      if [ $? -eq 0 ] && [ "$APP_RESTARTED_OR_STARTED" = false ]; then # if restart succeeded
          log_message "Application '$APP_NAME' restarted with PM2."
          APP_RESTARTED_OR_STARTED=true
      fi
      pm2 save >> "$LOG_FILE" 2>&1 # Save the PM2 process list
    else
      log_message "WARNING: PM2 is not installed. Cannot manage app lifecycle robustly."
      log_message "Consider installing PM2: npm install pm2 -g"
      # Fallback to a simple (less robust) start if PM2 is not available
      # This would require manual process killing if you want to "restart"
      log_message "Attempting simple 'npm start' in background (less robust)..."
      # Kill previous instance if any (very basic, relies on finding by command)
      pkill -f "npm.*start" # This is a bit risky, be careful
      sleep 2 # Give it a moment to die
      nohup npm start > "$PROJECT_DIR/app_stdout.log" 2> "$PROJECT_DIR/app_stderr.log" &
      log_message "Simple 'npm start' initiated. Check logs for status."
      APP_RESTARTED_OR_STARTED=true
    fi
  fi
fi

# 4. If no updates, ensure the app is running (if PM2 is used)
if [ "$NEEDS_UPDATE" = false ] && [ "$APP_RESTARTED_OR_STARTED" = false ]; then
  if command -v pm2 &> /dev/null; then
    pm2 describe "$APP_NAME" > /dev/null 2>&1
    if [ $? -ne 0 ]; then # if describe fails, app is not running or not known to PM2
      log_message "Application '$APP_NAME' is not running (or not managed by PM2). Attempting to start it."
      log_message "Running 'npm init -y' as requested (before starting)..."
      npm init -y >> "$LOG_FILE" 2>&1
      log_message "Installing/updating npm dependencies (before starting)..."
      npm install >> "$LOG_FILE" 2>&1

      pm2 start npm --name "$APP_NAME" -- start >> "$LOG_FILE" 2>&1
      START_STATUS=$?
      if [ $START_STATUS -ne 0 ]; then
          log_message "ERROR: PM2 failed to start '$APP_NAME'."
      else
          log_message "Application '$APP_NAME' started with PM2."
          pm2 save >> "$LOG_FILE" 2>&1
      fi
    else
      log_message "Application '$APP_NAME' is already running (managed by PM2)."
    fi
  else
    log_message "No updates and PM2 not installed. Manual check required to see if app is running."
  fi
fi

log_message "Script finished."
echo "--- Log End ---" >> "$LOG_FILE"