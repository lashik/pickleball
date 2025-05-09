import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ultralytics import YOLO
from collections import defaultdict

# Load YOLOv8 pretrained model (you can fine-tune for better results)
model = YOLO("yolov8n.pt")  # or "yolov8s.pt" for more accuracy

# Load video
VIDEO_PATH = "input_videos/Relive This Epic Rivalry When Ben Johns Faced Tyson McGuffin in This 2023 Pickleball Classic! 📅🏆🔥 [SuXudVtzh9M] (1).mp4"
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
positions_df= model.predict(VIDEO_PATH, save=True, project='D:/Projects/PIFU/pickleball', conf=0.2)
# Data storage
player_positions = defaultdict(list)
frame_idx = 0

# Object classes of interest (0 = person in COCO)
TARGET_CLASS = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_idx += 1
    results = model(frame)

    for box in results[0].boxes.data:
        x1, y1, x2, y2, conf, cls = box.cpu().numpy()
        if int(cls) == TARGET_CLASS:
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            player_positions[frame_idx].append((cx, cy))

cap.release()

# Convert positions to DataFrame
# After this block:
data = []
for frame_id, coords in player_positions.items():
    for i, (x, y) in enumerate(coords):
        data.append({"frame": frame_id, "player": f"Player_{i+1}", "x": x, "y": y})

# Convert to DataFrame
positions_df = pd.DataFrame(data)

# Check if DataFrame is empty
if positions_df.empty:
    print("⚠️ No player detections were recorded. Try using a clearer video or a better YOLO model.")
else:
    positions_df.to_csv("player_positions.csv", index=False)

    # Visualize Heatmap
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6))
    for player in positions_df['player'].unique():
        subset = positions_df[positions_df['player'] == player]
        plt.scatter(subset['x'], subset['y'], alpha=0.3, label=player)

    plt.title("Player Movement Heatmap")
    plt.xlabel("Court X")
    plt.ylabel("Court Y")
    plt.legend()
    plt.gca().invert_yaxis()
    plt.savefig("heatmap.png")
    plt.show()


# Visualize Heatmap
plt.figure(figsize=(10, 6))
for player in positions_df['player'].unique():
    subset = positions_df[positions_df['player'] == player]
    plt.scatter(subset['x'], subset['y'], alpha=0.3, label=player)

plt.title("Player Movement Heatmap")
plt.xlabel("Court X")
plt.ylabel("Court Y")
plt.legend()
plt.gca().invert_yaxis()
plt.savefig("heatmap.png")
plt.show()