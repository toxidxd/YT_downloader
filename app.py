import os
import subprocess
import threading
import uuid
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Хранилище активных загрузок: {job_id: {"url": ..., "status": ..., "file": ...}}
active_downloads = {}

def download_video(job_id, url, resolution="best"):
    job = active_downloads[job_id]
    job["status"] = "downloading"

    # Формируем аргументы для yt-dlp
    # bestvideo+bestaudio/best — хорошее качество, потом объединение через ffmpeg
    if resolution == "best":
        format_opt = "bestvideo+bestaudio/best"
    else:
        # Пример для конкретного разрешения: 1080p и т.д.
        format_opt = f"bestvideo[height<={resolution}]+bestaudio/bestvideo[height={resolution}]+bestaudio/best"

    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}-%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", format_opt,
        "--merge-output-format", "mp4",
        "-o", output_template,
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # Ищем скачанный файл (yt-dlp подставит имя вместо %(title)s)
            files = os.listdir(DOWNLOAD_DIR)
            found_file = None
            for f in files:
                if f.startswith(job_id):
                    found_file = os.path.join(DOWNLOAD_DIR, f)
                    break
            if found_file:
                job["file"] = found_file
                job["status"] = "done"
            else:
                job["status"] = "error"
                job["error"] = "Файл не найден после скачивания"
        else:
            job["status"] = "error"
            job["error"] = result.stderr or "Неизвестная ошибка yt-dlp"
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
    active_downloads[job_id] = {"url": url, "status": "pending", "file": None, "error": None}

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
