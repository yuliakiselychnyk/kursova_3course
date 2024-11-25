from flask import Flask, jsonify, request, render_template
import psycopg2
from flask_cors import CORS
import heapq
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')  # Вказуємо папку для шаблонів
CORS(app)

# Налаштування для підключення до бази даних
DB_CONFIG = {
    'dbname': 'air_route_map',
    'user': 'postgres',
    'password': 'yulia7305',  # Пароль для PostgreSQL
    'host': 'localhost'
}

# Маршрут для головної сторінки
@app.route('/')
def home():
    logger.info('Отримання головної сторінки')
    return render_template('index.html')

# Маршрут для отримання всіх аеропортів
@app.route('/api/airports', methods=['GET'])
def get_airports():
    try:
        logger.info('Отримання всіх аеропортів')
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT icao, lat, lon FROM airports")
        rows = cur.fetchall()
        airports = [{'icao': row[0], 'latitude': row[1], 'longitude': row[2]} for row in rows]
        cur.close()
        conn.close()
        logger.info(f'Знайдено {len(airports)} аеропортів')
        return jsonify(airports)
    except Exception as e:
        logger.error(f'Помилка при отриманні аеропортів: {str(e)}')
        return jsonify({'error': str(e)}), 500

# Маршрут для отримання вершини за її ідентифікатором
@app.route('/api/vertices', methods=['GET'])
def get_vertex():
    try:
        ident = request.args.get('ident')
        if not ident:
            logger.warning('Відсутній ідентифікатор вершини')
            return jsonify({'error': 'Vertex identifier is missing'}), 400

        logger.info(f'Отримання вершини з ідентифікатором: {ident}')
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT ident, ST_Y(geometry::geometry), ST_X(geometry::geometry) FROM vertices WHERE ident = %s", (ident,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            logger.info(f'Вершина знайдена: {row}')
            return jsonify({'ident': row[0], 'latitude': row[1], 'longitude': row[2]})
        else:
            logger.warning(f'Вершина з ідентифікатором {ident} не знайдена')
            return jsonify({'error': 'Vertex not found'}), 404
    except Exception as e:
        logger.error(f'Помилка при отриманні вершини: {str(e)}')
        return jsonify({'error': str(e)}), 500

# Маршрут для отримання всіх вершин
@app.route('/api/vertices/all', methods=['GET'])
def get_all_vertices():
    try:
        logger.info('Отримання всіх вершин')
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT ident, ST_Y(geometry::geometry), ST_X(geometry::geometry) FROM vertices;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Формуємо список вершин
        vertices = [{'ident': row[0], 'latitude': row[1], 'longitude': row[2]} for row in rows]
        logger.info(f'Знайдено {len(vertices)} вершин')
        return jsonify(vertices)
    except Exception as e:
        logger.error(f'Помилка при отриманні вершин: {str(e)}')
        return jsonify({'error': str(e)}), 500

# Маршрут для отримання найкоротшого шляху
@app.route('/api/shortest_path', methods=['POST'])
def get_shortest_path():
    try:
        data = request.get_json()
        source_icao = data.get('source_icao')
        target_icao = data.get('target_icao')

        if not source_icao or not target_icao:
            logger.warning('Відсутній код ICAO для початкового або кінцевого аеропорту')
            return jsonify({'error': 'Source or target airport ICAO code is missing'}), 400

        logger.info(f'Пошук найкоротшого шляху від {source_icao} до {target_icao}')
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Перевірка наявності введених аеропортів у базі даних
        cur.execute("SELECT ident FROM vertices WHERE ident IN (%s, %s)", (source_icao, target_icao))
        found_vertices = cur.fetchall()
        if len(found_vertices) < 2:
            logger.warning('Один або обидва введені аеропорти не існують у базі даних')
            return jsonify({'error': 'One or both of the provided airports do not exist in the database'}), 404

        # Отримання всіх вершин
        cur.execute("SELECT ident FROM vertices")
        vertices = [row[0] for row in cur.fetchall()]

        # Отримання всіх ребер
        cur.execute("SELECT source_ident, target_ident, distance FROM airways")
        edges = cur.fetchall()

        # Створення графу
        graph = {vertex: [] for vertex in vertices}
        for edge in edges:
            source, target, distance = edge
            graph[source].append((target, distance))
            graph[target].append((source, distance))

        # Алгоритм Дейкстри для пошуку найкоротшого шляху
        def dijkstra(graph, start, goal):
            logger.info(f'Запуск алгоритму Дейкстри для {start} -> {goal}')
            queue = [(0, start, [])]
            visited = set()
            while queue:
                (cost, vertex, path) = heapq.heappop(queue)
                if vertex in visited:
                    continue
                path = path + [vertex]
                if vertex == goal:
                    logger.info(f'Знайдено шлях: {path} з вартістю {cost}')
                    return (cost, path)
                visited.add(vertex)
                for next_vertex, weight in graph.get(vertex, []):
                    if next_vertex not in visited:
                        heapq.heappush(queue, (cost + weight, next_vertex, path))
            logger.warning(f'Шлях від {start} до {goal} не знайдено')
            return (None, [])

        # Знаходження найкоротшого шляху
        cost, path = dijkstra(graph, source_icao, target_icao)

        cur.close()
        conn.close()

        # Якщо шлях не знайдено, повертаємо відповідь з `cost` як `None`
        return jsonify({'cost': cost, 'path': path})
    except Exception as e:
        logger.error(f'Помилка при обчисленні найкоротшого шляху: {str(e)}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
