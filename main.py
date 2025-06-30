import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Создание Flask приложения
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


# Функция для подключения к БД
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_WEB_USER'),
            password=os.getenv('DB_WEB_PASSWORD'),
            port=os.getenv('DB_PORT', 5432)
        )
        return conn
    except psycopg2.Error as e:
        app.logger.error(f"Ошибка подключения к БД: {e}")
        flash('Ошибка подключения к базе данных', 'danger')
        return None


# Маршрут главной страницы
@app.route('/')
def home():
    return redirect(url_for('login'))



# Маршрут входа в систему
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем в личный кабинет
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Проверка заполненности полей
        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('login.html')

        conn = get_db_connection()
        if not conn:
            flash('Ошибка подключения к базе данных', 'danger')
            return render_template('login.html')

        try:
            with conn.cursor() as cur:
                # Получаем пользователя + роль
                cur.execute(
                    "SELECT id, name, role FROM users WHERE login = %s AND password = %s",
                    (username, password)
                )
                user = cur.fetchone()

            if user:
                # Сохраняем данные в сессии
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['user_role'] = user[2]  # Сохраняем роль пользователя

                # Редирект в зависимости от роли
                if user[2] == 'admin':
                    flash('Вы вошли как администратор', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Вход выполнен успешно', 'success')
                    return redirect(url_for('dashboard'))
            else:
                flash('Неверные учетные данные', 'danger')

        except psycopg2.Error as e:
            # Логирование ошибки для разработчика
            app.logger.error(f'Ошибка БД при входе: {e}')
            flash('Произошла ошибка при попытке входа', 'danger')

        finally:
            conn.close()

    return render_template('login.html')


# Маршрут выхода из системы
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Маршрут личного кабинета (dashboard)
@app.route('/dashboard')
def dashboard():
    # Проверка авторизации
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Подключаемся к БД
    conn = get_db_connection()
    if not conn:
        flash('Ошибка подключения к базе данных', 'danger')
        return redirect(url_for('login'))

    try:
        with conn.cursor() as cur:
            # Получаем имя пользователя
            cur.execute("SELECT name FROM users WHERE id = %s", (user_id,))
            user_name = cur.fetchone()[0]

            # Статистика по объявлениям
            cur.execute("""
                SELECT 
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) AS sold,
                    AVG(price) AS avg_price
                FROM listings 
                WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            if row:
                total, active, sold, avg_price = row
                # Заменяем None на 0
                avg_price = avg_price or 0
            else:
                total, active, sold, avg_price = 0, 0, 0, 0

            stats = (total, active, sold, avg_price)


            # Получаем топ-3 города по количеству объявлений
            cur.execute("""
                    SELECT city, COUNT(*) as count
                    FROM listings 
                    WHERE user_id = %s
                    GROUP BY city 
                    ORDER BY count DESC 
                    LIMIT 3
                """, (user_id,))
            top_cities = cur.fetchall()

            return render_template(
                'dashboard.html',
                user_name=user_name,
                stats=stats,
                top_cities=top_cities
            )

    except Exception as e:
        print(f"Ошибка: {e}")
        flash('Ошибка при загрузке данных', 'danger')
        return redirect(url_for('login'))
    finally:
        conn.close()


@app.route('/listings')
def listings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            # Добавляем property_type в запрос
            cur.execute("""
                SELECT id, title, price, city, status, property_type 
                FROM listings 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))

            # Преобразуем результаты в список словарей
            columns = [desc[0] for desc in cur.description]
            listings_data = [
                dict(zip(columns, row))
                for row in cur.fetchall()
            ]

            return render_template(
                'listings.html',
                user_name=session['user_name'],
                listings=listings_data
            )
    finally:
        conn.close()


@app.route('/edit_listing/<int:listing_id>', methods=['GET', 'POST'])
def edit_listing(listing_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Проверяем, существует ли объявление
            cur.execute("SELECT user_id FROM listings WHERE id = %s", (listing_id,))
            listing_data = cur.fetchone()

            if not listing_data:
                flash('Объявление не найдено', 'danger')
                return redirect(url_for('admin_dashboard' if session.get('user_role') == 'admin' else 'listings'))

            owner_id = listing_data[0]
            current_user_id = session['user_id']
            is_admin = session.get('user_role') == 'admin'

            # Проверка прав: пользователь должен быть владельцем или администратором
            if owner_id != current_user_id and not is_admin:
                flash('У вас нет прав на редактирование этого объявления', 'danger')
                return redirect(url_for('admin_dashboard' if is_admin else 'listings'))

            if request.method == 'POST':
                # Обновляем данные
                title = request.form['title']
                description = request.form['description']
                price = request.form['price']
                city = request.form['city']
                status = request.form['status']
                property_type = request.form['property_type']

                cur.execute(
                    "UPDATE listings SET title = %s, description = %s, price = %s, city = %s, status = %s, property_type = %s WHERE id = %s",
                    (title, description, price, city, status, property_type, listing_id)
                )
                conn.commit()
                flash('Объявление успешно обновлено', 'success')

                return redirect_back()  # Используем улучшенную функцию

            # Получаем данные объявления для формы
            cur.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
            columns = [desc[0] for desc in cur.description]
            listing_data = dict(zip(columns, cur.fetchone()))

            return render_template('edit_listing.html', listing=listing_data)
    finally:
        conn.close()


@app.route('/add_listing', methods=['GET', 'POST'])
def add_listing():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Получаем данные из формы
        title = request.form.get('title')
        description = request.form.get('description', '')
        price = request.form.get('price')
        city = request.form.get('city')
        address = request.form.get('address', '')
        district = request.form.get('district', '')
        area = request.form.get('area')
        rooms = request.form.get('rooms')
        property_type = request.form.get('property_type')
        status = request.form.get('status', 'active')
        user_id = session['user_id']  # ID текущего пользователя

        # Проверка обязательных полей
        if not all([title, price, city, property_type, status]):
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return redirect(url_for('add_listing'))

        try:
            # Преобразуем числовые поля
            price = float(price) if price else None
            area = float(area) if area else None
            rooms = int(rooms) if rooms else None
        except (ValueError, TypeError):
            flash('Некорректное значение в числовых полях', 'danger')
            return redirect(url_for('add_listing'))

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Вставляем новое объявление в БД
                cur.execute(
                    """
                    INSERT INTO listings (
                        user_id, title, description, price, city, 
                        address, district, area, rooms, property_type, status
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id, title, description, price, city,
                        address, district, area, rooms, property_type, status
                    )
                )
                conn.commit()
                flash('Объявление успешно добавлено!', 'success')
                return redirect(url_for('listings'))
        except Exception as e:
            conn.rollback()
            app.logger.error(f'Ошибка при добавлении объявления: {e}')
            flash('Произошла ошибка при добавлении объявления', 'danger')
            return redirect(url_for('add_listing'))
        finally:
            conn.close()

    return render_template('add_listing.html')


import json
from datetime import datetime, timedelta

import json
from datetime import datetime, timedelta


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Основная статистика
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM users) AS total_agents,
                    (SELECT COUNT(*) FROM listings) AS total_listings,
                    (SELECT COUNT(*) FROM listings WHERE status = 'active') AS active_listings,
                    (SELECT AVG(price) FROM listings) AS avg_price,
                    (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '1 month') AS new_agents_last_month,
                    (SELECT COUNT(*) FROM listings WHERE created_at >= NOW() - INTERVAL '1 week') AS new_listings_last_week,
                    (SELECT COUNT(*) FROM listings) - 
                    (SELECT COUNT(*) FROM listings WHERE created_at < NOW() - INTERVAL '1 month') AS listings_growth
            """)
            stats = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))

            # Статистика по статусам для диаграммы
            cur.execute("""
                SELECT 
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) AS sold,
                    SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) AS archived
                FROM listings
            """)
            status_data = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))

            # Распределение по типам недвижимости
            cur.execute("""
                SELECT property_type, COUNT(*) as count
                FROM listings
                GROUP BY property_type
            """)
            property_type_data = []
            property_type_labels = []
            for row in cur.fetchall():
                property_type_labels.append(row[0])
                property_type_data.append(row[1])

            # Топ агентов
            cur.execute("""
                SELECT 
                    u.id, 
                    u.name, 
                    u.login, 
                    u.phone,
                    COUNT(l.id) AS listings_count,
                    SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) AS active_listings,
                    AVG(l.price) AS avg_price
                FROM users u
                LEFT JOIN listings l ON u.id = l.user_id
                GROUP BY u.id, u.name, u.login, u.phone
                ORDER BY listings_count DESC
                LIMIT 5
            """)
            top_agents = [
                dict(zip([desc[0] for desc in cur.description], row))
                for row in cur.fetchall()
            ]

            return render_template(
                'admin_dashboard.html',
                stats=stats,
                status_data=status_data,
                top_agents=top_agents,
                property_type_labels=json.dumps(property_type_labels),
                property_type_data=json.dumps(property_type_data)
            )
    except Exception as e:
        app.logger.error(f'Ошибка в админ-панели: {e}')
        flash('Ошибка загрузки данных', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        conn.close()


@app.route('/manage_agents')
def manage_agents():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Получаем список агентов с количеством активных объявлений
            cur.execute("""
                SELECT 
                    u.id, u.name, u.login, u.phone, u.role, u.password,
                    COUNT(l.id) FILTER (WHERE l.status = 'active') AS active_listings
                FROM users u
                LEFT JOIN listings l ON u.id = l.user_id
                GROUP BY u.id
                ORDER BY u.role DESC, u.name
            """)

            agents = [
                dict(zip([desc[0] for desc in cur.description], row))
                for row in cur.fetchall()
            ]

            return render_template('manage_agents.html', agents=agents)
    except Exception as e:
        app.logger.error(f'Ошибка при загрузке агентов: {e}')
        flash('Ошибка при загрузке данных', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()


# Маршрут для добавления агента
@app.route('/add_agent', methods=['GET', 'POST'])
def add_agent():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        login = request.form.get('login')
        password = request.form.get('password')
        phone = request.form.get('phone')
        role = request.form.get('role', 'agent')

        if not all([name, login, password]):
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return redirect(url_for('add_agent'))

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (name, login, password, phone, role) VALUES (%s, %s, %s, %s, %s)",
                    (name, login, password, phone, role)
                )
                conn.commit()
                flash('Агент успешно добавлен', 'success')
                return redirect(url_for('manage_agents'))
        except psycopg2.Error as e:
            conn.rollback()
            flash(f'Ошибка при добавлении агента: {e}', 'danger')
            return redirect(url_for('add_agent'))
        finally:
            conn.close()

    return render_template('add_agent.html')


# Маршрут для редактирования агента
@app.route('/edit_agent/<int:agent_id>', methods=['GET', 'POST'])
def edit_agent(agent_id):
    # Проверка прав доступа
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash('Ошибка подключения к базе данных', 'danger')
        return redirect(url_for('manage_agents'))

    try:
        with conn.cursor() as cur:
            # Проверяем существование агента
            cur.execute("SELECT * FROM users WHERE id = %s", (agent_id,))
            agent_data = cur.fetchone()

            if not agent_data:
                flash('Агент не найден', 'danger')
                return redirect(url_for('manage_agents'))

            # Преобразуем данные в словарь
            columns = [desc[0] for desc in cur.description]
            agent_data = dict(zip(columns, agent_data))

            # Если запрос POST - обновляем данные
            if request.method == 'POST':
                name = request.form.get('name')
                login = request.form.get('login')
                password = request.form.get('password')
                phone = request.form.get('phone')
                role = request.form.get('role')

                # Проверка обязательных полей
                if not all([name, login, password, role]):
                    flash('Пожалуйста, заполните все обязательные поля', 'danger')
                    return render_template('edit_agent.html', agent=agent_data)

                # Проверка, что администратор не может изменить свою роль
                if agent_id == session['user_id'] and role != 'admin':
                    flash('Вы не можете изменить свою роль', 'danger')
                    return render_template('edit_agent.html', agent=agent_data)

                try:
                    # Обновляем данные агента
                    cur.execute(
                        "UPDATE users SET name = %s, login = %s, password = %s, phone = %s, role = %s WHERE id = %s",
                        (name, login, password, phone, role, agent_id)
                    )
                    conn.commit()

                    # Если редактируем себя - обновляем сессию
                    if agent_id == session['user_id']:
                        session['user_name'] = name

                    flash('Данные агента успешно обновлены', 'success')
                    return redirect(url_for('manage_agents'))

                except psycopg2.Error as e:
                    conn.rollback()
                    flash(f'Ошибка при обновлении данных агента: {e}', 'danger')
                    app.logger.error(f'Ошибка БД при обновлении агента: {e}')

            # Для GET-запроса показываем форму
            return render_template('edit_agent.html', agent=agent_data)

    except Exception as e:
        flash(f'Ошибка при обработке запроса: {e}', 'danger')
        app.logger.error(f'Ошибка в edit_agent: {e}')
        return redirect(url_for('manage_agents'))

    finally:
        conn.close()


# Маршрут для удаления агента
@app.route('/delete_agent/<int:agent_id>', methods=['POST'])
def delete_agent(agent_id):
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    if agent_id == session['user_id']:
        flash('Вы не можете удалить самого себя', 'danger')
        return redirect(url_for('manage_agents'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Удаляем все объявления агента перед удалением самого агента
            cur.execute("DELETE FROM listings WHERE user_id = %s", (agent_id,))

            # Удаляем агента
            cur.execute("DELETE FROM users WHERE id = %s", (agent_id,))
            conn.commit()
            flash('Агент и его объявления успешно удалены', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при удалении агента: {e}', 'danger')
        app.logger.error(f'Ошибка при удалении агента: {e}')
    finally:
        conn.close()

    return redirect(url_for('manage_agents'))



# Константы
ITEMS_PER_PAGE = 20


@app.route('/all_listings')
def all_listings():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    # Получаем параметры фильтрации
    title = request.args.get('title', '')
    city = request.args.get('city', '')
    property_type = request.args.get('property_type', '')
    status = request.args.get('status', '')
    price_min = request.args.get('price_min', '')
    price_max = request.args.get('price_max', '')
    district = request.args.get('district', '')
    agent_id = request.args.get('agent_id', '')


    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Базовый запрос
            query = """
                SELECT 
                    l.id, l.title, l.description, l.price, l.city, 
                    l.address, l.district, l.area, l.rooms, l.property_type, 
                    l.status, l.created_at, u.name AS agent_name
                FROM listings l
                JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """

            params = []

            # Добавляем условия фильтрации
            if title:
                query += " AND l.title ILIKE %s"
                params.append(f'%{title}%')

            if city:
                query += " AND l.city ILIKE %s"
                params.append(f'%{city}%')

            if property_type:
                query += " AND l.property_type = %s"
                params.append(property_type)

            if status:
                query += " AND l.status = %s"
                params.append(status)

            if price_min:
                query += " AND l.price >= %s"
                params.append(float(price_min))

            if price_max:
                query += " AND l.price <= %s"
                params.append(float(price_max))

            if district:
                query += " AND l.district ILIKE %s"
                params.append(f'%{district}%')

            if agent_id:
                query += " AND u.id = %s"
                params.append(int(agent_id))


            # Выполняем основной запрос
            cur.execute(query, params)  # Без LIMIT/OFFSET
            listings_data = [
                dict(zip([desc[0] for desc in cur.description], row))
                for row in cur.fetchall()  # Получаем все записи
            ]

            # Получаем список агентов для фильтра
            cur.execute("SELECT id, name FROM users ORDER BY name")
            agents = [
                dict(zip(['id', 'name'], row))
                for row in cur.fetchall()
            ]

            # Получаем уникальные типы недвижимости
            cur.execute("SELECT DISTINCT property_type FROM listings")
            property_types = [row[0] for row in cur.fetchall()]



            # Передаем параметры фильтрации в шаблон
            filter_params = {
                'title': title,
                'city': city,
                'property_type': property_type,
                'status': status,
                'price_min': price_min,
                'price_max': price_max,
                'district': district,
                'agent_id': agent_id
            }

            return render_template(
                'all_listings.html',
                listings=listings_data,
                agents=agents,
                property_types=property_types,
                filter_params=filter_params
            )
    except Exception as e:
        app.logger.error(f'Ошибка при загрузке объявлений: {e}')
        flash('Ошибка при загрузке данных', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()


# Маршрут для добавления объявления администратором
@app.route('/add_listing_admin', methods=['GET', 'POST'])
def add_listing_admin():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Получаем данные из формы
        title = request.form.get('title')
        description = request.form.get('description', '')
        price = request.form.get('price')
        city = request.form.get('city')
        address = request.form.get('address', '')
        district = request.form.get('district', '')
        area = request.form.get('area')
        rooms = request.form.get('rooms')
        property_type = request.form.get('property_type')
        status = request.form.get('status', 'active')
        user_id = request.form.get('agent_id')  # Агент выбирается из списка

        # Проверка обязательных полей
        if not all([title, price, city, property_type, status, user_id]):
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return redirect(url_for('add_listing_admin'))

        try:
            # Преобразуем числовые поля
            price = float(price) if price else None
            area = float(area) if area else None
            rooms = int(rooms) if rooms else None
        except (ValueError, TypeError):
            flash('Некорректное значение в числовых полях', 'danger')
            return redirect(url_for('add_listing_admin'))

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Вставляем новое объявление в БД
                cur.execute(
                    """
                    INSERT INTO listings (
                        user_id, title, description, price, city, 
                        address, district, area, rooms, property_type, status
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id, title, description, price, city,
                        address, district, area, rooms, property_type, status
                    )
                )
                conn.commit()
                flash('Объявление успешно добавлено!', 'success')
                return redirect(url_for('all_listings'))
        except Exception as e:
            conn.rollback()
            app.logger.error(f'Ошибка при добавлении объявления: {e}')
            flash('Произошла ошибка при добавлении объявления', 'danger')
            return redirect(url_for('add_listing_admin'))
        finally:
            conn.close()

    # Получаем список агентов для выпадающего списка
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM users ORDER BY name")
            agents = [
                dict(zip(['id', 'name'], row))
                for row in cur.fetchall()
            ]

            return render_template('add_listing_admin.html', agents=agents)
    finally:
        conn.close()


# Маршрут для формы добавления (шаблон)
@app.route('/add_listing_admin')
def add_listing_admin_form():
    if 'user_role' not in session or session['user_role'] != 'admin':
        flash('Доступ запрещен: требуются права администратора', 'danger')
        return redirect(url_for('login'))

    # Получаем список агентов
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM users ORDER BY name")
            agents = [
                dict(zip(['id', 'name'], row))
                for row in cur.fetchall()
            ]

            return render_template('add_listing_admin.html', agents=agents)
    finally:
        conn.close()




# Маршрут для удаления объявления
@app.route('/delete_listing/<int:listing_id>', methods=['POST'])
def delete_listing(listing_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Проверяем, существует ли объявление
            cur.execute("SELECT user_id FROM listings WHERE id = %s", (listing_id,))
            listing_data = cur.fetchone()

            if not listing_data:
                flash('Объявление не найдено', 'danger')
                return redirect(url_for('admin_dashboard' if session.get('user_role') == 'admin' else 'listings'))

            owner_id = listing_data[0]
            current_user_id = session['user_id']
            is_admin = session.get('user_role') == 'admin'

            # Проверка прав: пользователь должен быть владельцем или администратором
            if owner_id != current_user_id and not is_admin:
                flash('У вас нет прав на удаление этого объявления', 'danger')
                return redirect(url_for('admin_dashboard' if is_admin else 'listings'))

            # Удаление объявления
            cur.execute("DELETE FROM listings WHERE id = %s", (listing_id,))
            conn.commit()
            flash('Объявление успешно удалено', 'success')

            return redirect_back()  # Используем улучшенную функцию
    finally:
        conn.close()


from flask import request


def redirect_back(default_endpoint='listings'):
    # Пытаемся получить URL для перенаправления из параметров
    next_url = request.args.get('next') or \
               request.form.get('next') or \
               request.referrer

    # Проверяем безопасность URL (чтобы избежать атак открытого перенаправления)
    if next_url and is_safe_url(next_url):
        return redirect(next_url)

    # Перенаправление по умолчанию
    if session.get('user_role') == 'admin':
        return redirect(url_for('all_listings'))
    return redirect(url_for(default_endpoint))


from urllib.parse import urlparse, urljoin
def is_safe_url(target):
    """Проверяет, что URL безопасен для перенаправления"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

if __name__ == '__main__':
    app.run(debug=True)


