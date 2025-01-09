import os
import time
import ctypes
import requests
import webbrowser

from datetime import datetime, timedelta

import config

from set_logger import set_logger
from utils_json import load_json, save_json


class ApiError(Exception):
    pass


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
            docs = movies.get('docs', [])

            return docs
        else:
            logger.error("API Error %s: %s", response.status_code, response.text)
            raise ApiError(response.text)
    except ApiError as err:
        raise ApiError(err)
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

            raise ApiError(response.text)
    except ApiError as err:
        raise ApiError(err)
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
    api_available = True
    need_search_by_api = False

    try:
        if not cinematograph_experience:
            logger.warning("Нет данных о киноопыте для обновления.")
            return

        all_titles = cinematograph_experience.keys()
        update_threshold = datetime.now() - timedelta(days=update_threshold)

        for title in all_titles:
            try:
                kp_id = cinematograph_experience[title].get('kp_id')

                if kp_id:
                    if kp_id in cinematograph_data:
                        data = cinematograph_data[kp_id]

                        try:
                            update_date = datetime.strptime(data['date_update'], '%Y-%m-%d')
                        except ValueError:
                            logger.error("Неверный формат даты для %s: %s. Обновляем данные.", title, data['date_update'])
                            update_date = datetime(1970, 1, 1)  # Устанавливаем дату по умолчанию для некорректных значений

                        if update_date < update_threshold and api_available:
                            logger.info("Данные для %s устарели. Обновляем данные...", title)
                            data = updating_known_object(data, api_key, kp_id)
                            data = updating_object_images(data, api_key, kp_id)
                            cinematograph_data[kp_id] = data
                    else:
                        need_search_by_api = True
                else:
                    need_search_by_api = True

                if need_search_by_api and api_available:
                    need_search_by_api = False

                    logger.info("ID не найдено для %s, ищем название через API...", title)
                    new_data = updating_unknown_object(title, api_key)

                    for new_info in new_data:
                        webbrowser.open(f"https://www.kinopoisk.ru/film//{new_info['id']}")
                        time.sleep(2)
                        user_choice = show_message_box("Обновление данных", f"Это подходящая страница для: {title}")

                        if user_choice == 1:
                            new_info = updating_object_images(new_info, api_key, new_info['id'])
                            new_info['date_update'] = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                            cinematograph_data[new_info['id']] = new_info
                            cinematograph_experience[title]['kp_id'] = new_info['id']
                            logger.info("Данные для %s обновлены и сохранены в cinematograph_experience.", title)
                            break
            except ApiError:
                api_available = False
            except Exception as err:
                logger.error("Ошибка при обновлении данных для %s: %s", title, err)

        save_json(cinematograph_data, json_data_path, logger)
        save_json(cinematograph_experience, config.json_experience_path, logger)
    except Exception as err:
        logger.error("Ошибка в функции update_cinematograph_json: %s", err)


def main():
    try:
        if not os.path.exists(config.json_experience_path):
            save_json({}, config.json_experience_path, logger)

        if not os.path.exists(config.json_data_path):
            save_json({}, config.json_data_path, logger)

        update_cinematograph_json(
            cinematograph_experience=load_json(config.json_experience_path, {}, logger),
            cinematograph_data=load_json(config.json_data_path, {}, logger),
            json_data_path=config.json_data_path,
            update_threshold=config.update_threshold,
            api_key=config.api_key
        )
    except Exception as err:
        logger.error("Ошибка в функции main: %s", err)


logger = set_logger(log_folder=config.log_folder, log_subfolder_name='cinematograph_data_updater')

if __name__ == "__main__":
    main()