import os
import time
import ctypes
import requests
import webbrowser
import subprocess

from datetime import datetime, timedelta

import config

from set_logger import set_logger
from utils_json import load_json, save_json


class ApiError(Exception):
    pass


def entering_date():
    try:
        now = datetime.now()

        while True:
            try:
                date_str = input("Введите дату (DD / MM DD / YYYY MM DD): ")

                if len(date_str.split()) == 1:
                    day = int(date_str)
                    month = now.month
                    year = now.year

                    if day > now.day:
                        prev_month_date = now.replace(day=1) - timedelta(days=1)
                        month = prev_month_date.month
                        year = prev_month_date.year

                elif len(date_str.split()) == 2:
                    month, day = map(int, date_str.split())
                    year = now.year

                    if month > now.month or (month == now.month and day > now.day):
                        month = now.month - 1
                        if month == 0:
                            month = 12
                            year -= 1

                elif len(date_str.split()) == 3:
                    year, month, day = map(int, date_str.split())
                else:
                    continue

                return datetime(year, month, day)
            except ValueError as err:
                print("Некорректный формат даты: %s", err)
    except Exception as err:
        logger.error("Ошибка при вводе даты: %s", err)


def input_movie_data():
    try:
        movie_title = input("Введите название фильма: ")
        movie_date = entering_date().strftime("%Y-%m-%d")
        user_input_rating_movie = input("Введите рейтинг фильма: ")
        movie_rating = int(user_input_rating_movie)

        movie_data = {
            "date": movie_date,
            "rating": movie_rating
        }

        return {movie_title: {"experience": [movie_data], "kp_id": None}}
    except Exception as err:
        logger.error("Ошибка при вводе данных фильма: %s", err)


def input_series_data():
    try:
        series_title = input("Введите название сериала: ")
        series_date = entering_date().strftime("%Y-%m-%d")
        user_input_rating_series = input("Введите рейтинг сериала: ")
        series_rating = int(user_input_rating_series)
        user_input_number_series = input("Введите номер сезона сериала: ")
        series_season = int(user_input_number_series)

        series_data = {
            "date": series_date,
            "season": series_season,
            "rating": series_rating
        }

        return {series_title: {"experience": [series_data], "kp_id": None}}
    except Exception as err:
        logger.error("Ошибка при вводе данных сериала: %s", err)


def add_cinematograph_experience(cinematograph_data_path, cinematograph_current_path, cinematograph_experience_path, cinematograph_type):
    try:
        cinematograph_data = load_json(cinematograph_data_path, {}, logger)
        cinematograph_experience = load_json(cinematograph_experience_path, {}, logger)
        cinematograph_current = load_json(cinematograph_current_path, {}, logger)

        if cinematograph_type == 'Movies':
            data = input_movie_data()
        elif cinematograph_type == 'Series':
            data = input_series_data()

            # Если пользователь ставит оценку сезону — значит он закончил его просмотр,
            # можно удалить его из просматриваемых
            if list(data.keys())[0] in list(cinematograph_current.keys()):
                del cinematograph_current[list(data.keys())[0]]

                save_json(cinematograph_current, cinematograph_current_path, logger)

        for key, value in data.items():
            # Проверяем, что тип Film/Series совпадает с тем, что в cinematograph_experience
            if key in cinematograph_experience:
                existing_data = cinematograph_data.get(cinematograph_experience[key]['kp_id'], {})
                existing_is_series = existing_data.get('isSeries', None)

                if existing_is_series != (cinematograph_type == 'Series'):
                    logger.warning(
                        "В cinematograph_experience уже есть запись для %s, но тип отличается. Существующий: %s, добавляемый: %s.",
                        key, 'Series' if existing_is_series else 'Movie', cinematograph_type
                    )
                    user_choice = input("Вы хотите записать данные с другим типом в тот же ключ? (y/n): ")

                    if user_choice.lower() == 'y':
                        cinematograph_experience[key]['experience'].append(value['experience'][0])
                        logger.info("Добавлено новое значение для ключа %s", key)
            else:
                cinematograph_experience[key] = value
                logger.info("Добавлен новый ключ: %s", key)

        save_json(cinematograph_experience, cinematograph_experience_path, logger)
    except Exception as err:
        logger.error("Ошибка при добавлении данных в JSON: %s", err)


def update_cinematograph_json(cinematograph_data_path, cinematograph_current_path, cinematograph_experience_path, title, api_key):
    try:
        cinematograph_experience = load_json(cinematograph_experience_path, {}, logger)
        cinematograph_current = load_json(cinematograph_current_path, {}, logger)
        cinematograph_data = load_json(cinematograph_data_path, {}, logger)

        found_id = None

        if title in cinematograph_current:
            found_id = next((val['kp_id'] for key, val in cinematograph_current.items() if key.lower() == title.lower()), None)

        if not found_id and title in cinematograph_experience:
            experience_data = cinematograph_experience[title]
            found_id = experience_data.get('kp_id')

            if found_id:
                webbrowser.open(f"https://www.kinopoisk.ru/film/{found_id}")
                time.sleep(2)
                user_choice = show_message_box("Подтверждение", f"Это подходящая страница для: {title}?")

                if user_choice != 1:
                    found_id = None

        # Если ID не найдено, ищем через API
        if not found_id:
            logger.info("ID не найдено для %s, ищем название через API...", title)
            new_data = updating_unknown_object(title, api_key)

            for new_info in new_data:
                webbrowser.open(f"https://www.kinopoisk.ru/film/{new_info['id']}")
                time.sleep(2)
                user_choice = show_message_box("Обновление данных", f"Это подходящая страница для: {title}?")

                if user_choice == 1:
                    found_id = new_info['id']
                    new_info['date_update'] = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                    cinematograph_data[found_id] = new_info
                    cinematograph_data[found_id]['title'] = title  # Сохраняем заголовок для будущих проверок
                    save_json(cinematograph_data, cinematograph_data_path, logger)
                    break

        if found_id:
            if title not in cinematograph_current:
                cinematograph_current[title] = {}

            past_current_season = cinematograph_current[title].get('current_season')
            past_current_episode = cinematograph_current[title].get('current_episode')
            past_total_episodes = cinematograph_current[title].get('total_episodes')

            if past_current_season is not None:
                user_input_current_season = input(f'Введите текущий сезон (Enter, чтобы оставить {past_current_season}): ')
                cinematograph_current[title]['current_season'] = int(user_input_current_season) if user_input_current_season else past_current_season
            else:
                user_input_current_season = input('Введите текущий сезон: ')
                cinematograph_current[title]['current_season'] = int(user_input_current_season)

            if past_current_episode is not None:
                user_input_current_episode = input(f'Введите текущий эпизод (Enter, чтобы оставить {past_current_episode}): ')
                cinematograph_current[title]['current_episode'] = int(user_input_current_episode) if user_input_current_episode else past_current_episode
            else:
                user_input_current_episode = input('Введите текущий эпизод: ')
                cinematograph_current[title]['current_episode'] = int(user_input_current_episode)

            if past_total_episodes is not None:
                user_input_total_episodes = input(f'Всего эпизодов в текущем сезоне (Enter, чтобы оставить {past_total_episodes}): ')
                cinematograph_current[title]['total_episodes'] = int(user_input_total_episodes) if user_input_total_episodes else past_total_episodes
            else:
                user_input_total_episodes = input('Всего эпизодов в текущем сезоне: ')
                cinematograph_current[title]['total_episodes'] = int(user_input_total_episodes)

            cinematograph_current[title]['kp_id'] = found_id

            save_json(cinematograph_current, cinematograph_current_path, logger)
        else:
            logger.error("Не удалось найти подходящие данные для %s.", title)
    except Exception as err:
        logger.error("Ошибка при обновлении JSON для %s: %s", title, err)


def show_message_box(title, message):
    MB_OKCANCEL = 0x1
    return ctypes.windll.user32.MessageBoxW(None, message, title, MB_OKCANCEL)


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


def main():
    try:
        if not os.path.exists(config.json_experience_path):
            save_json({}, config.json_experience_path, logger)

        if not os.path.exists(config.json_data_path):
            save_json({}, config.json_data_path, logger)

        print('Вы добавляете:\n1. Фильм\n2. Сериал\n3. Просмотренная серия сериала\n')

        choice = input('Выберите: ')

        if choice == '1':
            add_cinematograph_experience(
                cinematograph_data_path=config.json_data_path,
                cinematograph_current_path=config.json_current_path,
                cinematograph_experience_path=config.json_experience_path,
                cinematograph_type='Movies'
            )
        elif choice == '2':
            add_cinematograph_experience(
                cinematograph_data_path=config.json_data_path,
                cinematograph_current_path=config.json_current_path,
                cinematograph_experience_path=config.json_experience_path,
                cinematograph_type='Series'
            )
        elif choice == '3':
            title = input('Введите название сериала: ')
            update_cinematograph_json(
                cinematograph_data_path=config.json_data_path,
                cinematograph_current_path=config.json_current_path,
                cinematograph_experience_path=config.json_experience_path,
                title=title,
                api_key=config.api_key
            )

        subprocess.run(['python', 'create_cinematograph_notes.py'], shell=True, check=False)
    except Exception as err:
        logger.error("Ошибка в функции main: %s", err)


logger = set_logger(log_folder=config.log_folder, log_subfolder_name='append_cinematograph_experience')

if __name__ == "__main__":
    main()