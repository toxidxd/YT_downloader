import os
import subprocess
import threading
import uuid
import re
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Хранилище задач: {job_id: {url, status, file, error, progress_pct, progress_text, title, duration, filesize}}
active_downloads = {}

def parse_yt_dlp_output(line: str, job):
    """Извлекает прогресс, название, длительность и размер из логов yt-dlp."""
    # Прогресс: [download]  45.3% of 123.45MiB
    m = re.search(r"\[download\]\s*([0-9.]+)% of ([0-9.,]+[KMGT]?i?B)", line)
    if m:
        pct = float(m.group(1))
        size_str = m.group(2)
        job["progress_pct"] = min(100.0, pct)
        job["progress_text"] = f"{pct:.1f}% ({size_str})"
        return

    # Название видео
    m_title = re.search(r"Destination:\s*(.+)\.[^.]+$", line)
    if m_title:
        job["title"] = m_title.group(1)
        return

    # Длительность и размер (в метаданных)
    m_meta = re.search(r"Duration:\s*(\d+:\d+:\d+)", line)
    if m_meta:
        job["duration"] = m_meta.group(1)
        return
    m_size = re.search(r"filesize:\s*([0-9.,]+[KMGT]?i?B)", line)
    if m_size:
        job["filesize"] = m_size.group(1)
        return

def download_video(job_id, url, resolution="best"):
    job = active_downloads[job_id]
    job["status"] = "downloading"

    if resolution == "best":
        format_opt = "bestvideo+bestaudio/best"
    else:
        format_opt = f"bestvideo[height<={resolution}]+bestaudio/bestvideo[height={resolution}]+bestaudio/best"

    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}-%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", format_opt,
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-warnings",
        url
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in proc.stdout:
            parse_yt_dlp_output(line, job)
            # Можно добавить логирование, если нужно

        proc.wait()

        if proc.returncode == 0:
            files = os.listdir(DOWNLOAD_DIR)
            found_file = None
            for f in files:
                if f.startswith(job_id):
                    found_file = os.path.join(DOWNLOAD_DIR, f)
                    break
            if found_file:
                job["file"] = found_file
                job["status"] = "done"
                job["progress_pct"] = 100.0
            else:
                job["status"] = "error"
                job["error"] = "Файл не найден после скачивания"
        else:
            job["status"] = "error"
            job["error"] = f"Ошибка yt-dlp (код {proc.returncode})"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def start_download():
    data = request.json or request.form
    url = data.get("url")
    resolution = data.get("resolution", "best")

    if not url:
        return jsonify({"error": "URL не указан"}), 400

    job_id = str(uuid.uuid4())
    active_downloads[job_id] = {
        "url": url,
        "status": "pending",
        "file": None,
        "error": None,
        "progress_pct": 0.0,
        "progress_text": "",
        "title": None,
        "duration": None,
        "filesize": None
    }

    thread = threading.Thread(target=download_video, args=(job_id, url, resolution))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    job = active_downloads.get(job_id)
    if not job:
        return jsonify({"error": "Задача не найдена"}), 404
    return jsonify(job)

@app.route("/download-file/<job_id>", methods=["GET"])
def download_file(job_id):
    job = active_downloads.get(job_id)
    if not job or job["status"] != "done" or not job.get("file"):
        return jsonify({"error": "Файл ещё не готов или не найден"}), 404
    return send_file(job["file"], as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
