import urllib.request
import zipfile
import os
import subprocess
import shutil

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg.zip"

print("Downloading ffmpeg...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting ffmpeg...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall("ffmpeg_temp")

ffmpeg_exe = None
for root, dirs, files in os.walk("ffmpeg_temp"):
    if "ffmpeg.exe" in files:
        ffmpeg_exe = os.path.join(root, "ffmpeg.exe")
        break

if not ffmpeg_exe:
    print("Could not find ffmpeg.exe")
    exit(1)

dialogues_dir = "dialogues"
for filename in os.listdir(dialogues_dir):
    if filename.endswith(".m4a"):
        in_path = os.path.join(dialogues_dir, filename)
        out_path = os.path.join(dialogues_dir, filename.replace(".m4a", ".mp3"))
        print(f"Converting {filename}...")
        subprocess.run([ffmpeg_exe, "-y", "-i", in_path, out_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(in_path)

print("Cleaning up...")
os.remove(zip_path)
shutil.rmtree("ffmpeg_temp")
print("Done!")
