import os
import time
import requests

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
USER_ID = os.getenv("IG_USER_ID")

REELS_FOLDER = "reels"

CAPTION = """Follow

This instagram reel shares a 15-second viral video from early December 2025, showing a capuchin monkey clinging to a water bottle rocket launched by a group during apparent Diwali festivities, soaring briefly before landing safely on a rooftop mattress.

Reactions in replies mix awe at the monkey's trust and survival-described as "bravest monkey"-with skepticism calling it AI-generated, though web sources confirm it's a real, unedited clip spreading across platforms like Instagram and YouTube.

The stunt highlights primate curiosity toward novel objects but raises ethical concerns about unintended animal risks in fireworks settings, with no peer-reviewed studies on such events but general research noting capuchins' adaptability in human environments."""

def get_next_reel():
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)
        return None
    
    files = sorted(os.listdir(REELS_FOLDER))
    video_files = [f for f in files if f.endswith(('.mp4', '.mov', '.MP4'))]
    
    if not video_files:
        return None
    
    return video_files[0]

def post_instagram_reel():
    video_file = get_next_reel()
    if not video_file:
        print("Koi video nahi mili reels folder mein!")
        return

    video_path = os.path.join(REELS_FOLDER, video_file)
    print(f"Posting video: {video_file}")

    REPO_NAME = os.getenv("GITHUB_REPOSITORY")
    BRANCH = "main"
    VIDEO_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{video_path}"

    print("Step 1: Container create ho raha hai...")
    url = f"https://graph.facebook.com/v20.0/{USER_ID}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': VIDEO_URL,
        'caption': CAPTION,
        'access_token': ACCESS_TOKEN,
        'hide_like_and_view_counts': 'true'
    }
    
    response = requests.post(url, data=payload)
    result = response.json()
    
    if 'id' not in result:
        print("Error creating container:", result)
        return
    
    creation_id = result['id']
    print(f"Container ID mil gayi: {creation_id}. High quality processing ka wait ho raha hai...")
    time.sleep(40)
    
    print("Step 2: Reel publish ki ja rahi hai...")
    publish_url = f"https://graph.facebook.com/v20.0/{USER_ID}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': ACCESS_TOKEN
    }
    
    pub_response = requests.post(publish_url, data=publish_payload)
    pub_result = pub_response.json()
    print("Publish Result:", pub_result)

    if 'id' in pub_result:
        os.remove(video_path)
        print("Posted file deleted successfully")

if __name__ == "__main__":
    post_instagram_reel()
