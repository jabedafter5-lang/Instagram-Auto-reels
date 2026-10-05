import os
import time
from datetime import datetime
import requests
import urllib.parse
import subprocess

# Account 1 Credentials (GitHub Secrets)
ACCESS_TOKEN_1 = os.getenv("IG_ACCESS_TOKEN")
USER_ID_1 = os.getenv("IG_USER_ID")

# Account 2 Credentials (GitHub Secrets)
ACCESS_TOKEN_2 = os.getenv("IG_ACCESS_TOKEN_2")
USER_ID_2 = os.getenv("IG_USER_ID_2")

# Folder aur Log Files
REELS_FOLDER_1 = "reels"
LOG_FILE_1 = "posted_videos.txt"

REELS_FOLDER_2 = "reels_acc2"
LOG_FILE_2 = "posted_videos.txt_2"

# Sirf Japanese caption har video ke liye
ONLY_CAPTION = "#あらゆる追いかけっこを繰り広げる"

def get_next_reel(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return None
    
    files = sorted(os.listdir(folder_path))
    video_files = [f for f in files if f.lower().endswith(('.mp4', '.mov'))]
    
    if not video_files:
        return None
        
    return video_files[0]

def log_posted_text(log_file, video_file, account_num):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now_str}] Account {account_num} | Caption: {ONLY_CAPTION} | File: {video_file}\n"
    with open(log_file, "a", encoding="utf-8") as f:
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
    REPO_NAME = os.getenv("GITHUB_REPOSITORY")
    BRANCH = "main"

    subprocess.run(['git', 'config', '--global', 'user.name', 'GitHub Action Bot'])
    subprocess.run(['git', 'config', '--global', 'user.email', 'action@github.com'])
    subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'])

    posted_files = []

    # ================= 1. ACCOUNT 1 POSTING =================
    video_file_1 = get_next_reel(REELS_FOLDER_1)
    if video_file_1 and USER_ID_1 and ACCESS_TOKEN_1:
        video_path_1 = os.path.join(REELS_FOLDER_1, video_file_1)
        print(f"Account 1 Selected Video: {video_file_1}")
        
        quoted_parts_1 = [urllib.parse.quote(part) for part in video_path_1.split(os.sep)]
        video_url_1 = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{'/'.join(quoted_parts_1)}"
        
        if upload_to_single_account(1, USER_ID_1, ACCESS_TOKEN_1, video_url_1):
            log_posted_text(LOG_FILE_1, video_file_1, 1)
            subprocess.run(['git', 'rm', '-f', video_path_1], stderr=subprocess.DEVNULL)
            if os.path.exists(video_path_1):
                try: os.remove(video_path_1)
                except Exception: pass
            posted_files.append(f"Account 1: {video_file_1}")
            print(f"[SUCCESS] Account 1 video uploaded aur {LOG_FILE_1} me save ho gayi!")
    else:
        print(f"Account 1 ke liye koi video ya credential nahi mila.")

    # ================= 2. 1 HOUR DELAY (3600 SECONDS) =================
    if USER_ID_2 and ACCESS_TOKEN_2:
        print("\n=======================================================")
        print("Account 1 process complete! Ab theek 1 ghanta (60 minutes) wait ho raha hai...")
        print("1 ghante baad Account 2 par 'reels_acc2' folder se video post hogi.")
        print("=======================================================")
        time.sleep(3600)

        # ================= 3. ACCOUNT 2 POSTING =================
        video_file_2 = get_next_reel(REELS_FOLDER_2)
        if video_file_2:
            video_path_2 = os.path.join(REELS_FOLDER_2, video_file_2)
            print(f"Account 2 Selected Video (from reels_acc2): {video_file_2}")
            
            quoted_parts_2 = [urllib.parse.quote(part) for part in video_path_2.split(os.sep)]
            video_url_2 = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{'/'.join(quoted_parts_2)}"
            
            if upload_to_single_account(2, USER_ID_2, ACCESS_TOKEN_2, video_url_2):
                log_posted_text(LOG_FILE_2, video_file_2, 2)
                subprocess.run(['git', 'rm', '-f', video_path_2], stderr=subprocess.DEVNULL)
                if os.path.exists(video_path_2):
                    try: os.remove(video_path_2)
                    except Exception: pass
                posted_files.append(f"Account 2: {video_file_2}")
                print(f"[SUCCESS] Account 2 video uploaded aur {LOG_FILE_2} me save ho gayi!")
        else:
            print("reels_acc2 folder me koi video nahi mili!")

    # ================= 4. GITHUB AUTO-COMMIT & PUSH =================
    if posted_files:
        print("\nRepo update ho rahi hai: posted videos delete hongi aur txt log files save hongi...")
        subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'])
        subprocess.run(['git', 'add', '-A'])
        commit_msg = "Posted: " + ", ".join(posted_files)
        subprocess.run(['git', 'commit', '-m', commit_msg])
        subprocess.run(['git', 'push', 'origin', 'main'])
        print("\n[ALL DONE] Videos successfully deleted and log text files updated on GitHub!")
    else:
        print("\nKoi bhi nayi video post nahi hui, repository unchanged.")

if __name__ == "__main__":
    post_instagram_reel()
