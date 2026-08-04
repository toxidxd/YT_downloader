from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os
import uuid
from datetime import datetime
import subprocess
import json

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

    # Удаляем служебные строки
    filename = filename.replace('[HD]', '').replace('[SD]', '')
    filename = filename.replace('[480p]', '').replace('[360p]', '')

    return filename[:150]  # Ограничение длины


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
        # Получаем информацию о видео с yt-dlp
        result = subprocess.run([
            'yt-dlp', '-J', '--dump-json', url
        ], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            error_msg = result.stderr[:200] if result.stderr else "Неизвестная ошибка"

            if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'error': 'Видео не найдено или было удалено с YouTube.'
                }), 404
            else:
                return jsonify({
                    'success': False,
                    'error': f'Ошибка при анализе видео: {error_msg}'
                }), 503

        video_info = json.loads(result.stdout)

        # Получаем метаданные
        title = sanitize_filename(video_info.get('title', 'downloaded'))
        thumbnail_url = video_info.get('thumbnail')
        duration = video_info.get('duration', 0)

        # Ищем лучшее видео (не только аудио)
        formats = video_info.get('formats', [])

        if not formats:
            return jsonify({
                'success': False,
                'error': 'Не удалось найти доступные форматы видео.'
            }), 500

        # Пытаемся найти лучшее видео с аудио
        best_format = None
        for fmt in sorted(formats, key=lambda x: int(x.get('vcodec') or 0), reverse=True):
            if fmt.get('acodec') and 'none' not in str(fmt.get('vcodec', '')):
                best_format = fmt
                break

        # Если не нашли комбинированный формат, ищем видео + отдельно аудио
        if not best_format or best_format.get('vcodec') == 'none':
            for fmt in sorted(formats, key=lambda x: int(x.get('vcodec') or 0), reverse=True):
                if fmt.get('vcodec') and fmt.get('vcodec') != 'none':
                    best_format = fmt

        # Если всё равно не нашли видео, берём лучшее доступное
        if not best_format:
            best_format = sorted(formats, key=lambda x: int(x.get('tsize') or 0), reverse=True)[0]

        # Формируем путь к файлу
        file_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{title}_{timestamp}.{best_format.get('extension', 'mp4')}"

        filepath = os.path.join(DOWNLOAD_FOLDER, file_id + '_' + filename)

        # Скачиваем видео через yt-dlp
        cmd = [
            'yt-dlp',
            '-o', filepath,
            '--no-playlist'  # Скачиваем только один видео, а не плейлист
        ]

        if best_format.get('acodec') == 'none':  # Только видео без звука
            cmd.append('-S')
            cmd.append('resolution')
            cmd.append('ext:')

        result = subprocess.run(
            cmd + [url],
            capture_output=True,
            text=True,
            timeout=720  # Максимум 12 минут
        )

        if result.returncode != 0:
            error_msg = result.stderr[:300]

            if 'already downloaded' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'error': 'Это видео уже скачано ранее.'
                })

            if 'unavailable' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'error': 'Видео недоступно в вашем регионе или YouTube.'
                }), 403

            if 'login required' in error_msg.lower() or 'sign in' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'error': 'Требуется вход в аккаунт (private video).'
                })

            return jsonify({
                'success': False,
                'error': f'Ошибка при загрузке: {error_msg}'
            }), 503

        # Проверяем, что файл был создан
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'Не удалось создать файл. Попробуйте позже.'
            }), 500

        return jsonify({
            'success': True,
            'title': video_info.get('title', title),
            'thumbnail': thumbnail_url,
            'download_url': f'/files/{file_id}_{filename}',
            'duration': duration
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Загрузка занимает слишком много времени. Видео может быть очень большим.'
        }), 504

    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Команда yt-dlp не найдена! Установите её с pip install yt-dlp'
        }), 500

    except Exception as e:
        error_msg = str(e)[:200]  # Обрезаем длинное сообщение об ошибке

        if 'SSL' in str(type(e)) or 'ssl' in str(error_msg).lower():
            return jsonify({
                'success': False,
                'error': 'Ошибка подключения. Убедитесь, что SSL-сертификаты обновлены.'
            }), 503
        # elif '404' in error_msg:
        #     return jsonify({
        #         'success': False,
        #         'error': 'Видео не найдено или было удалено с YouTube.'
        #     }), 404
        else:
            return jsonify({
                'success': False,
                'error': f'Неизвестная ошибка: {error_msg}'
            }), 500


@app.route('/files/<path:filepath>')
def serve_file(filepath):
    """Служба для доступа к скачанным файлам."""
    filepath = os.path.join(DOWNLOAD_FOLDER, filepath)
    # from flask import send_from_directory
    return send_from_directory(DOWNLOAD_FOLDER, filepath)


@app.route('/api/history', methods=['GET'])
def get_history():
    """Получить историю загрузки (список скачанных видео за 24 часа)."""
    history = []
    try:
        for filename in os.listdir(DOWNLOAD_FOLDER):
            if not filename.startswith('.'):
                # Получаем дату из имени файла
                timestamp_parts = filename.split('_')
                if len(timestamp_parts) > 1:
                    timestamp_str = timestamp_parts[1][:8]  # YYYYMMDD

                    try:
                        download_time = datetime.strptime(timestamp_str, '%Y%m%d').replace(
                            hour=12, minute=0, second=0)

                        if (datetime.now() - download_time).total_seconds() < 86400:
                            history.append(filename)
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Ошибка при чтении истории: {e}")

    return jsonify({'success': True, 'files': history})

@app.route('/api/installed', methods=['GET'])
def check_installed():
    """Проверить установлен ли yt-dlp."""
    try:
        result = subprocess.run(
            ['yt-dlp', '--version'],
            capture_output=True, text=True, timeout=10
        )
        return jsonify({
            'success': True,
            'version': result.stdout.strip()
        })
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'yt-dlp не установлен. Установите его через pip install yt-dlp'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка проверки: {str(e)[:100]}'
        }), 500


if __name__ == '__main__':
    # Создаем директорию для загрузок при первом запуске
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    app.run(debug=True, port=5000, host='127.0.0.1')
