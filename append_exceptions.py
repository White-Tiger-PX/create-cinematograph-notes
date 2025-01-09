import os
import logging

from datetime import datetime
from utils_json import load_json, save_json

import config


def main():
    if not os.path.exists(config.json_exceptions):
        save_json([], config.json_exceptions, logger)

    exception = None
    exceptions = []

    while exception != '':
        exception = input("Введите название (Оставьте пустым, чтобы сохранить): ")

        if exception != '':
            exceptions.append(exception)

    current_exceptions = load_json(config.json_exceptions, [], logger)
    current_exceptions.extend(exceptions)

    save_json(current_exceptions, config.json_exceptions, logger)


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