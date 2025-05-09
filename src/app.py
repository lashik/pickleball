# Save this as app.py (or backend_app.py)
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS # Import CORS
import subprocess
import json
import os
import uuid # To generate unique IDs for analysis jobs/results

app = Flask(__name__, static_folder='../pickleball-frontend/build') # Configure static folder for React build
CORS(app) # Enable CORS for development, adjust origins for production

# Define directories for storing analysis results and potentially video recordings
# In a real app, configure these securely and persistently
ANALYSIS_RESULTS_DIR = 'analysis_results'
if not os.path.exists(ANALYSIS_RESULTS_DIR):
    os.makedirs(ANALYSIS_RESULTS_DIR)

# --- Mock Data and Mapping ---
# In a real application, this mapping would come from your Huddle API integration
# and your Hikconnect video collection function.
# We need to map a booking ID (like the session_id from your frontend mock)
# to a video file path on the server where the analysis script can access it.

# Let's assume your frontend's mock data generates a unique session_id
# when a booking is "completed" and needs analysis.
# You would need a mechanism to associate that session_id with a video file
# that was previously saved by your Hikconnect video collection function.
# For this example, we'll use a dummy mapping. Replace with your actual logic.

MOCK_SESSION_VIDEO_MAP = {
    "sess_xyz_mock_court1_9am": "C:/Users/kashi/Downloads/Relive This Epic Rivalry When Ben Johns Faced Tyson McGuffin in This 2023 Pickleball Classic! 📅🏆🔥 [SuXudVtzh9M].webm", # Example video path
    "sess_abc_mock_court1_10am": "C:/Users/kashi/Downloads/Another_Pickleball_Video.mp4", # Another example
    # Add more mappings as needed for your mock/test data
}

# Dictionary to store analysis status (useful for async processing)
# For this simple example, our subprocess call waits, so status is either pending/completed/failed.
ANALYSIS_STATUS = {} # {session_id: "pending" | "completed" | "failed"}

# --- API Endpoints ---

# Endpoint to serve the React frontend build (Optional if using a separate web server like Nginx)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Endpoint to get court data (Mock or Huddle API integration)
# You already have a concept for this based on previous discussions.
# Modify your existing endpoint if it's in this Flask app.
# For this example, we'll just return the mock data structure the frontend expects.
@app.route('/api/courts', methods=['GET'])
def get_courts():
    # In a real app, fetch from Huddle API
    # Integrate the mockData structure, adding session_id and is_past
    mock_data_with_sessions = [
      {
        "id": "court_1",
        "name": "Court 1",
        "time_slots": [
          {"id": "slot_c1_8am", "time": "08:00", "status": "available", "is_past": False},
          # Ensure these session_ids match keys in MOCK_SESSION_VIDEO_MAP
          {"id": "slot_c1_9am", "time": "09:00", "status": "booked", "session_id": "sess_xyz_mock_court1_9am", "is_past": True, "bookedBy": "John Doe", "cost": 10, "startHour": 9}, # Add other mock data fields
          {"id": "slot_c1_10am", "time": "10:00", "status": "booked", "session_id": "sess_abc_mock_court1_10am", "is_past": True, "bookedBy": "Jane Smith", "cost": 10, "startHour": 10},
          {"id": "slot_c1_11am", "time": "11:00", "status": "booked", "session_id": "sess_def_mock_court1_11am", "is_past": False, "bookedBy": "Alice King", "cost": 10, "startHour": 11}, # Example future booking
          {"id": "slot_c1_12pm", "time": "12:00", "status": "available", "is_past": False},
          # ... other slots
        ]
      },
      {
        "id": "court_2",
        "name": "Court 2",
        "time_slots": [
           # Add mock slots for court 2 similarly, ensuring some are past/booked with session_ids
            {"id": "slot_c2_9am", "time": "09:00", "status": "booked", "session_id": "sess_ghi_mock_court2_9am", "is_past": True, "bookedBy": "Bob Lee", "cost": 10, "startHour": 9},
            {"id": "slot_c2_10am", "time": "10:00", "status": "available", "is_past": False},
           # ...
        ]
      }
    ]
    return jsonify(mock_data_with_sessions)


# Endpoint to trigger the analysis
@app.route('/api/analyze_booking/<session_id>', methods=['POST'])
def trigger_analysis(session_id):
    # Check if analysis is already running or completed
    status = ANALYSIS_STATUS.get(session_id)
    if status == "completed":
        return jsonify({"message": "Analysis already completed for this session."}), 200
    if status == "pending":
         return jsonify({"message": "Analysis is already in progress."}), 202 # Accepted, processing

    # Find the video path for the session ID
    video_path = MOCK_SESSION_VIDEO_MAP.get(session_id)
    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": f"Video not found for session ID: {session_id}. Path: {video_path}"}), 404

    # Define where to save the results for this session
    results_file = os.path.join(ANALYSIS_RESULTS_DIR, f"{session_id}.json")

    # If analysis file already exists from a previous run, return completed status
    if os.path.exists(results_file):
         ANALYSIS_STATUS[session_id] = "completed"
         return jsonify({"message": "Analysis previously completed and results found."}), 200


    # --- Run the analysis script as a subprocess ---
    try:
        ANALYSIS_STATUS[session_id] = "pending"
        # IMPORTANT: Adjust the path to your analyze_video.py script
        script_path = "path/to/your/analyze_video.py" # <--- UPDATE THIS PATH

        # Run the script, capture stdout and stderr
        # text=True decodes output as text
        process = subprocess.run(
            ["python", script_path, video_path],
            capture_output=True,
            text=True,
            check=False # Don't raise exception immediately on non-zero exit code
        )

        # Check the exit code
        if process.returncode != 0:
            # Log the error output from the script
            print(f"Analysis script failed for {session_id}. Stderr:\n{process.stderr}", file=sys.stderr)
            ANALYSIS_STATUS[session_id] = "failed"
            # Attempt to parse stderr if it was intended to be JSON error
            try:
                 error_output = json.loads(process.stderr.strip())
                 error_message = error_output.get("error", "Unknown script error")
            except json.JSONDecodeError:
                 error_message = process.stderr.strip() or "Script execution failed"

            return jsonify({"error": f"Analysis failed: {error_message}"}), 500 # Internal Server Error


        # Parse the JSON output from the script's stdout
        try:
            analysis_results = json.loads(process.stdout.strip())
        except json.JSONDecodeError:
             print(f"Analysis script for {session_id} returned invalid JSON. Stdout:\n{process.stdout}", file=sys.stderr)
             ANALYSIS_STATUS[session_id] = "failed"
             return jsonify({"error": "Analysis script returned invalid data."}), 500


        # Save the results
        with open(results_file, 'w') as f:
            json.dump(analysis_results, f)

        ANALYSIS_STATUS[session_id] = "completed"
        return jsonify({"message": "Analysis completed successfully", "session_id": session_id}), 200 # OK

    except FileNotFoundError:
         # This happens if the 'python' command or the script_path is not found
         print(f"Error: Python interpreter or script not found. Make sure 'python' is in PATH and script_path is correct.", file=sys.stderr)
         ANALYSIS_STATUS[session_id] = "failed"
         return jsonify({"error": "Server configuration error: Analysis script not found."}), 500
    except Exception as e:
        # Catch any other unexpected errors during subprocess handling
        print(f"An unexpected error occurred during analysis for {session_id}: {e}", file=sys.stderr)
        ANALYSIS_STATUS[session_id] = "failed"
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500


# Endpoint to get analysis results
@app.route('/api/analysis_results/<session_id>', methods=['GET'])
def get_analysis_results(session_id):
    results_file = os.path.join(ANALYSIS_RESULTS_DIR, f"{session_id}.json")

    if not os.path.exists(results_file):
        # Check if analysis is pending
        status = ANALYSIS_STATUS.get(session_id)
        if status == "pending":
             return jsonify({"status": "pending", "message": "Analysis is still in progress."}), 202 # Accepted, processing
        elif status == "failed":
             return jsonify({"status": "failed", "message": "Analysis failed previously."}), 500
        else:
            # Status is unknown or not started, and file doesn't exist
            return jsonify({"status": "not_found", "message": "Analysis results not found for this session."}), 404

    try:
        with open(results_file, 'r') as f:
            analysis_data = json.load(f)
        # Include status for clarity, although client got 200
        analysis_data["status"] = "completed"
        return jsonify(analysis_data), 200
    except Exception as e:
        print(f"Error reading analysis results file for {session_id}: {e}", file=sys.stderr)
        return jsonify({"error": "Failed to read analysis results."}), 500

# Endpoint to get a specific analysis asset (e.g., heatmap image if you generated one)
# Not strictly needed with the JSON heatmap data approach, but kept for completeness
@app.route('/api/analysis_assets/<session_id>/<filename>', methods=['GET'])
def get_analysis_asset(session_id, filename):
    # Basic security: Sanitize filename or check it's within expected bounds
    # Ensure filename doesn't contain path traversals (e.g., "../")
    safe_filename = os.path.basename(filename) # Only take the filename part

    asset_path = os.path.join(ANALYSIS_RESULTS_DIR, session_id) # Assuming assets are in a subfolder per session
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset directory not found"}), 404

    try:
        # Check if the requested file exists in the session's asset directory
        if os.path.exists(os.path.join(asset_path, safe_filename)):
             return send_from_directory(asset_path, safe_filename)
        else:
             return jsonify({"error": "Asset file not found"}), 404
    except Exception as e:
        print(f"Error serving asset {filename} for session {session_id}: {e}", file=sys.stderr)
        return jsonify({"error": "Failed to serve asset"}), 500


if __name__ == '__main__':
    # Run the Flask app
    # In production, use a production-ready WSGI server like Gunicorn
    app.run(debug=True) # Set debug=False in production