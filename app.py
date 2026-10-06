import os
import io
import csv
import shutil
import sqlite3
from datetime import datetime

from flask import (
    Flask, request, jsonify, render_template, Response
)

# ===================== КОНФИГУРАЦИЯ =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DEFAULT_DB = os.path.join(DATA_DIR, 'radiocomponents.db')
LEGACY_DB = os.path.join(BASE_DIR, 'radiocomponents.db')

# Путь к БД, адрес и порт можно переопределить переменными окружения
DATABASE = os.environ.get('DB_PATH', DEFAULT_DB)
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '5000'))
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

# Поля компонента (используются в API и при импорте/экспорте CSV)
FIELDS = ['name', 'inv_number', 'cabinet', 'drawer', 'section',
          'documentation', 'note', 'quantity', 'package']

app = Flask(__name__)


def ensure_data_dir():
    """Создаёт каталог для БД и переносит старый файл из корня при первом запуске."""
    data_dir = os.path.dirname(DATABASE) or '.'
    os.makedirs(data_dir, exist_ok=True)
    # Одноразовая миграция: radiocomponents.db в корне -> data/radiocomponents.db
    if (DATABASE == DEFAULT_DB and not os.path.exists(DATABASE)
            and os.path.exists(LEGACY_DB)):
        try:
            shutil.move(LEGACY_DB, DATABASE)
            print(f'[ComponentTracker] База данных перемещена: '
                  f'{LEGACY_DB} -> {DATABASE}')
        except OSError as exc:
            print(f'[ComponentTracker] Не удалось переместить базу: {exc}')


def get_db():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row  # чтобы возвращать словари
    return conn


def parse_quantity(value):
    """Приводит количество к целому числу >= 0 или бросает ValueError."""
    if value in (None, ''):
        return 0
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        raise ValueError('Поле quantity должно быть целым числом')
    if quantity < 0:
        raise ValueError('Поле quantity не может быть отрицательным')
    return quantity

def init_db():
    """Инициализация базы данных (создание таблицы)"""
    ensure_data_dir()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode=WAL')  # WAL улучшает параллельный доступ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            inv_number TEXT,
            cabinet TEXT,
            drawer TEXT,
            section TEXT,
            documentation TEXT,
            note TEXT,
            quantity INTEGER DEFAULT 0,
            package TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Инициализируем БД при запуске
init_db()

# ===================== API ЭНДПОИНТЫ =====================

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/components', methods=['GET'])
def get_components():
    """Получить все компоненты"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM components ORDER BY id DESC')
    components = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(components)

@app.route('/api/components/<int:component_id>', methods=['GET'])
def get_component(component_id):
    """Получить один компонент по ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM components WHERE id = ?', (component_id,))
    component = cursor.fetchone()
    conn.close()
    if component:
        return jsonify(dict(component))
    return jsonify({'error': 'Компонент не найден'}), 404

@app.route('/api/components', methods=['POST'])
def add_component():
    """Добавить новый компонент"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Ожидается JSON в теле запроса'}), 400

    if not (data.get('name') or '').strip():
        return jsonify({'error': 'Поле name обязательно'}), 400

    try:
        quantity = parse_quantity(data.get('quantity', 0))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO components 
        (name, inv_number, cabinet, drawer, section, documentation, note, quantity, package)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['name'].strip(),
        data.get('inv_number', ''),
        data.get('cabinet', ''),
        data.get('drawer', ''),
        data.get('section', ''),
        data.get('documentation', ''),
        data.get('note', ''),
        quantity,
        data.get('package', '')
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'id': new_id, 'message': 'Компонент добавлен'}), 201

@app.route('/api/components/<int:component_id>', methods=['PUT'])
def update_component(component_id):
    """Обновить компонент"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Ожидается JSON в теле запроса'}), 400

    if not (data.get('name') or '').strip():
        return jsonify({'error': 'Поле name обязательно'}), 400

    try:
        quantity = parse_quantity(data.get('quantity', 0))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE components 
        SET name = ?, inv_number = ?, cabinet = ?, drawer = ?, 
            section = ?, documentation = ?, note = ?, quantity = ?, 
            package = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        data['name'].strip(),
        data.get('inv_number', ''),
        data.get('cabinet', ''),
        data.get('drawer', ''),
        data.get('section', ''),
        data.get('documentation', ''),
        data.get('note', ''),
        quantity,
        data.get('package', ''),
        component_id
    ))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected == 0:
        return jsonify({'error': 'Компонент не найден'}), 404
    return jsonify({'message': 'Компонент обновлён'})

@app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component(component_id):
    """Удалить компонент"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM components WHERE id = ?', (component_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected == 0:
        return jsonify({'error': 'Компонент не найден'}), 404
    return jsonify({'message': 'Компонент удалён'})

@app.route('/api/search', methods=['GET'])
def search_components():
    """Поиск компонентов по тексту во всех полях"""
    query = request.args.get('q', '').strip()
    if not query:
        return get_components()
    
    conn = get_db()
    cursor = conn.cursor()
    # Поиск по всем текстовым полям
    cursor.execute('''
        SELECT * FROM components 
        WHERE name LIKE ? OR inv_number LIKE ? OR cabinet LIKE ? 
           OR drawer LIKE ? OR section LIKE ? OR documentation LIKE ? 
           OR note LIKE ? OR package LIKE ?
        ORDER BY id DESC
    ''', tuple([f'%{query}%'] * 8))
    components = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(components)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получить статистику"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM components')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT SUM(quantity) as total_qty FROM components')
    total_qty = cursor.fetchone()['total_qty'] or 0
    conn.close()
    return jsonify({'total': total, 'total_quantity': total_qty})

@app.route('/api/export', methods=['GET'])
def export_components():
    """Экспорт всех компонентов в CSV"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM components ORDER BY id')
    rows = cursor.fetchall()
    conn.close()

    header = ['id'] + FIELDS + ['created_at', 'updated_at']
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for row in rows:
        writer.writerow([row[column] for column in header])

    filename = 'components_{:%Y-%m-%d_%H%M}.csv'.format(datetime.now())
    # BOM в начале нужен, чтобы Excel корректно открывал русские символы
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/api/import', methods=['POST'])
def import_components():
    """Импорт компонентов из CSV-файла (поле формы file)"""
    file = request.files.get('file')
    if file is None:
        return jsonify({'error': 'Файл не загружен (ожидается поле "file")'}), 400

    try:
        content = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return jsonify({'error': 'Не удалось прочитать файл (ожидается CSV в UTF-8)'}), 400

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or 'name' not in reader.fieldnames:
        return jsonify({'error': 'CSV должен содержать колонку "name"'}), 400

    conn = get_db()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    for row in reader:
        name = (row.get('name') or '').strip()
        if not name:
            skipped += 1
            continue
        try:
            quantity = parse_quantity(row.get('quantity'))
        except ValueError:
            quantity = 0
        cursor.execute('''
            INSERT INTO components
            (name, inv_number, cabinet, drawer, section, documentation, note, quantity, package)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name,
            (row.get('inv_number') or '').strip(),
            (row.get('cabinet') or '').strip(),
            (row.get('drawer') or '').strip(),
            (row.get('section') or '').strip(),
            (row.get('documentation') or '').strip(),
            (row.get('note') or '').strip(),
            quantity,
            (row.get('package') or '').strip()
        ))
        inserted += 1
    conn.commit()
    conn.close()

    message = f'Импортировано: {inserted}, пропущено: {skipped}'
    return jsonify({'message': message, 'inserted': inserted, 'skipped': skipped}), 201


if __name__ == '__main__':
    # Локальный запуск для разработки. В продакшне используется gunicorn.
    app.run(host=HOST, port=PORT, debug=DEBUG)