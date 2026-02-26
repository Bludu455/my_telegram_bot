import telebot
import os
import logging
import requests
import json
from telebot import types
from datetime import datetime, timedelta
import html
import time
import uuid
import random
import string
import hashlib
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG_FILE = 'bot_config.json'
USERS_FILE = 'users.json'
SUBSCRIPTIONS_FILE = 'subscriptions.json'
PAYMENTS_FILE = 'payments.json'
REFERRALS_FILE = 'referrals.json'
APEX_PLANS_FILE = 'apex_plans.json'
KEYS_FILE = 'keys.json'
ACTIVATIONS_FILE = 'activations.json'
ADMINS_FILE = 'admins.json'
CLIENT_LINKS_FILE = 'client_links.json'
PROMOCODES_FILE = 'promocodes.json'

# Функция для получения токена
def get_token():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        return token.strip()
    
    try:
        with open('token.txt', 'r') as f:
            token = f.read().strip()
            if token:
                return token
    except FileNotFoundError:
        pass
    
    print("=" * 50)
    print("ВВЕДИТЕ ТОКЕН TELEGRAM BOT")
    print("=" * 50)
    
    while True:
        token = input("Токен: ").strip().strip('"').strip("'")
        
        if ':' not in token:
            print("❌ Неверный формат токена!")
            continue
        
        if ' ' in token:
            print("❌ Токен не должен содержать пробелы!")
            continue
        
        try:
            with open('token.txt', 'w') as f:
                f.write(token)
            print("✅ Токен сохранен в token.txt")
        except:
            pass
        
        return token

# Получаем токен и создаем бота
TOKEN = get_token()

if not TOKEN:
    logger.error("Токен не указан!")
    exit(1)

try:
    bot = telebot.TeleBot(TOKEN)
    logger.info("✅ Бот успешно создан")
except Exception as e:
    logger.error(f"❌ Ошибка создания бота: {e}")
    exit(1)

user_states = {}

# ========== КОНФИГУРАЦИЯ APEXDLC ==========
APEX_PLANS = {
    '30_days': {
        'name': 'ApexDLC 30 DAYS',
        'price_rub': 990,
        'price_stars': 99,
        'duration_days': 30,
        'features': [
            '✅ Доступ ко всем DLC',
            '✅ Обновления автоматически',
            '✅ Техподдержка 24/7',
            '✅ Безлимитные загрузки'
        ]
    },
    '90_days': {
        'name': 'ApexDLC 90 DAYS',
        'price_rub': 1990,
        'price_stars': 199,
        'duration_days': 90,
        'features': [
            '✅ Доступ ко всем DLC',
            '✅ Обновления автоматически',
            '✅ Техподдержка 24/7',
            '✅ Безлимитные загрузки',
            '✅ Скидка 33%'
        ]
    },
    '180_days': {
        'name': 'ApexDLC 180 DAYS',
        'price_rub': 2990,
        'price_stars': 299,
        'duration_days': 180,
        'features': [
            '✅ Доступ ко всем DLC',
            '✅ Обновления автоматически',
            '✅ Техподдержка 24/7',
            '✅ Безлимитные загрузки',
            '✅ Скидка 50%'
        ]
    },
    'lifetime': {
        'name': 'ApexDLC LIFETIME',
        'price_rub': 4990,
        'price_stars': 499,
        'duration_days': 36500,  # 100 лет (практически навсегда)
        'features': [
            '✅ ПОЖИЗНЕННЫЙ ДОСТУП',
            '✅ Все будущие обновления',
            '✅ Приоритетная поддержка',
            '✅ Безлимитные загрузки',
            '✅ Максимальная скидка 70%'
        ]
    }
}

# ========== ПЛАТЕЖНЫЕ НАСТРОЙКИ ==========
YKASSA_SHOP_ID = os.getenv('YKASSA_SHOP_ID', '')
YKASSA_SECRET_KEY = os.getenv('YKASSA_SECRET_KEY', '')

# ========== НАСТРОЙКИ КЛИЕНТА ==========
CLIENT_DOWNLOAD_LINK = os.getenv('CLIENT_DOWNLOAD_LINK', 'https://example.com/client.apk')
CLIENT_VERSION = "1.0.0"
CLIENT_SIZE = "150 MB"

FREE_CLIENT_DOWNLOAD_LINK = os.getenv('FREE_CLIENT_DOWNLOAD_LINK', 'https://example.com/free_client.apk')
FREE_CLIENT_VERSION = "1.0.0"
FREE_CLIENT_SIZE = "100 MB"

# ========== ФУНКЦИИ ЗАГРУЗКИ И СОХРАНЕНИЯ ==========

def load_json(filename, default=None):
    """Загружает данные из JSON файла"""
    if default is None:
        default = {} if filename not in [PAYMENTS_FILE, KEYS_FILE, ACTIVATIONS_FILE, CLIENT_LINKS_FILE, PROMOCODES_FILE] else []
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки {filename}: {e}")
    return default

def save_json(filename, data):
    """Сохраняет данные в JSON файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения {filename}: {e}")
        return False

# Загружаем все данные
users = load_json(USERS_FILE, {})
subscriptions = load_json(SUBSCRIPTIONS_FILE, {})
payments = load_json(PAYMENTS_FILE, [])
referrals = load_json(REFERRALS_FILE, {})
apex_plans = load_json(APEX_PLANS_FILE, APEX_PLANS)
keys = load_json(KEYS_FILE, {})
activations = load_json(ACTIVATIONS_FILE, [])
admins = load_json(ADMINS_FILE, [])
client_links = load_json(CLIENT_LINKS_FILE, {})
promocodes = load_json(PROMOCODES_FILE, {})

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПРОМОКОДАМИ ==========

def generate_promo_code(amount, max_uses=1, expiry_days=30):
    """Генерирует уникальный промокод"""
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    promocodes[code] = {
        'code': code,
        'amount': amount,
        'max_uses': max_uses,
        'used_count': 0,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(days=expiry_days)).isoformat(),
        'active': True,
        'used_by': []
    }
    
    save_json(PROMOCODES_FILE, promocodes)
    return code

def validate_promo_code(code):
    """Проверяет валидность промокода"""
    code = code.upper().strip()
    
    if code not in promocodes:
        return False, "Промокод не найден"
    
    promo = promocodes[code]
    
    if not promo.get('active', True):
        return False, "Промокод деактивирован"
    
    if datetime.now() > datetime.fromisoformat(promo['expires_at']):
        return False, "Срок действия промокода истек"
    
    if promo['used_count'] >= promo['max_uses']:
        return False, "Промокод больше не действителен (достигнут лимит использований)"
    
    return True, promo

def activate_promo_code(user_id, code):
    """Активирует промокод для пользователя"""
    is_valid, result = validate_promo_code(code)
    
    if not is_valid:
        return False, result
    
    promo = result
    
    # Начисляем бонус
    update_user_balance(user_id, promo['amount'])
    
    # Обновляем статистику промокода
    promocodes[code]['used_count'] += 1
    promocodes[code]['used_by'].append({
        'user_id': str(user_id),
        'activated_at': datetime.now().isoformat()
    })
    
    save_json(PROMOCODES_FILE, promocodes)
    
    logger.info(f"Пользователь {user_id} активировал промокод {code}, получено {promo['amount']} ₽")
    
    return True, promo['amount']

def get_all_promocodes():
    """Получает все промокоды (для админа)"""
    return list(promocodes.values())

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С КЛИЕНТОМ ==========

def set_client_download_link(link, version=None, size=None):
    """Устанавливает ссылку для скачивания премиум клиента"""
    global CLIENT_DOWNLOAD_LINK, CLIENT_VERSION, CLIENT_SIZE
    
    CLIENT_DOWNLOAD_LINK = link
    if version:
        CLIENT_VERSION = version
    if size:
        CLIENT_SIZE = size
    
    # Сохраняем в файл
    if 'premium' not in client_links:
        client_links['premium'] = {}
    client_links['premium']['download_link'] = CLIENT_DOWNLOAD_LINK
    client_links['premium']['version'] = CLIENT_VERSION
    client_links['premium']['size'] = CLIENT_SIZE
    client_links['premium']['updated_at'] = datetime.now().isoformat()
    save_json(CLIENT_LINKS_FILE, client_links)
    
    logger.info(f"Ссылка на премиум клиент обновлена: {link}")

def set_free_client_download_link(link, version=None, size=None):
    """Устанавливает ссылку для скачивания бесплатного клиента"""
    global FREE_CLIENT_DOWNLOAD_LINK, FREE_CLIENT_VERSION, FREE_CLIENT_SIZE
    
    FREE_CLIENT_DOWNLOAD_LINK = link
    if version:
        FREE_CLIENT_VERSION = version
    if size:
        FREE_CLIENT_SIZE = size
    
    # Сохраняем в файл
    if 'free' not in client_links:
        client_links['free'] = {}
    client_links['free']['download_link'] = FREE_CLIENT_DOWNLOAD_LINK
    client_links['free']['version'] = FREE_CLIENT_VERSION
    client_links['free']['size'] = FREE_CLIENT_SIZE
    client_links['free']['updated_at'] = datetime.now().isoformat()
    save_json(CLIENT_LINKS_FILE, client_links)
    
    logger.info(f"Ссылка на бесплатный клиент обновлена: {link}")

def get_client_download_link():
    """Получает ссылку для скачивания премиум клиента"""
    if client_links and 'premium' in client_links:
        return (client_links['premium'].get('download_link', CLIENT_DOWNLOAD_LINK), 
                client_links['premium'].get('version', '1.0.0'), 
                client_links['premium'].get('size', '150 MB'))
    return CLIENT_DOWNLOAD_LINK, CLIENT_VERSION, CLIENT_SIZE

def get_free_client_download_link():
    """Получает ссылку для скачивания бесплатного клиента"""
    if client_links and 'free' in client_links:
        return (client_links['free'].get('download_link', FREE_CLIENT_DOWNLOAD_LINK), 
                client_links['free'].get('version', '1.0.0'), 
                client_links['free'].get('size', '100 MB'))
    return FREE_CLIENT_DOWNLOAD_LINK, FREE_CLIENT_VERSION, FREE_CLIENT_SIZE

def create_download_button(link, version, size, button_text="📥 Скачать"):
    """Создает кнопку для скачивания клиента"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn = types.InlineKeyboardButton(
        f"{button_text} v{version} ({size})", 
        url=link
    )
    markup.add(btn)
    return markup

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С АДМИНАМИ ==========

def is_admin(user_id):
    """
    Проверяет, является ли пользователь администратором
    Поддерживает как строковые, так и числовые ID
    """
    # Преобразуем в строку для сравнения
    user_id_str = str(user_id)
    
    # Проверяем наличие в списке администраторов
    return user_id_str in admins

def add_admin(user_id):
    """Добавляет администратора"""
    user_id_str = str(user_id)
    if user_id_str not in admins:
        admins.append(user_id_str)
        save_json(ADMINS_FILE, admins)
        logger.info(f"Пользователь {user_id_str} добавлен в администраторы")
        return True
    return False

def remove_admin(user_id):
    """Удаляет администратора"""
    user_id_str = str(user_id)
    if user_id_str in admins:
        admins.remove(user_id_str)
        save_json(ADMINS_FILE, admins)
        logger.info(f"Пользователь {user_id_str} удален из администраторов")
        return True
    return False

def get_admins():
    """Получает список администраторов"""
    return admins

def init_first_admin(user_id):
    """Инициализирует первого администратора при первом запуске"""
    if len(admins) == 0:
        add_admin(user_id)
        logger.info(f"Пользователь {user_id} назначен администратором (первый запуск)")
        return True
    return False

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С КЛЮЧАМИ ==========

def normalize_key(key):
    """
    Нормализует ключ: убирает лишние пробелы, приводит к верхнему регистру
    """
    if not key:
        return key
    
    # Убираем пробелы в начале и конце
    key = key.strip()
    
    # Убираем все пробелы внутри ключа
    key = key.replace(' ', '')
    
    # Приводим к верхнему регистру
    key = key.upper()
    
    return key

def validate_key_format(key):
    """
    Проверяет формат ключа.
    Поддерживает форматы:
    - AXXX-XXXXX-XXXXX-XXXXX (4-5-5-5)
    - AXXXXX-XXXXX-XXXXX-XXXXX (5-5-5-5)
    - AXXX-XXXX-XXXX-XXXX (4-4-4-4)
    - и другие вариации
    """
    # Нормализуем ключ
    key = normalize_key(key)
    
    # Проверяем, что ключ начинается с A
    if not key.startswith('A'):
        return False, "Ключ должен начинаться с буквы A"
    
    # Разбиваем по дефисам
    parts = key.split('-')
    
    # Должно быть 4 части
    if len(parts) != 4:
        return False, "Ключ должен содержать 4 части, разделенных дефисами"
    
    # Проверяем каждую часть
    for i, part in enumerate(parts):
        if i == 0:
            # Первая часть должна быть длиной 4-6 символов (A + 3-5 символов)
            if len(part) < 4 or len(part) > 6:
                return False, f"Первая часть должна содержать 4-6 символов (сейчас {len(part)})"
        else:
            # Остальные части должны быть длиной 4-6 символов
            if len(part) < 4 or len(part) > 6:
                return False, f"Часть {i+1} должна содержать 4-6 символов (сейчас {len(part)})"
        
        # Проверяем, что все символы - буквы или цифры
        if not all(c.isalnum() for c in part):
            return False, "Ключ может содержать только буквы и цифры"
    
    return True, key

def generate_key(plan_id, user_id=None, created_by=None, is_free=False, is_purchased=False):
    """
    Генерирует уникальный ключ для активации
    Поддерживает разные форматы для совместимости
    """
    # Выбираем случайный формат для разнообразия
    format_type = random.choice(['4-5-5-5', '5-5-5-5', '4-4-4-4'])
    
    if format_type == '4-5-5-5':
        # Формат AXXX-XXXXX-XXXXX-XXXXX
        part1 = 'A' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        part3 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        part4 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    elif format_type == '5-5-5-5':
        # Формат AXXXXX-XXXXX-XXXXX-XXXXX
        part1 = 'A' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        part3 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        part4 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    else:  # 4-4-4-4
        # Формат AXXX-XXXX-XXXX-XXXX
        part1 = 'A' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part3 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part4 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    key = f"{part1}-{part2}-{part3}-{part4}"
    
    # Создаем хеш ключа для быстрого поиска
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    # Определяем тип ключа
    key_type = 'purchased' if is_purchased else 'paid' if not is_free else 'free'
    
    # Сохраняем ключ
    keys[key_hash] = {
        'key': key,
        'plan_id': plan_id,
        'generated_at': datetime.now().isoformat(),
        'generated_by': str(created_by) if created_by else 'system',
        'generated_for': str(user_id) if user_id else None,
        'is_free': is_free,
        'is_purchased': is_purchased,
        'key_type': key_type,  # purchased, paid, free
        'status': 'unused',  # unused, activated, expired
        'activated_by': None,
        'activated_at': None,
        'expires_at': None,
        'format': format_type  # Сохраняем формат для информации
    }
    
    save_json(KEYS_FILE, keys)
    
    type_display = "купленный" if is_purchased else "бесплатный (админ)" if is_free else "платный"
    logger.info(f"Сгенерирован ключ {key} (формат: {format_type}) для плана {plan_id} - тип: {type_display}")
    
    return key

def find_key_by_normalized(key):
    """
    Ищет ключ в базе, игнорируя формат (учитывает только хеш)
    """
    # Нормализуем ключ
    normalized = normalize_key(key)
    
    # Создаем хеш
    key_hash = hashlib.sha256(normalized.encode()).hexdigest()
    
    # Ищем по хешу
    if key_hash in keys:
        return keys[key_hash]
    
    # Если не нашли, пробуем найти среди всех ключей (для обратной совместимости)
    for k, v in keys.items():
        if normalize_key(v['key']) == normalized:
            return v
    
    return None

def validate_key(key):
    """
    Проверяет валидность ключа и возвращает информацию о нем
    """
    # Проверяем формат
    is_valid, result = validate_key_format(key)
    if not is_valid:
        return None, result
    
    # Нормализованный ключ
    normalized_key = result
    
    # Ищем ключ в базе
    key_data = find_key_by_normalized(normalized_key)
    
    if not key_data:
        return None, "Ключ не найден в базе данных"
    
    # Проверяем статус
    if key_data['status'] == 'activated':
        return None, f"❌ Ключ не действителен "
    
    if key_data['status'] == 'expired':
        return None, "❌ Срок действия ключа истек"
    
    return key_data, None

def activate_key(user_id, key):
    """
    Активирует ключ для пользователя
    """
    key_data, error = validate_key(key)
    
    if error:
        return False, error
    
    plan_id = key_data['plan_id']
    plan = APEX_PLANS.get(plan_id)
    
    if not plan:
        return False, "План не найден"
    
    # Проверяем, не предназначен ли ключ для другого пользователя
    if key_data.get('generated_for') and key_data['generated_for'] != str(user_id):
        return False, "Этот ключ предназначен для другого пользователя"
    
    # Вычисляем дату истечения
    expires_at = datetime.now() + timedelta(days=plan['duration_days'])
    
    # Обновляем данные ключа
    normalized_key = normalize_key(key)
    key_hash = hashlib.sha256(normalized_key.encode()).hexdigest()
    
    # Обновляем в словаре
    keys[key_hash]['status'] = 'activated'
    keys[key_hash]['activated_by'] = str(user_id)
    keys[key_hash]['activated_at'] = datetime.now().isoformat()
    keys[key_hash]['expires_at'] = expires_at.isoformat()
    
    # Сохраняем информацию об активации
    activation = {
        'key': key_data['key'],
        'normalized_key': normalized_key,
        'key_hash': key_hash,
        'user_id': str(user_id),
        'plan_id': plan_id,
        'activated_at': datetime.now().isoformat(),
        'expires_at': expires_at.isoformat(),
        'is_free': key_data.get('is_free', False),
        'is_purchased': key_data.get('is_purchased', False)
    }
    activations.append(activation)
    
    save_json(KEYS_FILE, keys)
    save_json(ACTIVATIONS_FILE, activations)
    
    # Создаем или продлеваем подписку пользователя
    subscription = create_apex_subscription(user_id, plan_id, expires_at)
    
    # Если ключ был бесплатным, записываем это
    if key_data.get('is_free'):
        user_data = get_user(user_id)
        user_data['total_free_keys'] = user_data.get('total_free_keys', 0) + 1
        save_json(USERS_FILE, users)
    
    logger.info(f"Пользователь {user_id} активировал ключ {key_data['key']}" + (" (бесплатный)" if key_data.get('is_free') else ""))
    
    return True, subscription

def get_key_status(key, current_user_id=None):
    """
    Получает статус ключа
    """
    # Нормализуем ключ для проверки формата
    normalized = normalize_key(key)
    
    # Проверяем формат
    is_valid, result = validate_key_format(key)
    if not is_valid:
        return f"❌ {result}"
    
    key_data = find_key_by_normalized(normalized)
    
    if not key_data:
        return "❌ Ключ не найден в базе данных"
    
    plan = APEX_PLANS.get(key_data['plan_id'])
    plan_name = plan['name'] if plan else key_data['plan_id']
    
    # Определяем отображаемый тип ключа
    if key_data.get('is_purchased'):
        type_display = "💳 Купленный"
    else:
        type_display = "💳 Платный"
    
    if key_data['status'] == 'activated':
        if current_user_id and str(current_user_id) == key_data.get('activated_by'):
            # Ключ активирован текущим пользователем
            return (
                f"🔑 <b>Информация о ключе:</b>\n\n"
                f"• Ключ: <code>{key_data['key']}</code>\n"
                f"• Тариф: {plan_name}\n"
                f"• Создан: {key_data['generated_at'][:10]}\n"
                f"• Тип: {type_display}\n"
                f"• Формат: {key_data.get('format', 'Неизвестно')}\n"
                f"• Статус: ✅ Активирован {key_data['activated_at'][:10]}\n"
                f"• Активирован вами"
            )
        else:
            # Ключ активирован другим пользователем
            return "❌ Ключ не действителен (активирован другим пользователем)"
    elif key_data['status'] == 'unused':
        # Ключ еще не активирован
        return (
            f"🔑 <b>Информация о ключе:</b>\n\n"
            f"• Ключ: <code>{key_data['key']}</code>\n"
            f"• Тариф: {plan_name}\n"
            f"• Создан: {key_data['generated_at'][:10]}\n"
            f"• Тип: {type_display}\n"
            f"• Формат: {key_data.get('format', 'Неизвестно')}\n"
            f"• Статус: ✅ Ожидает активации"
        )
    else:
        return "❌ Ключ не действителен"

def get_user_keys(user_id):
    """Получает все ключи пользователя"""
    user_id_str = str(user_id)
    user_keys = []
    
    for key_hash, key_data in keys.items():
        if (key_data.get('generated_by') == user_id_str or 
            key_data.get('activated_by') == user_id_str or 
            key_data.get('generated_for') == user_id_str):
            user_keys.append(key_data)
    
    # Сортируем по дате (сначала новые)
    user_keys.sort(key=lambda x: x['generated_at'], reverse=True)
    return user_keys

def get_all_keys(limit=50):
    """Получает все ключи (для админа)"""
    all_keys = []
    for key_hash, key_data in keys.items():
        all_keys.append(key_data)
    
    # Сортируем по дате генерации (сначала новые)
    all_keys.sort(key=lambda x: x['generated_at'], reverse=True)
    return all_keys[:limit]

def get_keys_stats():
    """Получает статистику по ключам"""
    total_keys = len(keys)
    unused_keys = sum(1 for k in keys.values() if k['status'] == 'unused')
    activated_keys = sum(1 for k in keys.values() if k['status'] == 'activated')
    purchased_keys = sum(1 for k in keys.values() if k.get('is_purchased'))
    free_keys = sum(1 for k in keys.values() if k.get('is_free'))
    
    return {
        'total': total_keys,
        'unused': unused_keys,
        'activated': activated_keys,
        'purchased': purchased_keys,
        'free': free_keys
    }

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ==========

def get_user(user_id):
    """Получает данные пользователя"""
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            'registered_at': datetime.now().isoformat(),
            'balance': 0,
            'total_purchases': 0,
            'total_free_keys': 0,
            'referral_code': generate_referral_code(),
            'referred_by': None,
            'apex_subscriptions': []
        }
        save_json(USERS_FILE, users)
    return users[user_id_str]

def update_user_balance(user_id, amount):
    """Обновляет баланс пользователя"""
    user_id_str = str(user_id)
    if user_id_str in users:
        users[user_id_str]['balance'] += amount
        save_json(USERS_FILE, users)
        return True
    return False

def get_user_balance(user_id):
    """Получает баланс пользователя"""
    user_data = get_user(user_id)
    return user_data['balance']

def generate_referral_code(length=8):
    """Генерирует уникальный реферальный код"""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        if code not in [u.get('referral_code') for u in users.values()]:
            return code

def get_referral_link(user_id):
    """Получает реферальную ссылку"""
    user_data = get_user(user_id)
    return f"https://t.me/{bot.get_me().username}?start=ref_{user_data['referral_code']}"

def process_referral(new_user_id, referral_code):
    """Обрабатывает реферальный переход"""
    referrer_id = None
    for uid, data in users.items():
        if data.get('referral_code') == referral_code:
            referrer_id = uid
            break
    
    if referrer_id and str(new_user_id) != referrer_id:
        referrals[str(new_user_id)] = {
            'referred_by': referrer_id,
            'referred_at': datetime.now().isoformat(),
            'bonus_paid': False
        }
        save_json(REFERRALS_FILE, referrals)
        return True
    return False

def get_referral_stats(user_id):
    """Получает статистику по рефералам"""
    user_id_str = str(user_id)
    referred_users = []
    total_bonus = 0
    
    for uid, data in referrals.items():
        if data.get('referred_by') == user_id_str:
            user_data = get_user(uid)
            referred_users.append({
                'user_id': uid,
                'referred_at': data['referred_at'],
                'purchases': user_data.get('total_purchases', 0),
                'bonus_paid': data.get('bonus_paid', False)
            })
            if data.get('bonus_paid'):
                total_bonus += 50
    
    return referred_users, total_bonus

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С APEXDLC ==========

def create_apex_subscription(user_id, plan_id, expires_at=None):
    """Создает подписку ApexDLC для пользователя"""
    user_id_str = str(user_id)
    plan = APEX_PLANS.get(plan_id)
    
    if not plan:
        return None
    
    if not expires_at:
        expires_at = datetime.now() + timedelta(days=plan['duration_days'])
    
    # Проверяем, есть ли уже активная подписка
    existing_sub = get_active_apex_subscription(user_id)
    
    if existing_sub:
        # Продлеваем существующую подписку
        current_expiry = datetime.fromisoformat(existing_sub['expires_at'])
        if datetime.now() < current_expiry:
            new_expiry = current_expiry + timedelta(days=plan['duration_days'])
        else:
            new_expiry = datetime.now() + timedelta(days=plan['duration_days'])
        
        subscription = {
            'id': existing_sub['id'],
            'user_id': user_id_str,
            'plan_id': plan_id,
            'plan_name': plan['name'],
            'created_at': existing_sub['created_at'],
            'expires_at': new_expiry.isoformat(),
            'active': True
        }
        
        # Обновляем существующую подписку
        for i, sub in enumerate(subscriptions.get(user_id_str, [])):
            if sub['id'] == existing_sub['id']:
                subscriptions[user_id_str][i] = subscription
                break
    else:
        # Новая подписка
        subscription = {
            'id': f"apex_{user_id}_{int(time.time())}",
            'user_id': user_id_str,
            'plan_id': plan_id,
            'plan_name': plan['name'],
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at,
            'active': True
        }
        
        # Сохраняем новую подписку
        if user_id_str not in subscriptions:
            subscriptions[user_id_str] = []
        subscriptions[user_id_str].append(subscription)
    
    save_json(SUBSCRIPTIONS_FILE, subscriptions)
    
    return subscription

def get_user_apex_subscriptions(user_id):
    """Получает все Apex подписки пользователя"""
    user_id_str = str(user_id)
    return subscriptions.get(user_id_str, [])

def get_active_apex_subscription(user_id):
    """Получает активную Apex подписку пользователя"""
    user_subs = get_user_apex_subscriptions(user_id)
    active_subs = [s for s in user_subs if s.get('active') and datetime.fromisoformat(s['expires_at']) > datetime.now()]
    
    if active_subs:
        return active_subs[0]  # Возвращаем первую активную
    return None

def check_apex_access(user_id):
    """Проверяет, есть ли у пользователя доступ к ApexDLC"""
    active_sub = get_active_apex_subscription(user_id)
    return active_sub is not None

# ========== ФУНКЦИИ ДЛЯ ОПЛАТЫ ==========

def create_yookassa_payment_link(user_id, amount, description):
    """Создает платеж через ЮKassa и возвращает ссылку для оплаты"""
    try:
        import base64
        from uuid import uuid4
        
        shop_id = YKASSA_SHOP_ID
        secret_key = YKASSA_SECRET_KEY
        
        if not shop_id or not secret_key:
            logger.error("Не настроены платежные реквизиты ЮKassa")
            return None
        
        idempotence_key = str(uuid4())
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{bot.get_me().username}"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "payment_type": "apex"
            }
        }
        
        auth = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
        headers = {
            'Content-Type': 'application/json',
            'Idempotence-Key': idempotence_key,
            'Authorization': f'Basic {auth}'
        }
        
        response = requests.post(
            'https://api.yookassa.ru/v3/payments',
            headers=headers,
            json=payment_data,
            timeout=30
        )
        
        if response.status_code in (200, 201):
            data = response.json()
            payment_id = data['id']
            confirmation_url = data['confirmation']['confirmation_url']
            
            payment_record = {
                'id': payment_id,
                'user_id': str(user_id),
                'amount': amount,
                'currency': 'RUB',
                'status': 'pending',
                'method': 'yookassa',
                'description': description,
                'created_at': datetime.now().isoformat(),
                'confirmation_url': confirmation_url
            }
            
            payments.append(payment_record)
            save_json(PAYMENTS_FILE, payments)
            
            return confirmation_url
        else:
            logger.error(f"Ошибка ЮKassa: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка создания платежа ЮKassa: {e}")
        return None

def create_stars_invoice(user_id, amount, title, description):
    """Создает счет на оплату в звездах"""
    try:
        prices = [types.LabeledPrice(label=title, amount=amount)]
        
        bot.send_invoice(
            user_id,
            title=title,
            description=description,
            invoice_payload=f"stars_{user_id}_{int(time.time())}",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="create_invoice",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка создания счета: {e}")
        return False

def check_yookassa_payment_status(payment_id):
    """Проверяет статус платежа в ЮKassa"""
    try:
        import base64
        
        shop_id = YKASSA_SHOP_ID
        secret_key = YKASSA_SECRET_KEY
        
        if not shop_id or not secret_key:
            return None
        
        auth = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth}'
        }
        
        response = requests.get(
            f'https://api.yookassa.ru/v3/payments/{payment_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except Exception as e:
        logger.error(f"Ошибка проверки статуса платежа: {e}")
        return None

def process_balance_payment(user_id, plan_id):
    """Обрабатывает оплату с баланса пользователя"""
    plan = APEX_PLANS.get(plan_id)
    if not plan:
        return False, "План не найден"
    
    user_balance = get_user_balance(user_id)
    amount = plan['price_rub']
    
    if user_balance < amount:
        return False, f"Недостаточно средств на балансе. Нужно: {amount} ₽, у вас: {user_balance} ₽"
    
    # Списываем средства
    update_user_balance(user_id, -amount)
    
    # Генерируем ключ (купленный)
    key = generate_key(plan_id, user_id, is_purchased=True)
    
    # Создаем запись о платеже
    payment_record = {
        'id': f"balance_{user_id}_{int(time.time())}",
        'user_id': str(user_id),
        'amount': amount,
        'currency': 'RUB',
        'status': 'completed',
        'method': 'balance',
        'description': f"Оплата с баланса: {plan['name']}",
        'created_at': datetime.now().isoformat()
    }
    payments.append(payment_record)
    save_json(PAYMENTS_FILE, payments)
    
    # Увеличиваем счетчик покупок
    user_data = get_user(user_id)
    user_data['total_purchases'] += 1
    save_json(USERS_FILE, users)
    
    logger.info(f"Пользователь {user_id} оплатил с баланса тариф {plan['name']}")
    
    return True, key

# ========== ФУНКЦИИ СОЗДАНИЯ МЕНЮ ==========

def create_main_menu(user_id=None):
    """Создает главное меню с учетом прав и подписок"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Основные кнопки для всех
    buttons = [
        types.KeyboardButton('🎮 Купить подписку ApexDLC'),
        types.KeyboardButton('🔑 Активировать ключ'),
        types.KeyboardButton('📥 FREE версия'),
        types.KeyboardButton('👤 Профиль'),
        types.KeyboardButton('📊 Информация'),
        types.KeyboardButton('🆘 Тех.Поддержка'),
        types.KeyboardButton('👥 Реферальная система'),
        types.KeyboardButton('⚙️ Настройки')
    ]
    
    # Проверяем, есть ли у пользователя активная подписка
    if user_id and check_apex_access(user_id):
        # Добавляем кнопку скачивания премиум клиента только для пользователей с подпиской
        buttons.insert(3, types.KeyboardButton('📥 PREMIUM клиент'))
        logger.info(f"Кнопка премиум клиента добавлена для пользователя {user_id} (есть подписка)")
    
    # Если пользователь админ, добавляем админ-панель в конец
    if user_id and is_admin(user_id):
        buttons.append(types.KeyboardButton('👑 Админ панель'))
        logger.info(f"Админ-панель добавлена для пользователя {user_id}")
    
    markup.add(*buttons)
    return markup

def create_admin_menu():
    """Создает меню администратора"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("🔑 Создать ключ", callback_data="admin_create_key")
    btn2 = types.InlineKeyboardButton("📋 Все ключи", callback_data="admin_all_keys")
    btn3 = types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn4 = types.InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
    btn5 = types.InlineKeyboardButton("📥 Настройки клиентов", callback_data="admin_client_settings")
    btn6 = types.InlineKeyboardButton("🎁 Управление промокодами", callback_data="admin_promocodes")
    btn7 = types.InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")
    btn8 = types.InlineKeyboardButton("➖ Удалить админа", callback_data="admin_remove")
    btn9 = types.InlineKeyboardButton("💰 Платежи", callback_data="admin_payments")
    btn10 = types.InlineKeyboardButton("💳 Начислить баланс", callback_data="admin_add_balance")
    btn11 = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10)
    markup.add(btn11)
    
    return markup

def create_promocode_menu():
    """Создает меню управления промокодами"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_create_promo")
    btn2 = types.InlineKeyboardButton("📋 Все промокоды", callback_data="admin_all_promos")
    btn3 = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    return markup

def create_client_settings_menu():
    """Создает меню настроек клиентов"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    btn1 = types.InlineKeyboardButton("🔗 Изменить PREMIUM ссылку", callback_data="client_change_premium")
    btn2 = types.InlineKeyboardButton("🔗 Изменить FREE ссылку", callback_data="client_change_free")
    btn3 = types.InlineKeyboardButton("📊 Текущие ссылки", callback_data="client_show_links")
    btn4 = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    
    markup.add(btn1, btn2, btn3, btn4)
    
    return markup

def create_key_type_menu():
    """Создает меню выбора типа ключа для админа"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("🎮 30 DAYS", callback_data="keytype_30_days")
    btn2 = types.InlineKeyboardButton("🎮 90 DAYS", callback_data="keytype_90_days")
    btn3 = types.InlineKeyboardButton("🎮 180 DAYS", callback_data="keytype_180_days")
    btn4 = types.InlineKeyboardButton("👑 LIFETIME", callback_data="keytype_lifetime")
    btn5 = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    
    markup.add(btn1, btn2, btn3, btn4)
    markup.add(btn5)
    
    return markup

def create_key_target_menu(plan_id):
    """Создает меню выбора получателя ключа"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("👤 Себе", callback_data=f"keytarget_self_{plan_id}")
    btn2 = types.InlineKeyboardButton("👥 Другому пользователю", callback_data=f"keytarget_other_{plan_id}")
    btn3 = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_create_key")
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    return markup

def create_apex_menu(user_id=None):
    """Создает меню подписок ApexDLC с учетом баланса"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    user_balance = get_user_balance(user_id) if user_id else 0
    
    btn1 = types.InlineKeyboardButton("🎮 30 DAYS - 990 ₽", callback_data="apex_30_days")
    btn2 = types.InlineKeyboardButton("🎮 90 DAYS - 1990 ₽", callback_data="apex_90_days")
    btn3 = types.InlineKeyboardButton("🎮 180 DAYS - 2990 ₽", callback_data="apex_180_days")
    btn4 = types.InlineKeyboardButton("👑 LIFETIME - 4990 ₽", callback_data="apex_lifetime")
    btn5 = types.InlineKeyboardButton("⭐ Мои подписки", callback_data="my_apex_subs")
    btn6 = types.InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")
    btn7 = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    
    markup.add(btn1, btn2, btn3, btn4)
    markup.add(btn5, btn6, btn7)
    
    return markup

def create_payment_method_menu(plan_id, amount_rub, amount_stars, user_balance):
    """Создает меню выбора способа оплаты"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Проверяем, достаточно ли средств на балансе
    balance_sufficient = user_balance >= amount_rub
    balance_text = f"💳 С баланса ({amount_rub} ₽)" + (" ✅" if balance_sufficient else " ❌")
    
    btn1 = types.InlineKeyboardButton(
        f"⭐ Оплатить звездами ({amount_stars} ⭐)", 
        callback_data=f"pay_stars_{plan_id}"
    )
    
    btn2 = types.InlineKeyboardButton(
        balance_text, 
        callback_data=f"pay_balance_{plan_id}"
    )
    
    btn3 = types.InlineKeyboardButton(
        f"💳 Оплатить картой ({amount_rub} ₽)", 
        callback_data=f"pay_card_{plan_id}"
    )
    
    btn4 = types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment")
    
    markup.add(btn1, btn2, btn3)
    markup.add(btn4)
    
    return markup

def create_support_menu():
    """Создает меню техподдержки"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📧 Написать в поддержку", url="https://t.me/support")
    btn2 = types.InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")
    btn3 = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    markup.add(btn1, btn2, btn3)
    return markup

def create_profile_menu():
    """Создает меню профиля"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")
    btn2 = types.InlineKeyboardButton("📜 История", callback_data="history")
    btn3 = types.InlineKeyboardButton("🎮 Мои подписки", callback_data="my_apex_subs")
    btn4 = types.InlineKeyboardButton("🔑 Мои ключи", callback_data="my_keys")
    btn5 = types.InlineKeyboardButton("🎁 Активировать промокод", callback_data="activate_promo")
    btn6 = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

def create_deposit_menu():
    """Создает меню пополнения баланса"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton("100 ₽", callback_data="deposit_100")
    btn2 = types.InlineKeyboardButton("300 ₽", callback_data="deposit_300")
    btn3 = types.InlineKeyboardButton("500 ₽", callback_data="deposit_500")
    btn4 = types.InlineKeyboardButton("1000 ₽", callback_data="deposit_1000")
    btn5 = types.InlineKeyboardButton("2000 ₽", callback_data="deposit_2000")
    btn6 = types.InlineKeyboardButton("5000 ₽", callback_data="deposit_5000")
    btn7 = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    markup.add(btn7)
    return markup

def create_key_menu():
    """Создает меню для работы с ключами"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🔑 Проверить ключ", callback_data="check_key")
    btn2 = types.InlineKeyboardButton("📋 Мои ключи", callback_data="my_keys")
    btn3 = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    markup.add(btn1, btn2, btn3)
    return markup

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    # Проверяем реферальный код
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref_'):
        referral_code = args[1][4:]
        process_referral(user_id, referral_code)
    
    # Если это первый запуск и админов нет, делаем первого пользователя админом
    init_first_admin(user_id)
    
    # Для отладки - выводим информацию об админах
    logger.info(f"Текущие администраторы: {admins}")
    logger.info(f"Пользователь {user_id} является админом: {is_admin(user_id)}")
    
    # Отправляем приветственное изображение
    try:
        image_path = 'image.png'
        if os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption="✨ <b>ДОБРО ПОЖАЛОВАТЬ В БОТА</b> ✨\n\n<b>ApexDLC</b>",
                    parse_mode='HTML'
                )
        else:
            bot.send_message(
                message.chat.id,
                "✨ <b>ДОБРО ПОЖАЛОВАТЬ В БОТА</b> ✨\n\n<b>ApexDLC</b>",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке изображения: {e}")
        bot.send_message(
            message.chat.id,
            "✨ <b>ДОБРО ПОЖАЛОВАТЬ В БОТА</b> ✨\n\n<b>ApexDLC</b>",
            parse_mode='HTML'
        )
    
    # Проверяем статус Apex подписки
    has_apex = check_apex_access(user_id)
    apex_sub = get_active_apex_subscription(user_id)
    
    welcome_text = (
        f"👋 <b>Привет, {message.from_user.first_name}!</b>\n\n"
        f"Добро пожаловать в <b>ApexDLC</b>\n\n"
        f"✨ <b>Наши подписки:</b>\n"
        f"• 🎮 30 DAYS - 990 ₽\n"
        f"• 🎮 90 DAYS - 1990 ₽\n"
        f"• 🎮 180 DAYS - 2990 ₽\n"
        f"• 👑 LIFETIME - 4990 ₽\n\n"
        f"📥 <b>Доступны две версии клиента:</b>\n"
        f"• FREE версия - бесплатно для всех\n"
        f"• PREMIUM версия - только для пользователей с подпиской\n\n"
    )
    
    if has_apex and apex_sub:
        expiry = datetime.fromisoformat(apex_sub['expires_at'])
        days_left = (expiry - datetime.now()).days
        welcome_text += f"✅ <b>Ваша подписка:</b> {apex_sub['plan_name']}\n"
        welcome_text += f"📅 <b>Действует до:</b> {apex_sub['expires_at'][:10]} (осталось {days_left} дн.)\n\n"
    else:
        welcome_text += f"❌ <b>У вас нет активной подписки</b>\n"
        welcome_text += f"💡 Скачайте FREE версию или приобретите PREMIUM подписку\n\n"
    
    welcome_text += f"💰 <b>Ваш баланс:</b> {user_data['balance']} ₽\n"
    
    if is_admin(user_id):
        welcome_text += f"👑 <b>Статус:</b> Администратор\n\n"
    else:
        welcome_text += f"\n"
    
    welcome_text += f"👇 <b>Выберите действие на клавиатуре</b>"
    
    markup = create_main_menu(user_id)
    bot.send_message(message.chat.id, welcome_text, 
                     parse_mode='HTML', reply_markup=markup)
    
    logger.info(f"Пользователь {user_id} запустил бота" + (" (админ)" if is_admin(user_id) else ""))

@bot.message_handler(func=lambda message: message.text == '👑 Админ панель')
def admin_panel(message):
    """Обработчик кнопки админ панели"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ У вас нет прав администратора")
        return
    
    stats = get_keys_stats()
    premium_link, premium_version, premium_size = get_client_download_link()
    free_link, free_version, free_size = get_free_client_download_link()
    
    text = (
        "👑 <b>Административная панель</b>\n\n"
        f"📊 <b>Статистика ключей:</b>\n"
        f"• Всего ключей: {stats['total']}\n"
        f"• Неактивированных: {stats['unused']}\n"
        f"• Активированных: {stats['activated']}\n"
        f"• Купленных: {stats['purchased']}\n"
        f"• Бесплатных (админ): {stats['free']}\n\n"
        f"📥 <b>PREMIUM клиент:</b>\n"
        f"• Версия: {premium_version}\n"
        f"• Размер: {premium_size}\n\n"
        f"📥 <b>FREE клиент:</b>\n"
        f"• Версия: {free_version}\n"
        f"• Размер: {free_size}\n\n"
        f"👥 <b>Администраторы:</b> {len(admins)}\n\n"
        f"Выберите действие:"
    )
    
    markup = create_admin_menu()
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📥 FREE версия')
def download_free_client(message):
    """Обработчик кнопки скачивания бесплатной версии клиента"""
    user_id = message.from_user.id
    
    link, version, size = get_free_client_download_link()
    
    text = (
        f"📥 <b>Скачать FREE версию клиента ApexDLC</b>\n\n"
        f"✅ <b>Доступно всем пользователям!</b>\n\n"
        f"📦 Версия: {version}\n"
        f"📏 Размер: {size}\n"
        f"📅 Дата обновления: {client_links.get('free', {}).get('updated_at', 'Неизвестно')[:10] if client_links.get('free', {}).get('updated_at') else 'Неизвестно'}\n\n"
        f"<b>Возможности FREE версии:</b>\n"
        f"• Базовый функционал\n"
        f"• Ограниченный доступ к DLC\n"
        f"• Стандартная поддержка\n\n"
        f"Хотите больше возможностей? Приобретите PREMIUM подписку!\n\n"
        f"Нажмите кнопку ниже для скачивания:"
    )
    
    markup = create_download_button(link, version, size, "📥 Скачать FREE")
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📥 PREMIUM клиент')
def download_premium_client(message):
    """Обработчик кнопки скачивания премиум клиента с проверкой актуальности подписки"""
    user_id = message.from_user.id
    has_apex = check_apex_access(user_id)
    
    # Дополнительная проверка - обновляем статус подписки из базы
    active_sub = get_active_apex_subscription(user_id)
    
    if not has_apex or not active_sub:
        # Если подписка закончилась, но кнопка еще видна
        logger.info(f"Пользователь {user_id} пытался скачать премиум клиент, но подписка истекла")
        
        # Обновляем меню (убираем кнопку премиум клиента)
        markup = create_main_menu(user_id)
        
        bot.reply_to(
            message,
            "❌ <b>Срок действия вашей подписки истек!</b>\n\n"
            "К сожалению, ваша подписка больше не активна.\n"
            "Для доступа к PREMIUM клиенту необходимо продлить подписку.\n\n"
            "Вы можете скачать FREE версию, которая доступна всем!\n\n"
            "👇 Нажмите кнопку ниже чтобы выбрать новый тариф:",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        # Дополнительно отправляем уведомление об истечении подписки
        bot.send_message(
            user_id,
            "⏰ <b>Уведомление об окончании подписки</b>\n\n"
            "Ваша подписка ApexDLC истекла. "
            "Чтобы продолжить пользоваться PREMIUM версией, пожалуйста, продлите подписку.\n\n"
            "FREE версия всегда доступна для всех! 🎮",
            parse_mode='HTML'
        )
        return
    
    # Если подписка активна - показываем ссылку на скачивание
    link, version, size = get_client_download_link()
    
    text = (
        f"📥 <b>Скачать PREMIUM клиент ApexDLC</b>\n\n"
        f"✅ <b>У вас есть активная подписка!</b>\n\n"
        f"📦 Версия: {version}\n"
        f"📏 Размер: {size}\n"
        f"📅 Действует до: {active_sub['expires_at'][:10]}\n"
        f"⏳ Осталось дней: {(datetime.fromisoformat(active_sub['expires_at']) - datetime.now()).days}\n\n"
        f"📅 Дата обновления клиента: {client_links.get('premium', {}).get('updated_at', 'Неизвестно')[:10] if client_links.get('premium', {}).get('updated_at') else 'Неизвестно'}\n\n"
        f"<b>Возможности PREMIUM версии:</b>\n"
        f"• Полный доступ ко всем DLC\n"
        f"• Автоматические обновления\n"
        f"• Приоритетная поддержка\n"
        f"• Безлимитные загрузки\n\n"
        f"Нажмите кнопку ниже для скачивания:"
    )
    
    markup = create_download_button(link, version, size, "📥 Скачать PREMIUM")
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🎮 Купить подписку ApexDLC')
def buy_apex(message):
    """Обработчик кнопки покупки ApexDLC"""
    user_id = message.from_user.id
    has_apex = check_apex_access(user_id)
    apex_sub = get_active_apex_subscription(user_id)
    
    markup = create_apex_menu(user_id)
    
    text = "🎮 <b>Подписки ApexDLC</b>\n\n"
    
    if has_apex and apex_sub:
        expiry = datetime.fromisoformat(apex_sub['expires_at'])
        days_left = (expiry - datetime.now()).days
        text += f"✅ <b>У вас активна подписка:</b> {apex_sub['plan_name']}\n"
        text += f"📅 Осталось дней: {days_left}\n\n"
        text += "🔄 <b>При покупке новой подписки срок будет увеличен!</b>\n\n"
    
    text += (
        "<b>Доступные тарифы:</b>\n\n"
        "🎮 <b>ApexDLC 30 DAYS - 990 ₽ / 99 ⭐</b>\n"
        "• Доступ ко всем DLC\n"
        "• Обновления автоматически\n"
        "• Техподдержка 24/7\n"
        "• Безлимитные загрузки\n\n"
        "🎮 <b>ApexDLC 90 DAYS - 1990 ₽ / 199 ⭐</b>\n"
        "• Всё из 30 DAYS\n"
        "• Скидка 33%\n\n"
        "🎮 <b>ApexDLC 180 DAYS - 2990 ₽ / 299 ⭐</b>\n"
        "• Всё из 30 DAYS\n"
        "• Скидка 50%\n\n"
        "👑 <b>ApexDLC LIFETIME - 4990 ₽ / 499 ⭐</b>\n"
        "• ПОЖИЗНЕННЫЙ ДОСТУП\n"
        "• Все будущие обновления\n"
        "• Приоритетная поддержка\n"
        "• Максимальная скидка 70%\n"
    )
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == '🔑 Активировать ключ')
def activate_key_prompt(message):
    """Обработчик кнопки активации ключа"""
    markup = create_key_menu()
    bot.send_message(
        message.chat.id,
        "🔑 <b>Активация ключа ApexDLC</b>\n\n"
        "Введите ваш ключ в формате:\n"
        "<code>AXXX-XXXXX-XXXXX-XXXXX</code> или <code>AXXXXX-XXXXX-XXXXX-XXXXX</code>\n\n"
        "Примеры правильных ключей:\n"
        "✅ <code>A4B7-9K2M5-7P9Q2-R5T8Y</code> - формат 4-5-5-5\n"
        "✅ <code>A57UV-VW50F-HYJUL-HVHMI</code> - формат 5-5-5-5\n"
        "✅ <code>A3B8-4C7D-9F2G-5H1J</code> - формат 4-4-4-4\n\n"
        "❌ Неправильные примеры:\n"
        "❌ <code>B123-45678-90123-45678</code> - должен начинаться с A\n"
        "❌ <code>A12-34567-89012-34567</code> - слишком короткая первая часть\n\n"
        "Ключ можно вводить с дефисами или без, регистр не важен.\n\n"
        "Или выберите действие:",
        parse_mode='HTML',
        reply_markup=markup
    )
    user_states[message.from_user.id] = {'state': 'waiting_key'}

@bot.message_handler(func=lambda message: message.text == '👤 Профиль')
def profile(message):
    """Обработчик кнопки профиля"""
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    referred_users, total_bonus = get_referral_stats(user_id)
    has_apex = check_apex_access(user_id)
    apex_sub = get_active_apex_subscription(user_id)
    
    profile_text = (
        f"👤 <b>Профиль пользователя</b>\n\n"
        f"🆔 ID: {user_id}\n"
        f"📅 Регистрация: {user_data['registered_at'][:10]}\n"
        f"💰 Баланс: {user_data['balance']} ₽\n"
        f"📊 Всего покупок: {user_data['total_purchases']}\n"
        f"🎁 Бесплатных ключей: {user_data.get('total_free_keys', 0)}\n"
        f"👥 Приглашено: {len(referred_users)}\n"
        f"🎁 Бонусов: {total_bonus} ₽\n\n"
    )
    
    if has_apex and apex_sub:
        expiry = datetime.fromisoformat(apex_sub['expires_at'])
        days_left = (expiry - datetime.now()).days
        profile_text += (
            f"🎮 <b>ApexDLC подписка:</b>\n"
            f"• Тариф: {apex_sub['plan_name']}\n"
            f"• 📅 Действует до: {apex_sub['expires_at'][:10]}\n"
            f"• ⏳ Осталось дней: {days_left}\n\n"
        )
    else:
        profile_text += "❌ <b>Нет активной подписки ApexDLC</b>\n\n"
    
    profile_text += f"🔗 <b>Ваша реферальная ссылка:</b>\n{get_referral_link(user_id)}"
    
    markup = create_profile_menu()
    bot.send_message(message.chat.id, profile_text, 
                     parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📊 Информация')
def info(message):
    """Обработчик кнопки информации"""
    premium_link, premium_version, premium_size = get_client_download_link()
    free_link, free_version, free_size = get_free_client_download_link()
    
    info_text = (
        "📊 <b>Информация о сервисе ApexDLC</b>\n\n"
        "🎮 <b>ApexDLC подписки:</b>\n"
        "• Доступ ко всем DLC\n"
        "• Автоматические обновления\n"
        "• Мгновенная активация\n"
        "• Поддержка 24/7\n\n"
        "📥 <b>Доступные версии клиента:</b>\n"
        f"• FREE версия: v{free_version} ({free_size}) - для всех\n"
        f"• PREMIUM версия: v{premium_version} ({premium_size}) - только для подписчиков\n\n"
        "💰 <b>Система баланса:</b>\n"
        "• Пополняйте баланс и оплачивайте подписки\n"
        "• Получайте бонусы за рефералов\n"
        "• Активируйте промокоды\n\n"
        "🔑 <b>Система ключей:</b>\n"
        "• После покупки вы получаете уникальный ключ\n"
        "• Ключ можно активировать только 1 раз\n"
        "• Ключ привязан к вашему аккаунту\n"
        "• Поддерживаются разные форматы ключей\n"
        "• Купленные ключи помечаются как 💳 Купленный\n"
        "• Ключи от администратора как 💳 Платный\n\n"
        "⚡ <b>Преимущества:</b>\n"
        "• Мгновенная активация после оплаты\n"
        "• Круглосуточная поддержка\n"
        "• Гибкие тарифы\n"
        "• Оплата в Telegram Stars\n\n"
        "💳 <b>Способы оплаты:</b>\n"
        "• 💳 С баланса (рубли)\n"
        "• ⭐ Telegram Stars\n"
        "• 💳 Банковская карта РФ (ЮKassa)\n"
        "• ₿ Криптовалюта (по запросу)\n\n"
        "📞 <b>Контакты:</b>\n"
        "• Поддержка: @apexdlc_support\n"
        "• Канал: @apexdlc_news"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📧 Тех.Поддержка", callback_data="support"))
    bot.send_message(message.chat.id, info_text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🆘 Тех.Поддержка')
def support(message):
    """Обработчик кнопки техподдержки"""
    support_text = (
        "🆘 <b>Техническая поддержка ApexDLC</b>\n\n"
        "📧 <b>Связь с поддержкой:</b>\n"
        "• @apexdlc_support - оперативная помощь (ответ до 30 мин)\n"
        "• support@apex-dlc.ru - email\n\n"
        "❓ <b>Частые вопросы:</b>\n"
        "• Как активировать ключ ApexDLC?\n"
        "• Не работает доступ к DLC\n"
        "• Как продлить подписку?\n"
        "• Как пополнить баланс?\n"
        "• Как активировать промокод?\n"
        "• Способы оплаты\n"
        "• Потерял ключ доступа\n"
        "• Чем отличается FREE от PREMIUM версии?\n"
        "• В чем разница между 💳 Купленный и 💳 Платный?\n\n"
        "⏰ <b>Время работы:</b>\n"
        "• Пн-Пт: 10:00 - 22:00 МСК\n"
        "• Сб-Вс: 12:00 - 20:00 МСК\n\n"
        "👇 Нажмите кнопку ниже для связи"
    )
    
    markup = create_support_menu()
    bot.send_message(message.chat.id, support_text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '👥 Реферальная система')
def referral_system(message):
    """Обработчик реферальной системы"""
    user_id = message.from_user.id
    referred_users, total_bonus = get_referral_stats(user_id)
    
    referral_text = (
        "👥 <b>Реферальная система ApexDLC</b>\n\n"
        "🎁 <b>Как это работает:</b>\n"
        "• Приглашайте друзей по вашей ссылке\n"
        "• За каждого приглашенного - 50 ₽ на баланс\n"
        "• Друг получает скидку 10% на первую покупку\n"
        "• Бонус начисляется после первой покупки друга\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n"
        f"{get_referral_link(user_id)}\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Приглашено: {len(referred_users)} чел.\n"
        f"• Заработано бонусов: {total_bonus} ₽\n\n"
    )
    
    if referred_users:
        referral_text += "📋 <b>Последние приглашения:</b>\n"
        for ref in referred_users[-5:]:
            ref_date = datetime.fromisoformat(ref['referred_at']).strftime('%d.%m.%Y')
            referral_text += f"• {ref_date} - Пользователь {ref['user_id'][:8]}...\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎁 Получить бонус", callback_data="get_bonus"))
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    
    bot.send_message(message.chat.id, referral_text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '⚙️ Настройки')
def settings(message):
    """Обработчик настроек"""
    settings_text = (
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете настроить параметры бота\n\n"
        "Доступные настройки:\n"
        "• Уведомления о статусе подписки\n"
        "• Напоминания о продлении\n"
        "• Автопродление подписки\n"
        "• Язык интерфейса\n\n"
        "<i>⚡ Функция в разработке</i>"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    
    bot.send_message(message.chat.id, settings_text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(commands=['admin_status'])
def admin_status(message):
    """Команда для проверки статуса администратора (только для отладки)"""
    user_id = message.from_user.id
    
    status_text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: {user_id}\n"
        f"👑 Администратор: {'✅ Да' if is_admin(user_id) else '❌ Нет'}\n"
        f"📋 Список админов: {admins}\n"
        f"🔑 Тип ID: {type(user_id)}\n"
        f"🎮 Подписка: {'✅ Есть' if check_apex_access(user_id) else '❌ Нет'}\n"
        f"💰 Баланс: {get_user_balance(user_id)} ₽\n"
    )
    
    bot.reply_to(message, status_text, parse_mode='HTML')

# ========== ОБРАБОТЧИКИ INLINE КНОПОК ==========

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    markup = create_main_menu(call.from_user.id)
    bot.send_message(
        call.message.chat.id,
        "✨ <b>Главное меню</b>",
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "my_apex_subs")
def my_apex_subs_callback(call):
    user_id = call.from_user.id
    user_subs = get_user_apex_subscriptions(user_id)
    active_subs = [s for s in user_subs if s.get('active') and datetime.fromisoformat(s['expires_at']) > datetime.now()]
    
    if not active_subs:
        text = "📭 <b>У вас нет активных ApexDLC подписок</b>"
    else:
        text = "🎮 <b>Ваши ApexDLC подписки</b>\n\n"
        for sub in active_subs:
            expiry = datetime.fromisoformat(sub['expires_at'])
            days_left = (expiry - datetime.now()).days
            text += (
                f"🔹 <b>{sub['plan_name']}</b>\n"
                f"• 📅 Приобретена: {sub['created_at'][:10]}\n"
                f"• 📅 Действует до: {sub['expires_at'][:10]}\n"
                f"• ⏳ Осталось дней: {days_left}\n"
                f"• ✅ Статус: Активна\n\n"
            )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎮 Купить еще", callback_data="apex_menu"))
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "my_keys")
def my_keys_callback(call):
    user_id = call.from_user.id
    user_keys = get_user_keys(user_id)
    
    if not user_keys:
        text = "📭 <b>У вас нет ключей</b>"
    else:
        text = "🔑 <b>Ваши ключи</b>\n\n"
        for key_data in user_keys[:10]:
            status_emoji = "✅" if key_data['status'] == 'activated' else "⏳"
            type_display = "💳 Купленный" if key_data.get('is_purchased') else "💳 Платный"
            plan = APEX_PLANS.get(key_data['plan_id'], {'name': key_data['plan_id']})
            text += f"{status_emoji} {type_display} <code>{key_data['key']}</code> - {plan['name']}\n"
            if key_data['status'] == 'activated':
                text += f"   Активирован: {key_data['activated_at'][:10]}\n\n"
            else:
                text += f"   Статус: Ожидает активации\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_key")
def check_key_callback(call):
    bot.edit_message_text(
        "🔑 <b>Проверка ключа</b>\n\n"
        "Введите ключ для проверки статуса:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    user_states[call.from_user.id] = {'state': 'checking_key'}
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "history")
def history_callback(call):
    user_id = call.from_user.id
    user_payments = [p for p in payments if p.get('user_id') == str(user_id)]
    
    if not user_payments:
        text = "📜 <b>История операций пуста</b>"
    else:
        text = "📜 <b>История операций</b>\n\n"
        for p in user_payments[-10:]:
            status_emoji = "✅" if p['status'] == 'completed' else "⏳" if p['status'] == 'pending' else "❌"
            date = datetime.fromisoformat(p['created_at']).strftime('%d.%m.%Y')
            method_emoji = "💳" if p.get('method') == 'balance' else "⭐" if p.get('method') == 'stars' else "💳"
            text += f"{status_emoji} {method_emoji} {date} - {p['amount']} {p['currency']} - {p['description'][:30]}...\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "activate_promo")
def activate_promo_callback(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
    
    bot.edit_message_text(
        "🎁 <b>Активация промокода</b>\n\n"
        "Введите промокод в чат:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    user_states[call.from_user.id] = {'state': 'waiting_promo'}
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "support")
def support_callback(call):
    bot.edit_message_text(
        "🆘 <b>Техническая поддержка ApexDLC</b>\n\n"
        "📧 @apexdlc_support - оперативная помощь\n\n"
        "👇 Нажмите кнопку ниже для связи",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=create_support_menu()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "faq")
def faq_callback(call):
    faq_text = (
        "❓ <b>Часто задаваемые вопросы</b>\n\n"
        "1️⃣ <b>Как активировать ключ ApexDLC?</b>\n"
        "   После покупки вы получите уникальный ключ.\n"
        "   Нажмите 'Активировать ключ' и введите его.\n\n"
        "2️⃣ <b>Можно ли активировать ключ несколько раз?</b>\n"
        "   Нет, каждый ключ можно активировать только 1 раз.\n"
        "   Ключ привязывается к вашему аккаунту.\n\n"
        "3️⃣ <b>Что делать, если я потерял ключ?</b>\n"
        "   Ваш ключ всегда доступен в разделе 'Мои ключи'.\n"
        "   Также можно запросить у поддержки.\n\n"
        "4️⃣ <b>Как продлить подписку?</b>\n"
        "   Купите новую подписку - срок увеличится.\n\n"
        "5️⃣ <b>Как пополнить баланс?</b>\n"
        "   Нажмите 'Профиль' -> 'Пополнить баланс' и выберите сумму.\n\n"
        "6️⃣ <b>Как активировать промокод?</b>\n"
        "   Нажмите 'Профиль' -> 'Активировать промокод' и введите код.\n\n"
        "7️⃣ <b>Где скачать клиент?</b>\n"
        "   FREE версия доступна всем в главном меню.\n"
        "   PREMIUM версия появляется после активации подписки.\n\n"
        "8️⃣ <b>Чем отличается FREE от PREMIUM?</b>\n"
        "   PREMIUM: полный доступ ко всем DLC, автообновления, приоритетная поддержка\n"
        "   FREE: базовый функционал, ограниченный доступ\n\n"
        "9️⃣ <b>В чем разница между 💳 Купленный и 💳 Платный?</b>\n"
        "   💳 Купленный - ключ, приобретенный через оплату\n"
        "   💳 Платный - ключ, выданный администратором\n\n"
        "🔟 <b>Способы оплаты</b>\n"
        "   • 💳 С баланса (рубли)\n"
        "   • ⭐ Telegram Stars\n"
        "   • 💳 Банковская карта РФ\n"
        "   • ₿ Криптовалюта (по запросу)"
    )
    bot.edit_message_text(
        faq_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=create_support_menu()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "get_bonus")
def get_bonus_callback(call):
    user_id = call.from_user.id
    referred_users, total_bonus = get_referral_stats(user_id)
    
    # Проверяем, есть ли невыплаченные бонусы
    unpaid_bonus = 0
    for uid, data in referrals.items():
        if data.get('referred_by') == str(user_id) and not data.get('bonus_paid'):
            # Проверяем, сделал ли реферал покупку
            user_data = get_user(uid)
            if user_data.get('total_purchases', 0) > 0:
                unpaid_bonus += 50
    
    if unpaid_bonus > 0:
        update_user_balance(user_id, unpaid_bonus)
        
        # Отмечаем бонусы как выплаченные
        for uid, data in referrals.items():
            if data.get('referred_by') == str(user_id) and not data.get('bonus_paid'):
                user_data = get_user(uid)
                if user_data.get('total_purchases', 0) > 0:
                    data['bonus_paid'] = True
        save_json(REFERRALS_FILE, referrals)
        
        bot.answer_callback_query(call.id, f"✅ Бонус {unpaid_bonus} ₽ зачислен!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Нет доступных бонусов", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "admin_create_key")
def admin_create_key_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    markup = create_key_type_menu()
    bot.edit_message_text(
        "🔑 <b>Создание ключа</b>\n\n"
        "Выберите тариф для ключа:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_all_keys")
def admin_all_keys_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    all_keys = get_all_keys(20)
    
    if not all_keys:
        text = "📭 <b>Ключи не найдены</b>"
    else:
        text = "🔑 <b>Последние ключи:</b>\n\n"
        for key_data in all_keys:
            plan = APEX_PLANS.get(key_data['plan_id'], {'name': 'Unknown'})
            status_emoji = "✅" if key_data['status'] == 'activated' else "⏳"
            type_display = "💳 Купленный" if key_data.get('is_purchased') else "💳 Платный"
            text += f"{status_emoji} {type_display} <code>{key_data['key']}</code> - {plan['name']}\n"
            text += f"   Статус: {key_data['status']}\n"
            if key_data['status'] == 'activated':
                text += f"   Активирован: {key_data['activated_by']}\n"
            text += "\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    key_stats = get_keys_stats()
    
    # Статистика по пользователям
    total_users = len(users)
    users_with_sub = sum(1 for u in subscriptions.values() if u)
    
    # Статистика по платежам
    total_payments = len(payments)
    completed_payments = sum(1 for p in payments if p['status'] == 'completed')
    total_revenue = sum(p['amount'] for p in payments if p['status'] == 'completed' and p['currency'] == 'RUB')
    balance_payments = sum(1 for p in payments if p.get('method') == 'balance')
    balance_total = sum(p['amount'] for p in payments if p.get('method') == 'balance' and p['status'] == 'completed')
    
    text = (
        "📊 <b>Полная статистика</b>\n\n"
        f"🔑 <b>Ключи:</b>\n"
        f"• Всего: {key_stats['total']}\n"
        f"• Неактивированных: {key_stats['unused']}\n"
        f"• Активированных: {key_stats['activated']}\n"
        f"• Купленных: {key_stats['purchased']}\n"
        f"• Бесплатных (админ): {key_stats['free']}\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: {total_users}\n"
        f"• С подпиской: {users_with_sub}\n"
        f"• Админов: {len(admins)}\n\n"
        f"💰 <b>Платежи:</b>\n"
        f"• Всего операций: {total_payments}\n"
        f"• Успешных: {completed_payments}\n"
        f"• Выручка всего: {total_revenue} ₽\n"
        f"• Оплата с баланса: {balance_payments} операций на {balance_total} ₽\n"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    recent_users = sorted(users.items(), key=lambda x: x[1]['registered_at'], reverse=True)[:10]
    
    text = "👥 <b>Последние пользователи:</b>\n\n"
    for uid, user_data in recent_users:
        has_sub = "✅" if check_apex_access(uid) else "❌"
        text += f"{has_sub} ID: {uid} - {user_data['registered_at'][:10]}\n"
        text += f"   Покупок: {user_data['total_purchases']}, Баланс: {user_data['balance']} ₽\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_client_settings")
def admin_client_settings_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    markup = create_client_settings_menu()
    premium_link, premium_version, premium_size = get_client_download_link()
    free_link, free_version, free_size = get_free_client_download_link()
    
    bot.edit_message_text(
        f"📥 <b>Настройки клиентов</b>\n\n"
        f"<b>PREMIUM клиент:</b>\n"
        f"Ссылка: {premium_link}\n"
        f"Версия: {premium_version}\n"
        f"Размер: {premium_size}\n\n"
        f"<b>FREE клиент:</b>\n"
        f"Ссылка: {free_link}\n"
        f"Версия: {free_version}\n"
        f"Размер: {free_size}\n\n"
        f"Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "client_change_premium")
def client_change_premium_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    user_states[call.from_user.id] = {'state': 'admin_waiting_premium_link'}
    bot.edit_message_text(
        "📥 <b>Изменение ссылки на PREMIUM клиент</b>\n\n"
        "Введите новую ссылку для скачивания PREMIUM клиента:\n\n"
        "Формат: <code>https://example.com/premium.apk</code>\n\n"
        "После ссылки можно указать версию и размер через пробел:\n"
        "<code>https://example.com/premium.apk 2.0.0 200 MB</code>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "client_change_free")
def client_change_free_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    user_states[call.from_user.id] = {'state': 'admin_waiting_free_link'}
    bot.edit_message_text(
        "📥 <b>Изменение ссылки на FREE клиент</b>\n\n"
        "Введите новую ссылку для скачивания FREE клиента:\n\n"
        "Формат: <code>https://example.com/free.apk</code>\n\n"
        "После ссылки можно указать версию и размер через пробел:\n"
        "<code>https://example.com/free.apk 1.0.0 100 MB</code>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "client_show_links")
def client_show_links_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    premium_link, premium_version, premium_size = get_client_download_link()
    free_link, free_version, free_size = get_free_client_download_link()
    
    text = (
        f"📥 <b>Текущие ссылки на клиенты</b>\n\n"
        f"<b>PREMIUM клиент:</b>\n"
        f"🔗 Ссылка: {premium_link}\n"
        f"📦 Версия: {premium_version}\n"
        f"📏 Размер: {premium_size}\n\n"
        f"<b>FREE клиент:</b>\n"
        f"🔗 Ссылка: {free_link}\n"
        f"📦 Версия: {free_version}\n"
        f"📏 Размер: {free_size}\n\n"
        f"📅 PREMIUM обновлено: {client_links.get('premium', {}).get('updated_at', 'Неизвестно')[:10]}\n"
        f"📅 FREE обновлено: {client_links.get('free', {}).get('updated_at', 'Неизвестно')[:10]}"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_client_settings"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_promocodes")
def admin_promocodes_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    markup = create_promocode_menu()
    bot.edit_message_text(
        "🎁 <b>Управление промокодами</b>\n\n"
        "Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_create_promo")
def admin_create_promo_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    user_states[call.from_user.id] = {'state': 'admin_waiting_promo_amount'}
    bot.edit_message_text(
        "🎁 <b>Создание промокода</b>\n\n"
        "Введите сумму бонуса в рублях:\n\n"
        "Пример: <code>100</code> - промокод на 100 ₽\n\n"
        "После суммы можно указать лимит использований и срок действия через пробел:\n"
        "<code>100 5 30</code> - 100 ₽, 5 использований, 30 дней",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_all_promos")
def admin_all_promos_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    all_promos = get_all_promocodes()
    
    if not all_promos:
        text = "📭 <b>Промокоды не найдены</b>"
    else:
        text = "🎁 <b>Все промокоды:</b>\n\n"
        for promo in all_promos[-10:]:
            status = "✅ Активен" if promo.get('active', True) and datetime.now() < datetime.fromisoformat(promo['expires_at']) else "❌ Неактивен"
            text += f"Код: <code>{promo['code']}</code>\n"
            text += f"💰 Сумма: {promo['amount']} ₽\n"
            text += f"📊 Использовано: {promo['used_count']}/{promo['max_uses']}\n"
            text += f"📅 Действует до: {promo['expires_at'][:10]}\n"
            text += f"📌 Статус: {status}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promocodes"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add")
def admin_add_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    user_states[call.from_user.id] = {'state': 'admin_waiting_new_admin'}
    bot.edit_message_text(
        "➕ <b>Добавление администратора</b>\n\n"
        "Введите Telegram ID пользователя, которого хотите сделать админом:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_remove")
def admin_remove_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    admin_list = "\n".join([f"• {admin_id}" for admin_id in admins])
    user_states[call.from_user.id] = {'state': 'admin_waiting_remove_admin'}
    
    bot.edit_message_text(
        f"➖ <b>Удаление администратора</b>\n\n"
        f"Текущие администраторы:\n{admin_list}\n\n"
        f"Введите ID пользователя, которого хотите удалить из админов:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_payments")
def admin_payments_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    recent_payments = sorted(payments, key=lambda x: x['created_at'], reverse=True)[:10]
    
    if not recent_payments:
        text = "📭 <b>Платежи не найдены</b>"
    else:
        text = "💰 <b>Последние платежи:</b>\n\n"
        for p in recent_payments:
            status_emoji = "✅" if p['status'] == 'completed' else "⏳" if p['status'] == 'pending' else "❌"
            date = datetime.fromisoformat(p['created_at']).strftime('%d.%m.%Y')
            method_emoji = "💳" if p.get('method') == 'balance' else "⭐" if p.get('method') == 'stars' else "💳"
            text += f"{status_emoji} {method_emoji} {date} - {p['user_id']} - {p['amount']} {p['currency']}\n"
            text += f"   {p['description'][:50]}...\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    user_states[call.from_user.id] = {'state': 'admin_waiting_balance_user'}
    bot.edit_message_text(
        "💳 <b>Начисление баланса пользователю</b>\n\n"
        "Введите ID пользователя и сумму через пробел:\n\n"
        "Пример: <code>123456789 1000</code>\n\n"
        "Сумма может быть положительной (начисление) или отрицательной (списание).",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("keytype_"))
def keytype_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    plan_id = call.data.replace("keytype_", "")
    markup = create_key_target_menu(plan_id)
    
    plan = APEX_PLANS.get(plan_id)
    bot.edit_message_text(
        f"🔑 <b>Создание ключа для {plan['name']}</b>\n\n"
        f"💰 Стоимость: {plan['price_rub']} ₽ / {plan['price_stars']} ⭐\n\n"
        f"Кому выдать ключ?",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("keytarget_self_"))
def keytarget_self_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    user_id = call.from_user.id
    plan_id = call.data.replace("keytarget_self_", "")
    plan = APEX_PLANS.get(plan_id)
    
    # Генерируем бесплатный ключ для админа
    key = generate_key(plan_id, user_id, created_by=user_id, is_free=True, is_purchased=False)
    
    bot.edit_message_text(
        f"✅ <b>Бесплатный ключ создан!</b>\n\n"
        f"🎮 <b>Тариф:</b> {plan['name']}\n"
        f"🔑 <b>Ваш ключ:</b>\n"
        f"<code>{key}</code>\n\n"
        f"Вы можете активировать его через меню '🔑 Активировать ключ'",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    
    # Отправляем уведомление админу в личку
    bot.send_message(
        user_id,
        f"✅ <b>Создан бесплатный ключ</b>\n\n"
        f"🎮 Тариф: {plan['name']}\n"
        f"🔑 Ключ: <code>{key}</code>",
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id, "✅ Ключ создан!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("keytarget_other_"))
def keytarget_other_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    plan_id = call.data.replace("keytarget_other_", "")
    user_states[call.from_user.id] = {'state': 'admin_waiting_user_id', 'plan_id': plan_id}
    
    bot.edit_message_text(
        "👤 <b>Выдача ключа другому пользователю</b>\n\n"
        "Введите Telegram ID пользователя (число):\n\n"
        "<i>ID можно узнать в профиле пользователя</i>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_profile")
def back_to_profile_callback(call):
    # Создаем объект message из call для передачи в функцию profile
    class MockMessage:
        def __init__(self, chat, from_user):
            self.chat = chat
            self.from_user = from_user
    
    mock_message = MockMessage(call.message.chat, call.from_user)
    profile(mock_message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def back_to_admin_panel_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    
    # Создаем объект message из call для передачи в функцию admin_panel
    class MockMessage:
        def __init__(self, chat, from_user):
            self.chat = chat
            self.from_user = from_user
    
    mock_message = MockMessage(call.message.chat, call.from_user)
    admin_panel(mock_message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "apex_menu")
def apex_menu_callback(call):
    user_id = call.from_user.id
    markup = create_apex_menu(user_id)
    bot.edit_message_text(
        "🎮 <b>Выберите тариф ApexDLC:</b>\n\n"
        "• 30 DAYS - 30 дней доступа\n"
        "• 90 DAYS - 90 дней (скидка 33%)\n"
        "• 180 DAYS - 180 дней (скидка 50%)\n"
        "• LIFETIME - пожизненный доступ (скидка 70%)\n\n"
        "<i>Все тарифы включают полный доступ ко всем DLC</i>\n\n"
        f"💰 Ваш баланс: {get_user_balance(user_id)} ₽",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_stars_"))
def pay_stars_callback(call):
    user_id = call.from_user.id
    data = call.data.replace("pay_stars_", "")
    
    logger.info(f"Оплата звездами: {data} от пользователя {user_id}")
    
    if data.startswith("deposit_"):
        amount = int(data.split("_")[1])
        success = create_stars_invoice(
            user_id, 
            amount // 10, 
            f"Пополнение баланса на {amount} ₽",
            f"Пополнение баланса ApexDLC"
        )
        if success:
            bot.answer_callback_query(call.id, "✅ Счет создан! Проверьте сообщение от бота.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка создания счета", show_alert=True)
    else:
        plan = APEX_PLANS.get(data)
        if plan:
            success = create_stars_invoice(
                user_id,
                plan['price_stars'],
                f"ApexDLC: {plan['name']}",
                f"Покупка подписки ApexDLC"
            )
            if success:
                bot.answer_callback_query(call.id, "✅ Счет создан! Проверьте сообщение от бота.", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка создания счета", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ План не найден", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_balance_"))
def pay_balance_callback(call):
    user_id = call.from_user.id
    plan_id = call.data.replace("pay_balance_", "")
    
    logger.info(f"Оплата с баланса: {plan_id} от пользователя {user_id}")
    
    plan = APEX_PLANS.get(plan_id)
    if not plan:
        bot.answer_callback_query(call.id, "❌ План не найден", show_alert=True)
        return
    
    # Обрабатываем оплату с баланса
    success, result = process_balance_payment(user_id, plan_id)
    
    if success:
        key = result
        
        # Обновляем сообщение
        bot.edit_message_text(
            f"✅ <b>Оплата с баланса прошла успешно!</b>\n\n"
            f"🎮 <b>Тариф:</b> {plan['name']}\n"
            f"🔑 <b>Ваш ключ активации:</b>\n"
            f"<code>{key}</code>\n\n"
            f"📝 <b>Инструкция:</b>\n"
            f"1. Скопируйте ключ выше\n"
            f"2. Нажмите кнопку '🔑 Активировать ключ'\n"
            f"3. Вставьте ключ и активируйте\n\n"
            f"<i>Ключ можно активировать только 1 раз!</i>\n\n"
            f"4. После активации появится кнопка для скачивания PREMIUM клиента",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
        # Отправляем ключ в личку для сохранности
        bot.send_message(
            user_id,
            f"✅ <b>Ключ активации (сохраните его):</b>\n\n"
            f"🎮 Тариф: {plan['name']}\n"
            f"🔑 Ключ: <code>{key}</code>\n\n"
            f"Активируйте его в меню '🔑 Активировать ключ'",
            parse_mode='HTML'
        )
        
        bot.answer_callback_query(call.id, f"✅ Оплата успешна! Ключ сгенерирован.", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ {result}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_card_"))
def pay_card_callback(call):
    user_id = call.from_user.id
    data = call.data.replace("pay_card_", "")
    
    logger.info(f"Оплата картой: {data} от пользователя {user_id}")
    
    if not YKASSA_SHOP_ID or not YKASSA_SECRET_KEY:
        bot.answer_callback_query(call.id, "❌ Оплата картой временно недоступна", show_alert=True)
        return
    
    if data.startswith("deposit_"):
        amount = int(data.split("_")[1])
        description = f"Пополнение баланса ApexDLC на {amount} ₽"
        payment_url = create_yookassa_payment_link(user_id, amount, description)
        item_display = f"deposit_{amount}"
    else:
        plan = APEX_PLANS.get(data)
        if plan:
            description = f"ApexDLC: {plan['name']}"
            payment_url = create_yookassa_payment_link(user_id, plan['price_rub'], description)
            item_display = f"apex_{data}"
        else:
            payment_url = None
    
    if payment_url:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💳 Перейти к оплате", url=payment_url))
        markup.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_payment_{item_display}"))
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment"))
        
        bot.edit_message_text(
            f"💳 <b>Оплата картой</b>\n\n"
            f"1️⃣ Нажмите 'Перейти к оплате'\n"
            f"2️⃣ Оплатите на сайте ЮKassa\n"
            f"3️⃣ Нажмите 'Я оплатил'\n\n"
            f"<i>После оплаты вы получите ключ активации</i>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "✅ Ссылка для оплаты создана!", show_alert=False)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка создания платежа", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_payment_"))
def check_payment_callback(call):
    user_id = call.from_user.id
    data = call.data.replace("check_payment_", "")
    
    logger.info(f"Проверка платежа: {data} от пользователя {user_id}")
    
    # Ищем последний платеж пользователя
    user_payments = [p for p in payments if p.get('user_id') == str(user_id) and p.get('method') == 'yookassa']
    
    if not user_payments:
        bot.answer_callback_query(call.id, "❌ Платеж не найден", show_alert=True)
        return
    
    latest_payment = user_payments[-1]
    payment_id = latest_payment['id']
    
    # Проверяем статус
    payment_info = check_yookassa_payment_status(payment_id)
    
    if payment_info and payment_info.get('status') == 'succeeded':
        if latest_payment['status'] != 'completed':
            # Обновляем статус платежа
            latest_payment['status'] = 'completed'
            save_json(PAYMENTS_FILE, payments)
            
            if data.startswith("deposit_"):
                amount = int(data.split("_")[1])
                update_user_balance(user_id, amount)
                bot.answer_callback_query(call.id, f"✅ Баланс пополнен на {amount} ₽", show_alert=True)
                
                bot.edit_message_text(
                    f"✅ <b>Баланс пополнен!</b>\n\n"
                    f"💰 Сумма: {amount} ₽\n"
                    f"Спасибо за использование ApexDLC!",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )
            
            elif data.startswith("apex_"):
                plan_id = data.replace("apex_", "")
                plan = APEX_PLANS.get(plan_id)
                
                if plan:
                    # Генерируем ключ (купленный)
                    key = generate_key(plan_id, user_id, is_purchased=True)
                    
                    # Отправляем ключ пользователю
                    key_text = (
                        f"✅ <b>Оплата прошла успешно!</b>\n\n"
                        f"🎮 <b>Тариф:</b> {plan['name']}\n"
                        f"🔑 <b>Ваш ключ активации:</b>\n"
                        f"<code>{key}</code>\n\n"
                        f"📝 <b>Инструкция:</b>\n"
                        f"1. Скопируйте ключ выше\n"
                        f"2. Нажмите кнопку '🔑 Активировать ключ'\n"
                        f"3. Вставьте ключ и активируйте\n\n"
                        f"<i>Ключ можно активировать только 1 раз!</i>\n\n"
                        f"4. После активации появится кнопка для скачивания PREMIUM клиента"
                    )
                    
                    bot.send_message(user_id, key_text, parse_mode='HTML')
                    
                    bot.edit_message_text(
                        f"✅ <b>Платеж подтвержден!</b>\n\n"
                        f"Ключ активации отправлен в личные сообщения.",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='HTML'
                    )
                    
                    bot.answer_callback_query(call.id, f"✅ Платеж подтвержден! Ключ отправлен.", show_alert=True)
    elif payment_info and payment_info.get('status') == 'pending':
        bot.answer_callback_query(call.id, "⏳ Платеж еще не завершен", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Платеж не найден", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_payment")
def cancel_payment_callback(call):
    bot.edit_message_text(
        "❌ Оплата отменена",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id, "❌ Оплата отменена")

@bot.callback_query_handler(func=lambda call: call.data.startswith("apex_"))
def apex_selection_callback(call):
    user_id = call.from_user.id
    plan_id = call.data.replace("apex_", "")
    
    logger.info(f"Выбор тарифа: {plan_id} от пользователя {user_id}")
    
    plan = APEX_PLANS.get(plan_id)
    if not plan:
        bot.answer_callback_query(call.id, "❌ План не найден", show_alert=True)
        return
    
    # Проверяем текущую подписку
    has_apex = check_apex_access(user_id)
    apex_sub = get_active_apex_subscription(user_id)
    
    # Получаем баланс пользователя
    user_balance = get_user_balance(user_id)
    
    # Формируем описание тарифа
    features_text = "\n".join([f"  {f}" for f in plan['features']])
    
    text = (
        f"🎮 <b>{plan['name']}</b>\n\n"
        f"💰 Цена: {plan['price_rub']} ₽ / {plan['price_stars']} ⭐\n"
        f"📅 Длительность: {plan['duration_days']} дней\n\n"
        f"<b>Что включено:</b>\n{features_text}\n\n"
        f"💳 <b>Ваш баланс:</b> {user_balance} ₽\n\n"
    )
    
    if has_apex and apex_sub:
        text += f"🔄 <b>При покупке текущая подписка будет продлена!</b>\n"
        text += f"📅 Текущая действует до: {apex_sub['expires_at'][:10]}\n\n"
    
    text += "Выберите способ оплаты:"
    
    markup = create_payment_method_menu(plan_id, plan['price_rub'], plan['price_stars'], user_balance)
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def deposit_callback(call):
    markup = create_deposit_menu()
    bot.edit_message_text(
        "💰 <b>Пополнение баланса</b>\n\n"
        "Выберите сумму пополнения:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("deposit_") and len(call.data.split("_")) == 2)
def deposit_amount_callback(call):
    amount = int(call.data.split("_")[1])
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton(
        f"⭐ Оплатить звездами ({amount // 10} ⭐)", 
        callback_data=f"pay_stars_deposit_{amount}"
    )
    btn2 = types.InlineKeyboardButton(
        f"💳 Оплатить картой ({amount} ₽)", 
        callback_data=f"pay_card_deposit_{amount}"
    )
    btn3 = types.InlineKeyboardButton("◀️ Назад", callback_data="deposit")
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    bot.edit_message_text(
        f"💰 <b>Пополнение на {amount} ₽</b>\n\n"
        f"Выберите способ оплаты:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    """Обработка предварительного запроса перед оплатой звездами"""
    try:
        logger.info(f"Pre-checkout query: {pre_checkout_query.invoice_payload}")
        bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=True
        )
    except Exception as e:
        logger.error(f"Ошибка в pre-checkout: {e}")
        bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message="Произошла ошибка. Попробуйте позже."
        )

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    """Обработка успешного платежа звездами"""
    user_id = message.from_user.id
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    total_amount = payment_info.total_amount
    
    logger.info(f"Успешный платеж звездами от пользователя {user_id}, сумма: {total_amount}")
    
    # Создаем запись о платеже
    payment_record = {
        'id': f"stars_{user_id}_{int(time.time())}",
        'user_id': str(user_id),
        'amount': total_amount,
        'currency': payment_info.currency,
        'status': 'completed',
        'method': 'stars',
        'telegram_charge_id': payment_info.telegram_payment_charge_id,
        'payload': payload,
        'created_at': datetime.now().isoformat()
    }
    
    payments.append(payment_record)
    save_json(PAYMENTS_FILE, payments)
    
    # Определяем, что куплено
    if "deposit" in payload.lower():
        # Пополнение баланса
        amount_rub = total_amount * 10  # Конвертация звезд в рубли
        update_user_balance(user_id, amount_rub)
        
        bot.send_message(
            user_id,
            f"✅ <b>Баланс пополнен!</b>\n\n"
            f"💰 Сумма: {amount_rub} ₽\n"
            f"⭐ Оплачено: {total_amount} звезд\n\n"
            f"Текущий баланс: {get_user_balance(user_id)} ₽",
            parse_mode='HTML'
        )
    else:
        # Покупка подписки (для примера 30 DAYS)
        plan_id = '30_days'
        plan = APEX_PLANS.get(plan_id)
        
        if plan:
            # Генерируем ключ (купленный)
            key = generate_key(plan_id, user_id, is_purchased=True)
            
            # Отправляем ключ пользователю
            key_text = (
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"🎮 <b>Тариф:</b> {plan['name']}\n"
                f"🔑 <b>Ваш ключ активации:</b>\n"
                f"<code>{key}</code>\n\n"
                f"📝 <b>Инструкция:</b>\n"
                f"1. Скопируйте ключ выше\n"
                f"2. Нажмите кнопку '🔑 Активировать ключ'\n"
                f"3. Вставьте ключ и активируйте\n\n"
                f"<i>Ключ можно активировать только 1 раз!</i>\n\n"
                f"4. После активации появится кнопка для скачивания PREMIUM клиента"
            )
            
            bot.send_message(user_id, key_text, parse_mode='HTML')
    
    # Возвращаем в главное меню
    markup = create_main_menu(user_id)
    bot.send_message(
        user_id,
        "✨ <b>Главное меню</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    state = user_states.get(user_id, {}).get('state', 'main')
    
    # Проверяем статус подписки при любом действии
    has_apex = check_apex_access(user_id)
    active_sub = get_active_apex_subscription(user_id)
    
    # Если у пользователя есть истекшие подписки в истории
    user_subs = get_user_apex_subscriptions(user_id)
    expired_subs = [s for s in user_subs if not s.get('active') or datetime.fromisoformat(s['expires_at']) <= datetime.now()]
    
    if expired_subs and not has_apex and text not in ['🎮 Купить подписку ApexDLC', '🔑 Активировать ключ', '/start', '/help', '📥 FREE версия']:
        # Была подписка, но истекла
        last_expired = expired_subs[-1]
        
        # Проверяем, не отправляли ли уже уведомление сегодня
        last_notification_key = f"last_expiry_notification_{user_id}"
        last_notification = user_states.get(user_id, {}).get(last_notification_key)
        
        if not last_notification or (datetime.now() - datetime.fromisoformat(last_notification)).days >= 1:
            # Отправляем уведомление не чаще раза в день
            bot.send_message(
                user_id,
                f"⏰ <b>Напоминание</b>\n\n"
                f"Ваша подписка на тариф {last_expired['plan_name']} истекла {last_expired['expires_at'][:10]}.\n\n"
                f"Хотите продлить? Нажмите '🎮 Купить подписку ApexDLC' для выбора тарифа.\n\n"
                f"FREE версия всегда доступна для всех!",
                parse_mode='HTML'
            )
            
            # Сохраняем время последнего уведомления
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id][last_notification_key] = datetime.now().isoformat()
    
    if state == 'waiting_key':
        # Активация ключа
        key = text
        
        # Пытаемся активировать
        success, result = activate_key(user_id, key)
        
        if success:
            # Активация успешна
            subscription = result
            plan = APEX_PLANS.get(subscription['plan_id'])
            
            reply_text = (
                f"✅ <b>Ключ успешно активирован!</b>\n\n"
                f"🎮 <b>Тариф:</b> {subscription['plan_name']}\n"
                f"📅 <b>Действует до:</b> {subscription['expires_at'][:10]}\n\n"
                f"📥 <b>Теперь вы можете скачать PREMIUM клиент</b>\n"
                f"Кнопка '📥 PREMIUM клиент' появилась в главном меню.\n\n"
                f"FREE версия также доступна для всех!\n\n"
                f"Спасибо за использование ApexDLC!"
            )
            
            # Обновляем меню с новой кнопкой
            markup = create_main_menu(user_id)
        else:
            # Ошибка активации
            reply_text = f"❌ <b>Ошибка активации:</b>\n{result}"
            markup = create_main_menu(user_id)
        
        user_states[user_id] = {'state': 'main'}
        bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        return
    
    elif state == 'checking_key':
        # Проверка статуса ключа
        key = text
        status = get_key_status(key, user_id)
        
        reply_text = f"🔑 <b>Статус ключа:</b>\n\n{status}"
        
        user_states[user_id] = {'state': 'main'}
        markup = create_main_menu(user_id)
        bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        return
    
    elif state == 'waiting_promo':
        # Активация промокода с проверкой
        promo_code = text.upper().strip()
        
        success, result = activate_promo_code(user_id, promo_code)
        
        if success:
            amount = result
            reply_text = (
                f"✅ <b>Промокод успешно активирован!</b>\n\n"
                f"🎁 Вам начислено {amount} ₽ бонуса.\n"
                f"💰 Текущий баланс: {get_user_balance(user_id)} ₽"
            )
        else:
            reply_text = f"❌ <b>Ошибка активации промокода:</b>\n{result}"
        
        user_states[user_id] = {'state': 'main'}
        markup = create_main_menu(user_id)
        bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        return
    
    elif state == 'admin_waiting_user_id':
        # Админ вводит ID пользователя для выдачи ключа
        try:
            target_user_id = int(text)
            plan_id = user_states[user_id].get('plan_id')
            plan = APEX_PLANS.get(plan_id)
            
            if target_user_id and plan:
                # Генерируем ключ для указанного пользователя
                key = generate_key(plan_id, target_user_id, created_by=user_id, is_free=True, is_purchased=False)
                
                reply_text = (
                    f"✅ <b>Бесплатный ключ создан!</b>\n\n"
                    f"🎮 <b>Тариф:</b> {plan['name']}\n"
                    f"👤 <b>Для пользователя:</b> {target_user_id}\n"
                    f"🔑 <b>Ключ:</b>\n"
                    f"<code>{key}</code>\n\n"
                    f"Пользователь может активировать его через меню '🔑 Активировать ключ'"
                )
                
                # Отправляем уведомление пользователю
                try:
                    bot.send_message(
                        target_user_id,
                        f"🎁 <b>Вам выдан бесплатный ключ!</b>\n\n"
                        f"🎮 Тариф: {plan['name']}\n"
                        f"🔑 Ключ: <code>{key}</code>\n\n"
                        f"Активируйте его в боте через меню '🔑 Активировать ключ'\n\n"
                        f"После активации появится кнопка для скачивания PREMIUM клиента.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
                
                user_states[user_id] = {'state': 'main'}
                markup = create_main_menu(user_id)
                bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
            else:
                bot.reply_to(message, "❌ Ошибка. Попробуйте снова.")
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат ID. Введите число.")
        return
    
    elif state == 'admin_waiting_new_admin':
        # Добавление нового админа
        try:
            new_admin_id = int(text)
            if add_admin(new_admin_id):
                reply_text = f"✅ Пользователь {new_admin_id} назначен администратором!"
            else:
                reply_text = f"❌ Пользователь {new_admin_id} уже является администратором."
            
            user_states[user_id] = {'state': 'main'}
            markup = create_main_menu(user_id)
            bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат ID. Введите число.")
        return
    
    elif state == 'admin_waiting_remove_admin':
        # Удаление админа
        try:
            remove_admin_id = int(text)
            if remove_admin(remove_admin_id):
                reply_text = f"✅ Пользователь {remove_admin_id} удален из администраторов!"
            else:
                reply_text = f"❌ Пользователь {remove_admin_id} не является администратором."
            
            user_states[user_id] = {'state': 'main'}
            markup = create_main_menu(user_id)
            bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат ID. Введите число.")
        return
    
    elif state == 'admin_waiting_premium_link':
        # Админ вводит новую ссылку на премиум клиент
        parts = text.split()
        link = parts[0]
        version = parts[1] if len(parts) > 1 else CLIENT_VERSION
        size = parts[2] if len(parts) > 2 else CLIENT_SIZE
        
        set_client_download_link(link, version, size)
        
        reply_text = (
            f"✅ <b>Ссылка на PREMIUM клиент обновлена!</b>\n\n"
            f"🔗 Ссылка: {link}\n"
            f"📦 Версия: {version}\n"
            f"📏 Размер: {size}"
        )
        
        user_states[user_id] = {'state': 'main'}
        markup = create_main_menu(user_id)
        bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        return
    
    elif state == 'admin_waiting_free_link':
        # Админ вводит новую ссылку на бесплатный клиент
        parts = text.split()
        link = parts[0]
        version = parts[1] if len(parts) > 1 else FREE_CLIENT_VERSION
        size = parts[2] if len(parts) > 2 else FREE_CLIENT_SIZE
        
        set_free_client_download_link(link, version, size)
        
        reply_text = (
            f"✅ <b>Ссылка на FREE клиент обновлена!</b>\n\n"
            f"🔗 Ссылка: {link}\n"
            f"📦 Версия: {version}\n"
            f"📏 Размер: {size}"
        )
        
        user_states[user_id] = {'state': 'main'}
        markup = create_main_menu(user_id)
        bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        return
    
    elif state == 'admin_waiting_balance_user':
        # Админ вводит ID пользователя и сумму для начисления
        parts = text.split()
        if len(parts) >= 2:
            try:
                target_user_id = int(parts[0])
                amount = int(parts[1])
                
                update_user_balance(target_user_id, amount)
                
                reply_text = (
                    f"✅ <b>Баланс пользователя обновлен!</b>\n\n"
                    f"👤 Пользователь: {target_user_id}\n"
                    f"💰 Сумма: {amount} ₽\n"
                    f"Новый баланс: {get_user_balance(target_user_id)} ₽"
                )
                
                # Отправляем уведомление пользователю
                try:
                    if amount > 0:
                        bot.send_message(
                            target_user_id,
                            f"💰 <b>Баланс пополнен!</b>\n\n"
                            f"Вам начислено {amount} ₽.\n"
                            f"Текущий баланс: {get_user_balance(target_user_id)} ₽",
                            parse_mode='HTML'
                        )
                    else:
                        bot.send_message(
                            target_user_id,
                            f"💳 <b>Списание с баланса</b>\n\n"
                            f"С вашего баланса списано {abs(amount)} ₽.\n"
                            f"Текущий баланс: {get_user_balance(target_user_id)} ₽",
                            parse_mode='HTML'
                        )
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
                
                user_states[user_id] = {'state': 'main'}
                markup = create_main_menu(user_id)
                bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
            except ValueError:
                bot.reply_to(message, "❌ Неверный формат. Введите ID и сумму через пробел.")
        else:
            bot.reply_to(message, "❌ Неверный формат. Введите ID и сумму через пробел.")
        return
    
    elif state == 'admin_waiting_promo_amount':
        # Админ вводит сумму для промокода
        parts = text.split()
        amount = int(parts[0])
        max_uses = int(parts[1]) if len(parts) > 1 else 1
        expiry_days = int(parts[2]) if len(parts) > 2 else 30
        
        promo_code = generate_promo_code(amount, max_uses, expiry_days)
        
        reply_text = (
            f"✅ <b>Промокод создан!</b>\n\n"
            f"🎁 Код: <code>{promo_code}</code>\n"
            f"💰 Сумма: {amount} ₽\n"
            f"📊 Лимит использований: {max_uses}\n"
            f"📅 Действует дней: {expiry_days}\n\n"
            f"Сохраните код для распространения!"
        )
        
        user_states[user_id] = {'state': 'main'}
        markup = create_main_menu(user_id)
        bot.reply_to(message, reply_text, parse_mode='HTML', reply_markup=markup)
        return

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("✨ Бот ApexDLC с исправленными обработчиками запущен... ✨")
    logger.info("=" * 50)
    
    # Проверка наличия изображения
    if os.path.exists('image.png'):
        logger.info("🖼️ Изображение найдено: image.png")
    else:
        logger.warning("⚠️ Изображение не найдено: image.png")
    
    # Проверка настроек ЮKassa
    if YKASSA_SHOP_ID and YKASSA_SECRET_KEY:
        logger.info("💳 ЮKassa настроена")
    else:
        logger.warning("⚠️ ЮKassa не настроена. Оплата картой будет недоступна.")
    
    # Инициализация ссылок на клиенты
    if not client_links:
        set_client_download_link(CLIENT_DOWNLOAD_LINK, CLIENT_VERSION, CLIENT_SIZE)
        set_free_client_download_link(FREE_CLIENT_DOWNLOAD_LINK, FREE_CLIENT_VERSION, FREE_CLIENT_SIZE)
    
    # Выводим информацию о тарифах
    logger.info("🎮 Доступные тарифы ApexDLC:")
    for plan_id, plan in APEX_PLANS.items():
        logger.info(f"   • {plan['name']}: {plan['price_rub']} ₽ / {plan['price_stars']} ⭐")
    
    # Информация об администраторах
    if admins:
        logger.info(f"👑 Администраторы: {', '.join(admins)}")
    else:
        logger.info("👑 Администраторы не назначены. Первый пользователь станет админом.")
    
    # Информация о клиентах
    premium_link, premium_version, premium_size = get_client_download_link()
    free_link, free_version, free_size = get_free_client_download_link()
    logger.info(f"📥 PREMIUM клиент: версия {premium_version}, размер {premium_size}")
    logger.info(f"📥 FREE клиент: версия {free_version}, размер {free_size}")
    
    logger.info("=" * 50)
    logger.info("📝 Бот начал polling. Нажмите Ctrl+C для остановки")
    logger.info("=" * 50)
    
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=5)
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:

        logger.error(f"❌ Ошибка при работе бота: {e}")
