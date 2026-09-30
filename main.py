import os
import re
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

# Sabse upar rehne wala permanent Japanese hashtag
TOP_HASHTAG = "#あらゆる追いかけっこを繰り広げる"

BASE_CAPTION = """Follow

This instagram reel shares a 15-second viral video from early December 2025, showing a capuchin monkey clinging to a water bottle rocket launched by a group during apparent Diwali festivities, soaring briefly before landing safely on a rooftop mattress.

Reactions in replies mix awe at the monkey's trust and survival-described as "bravest monkey"-with skepticism calling it AI-generated, though web sources confirm it's a real, unedited clip spreading across platforms like Instagram and YouTube.

The stunt highlights primate curiosity toward novel objects but raises ethical concerns about unintended animal risks in fireworks settings, with no peer-reviewed studies on such events but general research noting capuchins' adaptability in human environments."""

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

def build_caption_from_filename(video_file):
    name_without_ext = os.path.splitext(video_file)[0]
    
    # 1. Filename se sabhi hashtags extract karein (Unicode support ke sath)
    all_hashtags = re.findall(r'#[\w\u0080-\uffff]+', name_without_ext)
    
    # Agar Japanese hashtag filename me bhi ho toh use duplicate na karein
    filtered_hashtags = [tag for tag in all_hashtags if tag != TOP_HASHTAG]
    selected_hashtags = filtered_hashtags[:4]
    
    # 2. Filename me se hashtags hatayein
    title_text = re.sub(r'#[\w\u0080-\uffff]+', '', name_without_ext)
    
    # 3. Faltu download prefixes clean karein: "Copy of", "(1)", "[1]", leading numbers
    title_clean = re.sub(r'(?i)\bcopy\s*(?:of)?\b', '', title_text)
    title_clean = re.sub(r'[\(\[\{]\s*\d+\s*[\)\]\}]', '', title_clean)
    title_clean = re.sub(r'^\s*\d+[\.\-_:\s]+', '', title_clean)
    title_clean = " ".join(title_clean.replace("_", " ").replace("-", " ").split()).strip()
    
    hashtags_str = " ".join(selected_hashtags)
    
    # Middle block (Title + 4 Hashtags)
    middle_parts = []
    if title_clean:
        middle_parts.append(title_clean)
    if hashtags_str:
        middle_parts.append(hashtags_str)
        
    middle_content = " ".join(middle_parts)
    
    # Structure:
    # 1. Top Japanese Hashtag
    # 2. Title + 4 Hashtags
    # 3. Fixed Description / Keywords
    caption_blocks = [TOP_HASHTAG]
    if middle_content:
        caption_blocks.append(middle_content)
    caption_blocks.append(BASE_CAPTION)
    
    return "\n\n".join(caption_blocks)

def log_posted_text(video_file):
    name_without_ext = os.path.splitext(video_file)[0]
    all_hashtags = re.findall(r'#[\w\u0080-\uffff]+', name_without_ext)
    filtered_hashtags = [tag for tag in all_hashtags if tag != TOP_HASHTAG]
    selected_hashtags = filtered_hashtags[:4]
    
    title_text = re.sub(r'#[\w\u0080-\uffff]+', '', name_without_ext)
    title_clean = re.sub(r'(?i)\bcopy\s*(?:of)?\b', '', title_text)
    title_clean = re.sub(r'[\(\[\{]\s*\d+\s*[\)\]\}]', '', title_clean)
    title_clean = re.sub(r'^\s*\d+[\.\-_:\s]+', '', title_clean)
    title_clean = " ".join(title_clean.replace("_", " ").replace("-", " ").split()).strip()
    
    hashtags_str = " ".join(selected_hashtags)
    title_display = title_clean if title_clean else "No Title"
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now_str}] Title: {title_display} | Tags: {hashtags_str} | File: {video_file}\n"
    
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
            print(f"Checking video status: {status} (Attempt {attempt + 1}/{max_attempts})")
            if status == 'FINISHED':
                return True
            elif status == 'ERROR':
                print("Video processing failed on Instagram server:", res)
                return False
        except Exception as e:
            print("Status check request error:", e)
        time.sleep(delay)
    return False

def upload_to_single_account(account_num, user_id, token, video_url, caption):
    if not user_id or not token:
        print(f"Skipping Account {account_num}: Credentials missing.")
        return False
        
    print(f"\n--- Account {account_num} Uploading Started ---")
    url = f"https://graph.instagram.com/v20.0/{user_id}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
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
    print(f"Account {account_num} Container ID: {creation_id}. Processing wait...")
    
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

    final_caption = build_caption_from_filename(video_file)
    print("\n--- Final Caption to Post ---")
    print(final_caption)
    print("-----------------------------\n")

    # Dono accounts par upload karein
    posted_acc1 = upload_to_single_account(1, USER_ID_1, ACCESS_TOKEN_1, VIDEO_URL, final_caption)
    posted_acc2 = upload_to_single_account(2, USER_ID_2, ACCESS_TOKEN_2, VIDEO_URL, final_caption)

    # Dono accounts verify karein (Agar 2 accounts hain toh dono par hona zaroori hai tabhi delete karein)
    acc1_ok = posted_acc1 if USER_ID_1 else True
    acc2_ok = posted_acc2 if USER_ID_2 else True

    if acc1_ok and acc2_ok and (posted_acc1 or posted_acc2):
        print("\nDono accounts par successfully post ho gayi! Plain text log save ho raha hai aur video delete ho rahi hai...")
        
        # 1. Plain text entry add karein
        log_posted_text(video_file)
        
        # 2. Git setup
        subprocess.run(['git', 'config', '--global', 'user.name', 'GitHub Action Bot'])
        subprocess.run(['git', 'config', '--global', 'user.email', 'action@github.com'])
        subprocess.run(['git', 'pull', 'origin', 'main', '--rebase'])
        
        # 3. Safe deletion from GitHub
        subprocess.run(['git', 'rm', '-f', video_path], stderr=subprocess.DEVNULL)
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass
                
        subprocess.run(['git', 'add', '-A'])
        subprocess.run(['git', 'commit', '-m', f"Logged and deleted {video_file}"])
        subprocess.run(['git', 'push', 'origin', 'main'])
        
        print(f"\n[DONE] {video_file} repo se permanently delete ho gayi, aur uska text record {LOG_FILE} me save ho gaya!")
    else:
        print("\nKisi ek ya dono accounts par upload fail hua, isliye video ko delete nahi kiya gaya taaki retry ho sake.")

if __name__ == "__main__":
    post_instagram_reel()
