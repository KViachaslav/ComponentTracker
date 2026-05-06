from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
# CORS(app)  # разрешаем кросс-доменные запросы

# Путь к базе данных
DATABASE = 'radiocomponents.db'

def get_db():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # чтобы возвращать словари
    return conn

def init_db():
    """Инициализация базы данных (создание таблицы)"""
    conn = get_db()
    cursor = conn.cursor()
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
    data = request.json
    
    required_fields = ['name']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO components 
        (name, inv_number, cabinet, drawer, section, documentation, note, quantity, package)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['name'],
        data.get('inv_number', ''),
        data.get('cabinet', ''),
        data.get('drawer', ''),
        data.get('section', ''),
        data.get('documentation', ''),
        data.get('note', ''),
        data.get('quantity', 0),
        data.get('package', 'SMD (0805)')
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'id': new_id, 'message': 'Компонент добавлен'}), 201

@app.route('/api/components/<int:component_id>', methods=['PUT'])
def update_component(component_id):
    """Обновить компонент"""
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Поле name обязательно'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE components 
        SET name = ?, inv_number = ?, cabinet = ?, drawer = ?, 
            section = ?, documentation = ?, note = ?, quantity = ?, 
            package = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        data['name'],
        data.get('inv_number', ''),
        data.get('cabinet', ''),
        data.get('drawer', ''),
        data.get('section', ''),
        data.get('documentation', ''),
        data.get('note', ''),
        data.get('quantity', 0),
        data.get('package', 'SMD (0805)'),
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

if __name__ == '__main__':
    # Запускаем сервер на всех интерфейсах, порт 5000
    app.run(host='0.0.0.0', port=5000, debug=True)