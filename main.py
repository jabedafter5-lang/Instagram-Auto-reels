import os
import time
from datetime import datetime
import requests
import urllib.parse
import subprocess

# Account 1 Credentials
ACCESS_TOKEN_1 = os.getenv("IG_ACCESS_TOKEN")
USER_ID_1 = os.getenv("IG_USER_ID")

# Account 2 Credentials
ACCESS_TOKEN_2 = os.getenv("IG_ACCESS_TOKEN_2")
USER_ID_2 = os.getenv("IG_USER_ID_2")

REELS_FOLDER = "reels"
LOG_FILE = "posted_videos.txt"

# Sirf aur sirf yehi caption jayega har video me
ONLY_CAPTION = "#あらゆる追いかけっこを繰り広げる"

def get_next_reel():
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)
        return None
    
    os.system('git pull origin main --rebase || echo "Already up to date"')
    
    files = sorted(os.listdir(REELS_FOLDER))
    video_files = [f for f in files if f.lower().endswith(('.mp4', '.mov'))]
    
    if not video_files:
        return None
        
    return video_files[0]

def log_posted_text(video_file):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now_str}] Caption: {ONLY_CAPTION} | File: {video_file}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def wait_for_container_ready(creation_id, access_token, max_attempts=30, delay=10):
    status_url = f"https://graph.instagram.com/v20.0/{creation_id}"
    params = {
        'fields': 'status_code',
        'access_token': access_token
    }
    for attempt in range(max_attempts):
        try:
            res = requests.get(status_url, params=params).json()
            status = res.get('status_code')
            print(f"Status check: {status} (Attempt {attempt + 1}/{max_attempts})")
            if status == 'FINISHED':
                return True
            elif status == 'ERROR':
                print("Instagram processing error:", res)
                return False
        except Exception as e:
            print("Status request error:", e)
        time.sleep(delay)
    return False

def upload_to_single_account(account_num, user_id, token, video_url):
    if not user_id or not token:
        print(f"Skipping Account {account_num}: Credentials missing.")
        return False
        
    print(f"\n--- Account {account_num} Uploading Started ---")
    url = f"https://graph.instagram.com/v20.0/{user_id}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': ONLY_CAPTION,
        'access_token': token,
        'hide_like_and_view_counts': 'true'
    }
    
    try:
        response = requests.post(url, data=payload)
        result = response.json()
    except Exception as e:
        print(f"Network error on Account {account_num}:", e)
        return False
    
    if 'id' not in result:
        print(f"Error creating container for Account {account_num}:", result)
        return False
        
    creation_id = result['id']
    print(f"Account {account_num} Container ID: {creation_id}. Waiting for processing...")
    
    if not wait_for_container_ready(creation_id, token):
        print(f"Account {account_num} video process nahi ho saki.")
        return False
    
    publish_url = f"https://graph.instagram.com/v20.0/{user_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': token
    }
    
    try:
        pub_response = requests.post(publish_url, data=publish_payload)
        pub_result = pub_response.json()
        print(f"Account {account_num} Publish Result:", pub_result)
        return 'id' in pub_result
    except Exception as e:
        print(f"Publish request error on Account {account_num}:", e)
        return False

def post_instagram_reel():
    video_file = get_next_reel()
    if not video_file:
        print("Koi video nahi mili reels folder mein!")
        return

    video_path = os.path.join(REELS_FOLDER, video_file)
    print(f"Selected video: {video_file}")

    REPO_NAME = os.getenv("GITHUB_REPOSITORY")
    BRANCH = "main"
    
    quoted_parts = [urllib.parse.quote(part) for part in video_path.split(os.sep)]
    encoded_video_path = "/".join(quoted_parts)
    VIDEO_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{encoded_video_path}"

    print(f"Caption to post: {ONLY_CAPTION}")

    # Account 1 par upload
    posted_acc1 = upload_to_single_account(1, USER_ID_1, ACCESS_TOKEN_1, VIDEO_URL)

    # Dono accounts ke beech 15 minute ka delay taaki algorithm duplicate pakad kar reach zero na kare
    if posted_acc1 and USER_ID_2 and ACCESS_TOKEN_2:
        print("\nAccount 1 done. Waiting 15 minutes before posting to Account 2 for algorithm safety...")
        time.sleep(900)

    # Account 2 par upload
    posted_acc2 = upload_to_single_account(2, USER_ID_2, ACCESS_TOKEN_2, VIDEO_URL)

    acc1_ok = posted_acc1 if USER_ID_1 else True
    acc2_ok = posted_acc2 if USER_ID_2 else True

    if acc1_ok and acc2_ok and (posted_acc1 or posted_acc2):
        print("\nUpload complete! Video delete ho rahi hai aur log save ho raha hai...")
        
        log_posted_text(video_file)
        
        subprocess.run(['git', 'config', '--global', 'user.name', 'GitHub Action Bot'])
        subprocess.run(['git', 'config', '--global', 'user.email', 'action@github.com'])
        subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'])
        
        subprocess.run(['git', 'rm', '-f', video_path], stderr=subprocess.DEVNULL)
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass
                
        subprocess.run(['git', 'add', '-A'])
        subprocess.run(['git', 'commit', '-m', f"Posted {video_file} with Japanese tag and auto-deleted"])
        subprocess.run(['git', 'push', 'origin', 'main'])
        
        print(f"\n[DONE] {video_file} delete ho gayi aur posted_videos.txt update ho gaya!")
    else:
        print("\nUpload complete nahi hua, file safe rakhi gayi hai.")

if __name__ == "__main__":
    post_instagram_reel()
