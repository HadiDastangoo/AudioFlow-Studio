import os
import sys
import json
import html
import base64
import shutil
import subprocess
import socket
import webbrowser
import requests
from io import BytesIO
from PIL import Image
import webview
import imageio_ffmpeg
from mutagen.id3 import (
    ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK, TCON, TCOM, TPOS, TCOP, COMM,
    TPUB, TMOO, USLT, TBPM, TOPE, TSRC, error
)
from mutagen.mp3 import MP3

# ----------------- Global Variables -----------------
APP_NAME = "AudioFlow Studio"
APP_VERSION = "v1.3.0"
GITHUB_REPO = "HadiDastangoo/AudioFlow-Studio"
# --------------------------------------------------------

APIC_TYPES = {
    3: "Front Cover (Main)",
    4: "Back Cover",
    7: "Lead Artist / Performer",
    11: "Composer",
    9: "Band / Orchestra",
    12: "Lyricist",
    15: "Recording Location",
    14: "Illustration",
    19: "Artist Logo",
    20: "Publisher / Studio Logo"
}

def get_resource_path(relative_path):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, relative_path)

class MusicTaggerAPI:
    def __init__(self):
        self._window = None
        self.current_file_path = None
        self.initial_tags = {}
        self.initial_covers = []
        
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
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception:
                pass

    def save_settings_to_disk(self):
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

    def open_external_url(self, url):
        try:
            webbrowser.open(url)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_clipboard_text(self):
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            text = ""
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return {"status": "success", "text": text}
        except Exception:
            try:
                ps_cmd = 'powershell -Command "Get-Clipboard"'
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, creationflags=creationflags)
                return {"status": "success", "text": res.stdout.rstrip("\r\n")}
            except Exception as e:
                return {"status": "error", "text": "", "message": str(e)}

    def copy_text_to_clipboard(self, text):
        if text is None:
            return {"status": "error", "message": "Text is None"}
        try:
            normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, normalized)
            win32clipboard.CloseClipboard()
            return {"status": "success"}
        except ImportError:
            try:
                b64_bytes = base64.b64encode(normalized.encode('utf-8')).decode('ascii')
                ps_cmd = f'powershell -Command "[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String(\'{b64_bytes}\')) | Set-Clipboard"'
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(ps_cmd, shell=True, creationflags=creationflags)
                return {"status": "success"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_for_updates(self):
        if not self.is_online():
            return {"status": "no_internet"}

        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {"User-Agent": "AudioFlowStudio"}
            resp = requests.get(api_url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "").strip()
                html_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
                
                download_url = html_url
                file_size_str = ""
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".exe"):
                        download_url = asset.get("browser_download_url", html_url)
                        size_bytes = asset.get("size", 0)
                        if size_bytes > 0:
                            file_size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                        break

                current_clean = APP_VERSION.lower().replace("v.", "").replace("v", "").strip()
                latest_clean = latest_tag.lower().replace("v.", "").replace("v", "").strip()

                def parse_ver(v_str):
                    parts = []
                    for seg in v_str.split("."):
                        try:
                            parts.append(int(seg))
                        except ValueError:
                            parts.append(0)
                    return parts

                has_update = parse_ver(latest_clean) > parse_ver(current_clean)

                return {
                    "status": "success",
                    "has_update": has_update,
                    "latest_version": latest_tag or f"v{latest_clean}",
                    "current_version": APP_VERSION,
                    "download_url": download_url,
                    "file_size": file_size_str,
                    "release_notes": data.get("body", "")
                }
            return {"status": "error"}
        except Exception:
            return {"status": "error"}

    def select_file_dialog(self):
        dialog_type = getattr(webview.FileDialog, 'OPEN', webview.OPEN_DIALOG)
        result = self._window.create_file_dialog(
            dialog_type,
            allow_multiple=False,
            file_types=('Media Files (*.mp4;*.mp3;*.m4a;*.wav;*.mkv;*.flv;*.aac;*.flac)', 'All Files (*.*)')
        )
        if result and len(result) > 0:
            return self.process_selected_file(result[0])
        return None

    def select_folder_dialog(self):
        dialog_type = getattr(webview.FileDialog, 'FOLDER', webview.FOLDER_DIALOG)
        result = self._window.create_file_dialog(dialog_type)
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
        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "message": "File not found."}

        ext = os.path.splitext(file_path)[1].lower()
        self.current_file_path = file_path
        filename = os.path.basename(file_path)

        if ext == ".mp3":
            tags_data, covers_data = self._read_full_mp3_data(file_path)
            self.initial_tags = dict(tags_data)
            self.initial_covers = list(covers_data)
            audio_base64 = self._get_audio_data_url(file_path)
            return {
                "status": "ready_mp3",
                "file_path": file_path,
                "filename": filename,
                "tags": tags_data,
                "covers": covers_data,
                "audio_data": audio_base64
            }
        else:
            return {
                "status": "needs_conversion",
                "file_path": file_path,
                "filename": filename
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
            tags_data, covers_data = self._read_full_mp3_data(output_path)
            self.initial_tags = dict(tags_data)
            self.initial_covers = list(covers_data)
            audio_base64 = self._get_audio_data_url(output_path)

            return {
                "status": "success",
                "file_path": output_path,
                "filename": os.path.basename(output_path),
                "tags": tags_data,
                "covers": covers_data,
                "audio_data": audio_base64
            }
        except Exception as e:
            return {"status": "error", "message": f"Error converting file: {str(e)}"}

    def get_app_info(self):
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "repo_url": f"https://github.com/{GITHUB_REPO}"
        }

    def _get_audio_data_url(self, file_path):
        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            return f"data:audio/mp3;base64,{encoded}"
        except Exception:
            return ""

    def _read_full_mp3_data(self, file_path):
        tags_data = {
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
            "publisher": "",
            "mood": "",
            "lyrics": "",
            "bpm": "",
            "original_artist": "",
            "isrc": ""
        }
        covers_data = []

        try:
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                tags = audio.tags
                if 'TIT2' in tags: tags_data["title"] = str(tags['TIT2'].text[0])
                if 'TPE1' in tags: tags_data["artist"] = str(tags['TPE1'].text[0])
                if 'TALB' in tags: tags_data["album"] = str(tags['TALB'].text[0])
                if 'TDRC' in tags: tags_data["year"] = str(tags['TDRC'].text[0])
                if 'TRCK' in tags: tags_data["track"] = str(tags['TRCK'].text[0])
                if 'TCON' in tags: tags_data["genre"] = str(tags['TCON'].text[0])
                if 'TCOM' in tags: tags_data["composer"] = str(tags['TCOM'].text[0])
                if 'TPOS' in tags: tags_data["disc"] = str(tags['TPOS'].text[0])
                if 'TCOP' in tags: tags_data["copyright"] = str(tags['TCOP'].text[0])

                if 'TPUB' in tags: tags_data["publisher"] = str(tags['TPUB'].text[0])
                if 'TMOO' in tags: tags_data["mood"] = str(tags['TMOO'].text[0])
                if 'TBPM' in tags: tags_data["bpm"] = str(tags['TBPM'].text[0])
                if 'TOPE' in tags: tags_data["original_artist"] = str(tags['TOPE'].text[0])
                if 'TSRC' in tags: tags_data["isrc"] = str(tags['TSRC'].text[0])

                for key in tags.keys():
                    if key.startswith('COMM'):
                        tags_data["comment"] = str(tags[key].text[0])
                        break

                for key in tags.keys():
                    if key.startswith('USLT'):
                        tags_data["lyrics"] = str(tags[key].text)
                        break

                for key, tag in tags.items():
                    if isinstance(tag, APIC):
                        encoded = base64.b64encode(tag.data).decode('utf-8')
                        pic_type = tag.type if hasattr(tag, 'type') else 3
                        type_name = APIC_TYPES.get(pic_type, f"Type {pic_type}")
                        covers_data.append({
                            "type": pic_type,
                            "type_name": type_name,
                            "mime": tag.mime,
                            "desc": tag.desc or type_name,
                            "dataUrl": f"data:{tag.mime};base64,{encoded}"
                        })

                covers_data.sort(key=lambda c: (0 if c["type"] == 3 else 1, c["type"]))

        except Exception:
            pass

        return tags_data, covers_data

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

    def fetch_lyrics(self, title, artist):
        if not self.is_online():
            return {"status": "no_internet"}

        headers = {'User-Agent': 'AudioFlowStudio/1.2 (https://github.com)'}
        try:
            get_url = f"https://lrclib.net/api/get?track_name={requests.utils.quote(title)}&artist_name={requests.utils.quote(artist)}"
            resp = requests.get(get_url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
                if lyrics:
                    return {"status": "success", "lyrics": lyrics}

            search_url = f"https://lrclib.net/api/search?q={requests.utils.quote(f'{artist} {title}')}"
            resp_search = requests.get(search_url, headers=headers, timeout=6)
            if resp_search.status_code == 200:
                items = resp_search.json()
                if items and isinstance(items, list) and len(items) > 0:
                    for it in items:
                        lyrics = it.get("plainLyrics") or it.get("syncedLyrics")
                        if lyrics:
                            return {"status": "success", "lyrics": lyrics}

            return {"status": "not_found"}
        except requests.exceptions.RequestException:
            return {"status": "no_internet"}
        except Exception:
            return {"status": "not_found"}

    def translate_lyrics(self, lyrics_text, target_lang="fa"):
        if not self.is_online():
            return {"status": "no_internet"}
        if not lyrics_text or not lyrics_text.strip():
            return {"status": "empty"}

        try:
            lines = lyrics_text.splitlines()
            only_translated = []
            combined_lines = []

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            chunks = []
            current_chunk = []
            current_len = 0

            for line in lines:
                l_strip = line.strip()
                add_len = len(l_strip) + 1
                if current_chunk and (current_len + add_len > 350):
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [l_strip]
                    current_len = add_len
                else:
                    current_chunk.append(l_strip)
                    current_len += add_len

            if current_chunk:
                chunks.append("\n".join(current_chunk))

            all_translated_lines = []

            for ch in chunks:
                if not ch.strip():
                    all_translated_lines.extend([""] * len(ch.splitlines()))
                    continue

                encoded_q = requests.utils.quote(ch)
                url = f"https://api.mymemory.translated.net/get?q={encoded_q}&langpair=autodetect|{target_lang}"
                r = requests.get(url, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    res_data = r.json()
                    raw_text = res_data.get("responseData", {}).get("translatedText", "")
                    
                    if raw_text:
                        cleaned = html.unescape(raw_text)
                        cleaned = cleaned.replace("&#10;", "\n").replace("&#13;", "").replace("&amp;#10;", "\n")
                        all_translated_lines.extend(cleaned.splitlines())
                    else:
                        all_translated_lines.extend(ch.splitlines())
                else:
                    all_translated_lines.extend(ch.splitlines())

            for idx, orig_line in enumerate(lines):
                orig_s = orig_line.strip()
                if not orig_s:
                    only_translated.append("")
                    combined_lines.append("")
                else:
                    t_line = all_translated_lines[idx].strip() if idx < len(all_translated_lines) and all_translated_lines[idx].strip() else orig_s
                    only_translated.append(t_line)
                    combined_lines.append(orig_s)
                    combined_lines.append(t_line)
                    combined_lines.append("")

            return {
                "status": "success",
                "translated_text": "\n".join(only_translated).strip(),
                "combined_text": "\n".join(combined_lines).strip()
            }
        except requests.exceptions.RequestException:
            return {"status": "no_internet"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

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

    def save_music_tags(self, file_path, tags, covers_list=None):
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

            id3_audio.delall('TPUB'); id3_audio.add(TPUB(encoding=3, text=tags.get("publisher", "")))
            id3_audio.delall('TMOO'); id3_audio.add(TMOO(encoding=3, text=tags.get("mood", "")))
            id3_audio.delall('TBPM'); id3_audio.add(TBPM(encoding=3, text=tags.get("bpm", "")))
            id3_audio.delall('TOPE'); id3_audio.add(TOPE(encoding=3, text=tags.get("original_artist", "")))
            id3_audio.delall('TSRC'); id3_audio.add(TSRC(encoding=3, text=tags.get("isrc", "")))
            
            lyrics_text = tags.get("lyrics", "")
            id3_audio.delall('USLT')
            if lyrics_text:
                id3_audio.add(USLT(encoding=3, lang='eng', desc='', text=lyrics_text))

            id3_audio.delall('APIC')
            if covers_list and isinstance(covers_list, list):
                for cov in covers_list:
                    raw_data_url = cov.get("dataUrl", "")
                    if raw_data_url and "," in raw_data_url:
                        header, base64_data = raw_data_url.split(",", 1)
                        mime = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
                        img_bytes = base64.b64decode(base64_data)
                        p_type = int(cov.get("type", 3))
                        desc = cov.get("desc") or APIC_TYPES.get(p_type, "Cover")
                        id3_audio.add(
                            APIC(
                                encoding=3,
                                mime=mime,
                                type=p_type,
                                desc=desc,
                                data=img_bytes
                            )
                        )

            id3_audio.save(target_path, v2_version=3)
            self.current_file_path = target_path
            self.initial_tags = dict(tags)
            self.initial_covers = list(covers_list or [])

            return {"status": "success", "new_path": target_path, "filename": os.path.basename(target_path)}
        except Exception as e:
            return {"status": "error", "message": f"Error saving: {str(e)}"}

def main():
    api = MusicTaggerAPI()
    html_entry_point = get_resource_path(os.path.join("gui", "index.html"))

    window = webview.create_window(
        title=f"{APP_NAME} {APP_VERSION}",
        url=html_entry_point,
        js_api=api,
        width=1340,
        height=940,
        min_size=(1060, 780),
        background_color='#f8f9fa'
    )
    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()
