import os
import hashlib
import subprocess

from prettytable import PrettyTable

import config

from set_logger import set_logger
from utils_json import load_json, save_json


def normalize_newlines(text, replacements_file_name):
    try:
        if isinstance(text, str):
            for old, new in replacements_file_name.items():
                text = text.replace(old, new)

            return text
        return ''
    except Exception as err:
        logger.error("Ошибка при нормализации текста: %s", err)

        return ''


def save_md(data, file_path, replacements_file_name):
    try:
        data = normalize_newlines(data, replacements_file_name)
        data_hash = hashlib.md5(data.encode('utf-8')).hexdigest()
        file_name = os.path.basename(file_path)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding='utf-8') as file:
                existing_data = normalize_newlines(file.read(), replacements_file_name)
                existing_hash = hashlib.md5(existing_data.encode('utf-8')).hexdigest()

            if existing_hash == data_hash:
                return

            logger.info("Различия в файле: %s", file_name)
        else:
            logger.info("Новый файл %s", file_name)

        with open(file_path, "w", encoding='utf-8') as file:
            file.write(data)

    except Exception as err:
        logger.error("Ошибка при сохранении файла %s: %s", file_name, err)


def prettytable_to_markdown(pt: PrettyTable):
    try:
        md_table = []

        headers = [f" {field} " for field in pt.field_names]
        md_table.append("|" + "|".join(headers) + "|")

        separator = [":---:" for _ in pt.field_names]
        md_table.append("|" + "|".join(separator) + "|")

        for row in pt._rows:
            md_row = []

            for cell in row:
                if isinstance(cell, list):
                    md_row.append(f" {'<br>'.join(str(item) for item in cell)} ")
                else:
                    md_row.append(f" {cell} ")

            md_table.append("|" + "|".join(md_row) + "|")

        return "\n".join(md_table)
    except Exception as err:
        logger.error("Ошибка при преобразовании таблицы в Markdown: %s", err)

        return ''


def create_md_table(columns_and_values):
    try:
        columns, values = columns_and_values

        if not columns or not values:
            return None

        table = PrettyTable()
        table.field_names = columns

        for row in values:
            table.add_row(row)

        table = prettytable_to_markdown(table)

        return table
    except Exception as err:
        logger.error("Ошибка при создании Markdown таблицы: %s", err)

        return None


def get_rating_columns_and_values(experience_data, data):
    try:
        if data['isSeries']:
            rating_columns = ['Кинопоиск', 'IMDb']
            rating_values = [[
                data['rating']['kp'],
                data['rating']['imdb']
            ]]
        else:
            rating_columns = ['Кинопоиск', 'IMDb', 'Моя']
            rating_values = [[
                data['rating']['kp'],
                data['rating']['imdb'],
                experience_data[-1]['rating']
            ]]

        return rating_columns, rating_values
    except Exception as err:
        logger.error("Ошибка при получении колонок и значений рейтинга: %s", err)

        return [], []


def get_date_columns_and_values(experience_data, data):
    try:
        if data['isSeries']:
            date_columns = ['Дата просмотра', 'Сезон', 'Оценка']
            date_values = [
                [
                    viewing_information['date'],
                    viewing_information['season'],
                    viewing_information['rating']
                ]
                for viewing_information in experience_data
            ]
        else:
            date_columns = ['Дата просмотра']
            date_values = [[data['date']] for data in experience_data]

        return date_columns, date_values
    except Exception as err:
        logger.error("Ошибка при получении колонок и значений дат: %s", err)

        return [], []


def get_sequels_and_prequels_columns_and_values(all_ids, data, info, exceptions, replacements_file_name):
    try:
        values = []

        if 'sequelsAndPrequels' in data and len(data['sequelsAndPrequels']) > 0:
            for item in data['sequelsAndPrequels']:
                if item['name'] is None or item['poster']['url'] is None:
                    continue

                id_in_exceptions = str(item['id']) in exceptions
                content_in_local_data = item['id'] in all_ids
                item_name = item['name']

                if 'year' in item and item['year'] != 'None' and item['year'] is not None:
                    if int(item['year']) > 2024:
                        continue

                    item_name += f" ({item['year']})"

                # Формируем ссылку на КиноПоиск
                kp_url = f"https://www.kinopoisk.ru/film/{item['id']}/" # Универсальная ссылка

                if not id_in_exceptions and not content_in_local_data:
                    info['sequels_and_prequels_titles'].append(f"[{item_name}]({kp_url})")
                    info['sequels_and_prequels_links'].append(item['poster']['url'])
                    info['sequels_and_prequels'] = True

                if content_in_local_data and item['name']:
                    for old, new in replacements_file_name.items():
                        item['name'] = item['name'].replace(old, new)

                    values.append([f"<img src={item['poster']['url']} width='400'><br>[[{item['name']}]({kp_url})]"])
                else:
                    values.append([f"<img src={item['poster']['url']} width='400'><br>[{item['name']}]({kp_url})"])

        return ['Сиквелы и приквелы'], values
    except Exception as err:
        logger.error("Ошибка при получении сиквелов и приквелов: %s", err)

        return [], []


def create_info(data, title, experience_data, current_series, exceptions):
    try:
        info = {
            'tag': ['#Cinematograph'],
            'year': data['year'],
            'genres': [genre['name'] for genre in data['genres']],
            'poster': data['poster']['url'],
            'viewing_dates': [view['date'] for view in experience_data if view['date']],
            'sequels_and_prequels_titles': [],
            'sequels_and_prequels_links': [],
            'sequels_and_prequels': False,
            'new_seasons': False
        }

        if data['isSeries'] and 'seasonsInfo' in data and data['seasonsInfo']:
            if data['id'] not in exceptions:
                last_season_number = data['seasonsInfo'][-1]['number']
                last_experience_season = experience_data[-1]['season'] if experience_data else None

                if last_experience_season is not None:
                    info['new_seasons'] = last_season_number > last_experience_season
                else:
                    info['new_seasons'] = None

        if title in current_series:
            current = current_series[title]
            percentage = int(current['current_episode'] / current['total_episodes'] * 100)

            info.update({
                'current_season': current['current_season'],
                'current_episode': current['current_episode'],
                'total_episodes': current['total_episodes'],
                'progress': f'<progress max=100 value={percentage}> </progress> {percentage}%',
                'in_the_process_of_watching': True
            })

        return info
    except Exception as err:
        logger.error("Ошибка при создании информации: %s", err)

        return {}


def create_md_content(info, data, experience_data, all_ids, exceptions, replacements_file_name):
    try:
        date_table = create_md_table(get_date_columns_and_values(experience_data, data))
        rating_table = create_md_table(get_rating_columns_and_values(experience_data, data))
        sequels_and_prequels_table = create_md_table(
            get_sequels_and_prequels_columns_and_values(
                all_ids,
                data,
                info,
                exceptions,
                replacements_file_name
            )
        )

        text = ['---']
        text.extend([f"{key}: {value}" for key, value in info.items()])
        text.extend([
            '---',
            f'<img src={data["poster"]["url"]} width="400">',
            f"\n{date_table}",
            f"\n{rating_table}",
            '\n## Описание',
            f"\n{data['description']}",
            f"\n{sequels_and_prequels_table}" if sequels_and_prequels_table else ''
        ])

        return '\n'.join(text)
    except Exception as err:
        logger.error("Ошибка при создании MD контента: %s", err)

        return ''


def update_cinematograph_notes(
    notes_folder,
    replacements_file_name,
    replacements_file_content,
    json_experience_path,
    json_data_path,
    json_current_path,
    json_exceptions_path
):
    try:
        cinematograph_experience = load_json(json_experience_path, {}, logger)
        cinematograph_data = load_json(json_data_path, {}, logger)
        current_series = load_json(json_current_path, {}, logger)
        exceptions = load_json(json_exceptions_path, [], logger)

        if not cinematograph_experience:
            return

        if not cinematograph_data:
            return

        os.makedirs(notes_folder, exist_ok=True)

        all_titles = set(cinematograph_experience.keys())
        all_ids = [int(value['kp_id']) for title, value in cinematograph_experience.items()]

        count_movies = len([
            value['kp_id']
            for title, value in cinematograph_experience.items()
            if not cinematograph_data[value['kp_id']]['isSeries']
        ])

        all_series = cinematograph_experience | current_series

        count_series = len([
            value['kp_id']
            for title, value in all_series.items()
            if cinematograph_data[value['kp_id']]['isSeries']
        ])

        logger.info("Всего фильмов: %s", count_movies)
        logger.info("Всего сериалов: %s", count_series)

        for title in current_series:
            try:
                if title in all_titles:
                    cinematograph_experience[title]['experience'].append({
                        "date": 'in progress',
                        "rating": '',
                        "season": current_series[title]['current_season']
                    })
                else:
                    cinematograph_experience[title] = {'experience': [], 'kp_id': current_series[title]['kp_id']}
                    cinematograph_experience[title]['experience'] = [{
                        "date": 'in progress',
                        "rating": '',
                        "season": current_series[title]['current_season']
                    }]
            except Exception as err:
                logger.error("Ошибка обработки текущего сериала %s: %s", title, err)

        for title, data in cinematograph_experience.items():
            try:
                experience_data = data['experience']
                kp_id = cinematograph_experience[title]['kp_id']
                data = cinematograph_data[kp_id]
                info = create_info(data, title, experience_data, current_series, exceptions)
                content = create_md_content(info, data, experience_data, all_ids, exceptions, replacements_file_name)

                title_count = sum(
                    1
                    for key in cinematograph_data
                    if cinematograph_data[kp_id]['name'] == cinematograph_data[key]['name']
                )

                if cinematograph_data[kp_id]['name'] and title_count < 2:
                    cinematograph_title = cinematograph_data[kp_id]['name']
                else:
                    cinematograph_title = title

                for old, new in replacements_file_name.items():
                    cinematograph_title = cinematograph_title.replace(old, new)

                file_path = os.path.join(notes_folder, f"{cinematograph_title}.md")
                save_md(content, file_path, replacements_file_content)
            except Exception as err:
                logger.error("Ошибка при обновлении заметки %s: %s", title, err)
    except Exception as err:
        logger.error("Ошибка в функции update_cinematograph_notes: %s", err, exc_info=True)


def main():
    try:
        if not os.path.exists(config.json_experience_path):
            save_json(config.json_experience_path, {}, logger)

        if not os.path.exists(config.json_data_path):
            save_json(config.json_data_path, {}, logger)

        subprocess.run(['python', 'cinematograph_data_updater.py'], shell=True, check=True)

        update_cinematograph_notes(
            notes_folder=config.cinematograph_notes_folder,
            replacements_file_name=config.replacements_file_name,
            replacements_file_content=config.replacements_file_content,
            json_experience_path=config.json_experience_path,
            json_data_path=config.json_data_path,
            json_current_path=config.json_current_path,
            json_exceptions_path=config.json_exceptions_path
        )
    except Exception as err:
        logger.error("Ошибка в функции main: %s", err, exc_info=True)


logger = set_logger(log_folder=config.log_folder, log_subfolder_name='create_cinematograph_notes')

if __name__ == "__main__":
    main()