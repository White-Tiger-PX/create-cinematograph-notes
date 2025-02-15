"""
Модуль для создания логгера.
"""
import os
import logging

from datetime import datetime


def set_logger(log_folder: str = None) -> logging.Logger:
    """
    Создает и настраивает логгер для записи логов в файл и вывод в консоль.

    Логгер использует формат:
    `YYYY-MM-DD HH:MM:SS - LEVELNAME - Сообщение`

    Если указана папка `log_folder`, логи также сохраняются в файле
    с именем в формате `YYYY-MM-DD HH-MM-SS.log`.

    Args:
        log_folder (str, optional): Путь к папке для сохранения логов.
            Если `None`, логи пишутся только в консоль.

    Returns:
        logging.Logger: Настроенный объект логгера.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if log_folder:
        log_filename = datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')
        log_file_path = os.path.join(log_folder, log_filename)

        os.makedirs(log_folder, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
