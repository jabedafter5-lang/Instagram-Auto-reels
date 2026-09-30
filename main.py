import os
import re
import time
import requests
import urllib.parse

# Account 1 Credentials
ACCESS_TOKEN_1 = os.getenv("IG_ACCESS_TOKEN")
USER_ID_1 = os.getenv("IG_USER_ID")

# Account 2 Credentials
ACCESS_TOKEN_2 = os.getenv("IG_ACCESS_TOKEN_2")
USER_ID_2 = os.getenv("IG_USER_ID_2")

REELS_FOLDER = "reels"
LOG_FILE = "posted_videos.txt"

BASE_CAPTION = """Follow

This instagram reel shares a 15-second viral video from early December 2025, showing a capuchin monkey clinging to a water bottle rocket launched by a group during apparent Diwali festivities, soaring briefly before landing safely on a rooftop mattress.

Reactions in replies mix awe at the monkey's trust and survival-described as "bravest monkey"-with skepticism calling it AI-generated, though web sources confirm it's a real, unedited clip spreading across platforms like Instagram and YouTube.

The stunt highlights primate curiosity toward novel objects but raises ethical concerns about unintended animal risks in fireworks settings, with no peer-reviewed studies on such events but general research noting capuchins' adaptability in human environments."""

def get_posted_videos():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines() if line.strip())

def mark_as_posted(video_file):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(video_file + "\n")

def get_next_reel():
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)
        return None
    
    os.system('git pull origin main --rebase || echo "Already up to date"')
    
    files = sorted(os.listdir(REELS_FOLDER))
    video_files = [f for f in files if f.lower().endswith(('.mp4', '.mov'))]
    
    posted_videos = get_posted_videos()
    
    for video in video_files:
        if video not in posted_videos:
            return video
            
    return None

def build_caption_from_filename(video_file):
    # Extension hatana (.mp4 etc.)
    name_without_ext = os.path.splitext(video_file)[0]
    
    # Filename se sabhi hashtags dhoondna
    all_hashtags = re.findall(r'#\w+', name_without_ext)
    
    # Sirf pehle 4 hashtags select karna
    selected_hashtags = all_hashtags[:4]
    
    # Hashtags hata kar bacha hua naam Title banana
    title_text = re.sub(r'#\w+', '', name_without_ext)
    title_clean = " ".join(title_text.replace("_", " ").replace("-", " ").split()).strip()
    
    hashtags_str = " ".join(selected_hashtags)
    
    header_parts = []
    if title_clean:
        header_parts.append(title_clean)
    if hashtags_str:
        header_parts.append(hashtags_str)
        
    custom_header = " ".join(header_parts)
    
    # Final Caption: Upar Title + 4 Hashtags, fir fixed keyword description
    if custom_header:
        final_caption = f"{custom_header}\n\n{BASE_CAPTION}"
    else:
        final_caption = BASE_CAPTION
        
    return final_caption

def wait_for_container_ready(creation_id, access_token, max_attempts=15, delay=10):
    status_url = f"https://graph.instagram.com/v20.0/{creation_id}"
    params = {
        'fields': 'status_code',
        'access_token': access_token
    }
    for attempt in range(max_attempts):
        res = requests.get(status_url, params=params).json()
        status = res.get('status_code')
        print(f"Checking video status: {status} (Attempt {attempt + 1}/{max_attempts})")
        if status == 'FINISHED':
            return True
        elif status == 'ERROR':
            print("Video processing failed on Instagram server.")
            return False
        time.sleep(delay)
    return False

def upload_to_single_account(account_num, user_id, token, video_url, caption):
    if not user_id or not token:
        print(f"Skipping Account {account_num}: Secret missing hai.")
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
    
    response = requests.post(url, data=payload)
    result = response.json()
    
    if 'id' not in result:
        print(f"Error creating container for Account {account_num}:", result)
        return False
        
    creation_id = result['id']
    print(f"Account {account_num} Container ID: {creation_id}. Processing wait...")
    
    # Video process hone ka wait karein
    if not wait_for_container_ready(creation_id, token):
        print(f"Account {account_num} par video process nahi ho payi.")
        return False
    
    publish_url = f"https://graph.instagram.com/v20.0/{user_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': token
    }
    
    pub_response = requests.post(publish_url, data=publish_payload)
    pub_result = pub_response.json()
    print(f"Account {account_num} Publish Result:", pub_result)
    
    return 'id' in pub_result

def post_instagram_reel():
    video_file = get_next_reel()
    if not video_file:
        print("Koi nayi video nahi mili reels folder mein, sab post ho chuki hain!")
        return

    video_path = os.path.join(REELS_FOLDER, video_file)
    print(f"Selected video: {video_file}")

    REPO_NAME = os.getenv("GITHUB_REPOSITORY")
    BRANCH = "main"
    
    # Path ko proper format me encode karna taaki spaces se link na toote
    quoted_parts = [urllib.parse.quote(part) for part in video_path.split(os.sep)]
    encoded_video_path = "/".join(quoted_parts)
    VIDEO_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{encoded_video_path}"

    final_caption = build_caption_from_filename(video_file)
    print("Generated Caption:\n", final_caption)

    # Dono accounts par upload
    posted_acc1 = upload_to_single_account(1, USER_ID_1, ACCESS_TOKEN_1, VIDEO_URL, final_caption)
    posted_acc2 = upload_to_single_account(2, USER_ID_2, ACCESS_TOKEN_2, VIDEO_URL, final_caption)

    # Agar kisi ek account par bhi upload ho jaye toh log file update karo
    if posted_acc1 or posted_acc2:
        print("\nUpdating log file...")
        mark_as_posted(video_file)
        
        os.system('git config --global user.name "GitHub Action Bot"')
        os.system('git config --global user.email "action@github.com"')
        os.system('git pull origin main --rebase || echo "No need to pull"')
        os.system(f'git add {LOG_FILE}')
        os.system(f'git commit -m "Mark {video_file} as posted"')
        os.system('git push origin main')
        print("Log updated and pushed successfully!")

if __name__ == "__main__":
    post_instagram_reel()
