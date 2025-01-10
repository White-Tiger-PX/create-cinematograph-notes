import os
import re

import config

from set_logger import set_logger
from utils_json import load_json, save_json


def extract_id_from_url(url):
    """
    Функция для извлечения ID из ссылки Кинопоиска.
    Например, из https://www.kinopoisk.ru/film/4852097/ извлечет '4852097'.
    """
    match = re.search(r'/(film|serial)/(\d+)/', url)

    if match:
        return match.group(2)

    return None


def main():
    if not os.path.exists(config.json_exceptions_path):
        save_json([], config.json_exceptions_path, logger)

    exception = None
    exceptions = []

    while exception != '':
        exception = input("Введите ссылку на Кинопоиск или ID (Оставьте пустым, чтобы сохранить): ")

        if exception != '':
            if 'kinopoisk' in exception: # Если это ссылка, извлекаем ID
                exception_id = extract_id_from_url(exception)
                if exception_id:
                    exceptions.append(exception_id)
                else:
                    print("Ошибка: Невалидная ссылка.")
            else:
                exceptions.append(exception)

    current_exceptions = load_json(config.json_exceptions_path, [], logger)
    current_exceptions.extend(exceptions)

    save_json(current_exceptions, config.json_exceptions_path, logger)


logger = set_logger(log_folder=config.log_folder, log_subfolder_name='append_exceptions')

if __name__ == "__main__":
    main()