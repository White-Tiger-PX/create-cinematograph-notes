import os
import json

import config


def save_json(data, file_path):
    try:
        file_path = os.path.normpath(file_path)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as err:
        print(f"Ошибка при сохранении JSON в {file_path}: {err}")


def load_json(file_path, default_type):
    try:
        file_path = os.path.normpath(file_path)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            return data
    except Exception as err:
        print(f"Ошибка при загрузке JSON из {file_path}: {err}")

    return default_type


def main():
    if not os.path.exists(config.json_exceptions):
        save_json([], config.json_exceptions)

    exception = None
    exceptions = []

    while exception != '':
        exception = input("Введите название (Оставьте пустым, чтобы сохранить): ")

        if exception != '':
            exceptions.append(exception)

    current_exceptions = load_json(config.json_exceptions, [])
    current_exceptions.extend(exceptions)

    save_json(current_exceptions, config.json_exceptions)


if __name__ == "__main__":
    main()