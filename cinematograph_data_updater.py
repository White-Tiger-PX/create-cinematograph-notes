import os
import time
import json
import ctypes
import logging
import requests
import webbrowser

from datetime import datetime, timedelta

import config

class ApiError(Exception):
    pass


def save_json(data, file_path):
    try:
        file_path = os.path.normpath(file_path)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as err:
        logger.error("Ошибка при сохранении JSON в %s: %s", file_path, err)


def load_json(file_path, default_type):
    try:
        file_path = os.path.normpath(file_path)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            return data
    except Exception as err:
        logger.error("Ошибка при загрузке JSON из %s: %s", file_path, err)

    return default_type


def updating_unknown_object(cinematograph_title, api_key):
    try:
        headers = {"X-API-KEY": api_key}
        response = requests.get(
            'https://api.kinopoisk.dev/v1.4/movie/search',
            params={"query": cinematograph_title, "limit": 10, "page": 1},
            headers=headers,
            timeout=20
        )

        if response.status_code == 200:
            movies = response.json()

            return movies.get('docs', [])
        else:
            logger.error("API Error %s: %s", response.status_code, response.text)

    except Exception as err:
        logger.error("Ошибка при поиске данных для %s: %s", cinematograph_title, err)

    return []


def updating_known_object(old_cinematograph_data, api_key, kp_id):
    try:
        headers = {"X-API-KEY": api_key}
        response = requests.get(
            f'https://api.kinopoisk.dev/v1.4/movie/{kp_id}',
            headers=headers,
            timeout=20
        )

        if response.status_code == 200:
            current_cinematograph_data = response.json()
            current_cinematograph_data['date_update'] = datetime.now().strftime('%Y-%m-%d')

            return current_cinematograph_data
        else:
            logger.error("API Error %s: %s", response.status_code, response.text)

    except Exception as err:
        logger.error("Ошибка при обновлении данных для %s: %s", kp_id, err)

    return old_cinematograph_data


def updating_object_images(cinematograph_data, api_key, kp_id):
    try:
        headers = {"X-API-KEY": api_key}
        all_images = []
        page = 1

        while True:
            response = requests.get(
                'https://api.kinopoisk.dev/v1.4/image',
                headers=headers,
                params={'movieId': kp_id, 'page': page, 'limit': 50, 'type': 'still'},
                timeout=20
            )

            if response.status_code != 200:
                logger.error("API Error %s: %s", response.status_code, response.text)
                break

            data = response.json()
            all_images.extend(data.get('docs', []))

            if page >= data.get('pages', 0):
                break

            page += 1

        cinematograph_data['images'] = all_images
        cinematograph_data['date_image_update'] = datetime.now().strftime('%Y-%m-%d')

        return cinematograph_data

    except Exception as err:
        logger.error("Ошибка при обновлении изображений для %s: %s", kp_id, err)

    return cinematograph_data


def show_message_box(title, message):
    MB_OKCANCEL = 0x1

    return ctypes.windll.user32.MessageBoxW(None, message, title, MB_OKCANCEL)

def update_cinematograph_json(cinematograph_experience, cinematograph_data, json_data_path, update_threshold, api_key):
    try:
        if not cinematograph_experience:
            return

        all_titles = cinematograph_experience['Movies'] | cinematograph_experience['Series']
        unknown_cinematograph_titles = [key for key in all_titles if key not in cinematograph_data]
        update_threshold = datetime.now() - timedelta(days=update_threshold)

        for title, data in cinematograph_data.items():
            try:
                update_date = datetime.strptime(data['date_update'], '%Y-%m-%d')

                if update_date < update_threshold:
                    if 'id' in data:
                        kp_id = data['id']
                        data = updating_known_object(data, api_key, kp_id)
                        data = updating_object_images(data, api_key, kp_id)
                        cinematograph_data[title] = data
                    else:
                        unknown_cinematograph_titles.append(title)

                    time.sleep(5)
            except Exception as err:
                logger.error("Ошибка при обновлении данных для %s: %s", title, err)

        for title in unknown_cinematograph_titles:
            try:
                new_data = updating_unknown_object(title, api_key)

                for new_info in new_data:
                    webbrowser.open(f"https://www.kinopoisk.ru/film/{new_info['id']}")
                    user_choice = show_message_box("Обновление данных", "Это подходящая страница для: %s?" % title)

                    if user_choice == 1:
                        new_info = updating_object_images(new_info, api_key, new_info['id'])
                        new_info['date_update'] = datetime.now().strftime('%Y-%m-%d')
                        cinematograph_data[title] = new_info
                        break
            except Exception as err:
                logger.error("Ошибка при обновлении данных для неизвестного объекта %s: %s", title, err)

        save_json(cinematograph_data, json_data_path)

    except Exception as err:
        logger.error("Ошибка в функции update_cinematograph_json: %s", err)


def main():
    try:
        if not os.path.exists(config.json_experience):
            save_json({'Movies': {}, 'Series': {}}, config.json_experience)

        if not os.path.exists(config.json_data_path):
            save_json({}, config.json_data_path)

        update_cinematograph_json(
            cinematograph_experience=load_json(config.json_experience, {}),
            cinematograph_data=load_json(config.json_data_path, {}),
            json_data_path=config.json_data_path,
            update_threshold=config.update_threshold,
            api_key=config.api_key
        )
    except Exception as err:
        logger.error("Ошибка в функции main: %s", err)


def set_logger(log_folder):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if log_folder:  # Создание файла с логами только если указана папка
        log_filename = datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')
        log_folder = os.path.join(log_folder, 'cinematograph_data_updater')
        log_file_path = os.path.join(log_folder, log_filename)

        os.makedirs(log_folder, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = set_logger(config.log_folder)

if __name__ == "__main__":
    main()