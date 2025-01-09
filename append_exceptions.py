import os

import config

from set_logger import set_logger
from utils_json import load_json, save_json


def main():
    if not os.path.exists(config.json_exceptions_path):
        save_json([], config.json_exceptions_path, logger)

    exception = None
    exceptions = []

    while exception != '':
        exception = input("Введите название (Оставьте пустым, чтобы сохранить): ")

        if exception != '':
            exceptions.append(exception)

    current_exceptions = load_json(config.json_exceptions_path, [], logger)
    current_exceptions.extend(exceptions)

    save_json(current_exceptions, config.json_exceptions_path, logger)


logger = set_logger(log_folder=config.log_folder, log_subfolder_name='append_exceptions')

if __name__ == "__main__":
    main()