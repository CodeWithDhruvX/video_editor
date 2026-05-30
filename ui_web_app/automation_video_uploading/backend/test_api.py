import requests
import json
import time

url = "http://localhost:8000/editor/process"

files = [
    ('videos', ('1.1_126.mp4', open('sample_videos/1.1_126.mp4', 'rb'), 'video/mp4')),
    ('extra_video', ('1.1_126.mp4', open('sample_videos/1.1_126.mp4', 'rb'), 'video/mp4')),
    ('background_music', ('Jingle Bells Calm - Kevin MacLeod.mp3', open('sample_videos/Jingle Bells Calm - Kevin MacLeod.mp3', 'rb'), 'audio/mpeg'))
]
config = {
    "enable_merge": True,
    "quality_preset": "fast",
    "music_volume": 0.3,
    "enable_gpu": False,
    "enable_ducking": True,
    "subtitle_settings": {
        "mode": "mixed"
    }
}
data = {
    'config_json': json.dumps(config)
}

print("Sending request...")
response = requests.post(url, files=files, data=data)
print("Response:", response.status_code, response.text)

if response.status_code == 200:
    job_id = response.json()['job_id']
    print("Job ID:", job_id)
    while True:
        status_res = requests.get(f"http://localhost:8001/editor/status/{job_id}")
        if status_res.status_code == 200:
            status = status_res.json()
            print("Progress:", status['progress'], "Status:", status['status'])
            if status['status'] in ['complete', 'failed', 'stopped']:
                print("Final logs:")
                with open("test_logs.txt", "w", encoding="utf-8") as f:
                    for log in status['logs']:
                        f.write(log + "\n")
                print("Logs saved to test_logs.txt")
                break
        time.sleep(2)
