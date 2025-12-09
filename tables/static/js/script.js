// tables/static/js/script.js

document.addEventListener('DOMContentLoaded', function() {
    // Obtenemos el token CSRF del DOM
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const cards = document.querySelectorAll('.table-card');

    cards.forEach(card => {
        card.addEventListener('click', function() {
            const tableId = this.getAttribute('data-id');
            const statusSpan = this.querySelector('.status-indicator');
            
            // Petición fetch (AJAX) al servidor Django
            fetch(`/toggle/${tableId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken // Importante para seguridad en Django
                },
            })
            .then(response => response.json())
            .then(data => {
                // Actualizamos la interfaz inmediatamente basada en la respuesta
                if (data.is_occupied) {
                    this.classList.remove('free');
                    this.classList.add('occupied');
                    statusSpan.innerHTML = '<span class="icon">✅</span> Ocupada';
                } else {
                    this.classList.remove('occupied');
                    this.classList.add('free');
                    statusSpan.innerHTML = '<span class="icon">🍽️</span> Libre';
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
});