import os
import json
import subprocess

from datetime import datetime, timedelta

import config


def save_json(data, file_path):
    file_path = os.path.normpath(file_path)

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_json(file_path, default_type):
    file_path = os.path.normpath(file_path)

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        return data

    return default_type


def entering_date():
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

            date = datetime(year, month, day)
            break
        except ValueError as e:
            print("Некорректный формат даты: %s", e)

    return date


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
            if key in json_experience[cinematograph_type]:

                if value not in json_experience[cinematograph_type][key]:
                    json_experience[cinematograph_type][key].append(value)
                    print(f'\nДобавлено новое значение для ключа {key}\n')
                else:
                    print(f'\nЗначение уже существует для ключа {key}\n')

                if key in json_current:
                    del json_current[key]

                    save_json(json_current, json_current_path)
            else:
                json_experience[cinematograph_type][key] = [value]
                print(f'Новый ключ добавлен: {key}')

        save_json(json_experience, json_experience_path)
    except Exception as e:
        print(f"Ошибка при добавлении данных: {e}")


def input_movie_data():
    movie_title = input("Введите название фильма: ")
    movie_date = entering_date().strftime("%Y-%m-%d")
    movie_rating = int(input("Введите рейтинг фильма: "))

    movie_data = {
        "date": movie_date,
        "rating": movie_rating
    }

    return {movie_title: movie_data}


def input_series_data():
    series_title = input("Введите название сериала: ")
    series_date = entering_date().strftime("%Y-%m-%d")
    series_rating = int(input("Введите рейтинг сериала: "))
    series_season = int(input("Введите номер сезона сериала: "))

    series_data = {
        "date": series_date,
        "rating": series_rating,
        "season": series_season
    }

    return {series_title: series_data}


def update_cinematograph_json(cinematograph_data, json_current, title, json_data_path):
    if title not in cinematograph_data:
        cinematograph_data[title] = {
            "date_update": "2000-01-01",
        }
        save_json(cinematograph_data, json_data_path)

        subprocess.run(['python', 'create_cinematograph_notes.py'], shell=True, check=True)
        cinematograph_data = load_json(json_data_path, {})

    if title in json_current:
        current_season = input('Введите текущий сезон: ')

        if current_season == '':
            print(f"Ваш текущий сезон: {json_current[title]['current_season']}, текущий эпизод: {json_current[title]['current_episode']}")
        else:
            json_current[title]['current_season'] = int(current_season)
            json_current[title]['total_episodes'] = int(input(f'Всего эпизодов в {current_season} сезоне: '))

        json_current[title]['current_episode'] = int(input('Введите текущий эпизод: '))
    else:
        json_current[title] = {}
        json_current[title]['current_season'] = int(input('Введите текущий сезон: '))
        json_current[title]['current_episode'] = int(input('Введите текущий эпизод: '))
        json_current[title]['total_episodes'] = ''

        if cinematograph_data[title]['isSeries']:
            if 'seasonsInfo' in cinematograph_data[title]:
                if len(cinematograph_data[title]['seasonsInfo']) >= json_current[title]['current_season']:
                    json_current[title]['total_episodes'] = cinematograph_data[title]['seasonsInfo'][json_current[title]['current_season'] - 1]['episodesCount']

        if not(json_current[title]['total_episodes']):
            json_current[title]['total_episodes'] = int(input(f'Всего эпизодов в {current_season} сезоне: '))

    json_current[title]['in_the_process_of_watching'] = True

    save_json(json_current, config.json_current)


def main():
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


if __name__ == "__main__":
    main()
