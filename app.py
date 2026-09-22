import os
import sys
import json
import base64
import shutil
import subprocess
import socket
import requests
from io import BytesIO
from PIL import Image
import webview
import imageio_ffmpeg
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK, TCON, TCOM, TPOS, TCOP, COMM, error
from mutagen.mp3 import MP3

# ----------------- متغیرهای سراسری برنامه -----------------
APP_NAME = "AudioFlow Studio"
APP_VERSION = "v.1.0.0"
# --------------------------------------------------------

def get_embedded_font_css():
    """خوانش فونت وزیرمتن محلی و تبدیل به Base64 برای استقلال کامل و یکسانی ظاهر در همه سیستم‌ها"""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
    font_candidates = ["Vazirmatn.woff2", "Vazirmatn-Regular.woff2", "Vazirmatn.ttf", "vazirmatn.woff2", "vazirmatn.ttf"]
    
    for font_name in font_candidates:
        font_path = os.path.join(base_dir, font_name)
        if os.path.exists(font_path):
            try:
                with open(font_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                font_format = "woff2" if font_name.lower().endswith(".woff2") else "truetype"
                return f"""
                @font-face {{
                    font-family: 'Vazirmatn';
                    src: url(data:font/{font_format};charset=utf-8;base64,{b64}) format('{font_format}');
                    font-weight: 100 900;
                    font-style: normal;
                    font-display: swap;
                }}
                """
            except Exception:
                pass
    return ""


class MusicTaggerAPI:
    def __init__(self):
        self._window = None
        self.current_file_path = None
        self.initial_tags = {}
        
        # ذخیره فایل تنظیمات در کنار فایل اجرایی
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.config_path = os.path.join(base_dir, "config.json")

        self.settings = {
            "overwrite_original": False,
            "custom_output_dir": "",
            "language": "en",
            "theme": "system"
        }
        self.load_settings_from_disk()

    def load_settings_from_disk(self):
        """خواندن تنظیمات از دیسک"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception:
                pass

    def save_settings_to_disk(self):
        """ذخیره تنظیمات روی فایل config.json"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_window(self, window):
        self._window = window

    def is_online(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2.0)
            return True
        except OSError:
            return False

    def select_file_dialog(self):
        dialog_type = getattr(webview.FileDialog, 'OPEN', webview.OPEN_DIALOG)
        result = self._window.create_file_dialog(
            dialog_type,
            allow_multiple=False,
            file_types=('Media Files (*.mp4;*.mp3;*.m4a;*.wav;*.mkv;*.flv;*.aac)', 'All Files (*.*)')
        )
        if result and len(result) > 0:
            return self.process_selected_file(result[0])
        return None

    def select_folder_dialog(self):
        dialog_type = getattr(webview.FileDialog, 'FOLDER', webview.FOLDER_DIALOG)
        result = self._window.create_file_dialog(
            dialog_type
        )
        if result and len(result) > 0:
            self.settings["custom_output_dir"] = result[0]
            self.save_settings_to_disk()
            return result[0]
        return ""

    def save_image_dialog(self, image_base64, default_name="cover.jpg"):
        dialog_type = getattr(webview.FileDialog, 'SAVE', webview.SAVE_DIALOG)
        result = self._window.create_file_dialog(
            dialog_type,
            save_filename=default_name,
            file_types=('JPEG Image (*.jpg)', 'PNG Image (*.png)', 'All Files (*.*)')
        )
        if result:
            save_path = result if isinstance(result, str) else result[0]
            try:
                if "," in image_base64:
                    image_base64 = image_base64.split(",", 1)[1]
                img_data = base64.b64decode(image_base64)
                with open(save_path, "wb") as f:
                    f.write(img_data)
                return {"status": "success", "path": save_path}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "cancelled"}

    def update_settings(self, settings_dict):
        self.settings.update(settings_dict)
        self.save_settings_to_disk()
        return {"status": "success"}

    def get_settings(self):
        return self.settings

    def process_selected_file(self, file_path):
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found."}

        ext = os.path.splitext(file_path)[1].lower()
        self.current_file_path = file_path

        if ext == ".mp3":
            tags_data = self._read_full_mp3_data(file_path)
            self.initial_tags = dict(tags_data)
            audio_base64 = self._get_audio_data_url(file_path)
            return {
                "status": "ready_mp3",
                "file_path": file_path,
                "tags": tags_data,
                "audio_data": audio_base64
            }
        else:
            return {
                "status": "needs_conversion",
                "file_path": file_path,
                "filename": os.path.basename(file_path)
            }

    def convert_to_mp3(self, file_path):
        try:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            target_dir = self.settings["custom_output_dir"] if self.settings["custom_output_dir"] and os.path.exists(self.settings["custom_output_dir"]) else os.path.dirname(file_path)
            output_path = os.path.join(target_dir, f"{base_name}.mp3")

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            cmd = [
                ffmpeg_path,
                '-y',
                '-i', file_path,
                '-vn',
                '-acodec', 'libmp3lame',
                '-q:a', '2',
                output_path
            ]

            process = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )

            if process.returncode != 0:
                return {"status": "error", "message": "Conversion failed."}

            self.current_file_path = output_path
            tags_data = self._read_full_mp3_data(output_path)
            self.initial_tags = dict(tags_data)
            audio_base64 = self._get_audio_data_url(output_path)

            return {
                "status": "success",
                "file_path": output_path,
                "tags": tags_data,
                "audio_data": audio_base64
            }
        except Exception as e:
            return {"status": "error", "message": f"Error converting file: {str(e)}"}

    def _get_audio_data_url(self, file_path):
        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            return f"data:audio/mp3;base64,{encoded}"
        except Exception:
            return ""

    def _read_full_mp3_data(self, file_path):
        data = {
            "title": "",
            "artist": "",
            "album": "",
            "year": "",
            "track": "",
            "genre": "",
            "composer": "",
            "disc": "",
            "copyright": "",
            "comment": "",
            "cover_base64": ""
        }
        try:
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                tags = audio.tags
                if 'TIT2' in tags: data["title"] = str(tags['TIT2'].text[0])
                if 'TPE1' in tags: data["artist"] = str(tags['TPE1'].text[0])
                if 'TALB' in tags: data["album"] = str(tags['TALB'].text[0])
                if 'TDRC' in tags: data["year"] = str(tags['TDRC'].text[0])
                if 'TRCK' in tags: data["track"] = str(tags['TRCK'].text[0])
                if 'TCON' in tags: data["genre"] = str(tags['TCON'].text[0])
                if 'TCOM' in tags: data["composer"] = str(tags['TCOM'].text[0])
                if 'TPOS' in tags: data["disc"] = str(tags['TPOS'].text[0])
                if 'TCOP' in tags: data["copyright"] = str(tags['TCOP'].text[0])

                for key in tags.keys():
                    if key.startswith('COMM'):
                        data["comment"] = str(tags[key].text[0])
                        break

                for tag in tags.values():
                    if isinstance(tag, APIC):
                        encoded = base64.b64encode(tag.data).decode('utf-8')
                        data["cover_base64"] = f"data:{tag.mime};base64,{encoded}"
                        break
        except Exception:
            pass

        return data

    def search_online_metadata(self, title, artist):
        if not self.is_online():
            return {"status": "no_internet"}

        query = f"{title} {artist}".strip()
        if not query:
            return {"status": "success", "results": []}

        try:
            url = f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&entity=song&limit=10"
            resp = requests.get(url, timeout=7)
            if resp.status_code != 200:
                return {"status": "error", "results": []}

            results = resp.json().get("results", [])
            output = []
            for item in results:
                artwork_url = item.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                output.append({
                    "title": item.get("trackName", ""),
                    "artist": item.get("artistName", ""),
                    "album": item.get("collectionName", ""),
                    "year": item.get("releaseDate", "")[:4] if item.get("releaseDate") else "",
                    "track": str(item.get("trackNumber", "")),
                    "genre": item.get("primaryGenreName", ""),
                    "composer": item.get("composerName", ""),
                    "copyright": item.get("copyright", ""),
                    "artwork_url": artwork_url
                })
            return {"status": "success", "results": output}
        except requests.exceptions.RequestException:
            return {"status": "no_internet"}
        except Exception:
            return {"status": "error", "results": []}

    def fetch_image_base64(self, url):
        if not self.is_online():
            return {"status": "no_internet"}
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                encoded = base64.b64encode(resp.content).decode('utf-8')
                mime = resp.headers.get('Content-Type', 'image/jpeg')
                return {"status": "success", "dataUrl": f"data:{mime};base64,{encoded}"}
            return {"status": "error"}
        except Exception:
            return {"status": "no_internet"}

    def copy_image_to_clipboard(self, image_base64):
        try:
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            img_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(img_data)).convert("RGB")

            output = BytesIO()
            image.save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()

            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()

            return {"status": "success"}
        except ImportError:
            try:
                temp_path = os.path.join(os.environ.get("TEMP", "."), "_temp_cb_cover.png")
                image.save(temp_path, "PNG")
                ps_cmd = f'powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile(\'{temp_path}\'))"'
                subprocess.run(ps_cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                return {"status": "success"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_music_tags(self, file_path, tags, new_cover_base64=None):
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found."}

        try:
            title_clean = tags.get("title", "").strip().replace("/", "-").replace("\\", "-")
            artist_clean = tags.get("artist", "").strip().replace("/", "-").replace("\\", "-")
            target_dir = self.settings["custom_output_dir"] if self.settings["custom_output_dir"] and os.path.exists(self.settings["custom_output_dir"]) else os.path.dirname(file_path)

            if self.settings["overwrite_original"]:
                target_path = file_path
            else:
                new_filename = f"{artist_clean} - {title_clean}.mp3" if (title_clean and artist_clean) else os.path.basename(file_path)
                target_path = os.path.join(target_dir, new_filename)
                if os.path.abspath(file_path) != os.path.abspath(target_path):
                    shutil.copy2(file_path, target_path)

            try:
                id3_audio = ID3(target_path)
            except error:
                id3_audio = ID3()

            id3_audio.delall('TIT2'); id3_audio.add(TIT2(encoding=3, text=tags.get("title", "")))
            id3_audio.delall('TPE1'); id3_audio.add(TPE1(encoding=3, text=tags.get("artist", "")))
            id3_audio.delall('TALB'); id3_audio.add(TALB(encoding=3, text=tags.get("album", "")))
            id3_audio.delall('TDRC'); id3_audio.add(TDRC(encoding=3, text=tags.get("year", "")))
            id3_audio.delall('TRCK'); id3_audio.add(TRCK(encoding=3, text=tags.get("track", "")))
            id3_audio.delall('TCON'); id3_audio.add(TCON(encoding=3, text=tags.get("genre", "")))
            id3_audio.delall('TCOM'); id3_audio.add(TCOM(encoding=3, text=tags.get("composer", "")))
            id3_audio.delall('TPOS'); id3_audio.add(TPOS(encoding=3, text=tags.get("disc", "")))
            id3_audio.delall('TCOP'); id3_audio.add(TCOP(encoding=3, text=tags.get("copyright", "")))
            id3_audio.delall('COMM'); id3_audio.add(COMM(encoding=3, lang='eng', desc='desc', text=tags.get("comment", "")))

            if new_cover_base64 and "," in new_cover_base64:
                header, base64_data = new_cover_base64.split(",", 1)
                mime = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
                img_bytes = base64.b64decode(base64_data)

                id3_audio.delall('APIC')
                id3_audio.add(
                    APIC(
                        encoding=3,
                        mime=mime,
                        type=3,
                        desc='Cover',
                        data=img_bytes
                    )
                )

            id3_audio.save(target_path, v2_version=3)
            self.current_file_path = target_path
            self.initial_tags = dict(tags)
            self.initial_tags["cover_base64"] = new_cover_base64

            return {"status": "success", "new_path": target_path}
        except Exception as e:
            return {"status": "error", "message": f"Error saving: {str(e)}"}


UI_HTML = """
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<title>__APP_TITLE__</title>
<style>
  __EMBEDDED_FONT_CSS__
  
  :root {
    --primary: #ff7700;
    --primary-light: #fff2e6;
    --primary-hover: #e56a00;
    --bg-gradient: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%);
    --glass-bg: rgba(255, 255, 255, 0.78);
    --glass-border: rgba(255, 255, 255, 0.95);
    --glass-shadow: 0 10px 30px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0,0,0,0.03);
    --text-main: #2b2f38;
    --text-muted: #7b8390;
    --card-bg: rgba(255, 255, 255, 0.92);
    --input-bg: rgba(255, 255, 255, 0.95);
    --border-color: #dce2e8;
    --modal-bg: #ffffff;
    --cover-bg: #f1f3f6;
  }

  body.theme-dark {
    --bg-gradient: linear-gradient(135deg, #14171c 0%, #1d2229 100%);
    --glass-bg: rgba(29, 34, 42, 0.82);
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    --text-main: #f0f3f8;
    --text-muted: #9aa2b1;
    --card-bg: rgba(36, 42, 52, 0.92);
    --input-bg: rgba(22, 26, 32, 0.8);
    --border-color: rgba(255, 255, 255, 0.12);
    --modal-bg: #1e232b;
    --cover-bg: #16191f;
  }

  html, body {
    scrollbar-gutter: stable;
  }
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  ::-webkit-scrollbar-track {
    background: transparent !important;
  }
  ::-webkit-scrollbar-thumb {
    background-color: #cbd5e1;
    border-radius: 999px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background-color: var(--primary);
  }
  body.theme-dark ::-webkit-scrollbar-thumb {
    background-color: rgba(255, 255, 255, 0.22);
  }
  body.theme-dark ::-webkit-scrollbar-thumb:hover {
    background-color: var(--primary);
  }
  ::-webkit-scrollbar-button,
  ::-webkit-scrollbar-corner {
    display: none;
    background: transparent;
  }

  * { 
    box-sizing: border-box; 
    margin: 0; 
    padding: 0; 
    user-select: none; 
    font-family: 'Vazirmatn', 'Segoe UI', Tahoma, system-ui, -apple-system, sans-serif; 
  }
  body {
    background: var(--bg-gradient);
    color: var(--text-main);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
    transition: background 0.3s ease, color 0.3s ease;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 36px;
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--glass-border);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
  }
  .app-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 700;
    font-size: 1.25rem;
    color: var(--primary);
  }
  .app-version-badge {
    font-size: 0.72rem;
    font-weight: 500;
    background: var(--primary-light);
    color: var(--primary);
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid rgba(255, 119, 0, 0.25);
  }
  .brand-icon {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    border: 2px solid var(--primary);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .brand-icon svg { stroke: var(--primary); fill: none; stroke-width: 1.8; }
  
  .header-actions { display: flex; gap: 10px; align-items: center; }
  
  .icon-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    width: 38px;
    height: 38px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--text-muted);
    transition: all 0.2s ease;
  }
  .icon-btn:hover, .icon-btn.active { border-color: var(--primary); color: var(--primary); background: var(--card-bg); }

  .about-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    padding: 8px 18px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    color: var(--text-muted);
    transition: all 0.2s ease;
  }
  .about-btn:hover { border-color: var(--primary); color: var(--primary); background: var(--card-bg); }

  .container {
    max-width: 1320px;
    margin: 0 auto;
    padding: 24px 36px;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .drop-zone {
    background: var(--glass-bg);
    border: 2px dashed rgba(255, 119, 0, 0.4);
    border-radius: 22px;
    padding: 28px 20px;
    text-align: center;
    cursor: pointer;
    backdrop-filter: blur(10px);
    box-shadow: var(--glass-shadow);
    transition: all 0.25s ease;
  }
  .drop-zone:hover, .drop-zone.dragover {
    border-color: var(--primary);
    background: rgba(255, 119, 0, 0.06);
    transform: translateY(-2px);
  }
  .drop-zone svg { stroke: var(--primary); stroke-width: 1.6; margin-bottom: 6px; }

  .conversion-banner {
    display: none;
    background: var(--card-bg);
    padding: 16px 24px;
    border-radius: 16px;
    box-shadow: var(--glass-shadow);
    border: 1px solid var(--glass-border);
    justify-content: space-between;
    align-items: center;
  }

  .editor-grid {
    display: none;
    grid-template-columns: 500px 1fr;
    gap: 28px;
    align-items: stretch;
  }

  .left-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    height: 100%;
  }
  .cover-card {
    width: 500px;
    flex: 1;
    min-height: 480px;
    border-radius: 24px;
    position: relative;
    overflow: hidden;
    background: var(--cover-bg);
    border: 1px solid var(--glass-border);
    box-shadow: var(--glass-shadow);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cover-card img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .cover-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    color: var(--text-muted);
  }
  .cover-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.45);
    opacity: 0;
    transition: opacity 0.25s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 0.95rem;
    gap: 8px;
  }
  .cover-card:hover .cover-overlay { opacity: 1; }

  .player-card {
    background: var(--card-bg);
    border-radius: 18px;
    padding: 14px 20px;
    border: 1px solid var(--glass-border);
    box-shadow: var(--glass-shadow);
    display: flex;
    align-items: center;
  }
  .player-card audio { width: 100%; height: 38px; outline: none; }

  .right-panel {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    box-shadow: var(--glass-shadow);
    backdrop-filter: blur(14px);
    border-radius: 24px;
    padding: 26px 30px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 12px;
    height: 100%;
  }
  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .form-group label {
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--text-main);
  }
  .form-control {
    background: var(--input-bg);
    border: 1px solid var(--border-color);
    padding: 9px 14px;
    border-radius: 10px;
    font-size: 0.92rem;
    color: var(--text-main);
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .form-control:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(255, 119, 0, 0.15);
  }

  .btn {
    padding: 10px 20px;
    border-radius: 12px;
    border: none;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: all 0.2s ease;
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    filter: grayscale(1);
  }
  .btn-primary {
    background: var(--primary);
    color: #fff;
    box-shadow: 0 4px 14px rgba(255, 119, 0, 0.25);
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
  .btn-outline {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    color: var(--text-main);
  }
  .btn-outline:hover:not(:disabled) {
    border-color: var(--primary);
    color: var(--primary);
  }
  .btn-secondary {
    background: var(--cover-bg);
    color: var(--text-main);
    border: 1px solid var(--border-color);
  }
  .btn-secondary:hover:not(:disabled) {
    border-color: var(--primary);
  }

  .form-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
    padding-top: 16px;
    border-top: 1px solid var(--border-color);
  }
  .save-group { display: flex; gap: 10px; }

  .online-results-section {
    display: none;
    background: var(--glass-bg);
    backdrop-filter: blur(14px);
    border: 1px solid var(--glass-border);
    box-shadow: var(--glass-shadow);
    border-radius: 24px;
    padding: 26px;
  }
  .online-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
  }
  .online-header {
    font-weight: 700;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .view-toggles {
    display: flex;
    gap: 6px;
  }

  .results-grid.view-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 18px;
  }
  .results-grid.view-grid .result-card {
    background: var(--card-bg);
    border-radius: 16px;
    padding: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    border: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    gap: 10px;
    cursor: pointer;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }
  .results-grid.view-grid .result-card:hover {
    transform: translateY(-3px);
    border-color: var(--primary);
  }
  .results-grid.view-grid .result-thumb {
    width: 100%;
    height: 170px;
    border-radius: 12px;
    object-fit: cover;
  }

  .results-grid.view-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .results-grid.view-list .result-card {
    background: var(--card-bg);
    border-radius: 16px;
    padding: 12px 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    border: 1px solid var(--border-color);
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 16px;
    cursor: pointer;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }
  .results-grid.view-list .result-card:hover {
    transform: translateX(4px);
    border-color: var(--primary);
  }
  .results-grid.view-list .result-thumb {
    width: 72px;
    height: 72px;
    border-radius: 10px;
    object-fit: cover;
  }
  .results-grid.view-list .result-details {
    flex: 1;
  }
  .results-grid.view-list .result-buttons {
    flex-direction: row;
  }

  .result-details h4 {
    font-size: 0.95rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .result-details p {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .result-buttons {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: auto;
  }
  .btn-sm {
    padding: 6px 10px;
    font-size: 0.78rem;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    border: 1px solid var(--border-color);
    background: var(--card-bg);
    color: var(--text-main);
  }
  .btn-sm:hover {
    border-color: var(--primary);
    color: var(--primary);
    background: var(--primary-light);
  }
  .btn-sm.full-apply {
    background: var(--primary-light);
    border-color: var(--primary);
    color: var(--primary);
    font-weight: 600;
  }

  .modal-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(8px);
    z-index: 999;
    align-items: center;
    justify-content: center;
  }
  .modal-dialog {
    background: var(--modal-bg);
    width: 580px;
    max-width: 95vw;
    border-radius: 24px;
    padding: 26px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.25);
    display: flex;
    flex-direction: column;
    gap: 18px;
    border: 1px solid var(--glass-border);
  }

  .crop-offline-box {
    width: 100%;
    height: 380px;
    background: #000;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
  }
  .crop-offline-box canvas {
    cursor: grab;
  }
  .crop-offline-box canvas:active {
    cursor: grabbing;
  }
  .crop-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--input-bg);
    padding: 10px 14px;
    border-radius: 12px;
    border: 1px solid var(--border-color);
  }
  .crop-controls input[type="range"] {
    flex: 1;
    accent-color: var(--primary);
  }

  .detail-modal-body {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 20px;
    align-items: start;
  }
  .detail-cover-wrapper {
    position: relative;
    width: 200px;
    height: 200px;
    border-radius: 16px;
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(0,0,0,0.1);
  }
  .detail-cover-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .detail-cover-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    gap: 6px;
    z-index: 2;
  }
  .img-action-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    border: none;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.2s;
  }
  .img-action-btn:hover { background: var(--primary); }

  .detail-fields-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 340px;
    overflow-y: auto;
    padding-right: 6px;
  }
  .detail-field-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--input-bg);
    padding: 8px 12px;
    border-radius: 10px;
    border: 1px solid var(--border-color);
  }
  .detail-field-item .field-info {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .detail-field-item .field-title {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  .detail-field-item .field-val {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .copy-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    padding: 4px;
    border-radius: 6px;
  }
  .copy-btn:hover { color: var(--primary); }

  .lightbox-modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    backdrop-filter: blur(10px);
    z-index: 1100;
    align-items: center;
    justify-content: center;
    cursor: zoom-out;
  }
  .lightbox-modal img {
    max-width: 85vw;
    max-height: 85vh;
    border-radius: 20px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  }

  .settings-option {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    font-size: 0.92rem;
    font-weight: 500;
  }
  .checkbox-label input[type="checkbox"] {
    width: 18px;
    height: 18px;
    accent-color: var(--primary);
  }

  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #2b2f38;
    color: #fff;
    padding: 12px 24px;
    border-radius: 12px;
    font-size: 0.9rem;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    display: none;
    z-index: 1200;
    transition: all 0.25s ease;
  }
  .toast.toast-error {
    background: #d9534f;
    box-shadow: 0 8px 24px rgba(217, 83, 79, 0.35);
  }
</style>
</head>
<body class="theme-system">

  <header>
    <div class="app-brand">
      <div class="brand-icon">
        <svg width="22" height="22" viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
      </div>
      <span>__APP_NAME__</span>
      <span class="app-version-badge">__APP_VERSION__</span>
    </div>
    
    <div class="header-actions">
      <button class="icon-btn" title="Settings" onclick="openSettingsModal()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
      </button>
      <button class="about-btn" onclick="openAboutModal()" data-i18n="btnAbout">About</button>
    </div>
  </header>

  <div class="container">
    <div class="drop-zone" id="dropZone" onclick="handleSelectFile()">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
      <div style="font-weight: 600; font-size: 1.05rem;" data-i18n="dropText">Drop audio or video files here (MP4, MP3, ...) or browse</div>
      <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;" data-i18n="dropSubtext">Automatic online search, modern tag editor and full media player</div>
    </div>

    <div class="conversion-banner" id="conversionBanner">
      <div>
        <strong id="nonMp3Name">File name</strong>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;" data-i18n="nonMp3Notice">This is not an MP3 file; convert to MP3 to edit tags.</p>
      </div>
      <button class="btn btn-primary" id="btnConvert" onclick="convertCurrentFile()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
        <span data-i18n="btnConvert">Convert to MP3</span>
      </button>
    </div>

    <div class="editor-grid" id="editorGrid">
      <div class="left-panel">
        <div class="cover-card" id="coverCard" onclick="triggerPickCover()">
          <img id="coverImage" src="" alt="Album Cover" style="display: none;">
          <div class="cover-placeholder" id="coverPlaceholder">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#a0a8b4" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
            <span data-i18n="chooseCover">Choose Album Cover</span>
          </div>
          <div class="cover-overlay">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
            <span data-i18n="changeCover">Change & Crop Cover</span>
          </div>
        </div>

        <div class="player-card">
          <audio id="audioPlayer" controls preload="auto"></audio>
        </div>
      </div>

      <div class="right-panel">
        <div class="form-row">
          <div class="form-group">
            <label data-i18n="lblTitle">Title</label>
            <input type="text" class="form-control" id="inputTitle" oninput="handleFieldChange()">
          </div>
          <div class="form-group">
            <label data-i18n="lblArtist">Artist</label>
            <input type="text" class="form-control" id="inputArtist" oninput="handleFieldChange()">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label data-i18n="lblAlbum">Album</label>
            <input type="text" class="form-control" id="inputAlbum" oninput="handleFieldChange()">
          </div>
          <div class="form-group">
            <label data-i18n="lblGenre">Genre</label>
            <input type="text" class="form-control" id="inputGenre" oninput="handleFieldChange()">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label data-i18n="lblComposer">Composer</label>
            <input type="text" class="form-control" id="inputComposer" oninput="handleFieldChange()">
          </div>
          <div class="form-group">
            <label data-i18n="lblYear">Year</label>
            <input type="text" class="form-control" id="inputYear" oninput="handleFieldChange()">
          </div>
        </div>

        <div class="form-row" style="grid-template-columns: 1fr 1fr 1fr;">
          <div class="form-group">
            <label data-i18n="lblTrack">Track #</label>
            <input type="text" class="form-control" id="inputTrack" oninput="handleFieldChange()">
          </div>
          <div class="form-group">
            <label data-i18n="lblDisc">Disc #</label>
            <input type="text" class="form-control" id="inputDisc" oninput="handleFieldChange()">
          </div>
          <div class="form-group">
            <label data-i18n="lblCopyright">Copyright</label>
            <input type="text" class="form-control" id="inputCopyright" oninput="handleFieldChange()">
          </div>
        </div>

        <div class="form-group">
          <label data-i18n="lblComment">Comment / Lyrics</label>
          <input type="text" class="form-control" id="inputComment" oninput="handleFieldChange()">
        </div>

        <div class="form-actions">
          <button class="btn btn-outline" id="btnOnlineSearch" disabled onclick="searchOnline()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <span id="txtOnlineSearch" data-i18n="btnSearchOnline">Search Online Metadata</span>
          </button>

          <div class="save-group">
            <button class="btn btn-secondary" id="btnReset" onclick="promptResetTags()">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><polyline points="3 3 3 8 8 8"></polyline></svg>
              <span data-i18n="btnReset">Reset</span>
            </button>

            <button class="btn btn-primary" id="btnSave" disabled onclick="saveTags()">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
              <span data-i18n="btnSave">Save Tags</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="online-results-section" id="onlineSection">
      <div class="online-header-bar">
        <div class="online-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M2 12h20"></path><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
          <span data-i18n="onlineMatches">Online Matches (Up to 10 releases)</span>
        </div>
        
        <div class="view-toggles">
          <button class="icon-btn active" id="btnViewGrid" title="Grid View" onclick="setViewMode('grid')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
          </button>
          <button class="icon-btn" id="btnViewList" title="List View" onclick="setViewMode('list')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
          </button>
        </div>
      </div>
      
      <div class="results-grid view-grid" id="resultsGrid"></div>
    </div>
  </div>

  <div class="modal-backdrop" id="detailModal">
    <div class="modal-dialog">
      <h3 style="font-weight: 700; font-size: 1.15rem;" data-i18n="detailsTitle">Release Details</h3>
      <div class="detail-modal-body">
        <div class="detail-cover-wrapper" onclick="openLightbox(document.getElementById('detailCoverImg').src)">
          <img id="detailCoverImg" src="" alt="Cover">
          <div class="detail-cover-actions" onclick="event.stopPropagation()">
            <button class="img-action-btn" title="Save image" onclick="saveCoverToFile()">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
            </button>
            <button class="img-action-btn" title="Copy image" onclick="copyImageToClipboard()">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
          </div>
        </div>

        <div class="detail-fields-list" id="detailFieldsList"></div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px;">
        <button class="btn btn-outline" onclick="closeDetailModal()" data-i18n="btnClose">Close</button>
      </div>
    </div>
  </div>

  <div class="lightbox-modal" id="lightboxModal" onclick="closeLightbox()">
    <img id="lightboxImg" src="" alt="Enlarged Cover">
  </div>

  <div class="modal-backdrop" id="settingsModal">
    <div class="modal-dialog">
      <h3 style="font-weight: 700; font-size: 1.15rem; display: flex; align-items: center; gap: 8px;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        <span data-i18n="settingsTitle">Preferences & Storage</span>
      </h3>

      <div class="form-row">
        <div class="form-group">
          <label data-i18n="lblLanguage">Language</label>
          <select class="form-control" id="settingLanguage">
            <option value="en">English</option>
            <option value="fa">فارسی</option>
          </select>
        </div>
        <div class="form-group">
          <label data-i18n="lblTheme">Theme</label>
          <select class="form-control" id="settingTheme">
            <option value="system" data-i18n="themeSystem">System Default</option>
            <option value="light" data-i18n="themeLight">Light</option>
            <option value="dark" data-i18n="themeDark">Dark</option>
          </select>
        </div>
      </div>
      
      <div class="settings-option">
        <label class="checkbox-label">
          <input type="checkbox" id="settingOverwrite">
          <span data-i18n="overwriteNotice">Overwrite original file (If unchecked, saves as new file)</span>
        </label>
      </div>

      <div class="settings-option" style="border: none;">
        <label style="font-size: 0.88rem; font-weight: 600;" data-i18n="lblOutputDir">Output folder path:</label>
        <div style="display: flex; gap: 8px;">
          <input type="text" class="form-control" id="settingPathDisplay" readonly placeholder="Same directory as source" style="flex: 1;">
          <button class="btn btn-outline" onclick="browseOutputDir()" data-i18n="btnBrowse">Browse</button>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
        <button class="btn btn-primary" onclick="saveSettingsModal()" data-i18n="btnSaveAndClose">Save & Apply</button>
      </div>
    </div>
  </div>

  <div class="modal-backdrop" id="confirmResetModal">
    <div class="modal-dialog" style="width: 440px;">
      <h3 style="font-weight: 700; font-size: 1.1rem; color: #d9534f;" data-i18n="resetConfirmTitle">Reset Warning</h3>
      <p style="font-size: 0.92rem; color: var(--text-muted); line-height: 1.6;" data-i18n="resetConfirmDesc">
        Unsaved changes detected. Are you sure you want to discard them and revert to initial tags?
      </p>
      <div style="display: flex; justify-content: flex-end; gap: 10px;">
        <button class="btn btn-outline" onclick="closeConfirmResetModal()" data-i18n="btnCancel">Cancel</button>
        <button class="btn btn-primary" style="background: #d9534f;" onclick="performResetTags()" data-i18n="btnConfirmReset">Yes, Revert</button>
      </div>
    </div>
  </div>

  <div class="modal-backdrop" id="cropModal">
    <div class="modal-dialog">
      <h3 style="font-weight: 700; font-size: 1.1rem;" data-i18n="cropTitle">Square Crop Cover</h3>
      <div class="crop-offline-box">
        <canvas id="cropCanvas" width="340" height="340"></canvas>
      </div>
      <div class="crop-controls">
        <span style="font-size: 0.8rem; color: var(--text-muted);">Zoom</span>
        <input type="range" id="cropZoomSlider" min="1" max="3" step="0.05" value="1" oninput="updateCropTransform()">
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 12px;">
        <button class="btn btn-outline" onclick="closeCropModal()" data-i18n="btnCancel">Cancel</button>
        <button class="btn btn-primary" onclick="applyCrop()" data-i18n="btnApplyCrop">Apply 1:1 Crop</button>
      </div>
    </div>
  </div>
  <input type="file" id="coverFileInput" accept="image/*" style="display: none;" onchange="handleCoverFileSelected(event)">

  <div class="modal-backdrop" id="aboutModal">
    <div class="modal-dialog" style="text-align: center; gap: 14px;">
      <div class="brand-icon" style="margin: 0 auto; width: 48px; height: 48px;">
        <svg width="28" height="28" viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
      </div>
      <h3 style="font-weight: 700;">__APP_NAME__</h3>
      <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600; margin-top: -8px;">__APP_VERSION__</span>
      <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.7;" data-i18n="aboutDesc">
        Modern MP4 to MP3 converter & intelligent ID3 tag batch editor.
      </p>
      <div style="background: var(--primary-light); padding: 14px; border-radius: 12px;">
        <span style="font-weight: 600; color: var(--primary); font-size: 1.05rem;" data-i18n="aboutDev">Developer: Hadi Dastangoo</span>
        <div style="font-size: 0.8rem; color: #888; margin-top: 4px;">Crafted with Python & modern vibe code</div>
      </div>
      <button class="btn btn-outline" style="align-self: center; margin-top: 6px;" onclick="closeAboutModal()" data-i18n="btnClose">Close</button>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    let currentFilePath = "";
    let currentCoverDataUrl = "";
    let isModified = false;
    let cachedInitialTags = null;
    let currentSelectedDetailItem = null;

    let cropImg = new Image();
    let cropScale = 1;
    let cropPanX = 0;
    let cropPanY = 0;
    let isDraggingCrop = false;
    let dragStartX = 0, dragStartY = 0;

    const translations = {
      en: {
        btnAbout: "About",
        dropText: "Drop audio or video files here (MP4, MP3, ...) or browse",
        dropSubtext: "Automatic online search, modern tag editor and full media player",
        nonMp3Notice: "This is not an MP3 file; convert to MP3 to edit tags.",
        btnConvert: "Convert to MP3",
        chooseCover: "Choose Album Cover",
        changeCover: "Change & Crop Cover",
        lblTitle: "Title",
        lblArtist: "Artist",
        lblAlbum: "Album",
        lblGenre: "Genre",
        lblComposer: "Composer",
        lblYear: "Year",
        lblTrack: "Track #",
        lblDisc: "Disc #",
        lblCopyright: "Copyright",
        lblComment: "Comment / Lyrics",
        btnSearchOnline: "Search Online Metadata",
        btnReset: "Reset",
        btnSave: "Save Tags",
        onlineMatches: "Online Matches (Up to 10 releases)",
        detailsTitle: "Release Details",
        btnClose: "Close",
        settingsTitle: "Preferences & Storage",
        lblLanguage: "Language",
        lblTheme: "Theme",
        themeSystem: "System Default",
        themeLight: "Light",
        themeDark: "Dark",
        overwriteNotice: "Overwrite original file (If unchecked, saves as new file)",
        lblOutputDir: "Output folder path:",
        btnBrowse: "Browse",
        btnSaveAndClose: "Save & Apply",
        resetConfirmTitle: "Reset Warning",
        resetConfirmDesc: "Unsaved changes detected. Are you sure you want to discard them and revert to initial tags?",
        btnCancel: "Cancel",
        btnConfirmReset: "Yes, Revert",
        cropTitle: "Square Crop Cover",
        btnApplyCrop: "Apply 1:1 Crop",
        aboutDesc: "Modern MP4 to MP3 converter & intelligent ID3 tag batch editor.",
        aboutDev: "Developer: Hadi Dastangoo",
        searching: "Searching online...",
        copied: "Copied to clipboard!",
        savedSuccess: "Tags and cover saved successfully.",
        applyTags: "Set Tags",
        applyCover: "Set Cover",
        applyAll: "Set Tags & Cover",
        noInternet: "Unable to connect to the internet. Please check your network connection."
      },
      fa: {
        btnAbout: "درباره برنامه",
        dropText: "فایل صوتی یا تصویری (MP4, MP3, ...) را اینجا بکشید یا کلیک کنید",
        dropSubtext: "ویرایشگر تمامی تگ‌های ID3، پشتیبانی از کاور مربعی و پلیر استریم مستقیم",
        nonMp3Notice: "این فایل MP3 نیست؛ برای ویرایش تگ‌ها تبدیل به MP3 الزامی است.",
        btnConvert: "تبدیل به MP3",
        chooseCover: "انتخاب کاور آهنگ (کلیک کنید)",
        changeCover: "برش و تغییر کاور",
        lblTitle: "عنوان آهنگ (Title)",
        lblArtist: "هنرمند / خواننده (Artist)",
        lblAlbum: "آلبوم (Album)",
        lblGenre: "سبک موسیقی (Genre)",
        lblComposer: "آهنگساز (Composer)",
        lblYear: "سال انتشار (Year)",
        lblTrack: "شماره ترک (Track)",
        lblDisc: "شماره دیسک (Disc)",
        lblCopyright: "کپی‌رایت (Copyright)",
        lblComment: "توضیحات یا متن (Comment)",
        btnSearchOnline: "جستجوی آنلاین اطلاعات آهنگ",
        btnReset: "بازنشانی",
        btnSave: "ذخیره اطلاعات آهنگ",
        onlineMatches: "نتایج هوشمند آنلاین (تا ۱۰ مورد مشابه)",
        detailsTitle: "جزئیات انتشار آهنگ",
        btnClose: "بستن",
        settingsTitle: "تنظیمات و ذخیره‌سازی",
        lblLanguage: "زبان برنامه",
        lblTheme: "پوسته ظاهری",
        themeSystem: "پوسته سیستم",
        themeLight: "روز (روشن)",
        themeDark: "شب (تاریک)",
        overwriteNotice: "نوشتن مستقیم بر روی فایل اصلی (در صورت غیرفعال بودن، فایل جدید ایجاد می‌شود)",
        lblOutputDir: "پوشه ذخیره‌سازی خروجی:",
        btnBrowse: "انتخاب پوشه",
        btnSaveAndClose: "تأیید و اعمال",
        resetConfirmTitle: "هشدار بازنشانی",
        resetConfirmDesc: "تغییرات ذخیره‌نشده‌ای وجود دارد. آیا از بازگردانی اطلاعات اولیه اطمینان دارید؟",
        btnCancel: "انصراف",
        btnConfirmReset: "بله، بازنشانی کن",
        cropTitle: "برش مربعی کاور",
        btnApplyCrop: "تأیید و اعمال کاور",
        aboutDesc: "برنامه استخراج و تگ‌گذاری پیشرفته موسیقی با استانداردهای مدرن.",
        aboutDev: "توسعه‌دهنده: هادی داستانگو",
        searching: "در حال جستجو...",
        copied: "در حافظه کپی شد!",
        savedSuccess: "تگ‌ها و کاور با موفقیت ذخیره شدند.",
        applyTags: "تنظیم اطلاعات",
        applyCover: "تنظیم کاور",
        applyAll: "تنظیم اطلاعات و کاور",
        noInternet: "امکان برقراری ارتباط با وب وجود ندارد. لطفاً اتصال اینترنت خود را بررسی نمایید."
      }
    };

    let currentLang = "en";

    function applyLanguage(lang) {
      currentLang = lang;
      document.documentElement.lang = lang;
      document.documentElement.dir = (lang === "fa") ? "rtl" : "ltr";

      const dict = translations[lang];
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) el.innerText = dict[key];
      });
    }

    function applyTheme(theme) {
      document.body.classList.remove('theme-dark', 'theme-light', 'theme-system');
      if (theme === 'system') {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) document.body.classList.add('theme-dark');
      } else if (theme === 'dark') {
        document.body.classList.add('theme-dark');
      }
    }

    function showToast(msg, isError = false) {
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      if (isError) {
        toast.classList.add('toast-error');
      } else {
        toast.classList.remove('toast-error');
      }
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 4000);
    }

    async function handleSelectFile() {
      const res = await window.pywebview.api.select_file_dialog();
      if (res) renderFileState(res);
    }

    const dropZone = document.getElementById('dropZone');
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); });

    function renderFileState(res) {
      if (res.status === 'error') {
        showToast(res.message, true);
        return;
      }
      currentFilePath = res.file_path;

      if (res.status === 'needs_conversion') {
        document.getElementById('conversionBanner').style.display = 'flex';
        document.getElementById('nonMp3Name').innerText = res.filename;
        document.getElementById('editorGrid').style.display = 'none';
        document.getElementById('onlineSection').style.display = 'none';
      } else if (res.status === 'ready_mp3') {
        document.getElementById('conversionBanner').style.display = 'none';
        cachedInitialTags = JSON.parse(JSON.stringify(res.tags));
        loadMp3IntoEditor(res.file_path, res.tags, res.audio_data);
      }
    }

    async function convertCurrentFile() {
      const btn = document.getElementById('btnConvert');
      btn.disabled = true;
      btn.innerText = (currentLang === "fa") ? "در حال تبدیل..." : "Converting...";
      const res = await window.pywebview.api.convert_to_mp3(currentFilePath);
      btn.disabled = false;
      btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg> <span>${translations[currentLang].btnConvert}</span>`;

      if (res.status === 'success') {
        document.getElementById('conversionBanner').style.display = 'none';
        cachedInitialTags = JSON.parse(JSON.stringify(res.tags));
        loadMp3IntoEditor(res.file_path, res.tags, res.audio_data);
        showToast((currentLang === "fa") ? "تبدیل با موفقیت انجام شد." : "Conversion complete.");
      } else {
        showToast(res.message, true);
      }
    }

    function loadMp3IntoEditor(filePath, tags, audioDataUrl) {
      currentFilePath = filePath;
      document.getElementById('editorGrid').style.display = 'grid';

      const player = document.getElementById('audioPlayer');
      if (audioDataUrl) {
        player.src = audioDataUrl;
        player.load();
      }

      fillInputFields(tags);

      if (tags.cover_base64) {
        setCoverImage(tags.cover_base64);
      } else {
        removeCoverImage();
      }

      isModified = false;
      document.getElementById('btnSave').disabled = true;
      checkSearchBtnState();

      if (tags.title || tags.artist) {
        searchOnline();
      }
    }

    function fillInputFields(tags) {
      document.getElementById('inputTitle').value = tags.title || "";
      document.getElementById('inputArtist').value = tags.artist || "";
      document.getElementById('inputAlbum').value = tags.album || "";
      document.getElementById('inputGenre').value = tags.genre || "";
      document.getElementById('inputComposer').value = tags.composer || "";
      document.getElementById('inputYear').value = tags.year || "";
      document.getElementById('inputTrack').value = tags.track || "";
      document.getElementById('inputDisc').value = tags.disc || "";
      document.getElementById('inputCopyright').value = tags.copyright || "";
      document.getElementById('inputComment').value = tags.comment || "";
    }

    function handleFieldChange() {
      isModified = true;
      document.getElementById('btnSave').disabled = false;
      checkSearchBtnState();
    }

    function checkSearchBtnState() {
      const title = document.getElementById('inputTitle').value.trim();
      const artist = document.getElementById('inputArtist').value.trim();
      document.getElementById('btnOnlineSearch').disabled = (title === "" && artist === "");
    }

    function setCoverImage(dataUrl) {
      currentCoverDataUrl = dataUrl;
      const img = document.getElementById('coverImage');
      img.src = dataUrl;
      img.style.display = 'block';
      document.getElementById('coverPlaceholder').style.display = 'none';
    }

    function removeCoverImage() {
      currentCoverDataUrl = "";
      document.getElementById('coverImage').style.display = 'none';
      document.getElementById('coverPlaceholder').style.display = 'flex';
    }

    function triggerPickCover() {
      document.getElementById('coverFileInput').click();
    }

    function handleCoverFileSelected(e) {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        cropImg.onload = () => {
          cropScale = 1;
          cropPanX = 0;
          cropPanY = 0;
          document.getElementById('cropZoomSlider').value = 1;
          document.getElementById('cropModal').style.display = 'flex';
          initOfflineCanvasCrop();
        };
        cropImg.src = event.target.result;
      };
      reader.readAsDataURL(file);
      e.target.value = "";
    }

    function initOfflineCanvasCrop() {
      const canvas = document.getElementById('cropCanvas');
      const ctx = canvas.getContext('2d');
      drawCropCanvas(ctx, canvas);

      canvas.onmousedown = (e) => {
        isDraggingCrop = true;
        dragStartX = e.clientX - cropPanX;
        dragStartY = e.clientY - cropPanY;
      };
      window.onmousemove = (e) => {
        if (!isDraggingCrop) return;
        cropPanX = e.clientX - dragStartX;
        cropPanY = e.clientY - dragStartY;
        drawCropCanvas(ctx, canvas);
      };
      window.onmouseup = () => { isDraggingCrop = false; };
    }

    function updateCropTransform() {
      cropScale = parseFloat(document.getElementById('cropZoomSlider').value);
      const canvas = document.getElementById('cropCanvas');
      drawCropCanvas(canvas.getContext('2d'), canvas);
    }

    function drawCropCanvas(ctx, canvas) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const size = Math.min(cropImg.width, cropImg.height);
      const renderW = (cropImg.width / size) * canvas.width * cropScale;
      const renderH = (cropImg.height / size) * canvas.height * cropScale;
      const drawX = (canvas.width - renderW) / 2 + cropPanX;
      const drawY = (canvas.height - renderH) / 2 + cropPanY;
      ctx.drawImage(cropImg, drawX, drawY, renderW, renderH);
    }

    function closeCropModal() {
      document.getElementById('cropModal').style.display = 'none';
    }

    function applyCrop() {
      const canvas = document.getElementById('cropCanvas');
      const croppedBase64 = canvas.toDataURL('image/jpeg', 0.94);
      setCoverImage(croppedBase64);
      handleFieldChange();
      closeCropModal();
      showToast((currentLang === "fa") ? "کاور تنظیم شد؛ جهت ذخیره نهایی دکمه ذخیره را بزنید." : "Cover set. Press Save to apply.");
    }

    function promptResetTags() {
      if (isModified) {
        document.getElementById('confirmResetModal').style.display = 'flex';
      } else {
        performResetTags();
      }
    }

    function closeConfirmResetModal() {
      document.getElementById('confirmResetModal').style.display = 'none';
    }

    function performResetTags() {
      closeConfirmResetModal();
      if (!cachedInitialTags) return;

      fillInputFields(cachedInitialTags);
      if (cachedInitialTags.cover_base64) {
        setCoverImage(cachedInitialTags.cover_base64);
      } else {
        removeCoverImage();
      }
      isModified = false;
      document.getElementById('btnSave').disabled = true;
      checkSearchBtnState();
      showToast((currentLang === "fa") ? "اطلاعات اولیه آهنگ بازنشانی شد." : "Tags reverted to original.");
    }

    async function searchOnline() {
      const title = document.getElementById('inputTitle').value.trim();
      const artist = document.getElementById('inputArtist').value.trim();

      const btn = document.getElementById('btnOnlineSearch');
      const txt = document.getElementById('txtOnlineSearch');
      btn.disabled = true;
      txt.innerText = translations[currentLang].searching;

      const res = await window.pywebview.api.search_online_metadata(title, artist);
      btn.disabled = false;
      txt.innerText = translations[currentLang].btnSearchOnline;

      if (res.status === 'no_internet') {
        showToast(translations[currentLang].noInternet, true);
        return;
      }

      renderOnlineResults(res.results || []);
    }

    function setViewMode(mode) {
      const grid = document.getElementById('resultsGrid');
      const btnGrid = document.getElementById('btnViewGrid');
      const btnList = document.getElementById('btnViewList');
      if (mode === 'grid') {
        grid.className = 'results-grid view-grid';
        btnGrid.classList.add('active');
        btnList.classList.remove('active');
      } else {
        grid.className = 'results-grid view-list';
        btnList.classList.add('active');
        btnGrid.classList.remove('active');
      }
    }

    function renderOnlineResults(items) {
      const grid = document.getElementById('resultsGrid');
      const section = document.getElementById('onlineSection');
      grid.innerHTML = "";

      if (!items || items.length === 0) {
        section.style.display = 'none';
        showToast((currentLang === "fa") ? "موردی در جستجوی آنلاین یافت نشد." : "No online matches found.");
        return;
      }

      section.style.display = 'block';
      const dict = translations[currentLang];
      items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.onclick = () => openDetailModal(index);
        card.innerHTML = `
          <img class="result-thumb" src="${item.artwork_url}">
          <div class="result-details">
            <h4 title="${item.title}">${item.title}</h4>
            <p title="${item.artist}">${item.artist} | ${item.album || 'Single'}</p>
            <p>${item.year ? (currentLang==='fa' ? 'سال: ' : 'Year: ') + item.year : ''} ${item.genre ? ' | ' + item.genre : ''}</p>
          </div>
          <div class="result-buttons" onclick="event.stopPropagation()">
            <button class="btn-sm" onclick="applyOnlineData(${index}, 'tags')">${dict.applyTags}</button>
            <button class="btn-sm" onclick="applyOnlineData(${index}, 'cover')">${dict.applyCover}</button>
            <button class="btn-sm full-apply" onclick="applyOnlineData(${index}, 'all')">${dict.applyAll}</button>
          </div>
        `;
        grid.appendChild(card);
      });
      window.cachedOnlineItems = items;
    }

    async function applyOnlineData(idx, mode) {
      const item = window.cachedOnlineItems[idx];
      if (!item) return;

      if (mode === 'tags' || mode === 'all') {
        document.getElementById('inputTitle').value = item.title;
        document.getElementById('inputArtist').value = item.artist;
        document.getElementById('inputAlbum').value = item.album;
        document.getElementById('inputYear').value = item.year;
        document.getElementById('inputTrack').value = item.track;
        if (item.genre) document.getElementById('inputGenre').value = item.genre;
        if (item.composer) document.getElementById('inputComposer').value = item.composer;
        if (item.copyright) document.getElementById('inputCopyright').value = item.copyright;
      }

      if (mode === 'cover' || mode === 'all') {
        showToast((currentLang === "fa") ? "در حال دریافت کاور باکیفیت..." : "Fetching high-res cover...");
        const res = await window.pywebview.api.fetch_image_base64(item.artwork_url);
        if (res.status === 'success') {
          setCoverImage(res.dataUrl);
          handleFieldChange();
          showToast((currentLang === "fa") ? "کاور اعمال گردید." : "Cover set successfully.");
        } else if (res.status === 'no_internet') {
          showToast(translations[currentLang].noInternet, true);
        } else {
          showToast("Error downloading cover.", true);
        }
      }
      handleFieldChange();
    }

    function openDetailModal(index) {
      const item = window.cachedOnlineItems[index];
      if (!item) return;
      currentSelectedDetailItem = item;

      document.getElementById('detailCoverImg').src = item.artwork_url;
      const list = document.getElementById('detailFieldsList');
      list.innerHTML = "";

      const fields = [
        { key: "Title", val: item.title },
        { key: "Artist", val: item.artist },
        { key: "Album", val: item.album },
        { key: "Year", val: item.year },
        { key: "Track", val: item.track },
        { key: "Genre", val: item.genre },
        { key: "Composer", val: item.composer },
        { key: "Copyright", val: item.copyright }
      ];

      fields.forEach(f => {
        if (!f.val) return;
        const row = document.createElement('div');
        row.className = 'detail-field-item';
        row.innerHTML = `
          <div class="field-info">
            <span class="field-title">${f.key}</span>
            <span class="field-val" title="${f.val}">${f.val}</span>
          </div>
          <button class="copy-btn" title="Copy" onclick="copyTextToClipboard('${f.val.replace(/'/g, "\\'")}')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          </button>
        `;
        list.appendChild(row);
      });

      document.getElementById('detailModal').style.display = 'flex';
    }

    function closeDetailModal() {
      document.getElementById('detailModal').style.display = 'none';
    }

    function copyTextToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(translations[currentLang].copied);
      });
    }

    async function copyImageToClipboard() {
      if (!currentSelectedDetailItem) return;
      showToast((currentLang === "fa") ? "در حال کپی تصویر..." : "Copying image...");
      const res = await window.pywebview.api.fetch_image_base64(currentSelectedDetailItem.artwork_url);
      if (res.status === 'success') {
        const copyRes = await window.pywebview.api.copy_image_to_clipboard(res.dataUrl);
        if (copyRes.status === 'success') {
          showToast(translations[currentLang].copied);
        } else {
          showToast("Error copying image: " + (copyRes.message || ""), true);
        }
      } else if (res.status === 'no_internet') {
        showToast(translations[currentLang].noInternet, true);
      }
    }

    async function saveCoverToFile() {
      if (!currentSelectedDetailItem) return;
      showToast((currentLang === "fa") ? "در حال دریافت فایل تصویر..." : "Downloading image...");
      const res = await window.pywebview.api.fetch_image_base64(currentSelectedDetailItem.artwork_url);
      if (res.status === 'success') {
        const saveRes = await window.pywebview.api.save_image_dialog(res.dataUrl, `${currentSelectedDetailItem.artist} - ${currentSelectedDetailItem.title}.jpg`);
        if (saveRes.status === 'success') {
          showToast((currentLang === "fa") ? "تصویر با موفقیت ذخیره شد." : "Image saved successfully.");
        }
      } else if (res.status === 'no_internet') {
        showToast(translations[currentLang].noInternet, true);
      }
    }

    function openLightbox(url) {
      document.getElementById('lightboxImg').src = url;
      document.getElementById('lightboxModal').style.display = 'flex';
    }
    function closeLightbox() {
      document.getElementById('lightboxModal').style.display = 'none';
    }

    async function saveTags() {
      const tags = {
        title: document.getElementById('inputTitle').value.trim(),
        artist: document.getElementById('inputArtist').value.trim(),
        album: document.getElementById('inputAlbum').value.trim(),
        genre: document.getElementById('inputGenre').value.trim(),
        composer: document.getElementById('inputComposer').value.trim(),
        year: document.getElementById('inputYear').value.trim(),
        track: document.getElementById('inputTrack').value.trim(),
        disc: document.getElementById('inputDisc').value.trim(),
        copyright: document.getElementById('inputCopyright').value.trim(),
        comment: document.getElementById('inputComment').value.trim(),
      };

      const btn = document.getElementById('btnSave');
      btn.disabled = true;

      const res = await window.pywebview.api.save_music_tags(currentFilePath, tags, currentCoverDataUrl);

      btn.disabled = false;
      if (res.status === 'success') {
        currentFilePath = res.new_path;
        isModified = false;
        btn.disabled = true;
        showToast(translations[currentLang].savedSuccess);
      } else {
        showToast(res.message, true);
      }
    }

    async function openSettingsModal() {
      const settings = await window.pywebview.api.get_settings();
      document.getElementById('settingOverwrite').checked = settings.overwrite_original;
      document.getElementById('settingPathDisplay').value = settings.custom_output_dir || (currentLang === 'fa' ? "کنار فایل اصلی (پیش‌فرض)" : "Same directory as source");
      document.getElementById('settingLanguage').value = settings.language || "en";
      document.getElementById('settingTheme').value = settings.theme || "system";
      document.getElementById('settingsModal').style.display = 'flex';
    }

    function closeSettingsModal() {
      document.getElementById('settingsModal').style.display = 'none';
    }

    async function browseOutputDir() {
      const path = await window.pywebview.api.select_folder_dialog();
      if (path) {
        document.getElementById('settingPathDisplay').value = path;
      }
    }

    async function saveSettingsModal() {
      const lang = document.getElementById('settingLanguage').value;
      const theme = document.getElementById('settingTheme').value;
      const newSettings = {
        overwrite_original: document.getElementById('settingOverwrite').checked,
        custom_output_dir: (document.getElementById('settingPathDisplay').value.includes("Same") || document.getElementById('settingPathDisplay').value.includes("پیش‌فرض")) ? "" : document.getElementById('settingPathDisplay').value,
        language: lang,
        theme: theme
      };
      await window.pywebview.api.update_settings(newSettings);
      applyLanguage(lang);
      applyTheme(theme);
      closeSettingsModal();
      showToast((lang === 'fa') ? "تنظیمات اعمال و ذخیره شد." : "Settings saved permanently.");
    }

    function openAboutModal() { document.getElementById('aboutModal').style.display = 'flex'; }
    function closeAboutModal() { document.getElementById('aboutModal').style.display = 'none'; }

    // فراخوانی تنظیمات ذخیره شده از دیسک در هنگام شروع
    async function initSavedSettings() {
      try {
        const settings = await window.pywebview.api.get_settings();
        applyLanguage(settings.language || 'en');
        applyTheme(settings.theme || 'system');
      } catch (e) {
        applyLanguage('en');
        applyTheme('system');
      }
    }

    window.addEventListener('pywebviewready', initSavedSettings);
    window.addEventListener('DOMContentLoaded', () => {
      setTimeout(initSavedSettings, 200);
    });
  </script>
</body>
</html>
""".replace("__APP_NAME__", APP_NAME)\
   .replace("__APP_VERSION__", APP_VERSION)\
   .replace("__APP_TITLE__", f"{APP_NAME} {APP_VERSION}")\
   .replace("__EMBEDDED_FONT_CSS__", get_embedded_font_css())

def main():
    api = MusicTaggerAPI()
    window = webview.create_window(
        title=f"{APP_NAME} {APP_VERSION}",
        html=UI_HTML,
        js_api=api,
        width=1320,
        height=920,
        min_size=(1040, 760),
        background_color='#f8f9fa'
    )
    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()
