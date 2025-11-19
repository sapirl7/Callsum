import pytest
from pipeline import process_audio_file
import os

def test_process_audio_file():
    """Тест полного цикла обработки аудио"""
    # Проверяем, что тестовый файл существует
    test_file = "sample_aud1io.wav"  # Меньший файл для быстрого теста

    if not os.path.exists(test_file):
        pytest.skip(f"Тестовый файл {test_file} не найден")

    # Запускаем обработку
    result = process_audio_file(test_file)

    # Проверяем структуру результата
    assert isinstance(result, dict), "Результат должен быть словарем"

    # Проверяем наличие основных блоков (если нет ошибки)
    if "error" not in result:
        # Проверяем что хотя бы один блок присутствует
        assert any(key in result for key in ['technical_block', 'commercial_block', 'other_tasks']), \
            "Должен быть хотя бы один блок в результате"

def test_pipeline_structure():
    """Проверяем что функция process_audio_file существует и принимает правильные аргументы"""
    import inspect

    sig = inspect.signature(process_audio_file)
    params = list(sig.parameters.keys())

    assert 'audio_path' in params, "Функция должна принимать параметр audio_path"
