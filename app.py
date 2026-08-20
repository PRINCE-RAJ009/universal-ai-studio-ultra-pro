import os
import glob
import subprocess
import asyncio
import re
import requests
import numpy as np
from scipy.io import wavfile
import streamlit as st
import yt_dlp
from deep_translator import GoogleTranslator
from faster_whisper import WhisperModel
import edge_tts
from pydub import AudioSegment
import torch

st.set_page_config(page_title="Universal Studio AI", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #0d0d0d;
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    input, .stSelectbox > div > div {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #cccccc !important;
        color: #000000 !important;
    }
    .stProgress > div > div > div > div {
        background-color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

OUTPUT_DIR = "processed_output"
TEMP_DIR = "temp_workspace"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_workspace():
    for folder in [OUTPUT_DIR, TEMP_DIR]:
        for f in glob.glob(f"{folder}/*"):
            try:
                os.remove(f)
            except Exception:
                pass

def extract_youtube_id(url):
    match = re.search(r'(?:v=|\/|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

# 100% Colab IP Bypass Downloader Engine
def download_with_progress(url, progress_bar, status_text):
    out_file = os.path.join(TEMP_DIR, 'input_video.mp4')
    vid_id = extract_youtube_id(url)
    
    # Engine 1: Piped / Invidious Stream Proxy (Bypasses YouTube Colab IP Block completely)
    if vid_id:
        status_text.text("⚡ बायपास इंजन से वीडियो स्ट्रीम खोजी जा रही है...")
        progress_bar.progress(15)
        
        piped_instances = [
            "https://pipedapi.kavin.rocks",
            "https://api.piped.private.coffee",
            "https://pipedapi.leptons.xyz"
        ]
        
        for instance in piped_instances:
            try:
                res = requests.get(f"{instance}/streams/{vid_id}", timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    streams = data.get("videoStreams", [])
                    mp4_streams = [s for s in streams if s.get("format") == "MPEG_4" or s.get("mimeType", "").startswith("video/mp4")]
                    
                    if mp4_streams:
                        best_stream = sorted(mp4_streams, key=lambda x: x.get("bitrate", 0), reverse=True)[0]
                        stream_url = best_stream.get("url")
                        
                        if stream_url:
                            status_text.text("📥 वीडियो डाउनलोड हो रहा है (100% Bot Bypass)...")
                            with requests.get(stream_url, stream=True, timeout=30) as r:
                                r.raise_for_status()
                                total = int(r.headers.get('content-length', 0))
                                downloaded = 0
                                with open(out_file, 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                                        if chunk:
                                            f.write(chunk)
                                            downloaded += len(chunk)
                                            if total > 0:
                                                pct = int(downloaded / total * 80) + 15
                                                progress_bar.progress(min(pct, 95))
                            
                            progress_bar.progress(100)
                            status_text.text("✅ वीडियो डाउनलोड सफल!")
                            return out_file
            except Exception:
                continue

    # Engine 2: yt-dlp TV Embedded Fallback Engine
    status_text.text("📥 yt-dlp अल्टरनेटिव इंजन से डाउनलोड जारी है...")
    
    def ydl_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                pct = int(downloaded / total * 100)
                progress_bar.progress(pct)
                status_text.text(f"📥 डाउनलोडिंग: {pct}%...")
        elif d['status'] == 'finished':
            progress_bar.progress(100)
            status_text.text("✅ डाउनलोड पूरा हुआ!")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': out_file,
        'merge_output_format': 'mp4',
        'progress_hooks': [ydl_hook],
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'mweb', 'android'],
                'player_skip': ['webpage', 'configs']
            }
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    return out_file

def get_character_voice(wav_path, target_lang):
    try:
        rate, data = wavfile.read(wav_path)
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        w = np.fft.rfft(data)
        freqs = np.fft.rfftfreq(len(data), d=1.0/rate)
        peak = freqs[np.argmax(np.abs(w))]
    except Exception:
        peak = 150

    if target_lang in ["Hindi", "Bhojpuri"]:
        if peak > 175:
            return "hi-IN-SwaraNeural", "+0Hz", "+0%"
        elif peak > 135:
            return "hi-IN-MadhurNeural", "+15Hz", "+5%"
        elif peak < 100:
            return "hi-IN-MadhurNeural", "-20Hz", "-5%"
        else:
            return "hi-IN-MadhurNeural", "+0Hz", "+0%"
    else:
        if peak > 175:
            return "en-US-JennyNeural", "+0Hz", "+0%"
        else:
            return "en-US-ChristopherNeural", "+0Hz", "+0%"

async def render_tts_segment(text, voice, pitch, rate, out_path):
    comm = edge_tts.Communicate(text, voice=voice, pitch=pitch, rate=rate)
    await comm.save(out_path)

def run_ai_dubbing(video_path, target_lang, progress_bar, status_text):
    status_text.text("🎙️ वोकल्स और डायलॉग्स अलग किए जा रहे हैं...")
    progress_bar.progress(10)
    
    raw_audio = os.path.join(TEMP_DIR, "raw_audio.wav")
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        raw_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    status_text.text("🧠 AI भाषा पहचान कर ट्रांसक्राइब कर रहा है (Whisper GPU)...")
    progress_bar.progress(30)
    
    device_mode = "cuda" if torch.cuda.is_available() else "cpu"
    comp_type = "float16" if torch.cuda.is_available() else "int8"
    
    model = WhisperModel("base", device=device_mode, compute_type=comp_type)
    segments, _ = model.transcribe(raw_audio, beam_size=1)
    
    orig_audio = AudioSegment.from_wav(raw_audio)
    dubbed_track = AudioSegment.silent(duration=len(orig_audio))
    target_code = 'hi' if target_lang in ['Hindi', 'Bhojpuri'] else 'en'
    
    seg_list = list(segments)
    total_segs = len(seg_list)
    
    if total_segs == 0:
        return video_path

    for idx, seg in enumerate(seg_list):
        text = seg.text.strip()
        if not text:
            continue
            
        start_ms = int(seg.start * 1000)
        end_ms = int(seg.end * 1000)
        clip_wav = os.path.join(TEMP_DIR, f"clip_{idx}.wav")
        orig_audio[start_ms:end_ms].export(clip_wav, format="wav")
        
        voice, pitch, rate = get_character_voice(clip_wav, target_lang)
        
        try:
            translated = GoogleTranslator(source='auto', target=target_code).translate(text)
        except Exception:
            translated = text
            
        tts_out = os.path.join(TEMP_DIR, f"tts_{idx}.mp3")
        asyncio.run(render_tts_segment(translated, voice, pitch, rate, tts_out))
        
        if os.path.exists(tts_out):
            tts_seg = AudioSegment.from_file(tts_out)
            dubbed_track = dubbed_track.overlay(tts_seg, position=start_ms)
        
        curr_pct = 30 + int((idx + 1) / total_segs * 50)
        progress_bar.progress(curr_pct)
        status_text.text(f"🗣️ AI डबिंग: {idx+1}/{total_segs} डायलॉग्स ({target_lang})...")

    final_audio = os.path.join(TEMP_DIR, "final_dub.wav")
    dubbed_track.export(final_audio, format="wav")
    
    status_text.text("🎬 ऑडियो-वीडियो सिंक और री-मर्जिंग जारी है...")
    progress_bar.progress(85)
    
    dubbed_video = os.path.join(TEMP_DIR, "dubbed_final.mp4")
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path, '-i', final_audio,
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
        '-shortest', dubbed_video
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return dubbed_video

def slice_and_anti_copyright(video_path, seconds, progress_bar, status_text):
    status_text.text("🛡️ एंटी-कॉपीराइट फिल्टर और क्लिप स्लाइसिंग जारी है...")
    progress_bar.progress(90)
    
    vf = "scale=trunc(iw*1.02/2)*2:trunc(ih*1.02/2)*2,eq=contrast=1.05:brightness=0.02:saturation=1.07,setpts=0.98*PTS"
    af = "atempo=1.02,asetrate=44100*1.01"
    output_pattern = os.path.join(OUTPUT_DIR, "part_%03d.mp4")
    
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vf', vf, '-af', af,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-threads', '0',
        '-c:a', 'aac',
        '-f', 'segment', '-segment_time', str(seconds),
        '-reset_timestamps', '1',
        output_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    progress_bar.progress(100)
    status_text.text("✨ प्रोसेस पूरी तरह समाप्त!")
    return sorted(glob.glob(os.path.join(OUTPUT_DIR, "part_*.mp4")))

st.title("⚡ Universal AI Video Studio")
st.caption("Direct YouTube Downloader | Anti-Copyright Bypass | Multi-Character AI Dubbing")

video_url = st.text_input("1️⃣ वीडियो लिंक पेस्ट करें (YouTube, Web):", placeholder="https://www.youtube.com/watch?v=...")

timers = {
    "50 Seconds": 50,
    "1 Minute": 60,
    "5 Minutes": 300,
    "10 Minutes": 600,
    "15 Minutes": 900,
    "20 Minutes": 1200,
    "25 Minutes": 1500,
    "30 Minutes": 1800,
    "35 Minutes": 2100,
    "40 Minutes": 2400,
    "45 Minutes": 2700,
    "1 Hour": 3600
}
selected_time = st.selectbox("2️⃣ क्लिप टाइमर चुनें:", list(timers.keys()), index=7)
selected_lang = st.selectbox("3️⃣ टारगेट भाषा चुनें (Auto Detect & Dub):", ["Original Audio", "Hindi", "English", "Bhojpuri"])

if st.button("🚀 Process & Generate Clips", use_container_width=True):
    if not video_url:
        st.warning("⚠️ कृपया पहले वीडियो लिंक पेस्ट करें!")
    else:
        cleanup_workspace()
        progress = st.progress(0)
        status = st.empty()
        
        try:
            base_vid = download_with_progress(video_url, progress, status)
            
            if selected_lang != "Original Audio":
                base_vid = run_ai_dubbing(base_vid, selected_lang, progress, status)
            
            clips = slice_and_anti_copyright(base_vid, timers[selected_time], progress, status)
            
            st.success(f"🎉 प्रोसेस पूरा हुआ! कुल {len(clips)} क्लिप्स तैयार की गईं।")
            
            for idx, clip in enumerate(clips):
                with open(clip, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Part {idx+1} ({selected_time}) डाउनलोड करें",
                        data=f.read(),
                        file_name=os.path.basename(clip),
                        mime="video/mp4",
                        key=f"dl_{idx}"
                    )
        except Exception as e:
            st.error(f"❌ प्रोसेस एरर: {e}")
