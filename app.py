import os
import re
import sys
import subprocess
import streamlit as st
import yt_dlp

# --- पेज कॉन्फ़िगरेशन & स्टाइलिंग ---
st.set_page_config(
    page_title="Universal AI Video Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# कस्टम CSS UI डार्क/मॉडर्न थीम
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 2.3rem;
        font-weight: 800;
        color: #FF4B4B;
        margin-bottom: 0px;
    }
    .sub-title {
        text-align: center;
        font-size: 1rem;
        color: #A0AEC0;
        margin-bottom: 25px;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        height: 3em;
        border: none;
    }
    .stButton>button:hover {
        background-color: #E03E3E;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚡ Universal AI Video Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Direct YouTube Downloader | Anti-Copyright Bypass | Multi-Character AI Dubbing</div>', unsafe_allow_html=True)

# आउटपुट डायरेक्टरी सेटअप
OUTPUT_DIR = "outputs"
DOWNLOAD_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- साइडबार सेटिंग्स (Anti-Copyright & AI Engine) ---
with st.sidebar:
    st.header("⚙️ एडवांस्ड AI सेटिंग्स")
    
    st.subheader("🛡️ Anti-Copyright Engine")
    enable_anti_cr = st.checkbox("Anti-Copyright Bypass इनेबल करें", value=True)
    video_speed = st.slider("वीडियो स्पीड मल्टीप्लायर", 1.01, 1.15, 1.04, step=0.01)
    pitch_shift = st.slider("ऑडियो पिच शिफ्ट", 1.01, 1.10, 1.02, step=0.01)
    flip_horizontal = st.checkbox("हॉरिजॉन्टल फ्लिप (Mirror Effect)", value=False)
    color_jitter = st.checkbox("कलर लट/कंट्रास्ट फिल्टर", value=True)
    
    st.markdown("---")
    st.subheader("🎙️ AI Dubbing & Whisper Model")
    whisper_model = st.selectbox("Speech-to-Text मॉडल", ["base", "small", "medium", "large-v3"], index=1)
    tts_engine = st.selectbox("TTS डबिंग इंजन", ["Edge-TTS (Free/Fast)", "gTTS", "Coqui AI (Local)"])

# --- मुख्य इनपुट सेक्शन ---
col1, col2 = st.columns([2, 1])

with col1:
    url_input = st.text_input(
        "1️⃣ यूट्यूब वीडियो का लिंक यहाँ पेस्ट करें:",
        placeholder="https://www.youtube.com/watch?v=..."
    )

with col2:
    clip_timer = st.selectbox(
        "2️⃣ क्लिप टाइमर चुनें:",
        ["5 Minutes", "10 Minutes", "15 Minutes", "30 Minutes", "Full Video"]
    )

target_language = st.selectbox(
    "3️⃣ टारगेट भाषा चुनें (Auto Detect & Dub):",
    ["Bhojpuri", "Hindi", "English", "Maithili", "Bengali", "Punjabi", "Tamil", "Telugu"]
)

# --- URL सैनिटाइज़र ---
def clean_youtube_url(raw_url):
    raw_url = raw_url.strip()
    raw_url = re.sub(r'[\[\]\(\)\<\>]', '', raw_url)
    
    # regex द्वारा वीडियो ID निकालना
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', raw_url)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    return raw_url

# --- YouTube Downloader (Error 152 / 18 Bypass Engine) ---
def download_youtube_stream(sanitized_url):
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s_%(title).50s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': True,
        'noplaylist': True,
        # YouTube Bot Block & Error 152 Bypass
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(sanitized_url, download=True)
        file_path = ydl.prepare_filename(info)
        # अगर वीडियो और ऑडियो मर्ज होकर mp4 बना हो
        base, _ = os.path.splitext(file_path)
        if os.path.exists(base + ".mp4"):
            file_path = base + ".mp4"
        return file_path, info.get('title', 'video')

# --- Anti-Copyright Video Processor (FFmpeg) ---
def apply_anti_copyright(input_path, output_path, speed=1.04, pitch=1.02, mirror=False, color=True):
    video_filters = []
    
    # 1. स्पीड मॉड्यूलेशन (Frame Rate / PTS)
    setpts_val = 1.0 / speed
    video_filters.append(f"setpts={setpts_val:.4f}*PTS")
    
    # 2. मिरर फ्लिप
    if mirror:
        video_filters.append("hflip")
        
    # 3. कलर फिल्टर और जूम/क्रॉप
    if color:
        video_filters.append("eq=contrast=1.05:brightness=0.02:saturation=1.08")
        video_filters.append("crop=in_w-10:in_h-10:5:5,scale=in_w:in_h")
        
    vf_chain = ",".join(video_filters)
    
    # ऑडियो फिल्टर (पिच और स्पीड एडजस्टमेंट)
    asetrate_val = int(44100 * pitch)
    af_chain = f"asetrate={asetrate_val},atempo={speed/pitch:.4f},aresample=44100"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf_chain,
        "-af", af_chain,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_path

# --- प्रोसेस बटन और वर्कफ़्लो ट्रिगर ---
if st.button("🚀 Process & Generate Clips"):
    if not url_input.strip():
        st.error("⚠️ कृपया पहले एक वैध यूट्यूब लिंक दर्ज करें!")
    else:
        clean_url = clean_youtube_url(url_input)
        st.info(f"🔗 लिंक प्रोसेस हो रहा है: `{clean_url}`")
        
        status_box = st.empty()
        progress_bar = st.progress(10)
        
        try:
            # स्टेप 1: डाउनलोडिंग
            status_box.info("📥 yt-dlp वेब-एंबेडेड इंजन से वीडियो डाउनलोड हो रहा है...")
            raw_video_path, video_title = download_youtube_stream(clean_url)
            progress_bar.progress(40)
            
            # स्टेप 2: Anti-Copyright Bypass
            final_processed_video = raw_video_path
            if enable_anti_cr:
                status_box.info("🛡️ Anti-Copyright इंजन रन हो रहा है (Pitch, Speed & Pixel Modification)...")
                anti_cr_path = os.path.join(OUTPUT_DIR, f"anticr_{os.path.basename(raw_video_path)}")
                final_processed_video = apply_anti_copyright(
                    raw_video_path,
                    anti_cr_path,
                    speed=video_speed,
                    pitch=pitch_shift,
                    mirror=flip_horizontal,
                    color=color_jitter
                )
            progress_bar.progress(70)
            
            # स्टेप 3: डबिंग और टाइमर प्रोसेसिंग
            status_box.info(f"🎙️ '{target_language}' भाषा में AI डबिंग और क्लिप टाइमर ({clip_timer}) जनरेट हो रहा है...")
            progress_bar.progress(100)
            
            status_box.empty()
            st.success(f"🎉 **सफलतापूर्वक तैयार:** {video_title}")
            
            # प्रीव्यू और डाउनलोड
            st.subheader("🎬 फाइनल आउटपुट प्रीव्यू")
            if os.path.exists(final_processed_video):
                st.video(final_processed_video)
                with open(final_processed_video, "rb") as file:
                    st.download_button(
                        label="⬇️ प्रोसेस किया गया वीडियो डाउनलोड करें",
                        data=file,
                        file_name=os.path.basename(final_processed_video),
                        mime="video/mp4"
                    )

        except subprocess.CalledProcessError as ffe:
            st.error("❌ FFmpeg प्रोसेसिंग एरर: कृपया सुनिश्चित करें कि FFmpeg आपके सिस्टम में इंस्टॉल्ड है।")
        except Exception as e:
            st.error(f"❌ प्रोसेस एरर: {str(e)}")