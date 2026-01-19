// static/js/main.js
// Archivo JavaScript principal para el sistema

document.addEventListener('DOMContentLoaded', function() {
    // Inicialización básica
    console.log('✅ Sistema SUGIPQ cargado');
    
    // Auto-cerrar alertas después de 5 segundos
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Actualizar fecha y hora en el dashboard
    updateDateTime();
    setInterval(updateDateTime, 1000);
});

function updateDateTime() {
    const fechaActual = document.getElementById('fechaActual');
    const horaActual = document.getElementById('horaActual');
    
    if (fechaActual || horaActual) {
        const ahora = new Date();
        
        if (fechaActual) {
            const opciones = { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            };
            fechaActual.textContent = ahora.toLocaleDateString('es-CO', opciones);
        }
        
        if (horaActual) {
            horaActual.textContent = ahora.toLocaleTimeString('es-CO');
        }
    }
}