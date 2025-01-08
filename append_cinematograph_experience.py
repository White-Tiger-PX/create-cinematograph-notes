import os
import json
import logging
import subprocess

from datetime import datetime, timedelta

import config


def save_json(data, file_path):
    try:
        file_path = os.path.normpath(file_path)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as err:
        logger.error("Ошибка при сохранении JSON в файл %s: %s", file_path, err)


def load_json(file_path, default_type):
    try:
        file_path = os.path.normpath(file_path)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return default_type
    except Exception as err:
        logger.error("Ошибка при загрузке JSON из файла %s: %s", file_path, err)

        return default_type


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


def add_data_to_json(json_experience_path, json_current_path, cinematograph_type):
    try:
        json_experience = load_json(json_experience_path, {})
        json_current = load_json(json_current_path, {})

        if cinematograph_type == 'Movies':
            data = input_movie_data()
        elif cinematograph_type == 'Series':
            data = input_series_data()

            if list(data.keys())[0] in list(json_current.keys()):
                del json_current[list(data.keys())[0]]
                save_json(json_current, json_current_path)

        for key, value in data.items():
            try:
                if key in json_experience[cinematograph_type]:
                    if value not in json_experience[cinematograph_type][key]:
                        json_experience[cinematograph_type][key].append(value)
                        print('\nДобавлено новое значение для ключа %s\n', key)
                    else:
                        print('\nЗначение уже существует для ключа %s\n', key)

                    if key in json_current:
                        del json_current[key]
                        save_json(json_current, json_current_path)
                else:
                    json_experience[cinematograph_type][key] = [value]
                    print('Новый ключ добавлен: %s', key)
            except Exception as err:
                logger.error("Ошибка при обработке ключа %s: %s", key, err)

        save_json(json_experience, json_experience_path)
    except Exception as err:
        logger.error("Ошибка при добавлении данных в JSON: %s", err)


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

        return {movie_title: movie_data}
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
            "rating": series_rating,
            "season": series_season
        }

        return {series_title: series_data}
    except Exception as err:
        logger.error("Ошибка при вводе данных сериала: %s", err)


def update_cinematograph_json(cinematograph_data, json_current, title, json_data_path):
    try:
        if title not in cinematograph_data:
            cinematograph_data[title] = {
                "date_update": "2000-01-01",
            }
            save_json(cinematograph_data, json_data_path)
            subprocess.run(['python', 'create_cinematograph_notes.py'], shell=True, check=True)
            cinematograph_data = load_json(json_data_path, {})

        if title in json_current:
            try:
                user_input_current_season = input('Введите текущий сезон: ')
                if user_input_current_season == '':
                    print("Ваш текущий сезон: %s, текущий эпизод: %s", json_current[title]['current_season'], json_current[title]['current_episode'])
                else:
                    json_current[title]['current_season'] = int(user_input_current_season)
                    user_input_total_episodes = input('Всего эпизодов в %s сезоне: ', user_input_current_season)
                    json_current[title]['total_episodes'] = int(user_input_total_episodes)
            except Exception as err:
                logger.error("Ошибка при обновлении текущего сезона сериала %s: %s", title, err)
        else:
            json_current[title] = {}
            user_input_current_season = input('Введите текущий сезон: ')
            json_current[title]['current_season'] = int(user_input_current_season)
            user_input_current_episode = input('Введите текущий эпизод: ')
            json_current[title]['current_episode'] = int(user_input_current_episode)
            json_current[title]['total_episodes'] = ''

        save_json(json_current, config.json_current)
    except Exception as err:
        logger.error("Ошибка при обновлении JSON для %s: %s", title, err)


def main():
    try:
        if not os.path.exists(config.json_experience):
            save_json({'Movies': {}, 'Series': {}}, config.json_experience)

        if not os.path.exists(config.json_data_path):
            save_json({}, config.json_data_path)

        print('Вы добавляете:\n1. Фильм\n2. Сериал\n3. Просмотренная серия сериала\n')

        choice = input('Выберите: ')

        if choice == '1':
            add_data_to_json(config.json_experience, config.json_current, 'Movies')
        elif choice == '2':
            add_data_to_json(config.json_experience, config.json_current, 'Series')
        elif choice == '3':
            title = input('Введите название сериала: ')
            update_cinematograph_json(
                cinematograph_data=load_json(config.json_data_path, {}),
                json_current=load_json(config.json_current, {}),
                title=title,
                json_data_path=config.json_data_path
            )
        subprocess.run(['python', 'create_cinematograph_notes.py'], shell=True, check=False)
    except Exception as err:
        logger.error("Ошибка в функции main: %s", err)


def set_logger(log_folder):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if log_folder:  # Создание файла с логами только если указана папка
        log_filename = datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')
        log_folder = os.path.join(log_folder, 'append_cinematograph_experience')
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