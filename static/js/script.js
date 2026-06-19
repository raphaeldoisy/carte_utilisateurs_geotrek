document.addEventListener('DOMContentLoaded', function() {
    var map = L.map('map').setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    fetch('/load_data')
        .then(response => response.json())
        .then(data => {
            L.geoJSON(data).addTo(map);
        });

    document.getElementById('dataForm').addEventListener('submit', function(event) {
        event.preventDefault();
        var geom = document.getElementById('geom').value;
        var attrs = document.getElementById('attrs').value;
        fetch('/add_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ geom: geom, attrs: attrs }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
        });
    });
});
