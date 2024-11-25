// Створення карти OpenLayers
var map = new ol.Map({
    target: 'map',
    layers: [
        new ol.layer.Tile({
            source: new ol.source.OSM()
        })
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([30.5, 50.5]), // Координати центру карти
        zoom: 5
    })
});

// Функція для отримання найкоротшого шляху через API
function getShortestPath(source, target) {
    fetch('/api/shortest_path', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            source_icao: source,
            target_icao: target
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Error:', data.error);
        } else {
            console.log('Шлях:', data.path);
            // Перевірка на Infinity
            let distance = data.cost === null ? "невизначено" : data.cost;
            drawPathOnMap(data.path);
            displayRouteInfo(data.path, distance);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Функція для малювання шляху на карті
function drawPathOnMap(path) {
    var coordinates = [];

    // Отримуємо координати для кожної вершини у шляху
    path.forEach(function(ident, index) {
        // Запит до API для отримання координат вершини
        fetch(`/api/vertices?ident=${ident}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error:', data.error);
            } else {
                coordinates.push(ol.proj.fromLonLat([data.longitude, data.latitude]));

                if (coordinates.length === path.length) {
                    // Додаємо маршрут на карту, коли всі координати отримані
                    var routeFeature = new ol.Feature({
                        geometry: new ol.geom.LineString(coordinates)
                    });

                    var routeLayer = new ol.layer.Vector({
                        source: new ol.source.Vector({
                            features: [routeFeature]
                        }),
                        style: new ol.style.Style({
                            stroke: new ol.style.Stroke({
                                width: 4,
                                color: '#FF6347'
                            })
                        })
                    });

                    map.addLayer(routeLayer);

                    // Додавання точок на маршруті
                    coordinates.forEach(coord => {
                        var pointFeature = new ol.Feature({
                            geometry: new ol.geom.Point(coord)
                        });

                        var pointLayer = new ol.layer.Vector({
                            source: new ol.source.Vector({
                                features: [pointFeature]
                            }),
                            style: new ol.style.Style({
                                image: new ol.style.Circle({
                                    radius: 6,
                                    fill: new ol.style.Fill({
                                        color: '#FF4500'
                                    }),
                                    stroke: new ol.style.Stroke({
                                        color: '#ffffff',
                                        width: 2
                                    })
                                })
                            })
                        });

                        map.addLayer(pointLayer);
                    });
                }
            }
        });
    });
}

// Функція для відображення інформації про маршрут
function displayRouteInfo(path, distance) {
    var routeInfo = document.getElementById('route-info');
    if (distance === "невизначено") {
        routeInfo.innerHTML = `
            <h4>Інформація про маршрут</h4>
            <p>Шлях не знайдено. Можливо, між аеропортами немає доступних маршрутів або вони ізольовані.</p>
        `;
    } else {
        routeInfo.innerHTML = `
            <h4>Інформація про маршрут</h4>
            <p>Відстань маршруту: ${distance} км</p>
            <ul class="waypoint-list">
                ${path.map(waypoint => `<li class="waypoint-item">${waypoint}</li>`).join('')}
            </ul>
        `;
    }
}

// Обробка події форми для пошуку шляху
document.getElementById('route-form').addEventListener('submit', function(event) {
    event.preventDefault();
    var source = document.getElementById('source-icao').value;
    var target = document.getElementById('target-icao').value;
    getShortestPath(source, target);
});
