from flask import Flask, render_template, request, jsonify, redirect, url_for
from pytube import YouTube
import os
import uuid
from datetime import datetime

app = Flask(__name__)

# Настройки для хранения загрузочных задач
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


def sanitize_filename(filename):
    """Удаляет недопустимые символы из имени файла."""
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename


@app.route('/', methods=['GET'])
def index():
    """Главная страница с формой загрузки."""
    return render_template('index.html')


@app.route('/api/download', methods=['POST'])
def download_video():
    """Обработчик API для загрузки видео."""
    url = request.json.get('url', '').strip()

    if not url:
        return jsonify({
            'success': False,
            'error': 'URL видео не указан'
        }), 400

    try:
        yt = YouTube(url)
        title = sanitize_filename(yt.title)[:100]

        # Получаем доступные потоки (по умолчанию HD качество)
        streams = yt.streams.filter(only_audio=True).order_by('bitrate').desc()

        # Формируем путь к файлу
        file_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = yt.title.replace('[HD]', '').replace('[SD]', '')
        safe_title = sanitize_filename(original_filename)[:100]

        filename = f"{safe_title}_{timestamp}.{yt.extension}"
        filepath = os.path.join(DOWNLOAD_FOLDER, file_id + '_' + filename)

        # Скачиваем видео (автоматически выбираем лучшее аудио качество)
        stream = next((s for s in streams if 'worst' not in str(s)), yt.streams.get_highest_resolution())
        stream.download(output_path=DOWNLOAD_FOLDER)

        return jsonify({
            'success': True,
            'title': yt.title,
            'thumbnail': yt.thumbnail_url,
            'download_url': f'/files/{file_id}_{filename}',
            'duration': yt.duration
        })

    except Exception as e:
        error_msg = str(e)[:200]  # Обрезаем длинное сообщение об ошибке

        if 'SSL' in str(type(e)) or 'ssl' in str(error_msg).lower():
            return jsonify({
                'success': False,
                'error': 'Ошибка подключения. Убедитесь, что SSL-сертификаты обновлены.'
            }), 503
        elif '404' in error_msg:
            return jsonify({
                'success': False,
                'error': 'Видео не найдено или было удалено с YouTube.'
            }), 404
        else:
            return jsonify({
                'success': False,
                'error': f'Ошибка при загрузке: {error_msg}'
            }), 500


@app.route('/files/<path:filepath>')
def serve_file(filepath):
    """Служба для доступа к скачанным файлам."""
    filepath = os.path.join(DOWNLOAD_FOLDER, filepath)
    from flask import send_from_directory
    return send_from_directory(DOWNLOAD_FOLDER, filepath)


@app.route('/api/history', methods=['GET'])
def get_history():
    """Получить историю загрузки (список скачанных видео за 24 часа)."""
    history = []
    for filename in os.listdir(DOWNLOAD_FOLDER):
        if not filename.startswith('.'):
            timestamp_str = str(filename.split('_')[1])[:8]  # Получаем дату YYYYMMDD
            download_time = datetime.strptime(timestamp_str, '%Y%m%d').replace(
                hour=12, minute=0, second=0)

            if (datetime.now() - download_time).total_seconds() < 86400:
                history.append(filename)

    return jsonify({'success': True, 'files': history})


if __name__ == '__main__':
    # Создаем директорию для загрузок при первом запуске
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    app.run(debug=True, port=5000, host='127.0.0.1')
