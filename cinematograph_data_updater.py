import os
import time
import json
import ctypes
import requests
import webbrowser

from datetime import datetime, timedelta

import config


class ApiError(Exception):
    pass


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


def updating_unknown_object(cinematograph_title, api_key):
    headers = {"X-API-KEY": api_key}

    response = requests.get(
        'https://api.kinopoisk.dev/v1.4/movie/search',
        params={
            "query": cinematograph_title,
            "limit": 10,
            "page": 1
        },
        headers=headers,
        timeout=20
    )

    if response.status_code == 200:
        movies = response.json()

        if movies['docs']:
            return movies['docs']
    else:
        print(response.status_code)

    return []


def updating_known_object(old_cinematograph_data, api_key, kp_id):
    headers = {"X-API-KEY": api_key}

    response = requests.get(
        f'https://api.kinopoisk.dev/v1.4/movie/{kp_id}',
        headers=headers,
        timeout=20
    )

    if response.status_code == 200:
        current_cinematograph_data = response.json()
        current_cinematograph_data['date_update'] = datetime.now().strftime('%Y-%m-%d')
    else:
        print(f"Ошибка: {response.status_code}. {response.text}")

        return old_cinematograph_data

    return current_cinematograph_data


def updating_object_images(cinematograph_data, api_key, kp_id):
    headers = {"X-API-KEY": api_key}
    all_images = []
    page = 1

    while True:
        response = requests.get(
            'https://api.kinopoisk.dev/v1.4/image',
            headers=headers,
            params={
                'movieId': kp_id,
                'page': page,
                'limit': 50,
                'type': 'still'
                },
            timeout=20
        )

        if response.status_code != 200:
            if 'Вы израсходовали' in response.text:
                return
            
            print(f"Ошибка: {response.status_code}. {response.text}")
            break

        try:
            data = response.json()

            if 'docs' in data:
                all_images.extend(data['docs'])
            else:
                break

            # Если текущая страница - последняя, выход из цикла
            if page >= data['pages']:
                break

            page += 1
        except requests.exceptions.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
            break

    cinematograph_data['images'] = all_images
    cinematograph_data['date_image_update'] = datetime.now().strftime('%Y-%m-%d')

    return cinematograph_data


def show_message_box(title, message):
    MB_OKCANCEL = 0x1
    result = ctypes.windll.user32.MessageBoxW(None, message, title, MB_OKCANCEL)

    return result


def update_cinematograph_json(cinematograph_experience, cinematograph_data, json_data_path, update_threshold, api_key):
    if not cinematograph_experience:
        return

    all_titles = cinematograph_experience['Movies'] | cinematograph_experience['Series']
    unknown_cinematograph_titles = [key for key in all_titles if not(key in cinematograph_data)]
    update_threshold = datetime.now() - timedelta(days=update_threshold)

    try:
        for title, data in cinematograph_data.items():
            update_date = datetime.strptime(data['date_update'], '%Y-%m-%d')

            if update_date < update_threshold:
                print(f"Обновление данных: {title}")

                if 'id' in data:
                    kp_id = data['id']
                    data = updating_known_object(data, api_key, kp_id)
                    data = updating_object_images(data, api_key, kp_id)
                    cinematograph_data[title] = data
                else:
                    unknown_cinematograph_titles.append(title)

                time.sleep(5)
    except Exception as err:
        print(f'Ошибка в обновление текущих данных: {title}, {err}')

    for title in unknown_cinematograph_titles:
        try:
            new_data = updating_unknown_object(title, api_key)

            for new_info in new_data:
                if 'isSeries' in new_info and new_info['isSeries']:
                    url = f"https://www.kinopoisk.ru/series/{new_info['id']}"
                else:
                    url = f"https://www.kinopoisk.ru/film/{new_info['id']}"

                webbrowser.open(url)

                message = f"Это подходящая страница для: {title}?"
                user_choice = show_message_box("Обновление данных", message)

                if user_choice == 1:
                    new_info = updating_object_images(new_info, api_key, new_info['id'])
                    new_info['date_update'] = datetime.now().strftime('%Y-%m-%d')
                    cinematograph_data[title] = new_info

                    break  # Выход из цикла, если данные обновлены

                if 'date_update' in new_info:
                    break  # Выход из цикла, если уже была дата обновления

        except ApiError as err:
            print(f"Ошибка в API при обновлении данных для {title}: {err}")
            break
        except Exception as err:
            print(f"Ошибка при обновлении данных для {title}: {err}")

    save_json(cinematograph_data, json_data_path)


def main():
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


if __name__ == "__main__":
    main()