# Save this as analyze_video.py
import cv2
import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt # We won't use matplotlib for the final output
from ultralytics import YOLO
from collections import defaultdict
import sys
import json # Import json library

# Load models outside the processing function if possible, or handle reloading
# In a simple script run via subprocess, loading here is fine.
try:
    # Adjust paths as necessary
    player_model = YOLO("yolov8n.pt")
    ball_model = YOLO("models/ball_detect/best.pt")
    models_loaded = True
except Exception as e:
    print(json.dumps({"error": f"Failed to load models: {e}"}), file=sys.stderr)
    sys.exit(1) # Exit if models can't load

def analyze_pickleball_video(video_path):
    """
    Analyzes a pickleball video to detect shots and player positions.

    Args:
        video_path (str): Path to the video file.

    Returns:
        dict: Dictionary containing analysis results (e.g., total_shots, player_positions).
              Returns None or raises exception on failure.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": f"Could not open video file: {video_path}"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    player_positions = defaultdict(list)
    ball_positions_list = [] # Store ball positions as a list of (frame, x, y)
    frame_idx = 0
    total_shots = 0 # Let's refine this based on ball hits/bounces later if needed

    # Note: The current ball detection logic mostly just tells you a ball was seen,
    # not necessarily a 'shot'. Detecting actual shots (hits) is more complex.
    # For now, let's count instances where a ball is detected for simplicity.
    # A better approach would involve tracking the ball and detecting changes in velocity/direction.

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # Process every Nth frame to speed things up if needed
        # if frame_idx % 5 != 0:
        #     continue

        try:
            # Player detection
            player_results = player_model.predict(frame, verbose=False)[0] # verbose=False to reduce subprocess noise
            if player_results.boxes is not None:
                for box in player_results.boxes.data:
                    x1, y1, x2, y2, conf, cls = box.cpu().numpy()
                    if int(cls) == 0: # Assuming class 0 is 'person' in yolov8n
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)
                        # Store relative positions (0-1) for flexibility, or raw pixels
                        # Let's stick to raw pixels for now, but note this is screen-resolution dependent
                        player_positions[frame_idx].append({"x": cx, "y": cy, "conf": float(conf)}) # Store as dict for JSON


            # Ball detection
            ball_results = ball_model.predict(frame, verbose=False)[0]
            if ball_results.boxes is not None:
                for box in ball_results.boxes.data:
                    x1_ball, y1_ball, x2_ball, y2_ball, conf_ball, cls_ball = box.cpu().numpy()
                    if int(cls_ball) == 0: # Assuming class 0 is 'ball' in your custom model
                        ball_cx = int((x1_ball + x2_ball) / 2)
                        ball_cy = int((y1_ball + y2_ball) / 2)
                        ball_positions_list.append({"frame": frame_idx, "x": ball_cx, "y": ball_cy, "conf": float(conf_ball)})
                        # Simple shot count: increment each time a ball is detected with high confidence?
                        # Or maybe when ball changes direction significantly? This needs proper tracking.
                        # For now, let's count detections in separate frames above a threshold.
                        if float(conf_ball) > 0.5: # Example confidence threshold
                             total_shots += 1 # This is a very crude shot count

                        break # Assume only one ball per frame

        except Exception as e:
             # Log frame-specific errors but continue processing if possible
             print(f"Error processing frame {frame_idx}: {e}", file=sys.stderr)


    cap.release()

    # --- Data Aggregation and Formatting ---

    # Aggregate player positions from defaultdict to a list of all points for heatmap
    all_player_points = []
    # Sort frames for chronological order if needed, though not strictly necessary for simple heatmap
    # for frame_id in sorted(player_positions.keys()):
    #     for pos in player_positions[frame_id]:
    #         all_player_points.append({"frame": frame_id, "x": pos[0], "y": pos[1]})

    # Simple list of all player center points detected across all frames
    for frame_id, points in player_positions.items():
         for point in points:
              all_player_points.append(point) # Already dictionaries from earlier


    # Note: The simple 'total_shots' based on ball detections is unreliable.
    # A more accurate 'shot count' requires ball tracking and event detection.
    # Let's return the number of ball detections as a proxy for now,
    # or perhaps refine the ball detection to count unique 'events'.
    # For a proper shot count, you'd need to analyze `ball_positions_list` for velocity/bounce patterns.
    # Let's just return total ball detections for now.

    # Let's return total *unique* ball detections per frame above a threshold
    unique_ball_frames = set(p['frame'] for p in ball_positions_list if p['conf'] > 0.5) # Count frames with ball detection
    actual_shot_count_proxy = len(unique_ball_frames) # A slightly better proxy

    # Prepare results dictionary
    results = {
        # "total_shots": total_shots, # The very crude initial count
        "total_shots": actual_shot_count_proxy, # Proxy count
        "heatmap_data": all_player_points, # List of all detected player center points
        "video_dimensions": {"width": frame_width, "height": frame_height} # Useful for frontend scaling
        # You could add more here, like rally counts if you refine that logic
    }

    return results

if __name__ == "__main__":
    # Check if video path is provided as a command-line argument
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python analyze_video.py <video_filepath>"}), file=sys.stderr)
        sys.exit(1)

    video_filepath = sys.argv[1]

    # Perform analysis
    analysis_results = analyze_pickleball_video(video_filepath)

    # Check for errors during analysis
    if "error" in analysis_results:
         print(json.dumps(analysis_results), file=sys.stderr)
         sys.exit(1)

    # Output results as JSON to standard output
    print(json.dumps(analysis_results))