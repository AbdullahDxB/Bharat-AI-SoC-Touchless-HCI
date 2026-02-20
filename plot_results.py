import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('jetson_performance_data.csv')

# 1. FPS Plot
plt.figure(figsize=(10, 5))
plt.plot(df.index, df['FPS'], color='blue', alpha=0.7)
plt.axhline(df['FPS'].mean(), color='red', linestyle='dashed', linewidth=2, label=f"Avg FPS: {df['FPS'].mean():.1f}")
plt.title('Real-time Inference FPS on NVIDIA Jetson TX2')
plt.xlabel('Frame Number')
plt.ylabel('Frames Per Second (FPS)')
plt.ylim(0, 60)
plt.legend()
plt.tight_layout()
plt.savefig('fps_chart.png')
print(" Generated: fps_chart.png")

# 2. Latency Plot
plt.figure(figsize=(10, 5))
plt.plot(df.index, df['Inference_Latency_ms'], color='green', alpha=0.7)
plt.axhline(200, color='red', linestyle='solid', linewidth=2, label="200ms Target")
plt.axhline(df['Inference_Latency_ms'].mean(), color='orange', linestyle='dashed', linewidth=2, label=f"Avg Latency: {df['Inference_Latency_ms'].mean():.1f}ms")
plt.title('AI Inference Latency (ms)')
plt.xlabel('Frame Number')
plt.ylabel('Latency (ms)')
plt.ylim(0, 50) 
plt.legend()
plt.tight_layout()
plt.savefig('latency_chart.png')
print(" Generated: latency_chart.png")

# 3. Actions Plot
gesture_counts = df[df['Gesture_Detected'] != 'NEUTRAL']['Gesture_Detected'].value_counts()
plt.figure(figsize=(8, 5))
gesture_counts.plot(kind='bar', color='purple')
plt.title('Recognized Actions Distribution')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('gesture_chart.png')
print(" Generated: gesture_chart.png")

# 4. Confidence/Accuracy Plot (Only when hands are detected)
if 'Confidence_Score' in df.columns:
    df_hands = df[df['Confidence_Score'] > 0.0]
    plt.figure(figsize=(10, 5))
    plt.plot(df_hands.index, df_hands['Confidence_Score'] * 100, color='purple', alpha=0.7)
    avg_confidence = df_hands['Confidence_Score'].mean() * 100
    plt.axhline(avg_confidence, color='green', linestyle='dashed', linewidth=2, label=f"Avg Accuracy: {avg_confidence:.1f}%")
    plt.title('AI Hand Tracking Confidence (Accuracy Proxy)')
    plt.xlabel('Frame Number (Hand Detected)')
    plt.ylabel('Confidence Score (%)')
    plt.ylim(50, 105) 
    plt.legend()
    plt.tight_layout()
    plt.savefig('confidence_chart.png')
    print(" Generated: confidence_chart.png")