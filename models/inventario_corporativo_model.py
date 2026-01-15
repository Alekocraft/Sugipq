# models/inventario_corporativo_model.py.
from database import get_database_connection


def generar_codigo_unico():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ProductosCorporativos")
    total = cursor.fetchone()[0] + 1
    conn.close()
    return f"QInven-{total:04d}"


class InventarioCorporativoModel:
    # ================== UTILIDADES ==================
    @staticmethod
    def generar_codigo_unico():
        """
        Proxy estÃ¡tico para generar cÃ³digos Ãºnicos desde el modelo.
        Permite usar InventarioCorporativoModel.generar_codigo_unico()
        manteniendo tambiÃ©n la funciÃ³n de mÃ³dulo.
        """
        return generar_codigo_unico()

    # ================== LISTADO / LECTURA ==================
    @staticmethod
    def obtener_todos():
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    p.ProductoId           AS id,
                    p.CodigoUnico          AS codigo_unico,
                    p.NombreProducto       AS nombre,
                    p.Descripcion          AS descripcion,
                    c.NombreCategoria      AS categoria,
                    pr.NombreProveedor     AS proveedor,
                    p.ValorUnitario        AS valor_unitario,
                    p.CantidadDisponible   AS cantidad,
                    p.CantidadMinima       AS cantidad_minima,
                    p.Ubicacion            AS ubicacion,
                    p.EsAsignable          AS es_asignable,
                    p.RutaImagen           AS ruta_imagen,
                    p.FechaCreacion        AS fecha_creacion,
                    p.UsuarioCreador       AS usuario_creador
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                INNER JOIN Proveedores pr        ON p.ProveedorId = pr.ProveedorId
                WHERE p.Activo = 1
                ORDER BY p.NombreProducto
            """
            cursor.execute(query)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obteniendo productos corporativos: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_todos_con_oficina():
        """Obtener todos los productos con informaciÃ³n de oficina asignada"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    p.ProductoId           AS id,
                    p.CodigoUnico          AS codigo_unico,
                    p.NombreProducto       AS nombre,
                    p.Descripcion          AS descripcion,
                    c.NombreCategoria      AS categoria,
                    pr.NombreProveedor     AS proveedor,
                    p.ValorUnitario        AS valor_unitario,
                    p.CantidadDisponible   AS cantidad,
                    p.CantidadMinima       AS cantidad_minima,
                    p.Ubicacion            AS ubicacion,
                    p.EsAsignable          AS es_asignable,
                    p.RutaImagen           AS ruta_imagen,
                    p.FechaCreacion        AS fecha_creacion,
                    p.UsuarioCreador       AS usuario_creador,
                    COALESCE(o.NombreOficina, 'Sede Principal') AS oficina
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                INNER JOIN Proveedores pr        ON p.ProveedorId = pr.ProveedorId
                LEFT JOIN Asignaciones a ON p.ProductoId = a.ProductoId AND a.Activo = 1
                LEFT JOIN Oficinas o ON a.OficinaId = o.OficinaId
                WHERE p.Activo = 1
                ORDER BY p.NombreProducto
            """
            cursor.execute(query)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obteniendo productos corporativos con oficina: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_por_oficina(oficina_id):
        """Obtiene productos corporativos filtrados por oficina"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT
                    p.ProductoId           AS id,
                    p.CodigoUnico          AS codigo_unico,
                    p.NombreProducto       AS nombre,
                    p.Descripcion          AS descripcion,
                    c.NombreCategoria      AS categoria,
                    pr.NombreProveedor     AS proveedor,
                    p.ValorUnitario        AS valor_unitario,
                    p.CantidadDisponible   AS cantidad,
                    p.CantidadMinima       AS cantidad_minima,
                    p.Ubicacion            AS ubicacion,
                    p.EsAsignable          AS es_asignable,
                    p.RutaImagen           AS ruta_imagen,
                    p.FechaCreacion        AS fecha_creacion,
                    p.UsuarioCreador       AS usuario_creador
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                INNER JOIN Proveedores pr        ON p.ProveedorId = pr.ProveedorId
                LEFT JOIN Asignaciones a ON p.ProductoId = a.ProductoId AND a.Activo = 1
                WHERE p.Activo = 1 AND (a.OficinaId = ? OR p.OficinaCreadoraId = ?)
                ORDER BY p.NombreProducto
            """
            cursor.execute(query, (oficina_id, oficina_id))
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obteniendo productos corporativos por oficina: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_por_id(producto_id):
        conn = get_database_connection()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    p.ProductoId           AS id,
                    p.CodigoUnico          AS codigo_unico,
                    p.NombreProducto       AS nombre,
                    p.Descripcion          AS descripcion,
                    p.CategoriaId          AS categoria_id,
                    c.NombreCategoria      AS categoria,
                    p.ProveedorId          AS proveedor_id,
                    pr.NombreProveedor     AS proveedor,
                    p.ValorUnitario        AS valor_unitario,
                    p.CantidadDisponible   AS cantidad,
                    p.CantidadMinima       AS cantidad_minima,
                    p.Ubicacion            AS ubicacion,
                    p.EsAsignable          AS es_asignable,
                    p.RutaImagen           AS ruta_imagen,
                    p.FechaCreacion        AS fecha_creacion,
                    p.UsuarioCreador       AS usuario_creador
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                INNER JOIN Proveedores pr        ON p.ProveedorId = pr.ProveedorId
                WHERE p.ProductoId = ? AND p.Activo = 1
            """
            cursor.execute(query, (producto_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cursor.description]
            return dict(zip(cols, row))
        except Exception as e:
            print(f"Error obteniendo producto corporativo: {e}")
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ================== CREAR / ACTUALIZAR / ELIMINAR ==================
    @staticmethod
    def crear(codigo_unico, nombre, descripcion, categoria_id, proveedor_id,
              valor_unitario, cantidad, cantidad_minima, ubicacion,
              es_asignable, usuario_creador, ruta_imagen):
        """
        Inserta y retorna ProductoId (SQL Server: OUTPUT INSERTED.ProductoId)
        """
        conn = get_database_connection()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor()
            sql = """
                INSERT INTO ProductosCorporativos
                    (CodigoUnico, NombreProducto, Descripcion, CategoriaId, ProveedorId,
                     ValorUnitario, CantidadDisponible, CantidadMinima, Ubicacion,
                     EsAsignable, Activo, FechaCreacion, UsuarioCreador, RutaImagen)
                OUTPUT INSERTED.ProductoId
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, GETDATE(), ?, ?)
            """
            cursor.execute(sql, (
                codigo_unico, nombre, descripcion, int(categoria_id), int(proveedor_id),
                float(valor_unitario), int(cantidad), int(cantidad_minima or 0),
                ubicacion, int(es_asignable), usuario_creador, ruta_imagen
            ))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return new_id
        except Exception as e:
            print(f"Error creando producto corporativo: {e}")
            try:
                if conn: conn.rollback()
            except:
                pass
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def actualizar(producto_id, codigo_unico, nombre, descripcion, categoria_id,
                   proveedor_id, valor_unitario, cantidad, cantidad_minima,
                   ubicacion, es_asignable, ruta_imagen=None):
        """Actualizar producto incluyendo cantidad y ruta_imagen"""
        conn = get_database_connection()
        if not conn:
            return False
        cursor = None
        try:
            cursor = conn.cursor()

            if ruta_imagen:
                sql = """
                    UPDATE ProductosCorporativos 
                    SET CodigoUnico = ?, NombreProducto = ?, Descripcion = ?, 
                        CategoriaId = ?, ProveedorId = ?, ValorUnitario = ?,
                        CantidadDisponible = ?, CantidadMinima = ?, Ubicacion = ?, 
                        EsAsignable = ?, RutaImagen = ?
                    WHERE ProductoId = ? AND Activo = 1
                """
                params = (
                    codigo_unico, nombre, descripcion, int(categoria_id), int(proveedor_id),
                    float(valor_unitario), int(cantidad), int(cantidad_minima or 0),
                    ubicacion, int(es_asignable), ruta_imagen, int(producto_id)
                )
            else:
                sql = """
                    UPDATE ProductosCorporativos 
                    SET CodigoUnico = ?, NombreProducto = ?, Descripcion = ?, 
                        CategoriaId = ?, ProveedorId = ?, ValorUnitario = ?,
                        CantidadDisponible = ?, CantidadMinima = ?, Ubicacion = ?, 
                        EsAsignable = ?
                    WHERE ProductoId = ? AND Activo = 1
                """
                params = (
                    codigo_unico, nombre, descripcion, int(categoria_id), int(proveedor_id),
                    float(valor_unitario), int(cantidad), int(cantidad_minima or 0),
                    ubicacion, int(es_asignable), int(producto_id)
                )

            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error actualizando producto corporativo: {e}")
            try:
                if conn: conn.rollback()
            except:
                pass
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def eliminar(producto_id, usuario_accion):
        """Soft delete (Activo = 0) + deja traza minima en historial."""
        conn = get_database_connection()
        if not conn:
            return False
        cursor = None
        try:
            cursor = conn.cursor()
            # Traza en nueva tabla
            cursor.execute("""
                INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, Accion, Cantidad, OficinaId, UsuarioAccion, Fecha)
                VALUES (?, 'BAJA_PRODUCTO', 0, NULL, ?, GETDATE())
            """, (int(producto_id), usuario_accion))
            # Baja logica
            cursor.execute(
                "UPDATE ProductosCorporativos SET Activo = 0 WHERE ProductoId = ?",
                (int(producto_id),)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error eliminando producto corporativo: {e}")
            try:
                if conn: conn.rollback()
            except:
                pass
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ================== CATALOGOS ==================
    @staticmethod
    def obtener_categorias():
        """
        Retorna todas las categorÃ­as activas desde la tabla CategoriasProductos,
        incluso si todavÃ­a no tienen productos asociados.
        """
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.CategoriaId AS id,
                    c.NombreCategoria AS nombre
                FROM CategoriasProductos c
                WHERE c.Activo = 1
                ORDER BY c.NombreCategoria
            """)
            return [{'id': r[0], 'nombre': r[1]} for r in cursor.fetchall()]
        except Exception as e:
            print(f"âŒ Error obteniendo categorÃ­as activas: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_proveedores():
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.ProveedorId AS id, p.NombreProveedor AS nombre
                FROM Proveedores p
                WHERE p.Activo = 1
                ORDER BY p.NombreProveedor
            """)
            return [{'id': r[0], 'nombre': r[1]} for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obtener_proveedores: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_oficinas():
        """
        Oficinas para asignacion.
        """
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.OficinaId AS id, o.NombreOficina AS nombre
                FROM Oficinas o
                WHERE o.Activo = 1
                ORDER BY o.NombreOficina
            """)
            return [{'id': r[0], 'nombre': r[1]} for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obtener_oficinas: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ================== ASIGNACIONES / TRAZABILIDAD ==================
    @staticmethod
    def asignar_a_oficina(producto_id, oficina_id, cantidad, usuario_accion):
        """
        Resta stock de ProductosCorporativos.CantidadDisponible y crea registro
        en Asignaciones + guarda traza en AsignacionesCorporativasHistorial.
        """
        conn = get_database_connection()
        if not conn:
            return False
        cursor = None
        try:
            cursor = conn.cursor()

            # 1. PRIMERO: Obtener un UsuarioId vÃ¡lido
            cursor.execute(
                "SELECT TOP 1 UsuarioId FROM Usuarios WHERE Activo = 1 ORDER BY UsuarioId"
            )
            usuario_row = cursor.fetchone()
            if not usuario_row:
                print("Error: No hay usuarios activos en la base de datos")
                return False
            usuario_asignado_id = usuario_row[0]

            # 2. Verificar stock
            cursor.execute(
                "SELECT CantidadDisponible FROM ProductosCorporativos "
                "WHERE ProductoId = ? AND Activo = 1",
                (int(producto_id),)
            )
            row = cursor.fetchone()
            if not row:
                return False
            stock = int(row[0])
            cant = int(cantidad)

            # âœ… CORRECCIÃ“N: condiciÃ³n correcta
            if cant <= 0 or cant > stock:
                return False

            # 3. Descontar stock
            cursor.execute("""
                UPDATE ProductosCorporativos
                SET CantidadDisponible = CantidadDisponible - ?
                WHERE ProductoId = ?
            """, (cant, int(producto_id)))

            # 4. Crear registro en tabla Asignaciones (CON USUARIO VÃLIDO)
            cursor.execute("""
                INSERT INTO Asignaciones 
                (ProductoId, OficinaId, UsuarioAsignadoId, FechaAsignacion, Estado, UsuarioAsignador, Activo)
                VALUES (?, ?, ?, GETDATE(), 'ASIGNADO', ?, 1)
            """, (int(producto_id), int(oficina_id), usuario_asignado_id, usuario_accion))

            # 5. Trazabilidad en tabla AsignacionesCorporativasHistorial
            cursor.execute("""
                INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, OficinaId, Accion, Cantidad, UsuarioAccion, Fecha)
                VALUES (?, ?, 'ASIGNAR', ?, ?, GETDATE())
            """, (int(producto_id), int(oficina_id), cant, usuario_accion))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error asignar_a_oficina: {e}")
            try:
                if conn: conn.rollback()
            except:
                pass
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def historial_asignaciones(producto_id):
        """Obtener historial de asignaciones para un producto especÃ­fico"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            # âœ… CORRECCIÃ“N: Agregados los campos UsuarioAsignadoNombre y UsuarioAsignadoEmail
            cursor.execute("""
                SELECT 
                    h.HistorialId,
                    h.ProductoId,
                    h.OficinaId,
                    o.NombreOficina AS oficina,
                    h.Accion,
                    h.Cantidad,
                    h.UsuarioAccion,
                    h.Fecha,
                    h.UsuarioAsignadoNombre,
                    h.UsuarioAsignadoEmail
                FROM AsignacionesCorporativasHistorial h
                LEFT JOIN Oficinas o ON o.OficinaId = h.OficinaId
                WHERE h.ProductoId = ?
                ORDER BY h.Fecha DESC
            """, (int(producto_id),))
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error historial_asignaciones: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ================== REPORTES ==================
    @staticmethod
    def reporte_stock_por_categoria():
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.NombreCategoria AS categoria,
                    SUM(p.CantidadDisponible) AS total_stock
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                WHERE p.Activo = 1
                GROUP BY c.NombreCategoria
                ORDER BY c.NombreCategoria
            """)
            return [
                {'categoria': r[0], 'total_stock': int(r[1] or 0)}
                for r in cursor.fetchall()
            ]
        except Exception as e:
            print(f"Error reporte_stock_por_categoria: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def reporte_valor_inventario():
        conn = get_database_connection()
        if not conn:
            return {'valor_total': 0}
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(p.ValorUnitario * p.CantidadDisponible) AS valor_total
                FROM ProductosCorporativos p
                WHERE p.Activo = 1
            """)
            row = cursor.fetchone()
            return {'valor_total': float(row[0] or 0.0)}
        except Exception as e:
            print(f"Error reporte_valor_inventario: {e}")
            return {'valor_total': 0}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def reporte_asignaciones_por_oficina():
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    o.NombreOficina AS oficina,
                    COUNT(a.AsignacionId) AS cantidad_asignaciones
                FROM Asignaciones a
                INNER JOIN Oficinas o ON o.OficinaId = a.OficinaId
                WHERE a.Activo = 1
                GROUP BY o.NombreOficina
                ORDER BY o.NombreOficina
            """)
            return [
                {
                    'oficina': r[0],
                    'cantidad_asignaciones': int(r[1] or 0)
                }
                for r in cursor.fetchall()
            ]
        except Exception as e:
            print(f"Error reporte_asignaciones_por_oficina: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ================== REPORTES AVANZADOS ==================
    @staticmethod
    def reporte_productos_por_oficina():
        """Reporte de productos agrupados por oficina"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COALESCE(o.NombreOficina, 'Sede Principal') AS oficina,
                    COUNT(p.ProductoId) AS total_productos,
                    SUM(p.CantidadDisponible) AS total_stock,
                    SUM(p.ValorUnitario * p.CantidadDisponible) AS valor_total
                FROM ProductosCorporativos p
                LEFT JOIN Asignaciones a ON p.ProductoId = a.ProductoId AND a.Activo = 1
                LEFT JOIN Oficinas o ON a.OficinaId = o.OficinaId
                WHERE p.Activo = 1
                GROUP BY COALESCE(o.NombreOficina, 'Sede Principal')
                ORDER BY valor_total DESC
            """)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error reporte_productos_por_oficina: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def reporte_stock_bajo():
        """Productos con stock bajo o crÃ­tico"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.ProductoId,
                    p.CodigoUnico,
                    p.NombreProducto,
                    c.NombreCategoria AS categoria,
                    p.CantidadDisponible,
                    p.CantidadMinima,
                    p.ValorUnitario,
                    (p.ValorUnitario * p.CantidadDisponible) AS valor_total,
                    CASE 
                        WHEN p.CantidadDisponible = 0 THEN 'CrÃ­tico'
                        WHEN p.CantidadDisponible <= p.CantidadMinima THEN 'Bajo'
                        ELSE 'Normal'
                    END AS estado_stock
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                WHERE p.Activo = 1 
                AND (p.CantidadDisponible = 0 OR p.CantidadDisponible <= p.CantidadMinima)
                ORDER BY p.CantidadDisponible ASC
            """)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error reporte_stock_bajo: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def reporte_movimientos_recientes(limite=50):
        """Movimientos recientes del inventario"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP (?) 
                    h.HistorialId,
                    p.NombreProducto,
                    o.NombreOficina AS oficina,
                    h.Accion,
                    h.Cantidad,
                    h.UsuarioAccion,
                    h.Fecha
                FROM AsignacionesCorporativasHistorial h
                INNER JOIN ProductosCorporativos p ON h.ProductoId = p.ProductoId
                LEFT JOIN Oficinas o ON h.OficinaId = o.OficinaId
                ORDER BY h.Fecha DESC
            """, (limite,))
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error reporte_movimientos_recientes: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_estadisticas_generales():
        """EstadÃ­sticas generales del inventario"""
        conn = get_database_connection()
        if not conn:
            return {}
        cursor = None
        try:
            cursor = conn.cursor()

            # Total productos
            cursor.execute(
                "SELECT COUNT(*) FROM ProductosCorporativos WHERE Activo = 1"
            )
            total_productos = cursor.fetchone()[0]

            # Valor total inventario
            cursor.execute("""
                SELECT SUM(ValorUnitario * CantidadDisponible)
                FROM ProductosCorporativos
                WHERE Activo = 1
            """)
            valor_total = cursor.fetchone()[0] or 0

            # Productos con stock bajo
            cursor.execute("""
                SELECT COUNT(*) 
                FROM ProductosCorporativos 
                WHERE Activo = 1 
                AND (CantidadDisponible = 0 OR CantidadDisponible <= CantidadMinima)
            """)
            stock_bajo = cursor.fetchone()[0]

            # Productos asignables
            cursor.execute("""
                SELECT COUNT(*)
                FROM ProductosCorporativos
                WHERE Activo = 1 AND EsAsignable = 1
            """)
            asignables = cursor.fetchone()[0]

            # Total categorÃ­as
            cursor.execute("""
                SELECT COUNT(DISTINCT CategoriaId)
                FROM ProductosCorporativos
                WHERE Activo = 1
            """)
            total_categorias = cursor.fetchone()[0]

            return {
                'total_productos': total_productos,
                'valor_total': float(valor_total),
                'stock_bajo': stock_bajo,
                'asignables': asignables,
                'total_categorias': total_categorias
            }
        except Exception as e:
            print(f"Error obtener_estadisticas_generales: {e}")
            return {}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ================== VISTAS POR TIPO DE OFICINA ==================

    @staticmethod
    def obtener_por_sede_principal():
        """Obtiene productos de la sede principal (no asignados a oficinas)"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.ProductoId           AS id,
                    p.CodigoUnico          AS codigo_unico,
                    p.NombreProducto       AS nombre,
                    p.Descripcion          AS descripcion,
                    c.NombreCategoria      AS categoria,
                    pr.NombreProveedor     AS proveedor,
                    p.ValorUnitario        AS valor_unitario,
                    p.CantidadDisponible   AS cantidad,
                    p.CantidadMinima       AS cantidad_minima,
                    p.Ubicacion            AS ubicacion,
                    p.EsAsignable          AS es_asignable,
                    p.RutaImagen           AS ruta_imagen,
                    p.FechaCreacion        AS fecha_creacion,
                    p.UsuarioCreador       AS usuario_creador,
                    'Sede Principal'       AS oficina
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                INNER JOIN Proveedores pr        ON p.ProveedorId = pr.ProveedorId
                WHERE p.Activo = 1
                AND NOT EXISTS (
                    SELECT 1 FROM Asignaciones a 
                    WHERE a.ProductoId = p.ProductoId AND a.Activo = 1
                )
                ORDER BY p.NombreProducto
            """)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obteniendo sede principal: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    @staticmethod
    def obtener_por_oficinas_servicio():
        """Obtiene productos de oficinas de servicio (asignados a oficinas)"""
        conn = get_database_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    p.ProductoId           AS id,
                    p.CodigoUnico          AS codigo_unico,
                    p.NombreProducto       AS nombre,
                    p.Descripcion          AS descripcion,
                    c.NombreCategoria      AS categoria,
                    pr.NombreProveedor     AS proveedor,
                    p.ValorUnitario        AS valor_unitario,
                    p.CantidadDisponible   AS cantidad,
                    p.CantidadMinima       AS cantidad_minima,
                    p.Ubicacion            AS ubicacion,
                    p.EsAsignable          AS es_asignable,
                    p.RutaImagen           AS ruta_imagen,
                    p.FechaCreacion        AS fecha_creacion,
                    p.UsuarioCreador       AS usuario_creador,
                    o.NombreOficina        AS oficina
                FROM ProductosCorporativos p
                INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                INNER JOIN Proveedores pr        ON p.ProveedorId = pr.ProveedorId
                INNER JOIN Asignaciones a        ON p.ProductoId = a.ProductoId AND a.Activo = 1
                INNER JOIN Oficinas o            ON a.OficinaId = o.OficinaId
                WHERE p.Activo = 1
                ORDER BY o.NombreOficina, p.NombreProducto
            """)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error obteniendo oficinas servicio: {e}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ==================== NUEVAS FUNCIONALIDADES ====================
    # Agregadas: 14/01/2026 
    # Funcionalidades: Devoluciones, Bajas y Traspasos entre Oficinas
    # Total: 13 funciones nuevas
    # ================================================================

    @staticmethod
    def solicitar_devolucion(producto_id, oficina_id, cantidad, motivo, usuario_solicita):
            """
            Crear una solicitud de devolución desde una oficina.
            Estado inicial: Pendiente de aprobación
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Verificar que la oficina tenga asignado este producto
                cursor.execute("""
                    SELECT a.AsignacionId, a.ProductoId, p.NombreProducto, a.Estado
                    FROM Asignaciones a
                    INNER JOIN ProductosCorporativos p ON a.ProductoId = p.ProductoId
                    WHERE a.ProductoId = ? AND a.OficinaId = ? AND a.Activo = 1
                """, (int(producto_id), int(oficina_id)))
            
                asignacion = cursor.fetchone()
                if not asignacion:
                    return {'success': False, 'message': 'Este producto no está asignado a la oficina'}
            
                asignacion_id = asignacion[0]
                nombre_producto = asignacion[2]
            

            # Crear la solicitud de devolución
                cursor.execute("""
                    INSERT INTO DevolucionesInventarioCorporativo
                    (ProductoId, OficinaId, AsignacionId, Cantidad, Motivo, EstadoDevolucion, 
                     UsuarioSolicita, FechaSolicitud, Activo)
                    VALUES (?, ?, ?, ?, ?, 'PENDIENTE', ?, GETDATE(), 1)
                """, (int(producto_id), int(oficina_id), asignacion_id, int(cantidad), motivo, usuario_solicita))
            

            # Obtener el ID de la devolución creada
                cursor.execute("SELECT @@IDENTITY")
                devolucion_id = cursor.fetchone()[0]
            

            # Registrar en historial
                cursor.execute("""
                    INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, OficinaId, Accion, Cantidad, UsuarioAccion, Fecha, Observaciones)
                    VALUES (?, ?, 'SOLICITUD_DEVOLUCION', ?, ?, GETDATE(), ?)
                """, (int(producto_id), int(oficina_id), int(cantidad), usuario_solicita, motivo))
            
                conn.commit()
            
                logger.info(f"Devolución solicitada: Producto {producto_id}, Oficina {oficina_id}, Usuario {usuario_solicita}")
            
                return {
                    'success': True,
                    'message': f'Solicitud de devolución creada exitosamente para {nombre_producto}',
                    'devolucion_id': devolucion_id
                }
            
            except Exception as e:
                logger.error(f"Error en solicitar_devolucion: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al crear solicitud: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def aprobar_devolucion(devolucion_id, usuario_aprueba, observaciones=''):
            """
            Aprobar una devolución y devolver el stock al inventario.
            Solo: Líder de Inventario, Administrador o Aprobador
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Obtener información de la devolución
                cursor.execute("""
                    SELECT d.ProductoId, d.OficinaId, d.Cantidad, d.AsignacionId, 
                           p.NombreProducto, o.NombreOficina, d.EstadoDevolucion
                    FROM DevolucionesInventarioCorporativo d
                    INNER JOIN ProductosCorporativos p ON d.ProductoId = p.ProductoId
                    INNER JOIN Oficinas o ON d.OficinaId = o.OficinaId
                    WHERE d.DevolucionId = ? AND d.Activo = 1
                """, (int(devolucion_id),))
            
                devolucion = cursor.fetchone()
                if not devolucion:
                    return {'success': False, 'message': 'Devolución no encontrada'}
            
                producto_id, oficina_id, cantidad, asignacion_id, nombre_producto, nombre_oficina, estado = devolucion
            
                if estado != 'PENDIENTE':
                    return {'success': False, 'message': f'Esta devolución ya fue {estado.lower()}'}
            

            # Actualizar el stock del producto (devolver al inventario)
                cursor.execute("""
                    UPDATE ProductosCorporativos
                    SET CantidadDisponible = CantidadDisponible + ?
                    WHERE ProductoId = ?
                """, (int(cantidad), int(producto_id)))
            

            # Actualizar el estado de la asignación a "DEVUELTO"
                cursor.execute("""
                    UPDATE Asignaciones
                    SET Estado = 'DEVUELTO', FechaDevolucion = GETDATE()
                    WHERE AsignacionId = ?
                """, (asignacion_id,))
            

            # Actualizar la devolución
                cursor.execute("""
                    UPDATE DevolucionesInventarioCorporativo
                    SET EstadoDevolucion = 'APROBADA',
                        UsuarioAprueba = ?,
                        FechaAprobacion = GETDATE(),
                        ObservacionesAprobacion = ?
                    WHERE DevolucionId = ?
                """, (usuario_aprueba, observaciones, int(devolucion_id)))
            

            # Registrar en historial
                cursor.execute("""
                    INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, OficinaId, Accion, Cantidad, UsuarioAccion, Fecha, Observaciones)
                    VALUES (?, ?, 'DEVOLUCION_APROBADA', ?, ?, GETDATE(), ?)
                """, (int(producto_id), int(oficina_id), int(cantidad), usuario_aprueba, observaciones or 'Devolución aprobada'))
            
                conn.commit()
            
                logger.info(f"Devolución aprobada: ID {devolucion_id}, Producto {nombre_producto}, por {usuario_aprueba}")
            
                return {
                    'success': True,
                    'message': f'Devolución aprobada. {cantidad} unidades de {nombre_producto} devueltas al inventario'
                }
            
            except Exception as e:
                logger.error(f"Error en aprobar_devolucion: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al aprobar devolución: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def rechazar_devolucion(devolucion_id, usuario_rechaza, motivo_rechazo):
            """
            Rechazar una solicitud de devolución
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Verificar que la devolución existe y está pendiente
                cursor.execute("""
                    SELECT EstadoDevolucion FROM DevolucionesInventarioCorporativo
                    WHERE DevolucionId = ? AND Activo = 1
                """, (int(devolucion_id),))
            
                result = cursor.fetchone()
                if not result:
                    return {'success': False, 'message': 'Devolución no encontrada'}
            
                estado = result[0]
                if estado != 'PENDIENTE':
                    return {'success': False, 'message': f'Esta devolución ya fue {estado.lower()}'}
            

            # Actualizar la devolución
                cursor.execute("""
                    UPDATE DevolucionesInventarioCorporativo
                    SET EstadoDevolucion = 'RECHAZADA',
                        UsuarioAprueba = ?,
                        FechaAprobacion = GETDATE(),
                        ObservacionesAprobacion = ?
                    WHERE DevolucionId = ?
                """, (usuario_rechaza, motivo_rechazo, int(devolucion_id)))
            
                conn.commit()
            
                logger.info(f"Devolución rechazada: ID {devolucion_id}, por {usuario_rechaza}")
            
                return {
                    'success': True,
                    'message': 'Devolución rechazada exitosamente'
                }
            
            except Exception as e:
                logger.error(f"Error en rechazar_devolucion: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al rechazar devolución: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def obtener_devoluciones_pendientes():
            """
            Obtener todas las devoluciones pendientes de aprobación
            """
            conn = get_database_connection()
            if not conn:
                return []
        
            cursor = None
            try:
                cursor = conn.cursor()
            
                query = """
                    SELECT 
                        d.DevolucionId AS id,
                        d.ProductoId AS producto_id,
                        p.NombreProducto AS producto_nombre,
                        p.CodigoUnico AS producto_codigo,
                        d.OficinaId AS oficina_id,
                        o.NombreOficina AS oficina_nombre,
                        d.Cantidad AS cantidad,
                        d.Motivo AS motivo,
                        d.EstadoDevolucion AS estado,
                        d.UsuarioSolicita AS usuario_solicita,
                        d.FechaSolicitud AS fecha_solicitud,
                        d.UsuarioAprueba AS usuario_aprueba,
                        d.FechaAprobacion AS fecha_aprobacion,
                        d.ObservacionesAprobacion AS observaciones_aprobacion
                    FROM DevolucionesInventarioCorporativo d
                    INNER JOIN ProductosCorporativos p ON d.ProductoId = p.ProductoId
                    INNER JOIN Oficinas o ON d.OficinaId = o.OficinaId
                    WHERE d.Activo = 1 AND d.EstadoDevolucion = 'PENDIENTE'
                    ORDER BY d.FechaSolicitud DESC
                """
            
                cursor.execute(query)
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]
            
            except Exception as e:
                logger.error(f"Error en obtener_devoluciones_pendientes: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def obtener_devoluciones_por_oficina(oficina_id):
            """
            Obtener todas las devoluciones de una oficina específica
            """
            conn = get_database_connection()
            if not conn:
                return []
        
            cursor = None
            try:
                cursor = conn.cursor()
            
                query = """
                    SELECT 
                        d.DevolucionId AS id,
                        d.ProductoId AS producto_id,
                        p.NombreProducto AS producto_nombre,
                        p.CodigoUnico AS producto_codigo,
                        d.Cantidad AS cantidad,
                        d.Motivo AS motivo,
                        d.EstadoDevolucion AS estado,
                        d.UsuarioSolicita AS usuario_solicita,
                        d.FechaSolicitud AS fecha_solicitud,
                        d.UsuarioAprueba AS usuario_aprueba,
                        d.FechaAprobacion AS fecha_aprobacion,
                        d.ObservacionesAprobacion AS observaciones_aprobacion
                    FROM DevolucionesInventarioCorporativo d
                    INNER JOIN ProductosCorporativos p ON d.ProductoId = p.ProductoId
                    WHERE d.OficinaId = ? AND d.Activo = 1
                    ORDER BY d.FechaSolicitud DESC
                """
            
                cursor.execute(query, (int(oficina_id),))
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]
            
            except Exception as e:
                logger.error(f"Error en obtener_devoluciones_por_oficina: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
    

    # ==================== BAJAS DE PRODUCTOS ==================

    @staticmethod
    def dar_de_baja_producto(producto_id, asignacion_id, motivo, usuario_accion):
            """
            Dar de baja un producto que está en estado DEVUELTO.
            Solo Líder de Inventario puede ejecutar esta acción.
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Verificar que la asignación existe y está en estado DEVUELTO
                cursor.execute("""
                    SELECT a.AsignacionId, a.Estado, p.NombreProducto, p.CodigoUnico, 
                           o.NombreOficina
                    FROM Asignaciones a
                    INNER JOIN ProductosCorporativos p ON a.ProductoId = p.ProductoId
                    LEFT JOIN Oficinas o ON a.OficinaId = o.OficinaId
                    WHERE a.AsignacionId = ? AND a.Activo = 1
                """, (int(asignacion_id),))
            
                asignacion = cursor.fetchone()
                if not asignacion:
                    return {'success': False, 'message': 'Asignación no encontrada'}
            
                _, estado, nombre_producto, codigo_producto, nombre_oficina = asignacion
            
                if estado != 'DEVUELTO':
                    return {
                        'success': False,
                        'message': f'No se puede dar de baja. El producto debe estar en estado DEVUELTO (actual: {estado})'
                    }
            

            # Crear registro en tabla de bajas
                cursor.execute("""
                    INSERT INTO BajasInventarioCorporativo
                    (ProductoId, AsignacionId, Motivo, UsuarioBaja, FechaBaja, Activo)
                    VALUES (?, ?, ?, ?, GETDATE(), 1)
                """, (int(producto_id), int(asignacion_id), motivo, usuario_accion))
            

            # Actualizar la asignación
                cursor.execute("""
                    UPDATE Asignaciones
                    SET Estado = 'DADO_DE_BAJA', FechaBaja = GETDATE()
                    WHERE AsignacionId = ?
                """, (int(asignacion_id),))
            

            # Registrar en historial
                cursor.execute("""
                    INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, OficinaId, Accion, Cantidad, UsuarioAccion, Fecha, Observaciones)
                    SELECT ProductoId, OficinaId, 'BAJA', 1, ?, GETDATE(), ?
                    FROM Asignaciones
                    WHERE AsignacionId = ?
                """, (usuario_accion, motivo, int(asignacion_id)))
            
                conn.commit()
            
                logger.info(f"Producto dado de baja: {codigo_producto} - {nombre_producto}, por {usuario_accion}")
            
                return {
                    'success': True,
                    'message': f'Producto {codigo_producto} - {nombre_producto} dado de baja exitosamente'
                }
            
            except Exception as e:
                logger.error(f"Error en dar_de_baja_producto: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al dar de baja: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def obtener_productos_devueltos():
            """
            Obtener todos los productos en estado DEVUELTO que pueden ser dados de baja
            """
            conn = get_database_connection()
            if not conn:
                return []
        
            cursor = None
            try:
                cursor = conn.cursor()
            
                query = """
                    SELECT 
                        a.AsignacionId AS asignacion_id,
                        a.ProductoId AS producto_id,
                        p.CodigoUnico AS producto_codigo,
                        p.NombreProducto AS producto_nombre,
                        c.NombreCategoria AS categoria,
                        a.OficinaId AS oficina_id,
                        COALESCE(o.NombreOficina, 'Sede Principal') AS oficina_nombre,
                        a.FechaAsignacion AS fecha_asignacion,
                        a.FechaDevolucion AS fecha_devolucion,
                        a.Estado AS estado
                    FROM Asignaciones a
                    INNER JOIN ProductosCorporativos p ON a.ProductoId = p.ProductoId
                    INNER JOIN CategoriasProductos c ON p.CategoriaId = c.CategoriaId
                    LEFT JOIN Oficinas o ON a.OficinaId = o.OficinaId
                    WHERE a.Estado = 'DEVUELTO' AND a.Activo = 1
                    ORDER BY a.FechaDevolucion DESC
                """
            
                cursor.execute(query)
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]
            
            except Exception as e:
                logger.error(f"Error en obtener_productos_devueltos: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
    

    # ==================== TRASPASOS ENTRE OFICINAS ==================

    @staticmethod
    def solicitar_traspaso(producto_id, oficina_origen_id, oficina_destino_id,
                              cantidad, motivo, usuario_solicita):
            """
            Solicitar traspaso de producto de una oficina a otra.
            Requiere aprobación del líder de inventario, administrador o aprobador.
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Verificar que la oficina origen tiene el producto asignado
                cursor.execute("""
                    SELECT a.AsignacionId, p.NombreProducto, p.CodigoUnico
                    FROM Asignaciones a
                    INNER JOIN ProductosCorporativos p ON a.ProductoId = p.ProductoId
                    WHERE a.ProductoId = ? AND a.OficinaId = ? AND a.Activo = 1 AND a.Estado = 'ASIGNADO'
                """, (int(producto_id), int(oficina_origen_id)))
            
                asignacion = cursor.fetchone()
                if not asignacion:
                    return {'success': False, 'message': 'Este producto no está asignado a la oficina de origen'}
            
                asignacion_id, nombre_producto, codigo_producto = asignacion
            

            # Obtener nombres de oficinas
                cursor.execute("SELECT NombreOficina FROM Oficinas WHERE OficinaId = ?", (int(oficina_origen_id),))
                oficina_origen = cursor.fetchone()
            
                cursor.execute("SELECT NombreOficina FROM Oficinas WHERE OficinaId = ?", (int(oficina_destino_id),))
                oficina_destino = cursor.fetchone()
            
                if not oficina_origen or not oficina_destino:
                    return {'success': False, 'message': 'Una de las oficinas no existe'}
            
                nombre_oficina_origen = oficina_origen[0]
                nombre_oficina_destino = oficina_destino[0]
            

            # Crear la solicitud de traspaso
                cursor.execute("""
                    INSERT INTO TraspasosInventarioCorporativo
                    (ProductoId, OficinaOrigenId, OficinaDestinoId, AsignacionOrigenId, 
                     Cantidad, Motivo, EstadoTraspaso, UsuarioSolicita, FechaSolicitud, Activo)
                    VALUES (?, ?, ?, ?, ?, ?, 'PENDIENTE', ?, GETDATE(), 1)
                """, (int(producto_id), int(oficina_origen_id), int(oficina_destino_id), 
                      asignacion_id, int(cantidad), motivo, usuario_solicita))
            

            # Obtener el ID del traspaso creado
                cursor.execute("SELECT @@IDENTITY")
                traspaso_id = cursor.fetchone()[0]
            

            # Registrar en historial
                cursor.execute("""
                    INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, OficinaId, Accion, Cantidad, UsuarioAccion, Fecha, Observaciones)
                    VALUES (?, ?, 'SOLICITUD_TRASPASO', ?, ?, GETDATE(), ?)
                """, (int(producto_id), int(oficina_origen_id), int(cantidad), usuario_solicita,
                      f'Traspaso solicitado de {nombre_oficina_origen} a {nombre_oficina_destino}'))
            
                conn.commit()
            
                logger.info(f"Traspaso solicitado: Producto {producto_id}, {nombre_oficina_origen} -> {nombre_oficina_destino}, Usuario {usuario_solicita}")
            
                return {
                    'success': True,
                    'message': f'Solicitud de traspaso creada: {nombre_producto} de {nombre_oficina_origen} a {nombre_oficina_destino}',
                    'traspaso_id': traspaso_id
                }
            
            except Exception as e:
                logger.error(f"Error en solicitar_traspaso: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al crear solicitud de traspaso: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def aprobar_traspaso(traspaso_id, usuario_aprueba, observaciones=''):
            """
            Aprobar un traspaso y realizar el cambio de oficina.
            Solo: Líder de Inventario, Administrador o Aprobador
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Obtener información del traspaso
                cursor.execute("""
                    SELECT t.ProductoId, t.OficinaOrigenId, t.OficinaDestinoId, t.Cantidad, 
                           t.AsignacionOrigenId, t.EstadoTraspaso, p.NombreProducto,
                           o1.NombreOficina AS oficina_origen,
                           o2.NombreOficina AS oficina_destino
                    FROM TraspasosInventarioCorporativo t
                    INNER JOIN ProductosCorporativos p ON t.ProductoId = p.ProductoId
                    INNER JOIN Oficinas o1 ON t.OficinaOrigenId = o1.OficinaId
                    INNER JOIN Oficinas o2 ON t.OficinaDestinoId = o2.OficinaId
                    WHERE t.TraspasoId = ? AND t.Activo = 1
                """, (int(traspaso_id),))
            
                traspaso = cursor.fetchone()
                if not traspaso:
                    return {'success': False, 'message': 'Traspaso no encontrado'}
            
                (producto_id, oficina_origen_id, oficina_destino_id, cantidad, 
                 asignacion_origen_id, estado, nombre_producto, 
                 nombre_oficina_origen, nombre_oficina_destino) = traspaso
            
                if estado != 'PENDIENTE':
                    return {'success': False, 'message': f'Este traspaso ya fue {estado.lower()}'}
            

            # Obtener un UsuarioId válido para la nueva asignación
                cursor.execute("SELECT TOP 1 UsuarioId FROM Usuarios WHERE Activo = 1 ORDER BY UsuarioId")
                usuario_row = cursor.fetchone()
                if not usuario_row:
                    return {'success': False, 'message': 'No hay usuarios activos en la base de datos'}
                usuario_asignado_id = usuario_row[0]
            

            # Actualizar la asignación origen (marcar como traspasada)
                cursor.execute("""
                    UPDATE Asignaciones
                    SET Estado = 'TRASPASADO', FechaDevolucion = GETDATE(), Activo = 0
                    WHERE AsignacionId = ?
                """, (asignacion_origen_id,))
            

            # Crear nueva asignación en la oficina destino
                cursor.execute("""
                    INSERT INTO Asignaciones
                    (ProductoId, OficinaId, UsuarioAsignadoId, FechaAsignacion, Estado, 
                     UsuarioAsignador, Activo)
                    VALUES (?, ?, ?, GETDATE(), 'ASIGNADO', ?, 1)
                """, (int(producto_id), int(oficina_destino_id), usuario_asignado_id, usuario_aprueba))
            

            # Actualizar el estado del traspaso
                cursor.execute("""
                    UPDATE TraspasosInventarioCorporativo
                    SET EstadoTraspaso = 'APROBADO',
                        UsuarioAprueba = ?,
                        FechaAprobacion = GETDATE(),
                        ObservacionesAprobacion = ?
                    WHERE TraspasoId = ?
                """, (usuario_aprueba, observaciones, int(traspaso_id)))
            

            # Registrar en historial
                cursor.execute("""
                    INSERT INTO AsignacionesCorporativasHistorial
                    (ProductoId, OficinaId, Accion, Cantidad, UsuarioAccion, Fecha, Observaciones)
                    VALUES (?, ?, 'TRASPASO_APROBADO', ?, ?, GETDATE(), ?)
                """, (int(producto_id), int(oficina_destino_id), int(cantidad), usuario_aprueba,
                      f'Traspasado de {nombre_oficina_origen} a {nombre_oficina_destino}'))
            
                conn.commit()
            
                logger.info(f"Traspaso aprobado: ID {traspaso_id}, Producto {nombre_producto}, por {usuario_aprueba}")
            
                return {
                    'success': True,
                    'message': f'Traspaso aprobado. {nombre_producto} transferido de {nombre_oficina_origen} a {nombre_oficina_destino}'
                }
            
            except Exception as e:
                logger.error(f"Error en aprobar_traspaso: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al aprobar traspaso: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def rechazar_traspaso(traspaso_id, usuario_rechaza, motivo_rechazo):
            """
            Rechazar una solicitud de traspaso
            """
            conn = get_database_connection()
            if not conn:
                return {'success': False, 'message': 'Error de conexión'}
        
            cursor = None
            try:
                cursor = conn.cursor()
            

            # Verificar que el traspaso existe y está pendiente
                cursor.execute("""
                    SELECT EstadoTraspaso FROM TraspasosInventarioCorporativo
                    WHERE TraspasoId = ? AND Activo = 1
                """, (int(traspaso_id),))
            
                result = cursor.fetchone()
                if not result:
                    return {'success': False, 'message': 'Traspaso no encontrado'}
            
                estado = result[0]
                if estado != 'PENDIENTE':
                    return {'success': False, 'message': f'Este traspaso ya fue {estado.lower()}'}
            

            # Actualizar el traspaso
                cursor.execute("""
                    UPDATE TraspasosInventarioCorporativo
                    SET EstadoTraspaso = 'RECHAZADO',
                        UsuarioAprueba = ?,
                        FechaAprobacion = GETDATE(),
                        ObservacionesAprobacion = ?
                    WHERE TraspasoId = ?
                """, (usuario_rechaza, motivo_rechazo, int(traspaso_id)))
            
                conn.commit()
            
                logger.info(f"Traspaso rechazado: ID {traspaso_id}, por {usuario_rechaza}")
            
                return {
                    'success': True,
                    'message': 'Traspaso rechazado exitosamente'
                }
            
            except Exception as e:
                logger.error(f"Error en rechazar_traspaso: {e}")
                if conn:
                    conn.rollback()
                return {'success': False, 'message': f'Error al rechazar traspaso: {str(e)}'}
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def obtener_traspasos_pendientes():
            """
            Obtener todos los traspasos pendientes de aprobación
            """
            conn = get_database_connection()
            if not conn:
                return []
        
            cursor = None
            try:
                cursor = conn.cursor()
            
                query = """
                    SELECT 
                        t.TraspasoId AS id,
                        t.ProductoId AS producto_id,
                        p.NombreProducto AS producto_nombre,
                        p.CodigoUnico AS producto_codigo,
                        t.OficinaOrigenId AS oficina_origen_id,
                        o1.NombreOficina AS oficina_origen,
                        t.OficinaDestinoId AS oficina_destino_id,
                        o2.NombreOficina AS oficina_destino,
                        t.Cantidad AS cantidad,
                        t.Motivo AS motivo,
                        t.EstadoTraspaso AS estado,
                        t.UsuarioSolicita AS usuario_solicita,
                        t.FechaSolicitud AS fecha_solicitud,
                        t.UsuarioAprueba AS usuario_aprueba,
                        t.FechaAprobacion AS fecha_aprobacion,
                        t.ObservacionesAprobacion AS observaciones_aprobacion
                    FROM TraspasosInventarioCorporativo t
                    INNER JOIN ProductosCorporativos p ON t.ProductoId = p.ProductoId
                    INNER JOIN Oficinas o1 ON t.OficinaOrigenId = o1.OficinaId
                    INNER JOIN Oficinas o2 ON t.OficinaDestinoId = o2.OficinaId
                    WHERE t.Activo = 1 AND t.EstadoTraspaso = 'PENDIENTE'
                    ORDER BY t.FechaSolicitud DESC
                """
            
                cursor.execute(query)
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]
            
            except Exception as e:
                logger.error(f"Error en obtener_traspasos_pendientes: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    @staticmethod
    def obtener_traspasos_por_oficina(oficina_id):
            """
            Obtener todos los traspasos relacionados con una oficina específica
            (tanto origen como destino)
            """
            conn = get_database_connection()
            if not conn:
                return []
        
            cursor = None
            try:
                cursor = conn.cursor()
            
                query = """
                    SELECT 
                        t.TraspasoId AS id,
                        t.ProductoId AS producto_id,
                        p.NombreProducto AS producto_nombre,
                        p.CodigoUnico AS producto_codigo,
                        t.OficinaOrigenId AS oficina_origen_id,
                        o1.NombreOficina AS oficina_origen,
                        t.OficinaDestinoId AS oficina_destino_id,
                        o2.NombreOficina AS oficina_destino,
                        t.Cantidad AS cantidad,
                        t.Motivo AS motivo,
                        t.EstadoTraspaso AS estado,
                        t.UsuarioSolicita AS usuario_solicita,
                        t.FechaSolicitud AS fecha_solicitud,
                        t.UsuarioAprueba AS usuario_aprueba,
                        t.FechaAprobacion AS fecha_aprobacion,
                        CASE 
                            WHEN t.OficinaOrigenId = ? THEN 'Salida'
                            WHEN t.OficinaDestinoId = ? THEN 'Entrada'
                        END AS tipo_movimiento
                    FROM TraspasosInventarioCorporativo t
                    INNER JOIN ProductosCorporativos p ON t.ProductoId = p.ProductoId
                    INNER JOIN Oficinas o1 ON t.OficinaOrigenId = o1.OficinaId
                    INNER JOIN Oficinas o2 ON t.OficinaDestinoId = o2.OficinaId
                    WHERE t.Activo = 1 AND (t.OficinaOrigenId = ? OR t.OficinaDestinoId = ?)
                    ORDER BY t.FechaSolicitud DESC
                """
            
                cursor.execute(query, (int(oficina_id), int(oficina_id), int(oficina_id), int(oficina_id)))
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]
            
            except Exception as e:
                logger.error(f"Error en obtener_traspasos_por_oficina: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()