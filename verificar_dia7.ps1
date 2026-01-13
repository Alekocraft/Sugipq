# verificar_dia7.ps1
# Script de verificación para correcciones del Día 7

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔍 VERIFICACIÓN DÍA 7 - SUGIPQ-V1" -ForegroundColor Cyan
Write-Host "Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Contadores
$tests_passed = 0
$tests_failed = 0
$total_tests = 8

# Función para verificar archivos
function Check-File {
    param(
        [string]$file,
        [string]$pattern,
        [string]$description,
        [string]$test_num
    )
    
    Write-Host "${test_num}️⃣  TEST: ${description}" -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    
    if (Test-Path $file) {
        if (Select-String -Path $file -Pattern $pattern -Quiet) {
            Write-Host "✅ PASADO: ${description}" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ FALLIDO: ${description}" -ForegroundColor Red
            Write-Host "   Archivo: $file" -ForegroundColor Red
            Write-Host "   No se encontró el patrón esperado" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "❌ FALLIDO: Archivo no encontrado" -ForegroundColor Red
        Write-Host "   $file" -ForegroundColor Red
        return $false
    }
}

# Test 1: login.html
if (Check-File "templates\auth\login.html" 'autocomplete="off"' "login.html - autocomplete deshabilitado" "1") {
    $tests_passed++
} else {
    $tests_failed++
}
Write-Host ""

# Test 2: test_ldap.html
if (Check-File "templates\auth\test_ldap.html" 'autocomplete="off"' "test_ldap.html - autocomplete deshabilitado" "2") {
    $tests_passed++
} else {
    $tests_failed++
}
Write-Host ""

# Test 3: crear.html
if (Check-File "templates\usuarios\crear.html" 'autocomplete="off"' "crear.html - autocomplete deshabilitado" "3") {
    $tests_passed++
} else {
    $tests_failed++
}
Write-Host ""

# Test 4: editar.html - múltiples campos
Write-Host "4️⃣  TEST: editar.html - múltiples campos" -ForegroundColor Yellow
Write-Host "-------------------------------------------"
if (Test-Path "templates\usuarios\editar.html") {
    $count = (Select-String -Path "templates\usuarios\editar.html" -Pattern 'autocomplete="off"' -AllMatches).Matches.Count
    if ($count -ge 2) {
        Write-Host "✅ PASADO: editar.html tiene $count campos con autocomplete" -ForegroundColor Green
        $tests_passed++
    } else {
        Write-Host "❌ FALLIDO: editar.html solo tiene $count campos (esperado: 2+)" -ForegroundColor Red
        $tests_failed++
    }
} else {
    Write-Host "❌ FALLIDO: Archivo no encontrado" -ForegroundColor Red
    $tests_failed++
}
Write-Host ""

# Test 5: gestionar.html - múltiples campos
Write-Host "5️⃣  TEST: gestionar.html - múltiples campos" -ForegroundColor Yellow
Write-Host "-------------------------------------------"
if (Test-Path "templates\usuarios\gestionar.html") {
    $count = (Select-String -Path "templates\usuarios\gestionar.html" -Pattern 'autocomplete="off"' -AllMatches).Matches.Count
    if ($count -ge 3) {
        Write-Host "✅ PASADO: gestionar.html tiene $count campos con autocomplete" -ForegroundColor Green
        $tests_passed++
    } else {
        Write-Host "❌ FALLIDO: gestionar.html solo tiene $count campos (esperado: 3+)" -ForegroundColor Red
        $tests_failed++
    }
} else {
    Write-Host "❌ FALLIDO: Archivo no encontrado" -ForegroundColor Red
    $tests_failed++
}
Write-Host ""

# Test 6: confirmar.html
if (Check-File "templates\confirmacion\confirmar.html" 'rel="noopener noreferrer"' "confirmar.html - enlaces seguros" "6") {
    $tests_passed++
} else {
    $tests_failed++
}
Write-Host ""

# Test 7: inventario_corporativo.html
if (Check-File "templates\reportes\inventario_corporativo.html" 'rel="noopener noreferrer"' "inventario_corporativo.html - enlaces seguros" "7") {
    $tests_passed++
} else {
    $tests_failed++
}
Write-Host ""

# Test 8: oficinas.html
if (Check-File "templates\reportes\oficinas.html" 'rel="noopener noreferrer"' "oficinas.html - enlaces seguros" "8") {
    $tests_passed++
} else {
    $tests_failed++
}
Write-Host ""

# Resumen
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📊 RESUMEN DE VERIFICACIÓN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total de tests:  $total_tests"
Write-Host "Tests pasados:   $tests_passed" -ForegroundColor Green
Write-Host "Tests fallidos:  $tests_failed" -ForegroundColor $(if ($tests_failed -eq 0) { "Green" } else { "Red" })
Write-Host ""

$percentage = [math]::Round(($tests_passed / $total_tests) * 100)
Write-Host "Porcentaje completado: ${percentage}%" -ForegroundColor $(if ($percentage -eq 100) { "Green" } else { "Yellow" })
Write-Host ""

if ($tests_failed -eq 0) {
    Write-Host "🎉 ¡TODOS LOS TESTS PASARON!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Próximo paso:" -ForegroundColor Cyan
    Write-Host "  git add templates/"
    Write-Host "  git commit -m '✅ Día 7 completado'"
    Write-Host "  git push"
} else {
    Write-Host "⚠️  HAY TESTS FALLIDOS" -ForegroundColor Yellow
    Write-Host "Revisar los tests marcados con ❌ y corregir"
    Write-Host ""
    Write-Host "Consultar:" -ForegroundColor Cyan
    Write-Host "  - INSTRUCCIONES_DETALLADAS_DIA7.md"
    Write-Host "  - PLAN_DIA7_FORMULARIOS.md"
}

Write-Host "========================================" -ForegroundColor Cyan
Read-Host "Presiona ENTER para continuar"

if ($tests_failed -gt 0) {
    exit 1
} else {
    exit 0
}
