import os
import time
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_from_directory, session
)
import yt_dlp

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB default

# Создаем папку для загрузок при старте
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def is_valid_youtube_url(url: str) -> bool:
    """Простая проверка URL перед отправкой в yt-dlp."""
    parsed = urlparse(url)
    return all([parsed.scheme in ["http", "https"], "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc])


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form.get('video_url')

        if not video_url:
            flash('Введите ссылку на видео.', 'error')
            return redirect(url_for('index'))

        if not is_valid_youtube_url(video_url):
            flash('Некорректная ссылка на YouTube.', 'error')
            return redirect(url_for('index'))

        # Инициализируем сессию пользователя для истории
        if 'history' not in session:
            session['history'] = []

        try:
            # Опции yt-dlp. Формат best — лучшее доступное качество.
            # В outtmpl можно добавить %(uploader)s или другие поля метаданных.
            ydl_opts = {
                'format': 'best',
                'outtmpl': f"{app.config['UPLOAD_FOLDER']}/%(title)s.%(ext)s",
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)
                title = info_dict.get('title', 'unknown_video')

                # Скачивание файла
                ydl.download([video_url])

            filename = f"{title}.mp4"

            # Проверка реального расширения скачанного файла
            for file in os.listdir(app.config['UPLOAD_FOLDER']):
                if file.startswith(title):
                    filename = file
                    break

            # Запись в историю (сохраняем только последние 20 записей)
            entry = {
                'title': title,
                'filename': filename,
                'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
            session['history'].insert(0, entry)
            if len(session['history']) > 20:
                session['history'] = session['history'][:20]
            session.modified = True

            flash(f'Видео "{title}" успешно загружено!', 'success')
            return redirect(url_for('serve_file', filename=filename))

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if 'Private video' in error_msg or 'Sign in' in error_msg:
                message = 'Это приватное видео или требуется авторизация.'
            elif 'unavailable' in error_msg.lower() or 'not found' in error_msg.lower():
                message = 'Видео недоступно или удалено.'
            else:
                message = f'Ошибка скачивания: {e}'
            flash(message, 'error')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Произошла непредвиденная ошибка: {str(e)}', 'error')
            return redirect(url_for('index'))

    return render_template('index.html')


@app.route('/history')
def history():
    return render_template('history.html', items=session.get('history', []))


@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/clear_history', methods=['POST'])
def clear_history():
    session.pop('history', None)
    flash('История очищена.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
