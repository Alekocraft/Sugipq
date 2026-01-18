/**
 * FUNCIONES JAVASCRIPT PARA FORMATO DE NÚMEROS
 * Usar en archivos JavaScript donde se actualicen números dinámicamente
 */

/**
 * Formatea un número con separador de miles (punto)
 * @param {number} numero - El número a formatear
 * @param {number} decimales - Cantidad de decimales (por defecto 0)
 * @returns {string} - Número formateado (ej: 100.000 o 1.234,56)
 */
function formatoNumero(numero, decimales = 0) {
    try {
        numero = parseFloat(numero) || 0;
        
        if (decimales > 0) {
            // Con decimales
            return numero.toLocaleString('es-CO', {
                minimumFractionDigits: decimales,
                maximumFractionDigits: decimales
            });
        } else {
            // Sin decimales
            return numero.toLocaleString('es-CO', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            });
        }
    } catch (e) {
        return '0';
    }
}

/**
 * Formatea un número como moneda
 * @param {number} numero - El número a formatear
 * @param {string} simbolo - Símbolo de moneda (por defecto '$')
 * @param {number} decimales - Cantidad de decimales (por defecto 0)
 * @returns {string} - Moneda formateada (ej: $100.000 o $1.500.000,50)
 */
function formatoMoneda(numero, simbolo = '$', decimales = 0) {
    const numeroFormateado = formatoNumero(numero, decimales);
    return `${simbolo}${numeroFormateado}`;
}

/**
 * Formatea un número como porcentaje
 * @param {number} numero - El número a formatear (0-1 o 0-100)
 * @param {number} decimales - Cantidad de decimales (por defecto 1)
 * @returns {string} - Porcentaje formateado (ej: 85,5%)
 */
function formatoPorcentaje(numero, decimales = 1) {
    try {
        numero = parseFloat(numero) || 0;
        // Si el número es menor a 1, asumimos que está en formato 0-1
        const porcentaje = numero < 1 ? numero * 100 : numero;
        
        return porcentaje.toLocaleString('es-CO', {
            minimumFractionDigits: decimales,
            maximumFractionDigits: decimales
        }) + '%';
    } catch (e) {
        return '0%';
    }
}

/**
 * Formatea un número de forma compacta (K, M, B)
 * @param {number} numero - El número a formatear
 * @returns {string} - Número compacto (ej: 1.5K, 2.3M)
 */
function formatoCompacto(numero) {
    try {
        numero = parseFloat(numero) || 0;
        
        if (numero >= 1000000000) {
            return (numero / 1000000000).toFixed(1) + 'B';
        } else if (numero >= 1000000) {
            return (numero / 1000000).toFixed(1) + 'M';
        } else if (numero >= 1000) {
            return (numero / 1000).toFixed(1) + 'K';
        }
        return numero.toString();
    } catch (e) {
        return '0';
    }
}


// ========================================
// EJEMPLOS DE USO
// ========================================

/*
// Ejemplo 1: Formato básico de números
console.log(formatoNumero(100000));        // "100.000"
console.log(formatoNumero(1234.56, 2));    // "1.234,56"

// Ejemplo 2: Formato de moneda
console.log(formatoMoneda(100000));           // "$100.000"
console.log(formatoMoneda(1500000.50, '$', 2)); // "$1.500.000,50"

// Ejemplo 3: Formato de porcentaje
console.log(formatoPorcentaje(0.855));     // "85,5%"
console.log(formatoPorcentaje(75, 0));     // "75%"

// Ejemplo 4: Formato compacto
console.log(formatoCompacto(1500));        // "1.5K"
console.log(formatoCompacto(2500000));     // "2.5M"

// Ejemplo 5: Actualizar elementos HTML
document.getElementById('totalProductos').textContent = formatoNumero(1250);
document.getElementById('valorTotal').textContent = formatoMoneda(15000000);
document.getElementById('stockBajo').textContent = formatoNumero(45);
document.getElementById('tasaAprobacion').textContent = formatoPorcentaje(0.85, 1);
*/


// ========================================
// APLICACIÓN EN DASHBOARD
// ========================================

/*
// Ejemplo de cómo usar en fetch de estadísticas del dashboard

fetch('/materiales/api/estadisticas-dashboard')
    .then(response => response.json())
    .then(data => {
        // ✅ CON FORMATO
        document.getElementById('totalMateriales').textContent = formatoNumero(data.total_materiales);
        document.getElementById('stockTotal').textContent = formatoNumero(data.stock_total);
        document.getElementById('valorTotal').textContent = formatoMoneda(data.valor_total, '$', 0);
        document.getElementById('stockBajo').textContent = formatoNumero(data.stock_bajo);
        
        // ❌ SIN FORMATO (antes)
        // document.getElementById('totalMateriales').textContent = data.total_materiales;
        // document.getElementById('valorTotal').textContent = data.valor_total;
    });

fetch('/inventario-corporativo/api/estadisticas-dashboard')
    .then(response => response.json())
    .then(data => {
        // ✅ CON FORMATO
        document.getElementById('totalProductos').textContent = formatoNumero(data.total_productos);
        document.getElementById('valorInventario').textContent = formatoMoneda(data.valor_total, '$', 0);
        document.getElementById('productosBajoStock').textContent = formatoNumero(data.stock_bajo);
    });
*/


// ========================================
// EXTENSIÓN: Formatear todos los elementos con data-format
// ========================================

/**
 * Formatea automáticamente todos los elementos con atributo data-format
 * Uso: <span data-format="numero">100000</span> → 100.000
 *      <span data-format="moneda">1500000</span> → $1.500.000
 *      <span data-format="porcentaje">0.85</span> → 85%
 */
function formatearElementos() {
    document.querySelectorAll('[data-format]').forEach(elemento => {
        const formato = elemento.getAttribute('data-format');
        const valor = parseFloat(elemento.textContent) || 0;
        const decimales = parseInt(elemento.getAttribute('data-decimales')) || 0;
        
        switch(formato) {
            case 'numero':
                elemento.textContent = formatoNumero(valor, decimales);
                break;
            case 'moneda':
                const simbolo = elemento.getAttribute('data-simbolo') || '$';
                elemento.textContent = formatoMoneda(valor, simbolo, decimales);
                break;
            case 'porcentaje':
                elemento.textContent = formatoPorcentaje(valor, decimales);
                break;
            case 'compacto':
                elemento.textContent = formatoCompacto(valor);
                break;
        }
    });
}

// Ejecutar al cargar la página
document.addEventListener('DOMContentLoaded', formatearElementos);


// ========================================
// EXPORTAR FUNCIONES (si usas módulos ES6)
// ========================================

// export { formatoNumero, formatoMoneda, formatoPorcentaje, formatoCompacto, formatearElementos };