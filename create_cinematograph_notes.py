import os
import json
import hashlib
import logging
import subprocess

from datetime import datetime
from prettytable import PrettyTable

import config


def save_json(data, file_path):
    try:
        file_path = os.path.normpath(file_path)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as err:
        logger.error("Ошибка при сохранении файла %s: %s", file_path, err)


def load_json(file_path, default_type):
    try:
        file_path = os.path.normpath(file_path)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            logger.warning("Файл %s не найден, возвращаем значение по умолчанию.", file_path)
    except Exception as err:
        logger.error("Ошибка при загрузке файла %s: %s", file_path, err)

    return default_type


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
                par1 = item['name'] in exceptions
                par2 = item['id'] in all_ids
                par3 = item['poster']['url'] in exceptions

                stringh_item_name = str(item['name'])

                if 'year' in item and item['year'] != 'None' and item['year'] is not None:
                    if int(item['year']) > 2024:
                        continue

                    stringh_item_name = stringh_item_name + f" ({item['year']})"

                if not par3:
                    if not par1 and not par2:
                        info['sequels_and_prequels_titles'].append(stringh_item_name)
                        info['sequels_and_prequels_links'].append(item['poster']['url'])
                        info['sequels_and_prequels'] = True

                    if par2 and item['name']:
                        for old, new in replacements_file_name.items():
                            item['name'] = item['name'].replace(old, new)

                        values.append([f"<img src={item['poster']['url']} width='400'><br>[[{item['name']}]]"])
                    else:
                        values.append([f"<img src={item['poster']['url']} width='400'><br>{item['name']}"])

        return ['Сиквелы и приквелы'], values
    except Exception as err:
        logger.error("Ошибка при получении сиквелов и приквелов: %s", err)

        return [], []


def create_info(data, title, experience_data, current_cinematograph, exceptions):
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
            if title not in exceptions:
                last_season_number = data['seasonsInfo'][-1]['number']
                last_experience_season = experience_data[-1]['season'] if experience_data else None

                if last_experience_season is not None:
                    info['new_seasons'] = last_season_number > last_experience_season
                else:
                    info['new_seasons'] = None

        if title in current_cinematograph:
            current = current_cinematograph[title]
            percentage = int(current['current_episode'] / current['total_episodes'] * 100)

            info.update({
                'current_season': current['current_season'],
                'current_episode': current['current_episode'],
                'total_episodes': current['total_episodes'],
                'progress': f'<progress max=100 value={percentage}> </progress> {percentage}%',
                'in_the_process_of_watching': current['in_the_process_of_watching']
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


def update_cinematograph_notes(notes_folder, replacements_file_name, replacements_file_content, cinematograph_experience, cinematograph_data, current_cinematograph, exceptions):
    try:
        if not cinematograph_experience:
            logger.warning("Список опыта кинематографа пуст.")

            return

        if not cinematograph_data:
            logger.warning("Данные кинематографа отсутствуют.")

            return

        os.makedirs(notes_folder, exist_ok=True)

        logger.info("Всего фильмов: %s", len(cinematograph_experience['Movies']))
        logger.info("Всего сериалов: %s", len(cinematograph_experience['Series'] | current_cinematograph))

        all_titles = set(cinematograph_experience['Movies'] | cinematograph_experience['Series'])

        for title in current_cinematograph:
            try:
                if title not in all_titles:
                    cinematograph_experience['Series'][title] = [{
                        "date": 'in progress',
                        "rating": '',
                        "season": current_cinematograph[title]['current_season']
                    }]
                else:
                    cinematograph_experience['Series'][title].append({
                        "date": 'in progress',
                        "rating": '',
                        "season": current_cinematograph[title]['current_season']
                    })
            except Exception as err:
                logger.error("Ошибка обработки текущего сериала %s: %s", title, err)

        cinematograph_experience = cinematograph_experience['Movies'] | cinematograph_experience['Series']

        all_ids = [
            cinematograph_data[item]['id']
            for item in cinematograph_experience
            if item in cinematograph_data
        ]

        all_official_names = [
            cinematograph_data[title]['name']
            for title in cinematograph_experience
        ]

        for title, experience_data in cinematograph_experience.items():
            try:
                data = cinematograph_data[title]
                info = create_info(data, title, experience_data, current_cinematograph, exceptions)
                content = create_md_content(info, data, experience_data, all_ids, exceptions, replacements_file_name)

                title_count = sum(
                    1
                    for key in all_official_names
                    if cinematograph_data[title]['name'] == key
                )

                if cinematograph_data[title]['name'] and title_count < 2:
                    cinematograph_title = cinematograph_data[title]['name']
                else:
                    cinematograph_title = title

                for old, new in replacements_file_name.items():
                    cinematograph_title = cinematograph_title.replace(old, new)

                file_path = os.path.join(notes_folder, f"{cinematograph_title}.md")
                save_md(content, file_path, replacements_file_content)
            except Exception as err:
                logger.error("Ошибка при обновлении заметки %s: %s", title, err)
    except Exception as err:
        logger.error("Ошибка в функции update_cinematograph_notes: %s", err)


def main():
    try:
        if not os.path.exists(config.json_experience):
            save_json({'Movies': {}, 'Series': {}}, config.json_experience)

        if not os.path.exists(config.json_data_path):
            save_json({}, config.json_data_path)

        subprocess.run(['python', 'cinematograph_data_updater.py'], shell=True, check=True)

        update_cinematograph_notes(
            notes_folder=config.cinematograph_notes_folder,
            replacements_file_name=config.replacements_file_name,
            replacements_file_content=config.replacements_file_content,
            cinematograph_experience=load_json(config.json_experience, {}),
            cinematograph_data=load_json(config.json_data_path, {}),
            current_cinematograph=load_json(config.json_current, {}),
            exceptions=load_json(config.json_exceptions, [])
        )
    except Exception as err:
        logger.error("Ошибка в функции main: %s", err)


def set_logger(log_folder):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if log_folder:  # Создание файла с логами только если указана папка
        log_filename = datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')
        log_folder = os.path.join(log_folder, 'create_cinematograph_notes')
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