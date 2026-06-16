import sqlite3
from datetime import datetime
from io import BytesIO

from PIL import Image

from . import config


def _connect():
    return sqlite3.connect(config.db_path())


def init_database():
    con = _connect()
    cur = con.cursor()

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        clave TEXT,
        rol TEXT
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        categoria TEXT,
        precio REAL,
        imagen BLOB,
        activo INTEGER DEFAULT 1
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora TEXT,
        items TEXT,
        total REAL,
        usuario TEXT,
        metodo_pago TEXT,
        anulada INTEGER DEFAULT 0,
        motivo_anulacion TEXT,
        fecha_anulacion TEXT,
        usuario_anulacion TEXT
    )
    """
    )

    cur.execute("PRAGMA table_info(ventas)")
    ventas_cols = {row[1] for row in cur.fetchall()}
    if "anulada" not in ventas_cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN anulada INTEGER DEFAULT 0")
    if "motivo_anulacion" not in ventas_cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN motivo_anulacion TEXT")
    if "fecha_anulacion" not in ventas_cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN fecha_anulacion TEXT")
    if "usuario_anulacion" not in ventas_cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN usuario_anulacion TEXT")
    if "cliente" not in ventas_cols:
        cur.execute("ALTER TABLE ventas ADD COLUMN cliente TEXT")

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS cierres_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora TEXT,
        total REAL,
        usuario TEXT,
        archivo_pdf TEXT,
        total_efectivo REAL,
        total_yape REAL,
        ventas_count INTEGER,
        efectivo_contado REAL,
        diferencia_efectivo REAL,
        estado TEXT DEFAULT 'CERRADA',
        motivo_reapertura TEXT,
        fecha_reapertura TEXT,
        usuario_reapertura TEXT,
        UNIQUE(fecha, usuario)
    )
    """
    )

    cur.execute("PRAGMA table_info(cierres_caja)")
    cierres_cols = {row[1] for row in cur.fetchall()}
    if "total_efectivo" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_efectivo REAL")
    if "total_yape" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_yape REAL")
    if "ventas_count" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN ventas_count INTEGER")
    if "efectivo_contado" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN efectivo_contado REAL")
    if "diferencia_efectivo" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN diferencia_efectivo REAL")
    if "estado" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN estado TEXT DEFAULT 'CERRADA'")
    if "motivo_reapertura" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN motivo_reapertura TEXT")
    if "fecha_reapertura" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN fecha_reapertura TEXT")
    if "usuario_reapertura" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN usuario_reapertura TEXT")
    if "total_tarjeta" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_tarjeta REAL")
    if "total_qr" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_qr REAL")
    if "total_ingresos" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_ingresos REAL")
    if "total_egresos" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_egresos REAL")
    if "monto_apertura" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN monto_apertura REAL")
    if "efectivo_esperado" not in cierres_cols:
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN efectivo_esperado REAL")

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS aperturas_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora_apertura TEXT,
        usuario TEXT,
        monto_inicial REAL DEFAULT 0,
        estado TEXT DEFAULT 'ABIERTA',
        hora_cierre TEXT,
        UNIQUE(fecha, usuario)
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS movimientos_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora TEXT,
        usuario TEXT,
        tipo TEXT,
        monto REAL,
        descripcion TEXT
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS ajustes (
        clave TEXT PRIMARY KEY,
        valor TEXT
    )
    """
    )

    cur.execute("INSERT OR IGNORE INTO usuarios (usuario, clave, rol) VALUES ('admin','1234','admin')")
    cur.execute("INSERT OR IGNORE INTO usuarios (usuario, clave, rol) VALUES ('caja','1234','cajero')")

    cur.execute("SELECT COUNT(*) FROM productos")
    total_productos = cur.fetchone()[0]
    if total_productos == 0:
        productos_demo = [
            ("Alitas BBQ", "Alitas", 0.00),
            ("Alitas Crispy", "Alitas", 0.00),
            ("Salchipapas", "Salchipapas", 0.00),
            ("Chicha morada", "Bebidas", 0.00),
        ]
        for nombre, cat, precio in productos_demo:
            cur.execute("INSERT INTO productos (nombre, categoria, precio) VALUES (?,?,?)", (nombre, cat, precio))

    con.commit()
    con.close()


def obtener_ajuste(clave, default=None):
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT valor FROM ajustes WHERE clave=?", (str(clave),))
    row = cur.fetchone()
    con.close()
    if row is None:
        return default
    val = row[0]
    return default if val is None else val


def guardar_ajuste(clave, valor):
    con = _connect()
    cur = con.cursor()
    cur.execute("INSERT INTO ajustes (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (str(clave), None if valor is None else str(valor)))
    con.commit()
    con.close()


def validar_login(usuario, clave):
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT usuario, rol FROM usuarios WHERE usuario=? AND clave=?", (usuario, clave))
    data = cur.fetchone()
    con.close()
    return data


def obtener_productos():
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT id, nombre, categoria, precio, imagen FROM productos WHERE activo=1 ORDER BY categoria, nombre")
    data = cur.fetchall()
    con.close()
    return data


def agregar_producto(nombre, categoria, precio, imagen_blob=None):
    con = _connect()
    cur = con.cursor()
    cur.execute("INSERT INTO productos (nombre, categoria, precio, imagen) VALUES (?,?,?,?)", (nombre, categoria, precio, imagen_blob))
    con.commit()
    con.close()


def actualizar_producto(producto_id, nombre, categoria, precio):
    con = _connect()
    cur = con.cursor()
    cur.execute("UPDATE productos SET nombre=?, categoria=?, precio=? WHERE id=?", (nombre, categoria, precio, producto_id))
    con.commit()
    con.close()


def desactivar_producto(producto_id):
    con = _connect()
    cur = con.cursor()
    cur.execute("UPDATE productos SET activo=0 WHERE id=?", (producto_id,))
    con.commit()
    con.close()


def actualizar_imagen_producto(producto_id, imagen_blob):
    con = _connect()
    cur = con.cursor()
    cur.execute("UPDATE productos SET imagen=? WHERE id=?", (imagen_blob, producto_id))
    con.commit()
    con.close()


def convertir_imagen_a_blob_png(file_path, max_size=(512, 512)):
    img = Image.open(file_path)
    img = img.convert("RGBA")
    img.thumbnail(max_size)
    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True, compress_level=6)
    return buffer.getvalue()


def registrar_venta(items, total, usuario, metodo_pago, cliente=None):
    fecha = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO ventas (fecha, hora, items, total, usuario, metodo_pago, cliente, anulada) VALUES (?,?,?,?,?,?,?,0)",
        (fecha, hora, items, total, usuario, metodo_pago, cliente),
    )
    venta_id = cur.lastrowid
    con.commit()
    con.close()
    return venta_id


def obtener_ventas_dia(usuario=None, incluir_anuladas=False):
    fecha = datetime.now().strftime("%Y-%m-%d")
    con = _connect()
    cur = con.cursor()
    anulada_sql = "" if incluir_anuladas else " AND anulada=0"
    if usuario:
        cur.execute(
            f"SELECT id, hora, items, total, metodo_pago, usuario, anulada, motivo_anulacion, cliente FROM ventas WHERE fecha=? AND usuario=?{anulada_sql} ORDER BY hora",
            (fecha, usuario),
        )
    else:
        cur.execute(
            f"SELECT id, hora, items, total, metodo_pago, usuario, anulada, motivo_anulacion, cliente FROM ventas WHERE fecha=?{anulada_sql} ORDER BY hora",
            (fecha,),
        )
    data = cur.fetchall()
    con.close()
    return data


def total_ventas_dia(usuario=None):
    fecha = datetime.now().strftime("%Y-%m-%d")
    con = _connect()
    cur = con.cursor()
    if usuario:
        cur.execute("SELECT SUM(total) FROM ventas WHERE fecha=? AND usuario=? AND anulada=0", (fecha, usuario))
    else:
        cur.execute("SELECT SUM(total) FROM ventas WHERE fecha=? AND anulada=0", (fecha,))
    total = cur.fetchone()[0]
    con.close()
    return total if total else 0


def obtener_ventas_rango(fecha_inicio, fecha_fin, usuario=None, incluir_anuladas=False):
    con = _connect()
    cur = con.cursor()
    anulada_sql = "" if incluir_anuladas else " AND anulada=0"
    if usuario:
        cur.execute(
            f"SELECT id, fecha, hora, items, total, usuario, metodo_pago, anulada, motivo_anulacion, cliente FROM ventas WHERE fecha BETWEEN ? AND ? AND usuario=?{anulada_sql} ORDER BY fecha, hora",
            (fecha_inicio, fecha_fin, usuario),
        )
    else:
        cur.execute(
            f"SELECT id, fecha, hora, items, total, usuario, metodo_pago, anulada, motivo_anulacion, cliente FROM ventas WHERE fecha BETWEEN ? AND ?{anulada_sql} ORDER BY fecha, hora",
            (fecha_inicio, fecha_fin),
        )
    data = cur.fetchall()
    con.close()
    return data


def obtener_resumen_por_dia(fecha_inicio, fecha_fin, usuario=None):
    con = _connect()
    cur = con.cursor()
    if usuario:
        cur.execute(
            "SELECT fecha, COUNT(*), SUM(total) FROM ventas WHERE fecha BETWEEN ? AND ? AND usuario=? AND anulada=0 GROUP BY fecha ORDER BY fecha",
            (fecha_inicio, fecha_fin, usuario),
        )
    else:
        cur.execute(
            "SELECT fecha, COUNT(*), SUM(total) FROM ventas WHERE fecha BETWEEN ? AND ? AND anulada=0 GROUP BY fecha ORDER BY fecha",
            (fecha_inicio, fecha_fin),
        )
    data = cur.fetchall()
    con.close()
    return [(f, int(c), float(t or 0)) for (f, c, t) in data]


def obtener_resumen_por_metodo(fecha_inicio, fecha_fin, usuario=None):
    con = _connect()
    cur = con.cursor()
    if usuario:
        cur.execute(
            "SELECT metodo_pago, COUNT(*), SUM(total) FROM ventas WHERE fecha BETWEEN ? AND ? AND usuario=? AND anulada=0 GROUP BY metodo_pago ORDER BY metodo_pago",
            (fecha_inicio, fecha_fin, usuario),
        )
    else:
        cur.execute(
            "SELECT metodo_pago, COUNT(*), SUM(total) FROM ventas WHERE fecha BETWEEN ? AND ? AND anulada=0 GROUP BY metodo_pago ORDER BY metodo_pago",
            (fecha_inicio, fecha_fin),
        )
    data = cur.fetchall()
    con.close()
    return [(m or "Sin método", int(c), float(t or 0)) for (m, c, t) in data]


def anular_venta(venta_id, motivo, usuario_admin):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "UPDATE ventas SET anulada=1, motivo_anulacion=?, fecha_anulacion=?, usuario_anulacion=? WHERE id=? AND anulada=0",
        (motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario_admin, venta_id),
    )
    con.commit()
    con.close()


def obtener_venta_por_id(venta_id):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, fecha, hora, items, total, metodo_pago, usuario, anulada, motivo_anulacion, cliente FROM ventas WHERE id=?",
        (venta_id,),
    )
    row = cur.fetchone()
    con.close()
    return row


def obtener_cierre_caja(fecha, usuario):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """
        SELECT
            fecha,
            hora,
            total,
            usuario,
            archivo_pdf,
            total_efectivo,
            total_yape,
            ventas_count,
            efectivo_contado,
            diferencia_efectivo,
            estado,
            motivo_reapertura,
            fecha_reapertura,
            usuario_reapertura,
            total_tarjeta,
            total_qr,
            total_ingresos,
            total_egresos,
            monto_apertura,
            efectivo_esperado
        FROM cierres_caja
        WHERE fecha=? AND usuario=?
        """,
        (fecha, usuario),
    )
    data = cur.fetchone()
    con.close()
    return data


def registrar_cierre_caja(fecha, hora, total, usuario, archivo_pdf, total_efectivo, total_yape, ventas_count, efectivo_contado, diferencia_efectivo):
    return registrar_cierre_caja_v2(
        fecha=fecha,
        hora=hora,
        total=total,
        usuario=usuario,
        archivo_pdf=archivo_pdf,
        total_efectivo=total_efectivo,
        total_yape=total_yape,
        ventas_count=ventas_count,
        efectivo_contado=efectivo_contado,
        diferencia_efectivo=diferencia_efectivo,
    )


def registrar_cierre_caja_v2(
    *,
    fecha,
    hora,
    total,
    usuario,
    archivo_pdf,
    total_efectivo,
    total_yape,
    ventas_count,
    efectivo_contado,
    diferencia_efectivo,
    total_tarjeta=0.0,
    total_qr=0.0,
    total_ingresos=0.0,
    total_egresos=0.0,
    monto_apertura=0.0,
    efectivo_esperado=None,
):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO cierres_caja
        (
            fecha,
            hora,
            total,
            usuario,
            archivo_pdf,
            total_efectivo,
            total_yape,
            ventas_count,
            efectivo_contado,
            diferencia_efectivo,
            estado,
            motivo_reapertura,
            fecha_reapertura,
            usuario_reapertura,
            total_tarjeta,
            total_qr,
            total_ingresos,
            total_egresos,
            monto_apertura,
            efectivo_esperado
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            fecha,
            hora,
            total,
            usuario,
            archivo_pdf,
            float(total_efectivo or 0),
            float(total_yape or 0),
            int(ventas_count or 0),
            float(efectivo_contado or 0),
            float(diferencia_efectivo or 0),
            "CERRADA",
            None,
            None,
            None,
            float(total_tarjeta or 0),
            float(total_qr or 0),
            float(total_ingresos or 0),
            float(total_egresos or 0),
            float(monto_apertura or 0),
            None if efectivo_esperado is None else float(efectivo_esperado),
        ),
    )
    con.commit()
    con.close()


def obtener_apertura_caja(fecha, usuario):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT fecha, hora_apertura, usuario, monto_inicial, estado, hora_cierre FROM aperturas_caja WHERE fecha=? AND usuario=?",
        (fecha, usuario),
    )
    data = cur.fetchone()
    con.close()
    return data


def registrar_apertura_caja(fecha, hora_apertura, usuario, monto_inicial):
    con = _connect()
    cur = con.cursor()
    try:
        cur.execute(
            "INSERT INTO aperturas_caja (fecha, hora_apertura, usuario, monto_inicial, estado, hora_cierre) VALUES (?,?,?,?, 'ABIERTA', NULL)",
            (fecha, hora_apertura, usuario, float(monto_inicial or 0)),
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()


def cerrar_apertura_caja(fecha, usuario, hora_cierre):
    con = _connect()
    cur = con.cursor()
    cur.execute("UPDATE aperturas_caja SET estado='CERRADA', hora_cierre=? WHERE fecha=? AND usuario=?", (hora_cierre, fecha, usuario))
    con.commit()
    con.close()


def reabrir_caja(fecha, usuario_caja, usuario_reapertura, motivo):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """
        UPDATE cierres_caja
        SET estado='ABIERTA', motivo_reapertura=?, fecha_reapertura=?, usuario_reapertura=?
        WHERE fecha=? AND usuario=?
        """,
        (motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario_reapertura, fecha, usuario_caja),
    )
    cur.execute(
        """
        UPDATE aperturas_caja
        SET estado='ABIERTA', hora_cierre=NULL
        WHERE fecha=? AND usuario=?
        """,
        (fecha, usuario_caja),
    )
    con.commit()
    con.close()


def registrar_movimiento_caja(fecha, hora, usuario, tipo, monto, descripcion=None):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO movimientos_caja (fecha, hora, usuario, tipo, monto, descripcion) VALUES (?,?,?,?,?,?)",
        (fecha, hora, usuario, str(tipo or ""), float(monto or 0), descripcion),
    )
    con.commit()
    con.close()


def obtener_movimientos_dia(usuario=None):
    fecha = datetime.now().strftime("%Y-%m-%d")
    con = _connect()
    cur = con.cursor()
    if usuario:
        cur.execute(
            "SELECT id, fecha, hora, tipo, monto, descripcion, usuario FROM movimientos_caja WHERE fecha=? AND usuario=? ORDER BY hora",
            (fecha, usuario),
        )
    else:
        cur.execute("SELECT id, fecha, hora, tipo, monto, descripcion, usuario FROM movimientos_caja WHERE fecha=? ORDER BY hora", (fecha,))
    data = cur.fetchall()
    con.close()
    return data


def resumen_movimientos(fecha_inicio, fecha_fin, usuario=None):
    con = _connect()
    cur = con.cursor()
    if usuario:
        cur.execute(
            "SELECT tipo, SUM(monto) FROM movimientos_caja WHERE fecha BETWEEN ? AND ? AND usuario=? GROUP BY tipo",
            (fecha_inicio, fecha_fin, usuario),
        )
    else:
        cur.execute("SELECT tipo, SUM(monto) FROM movimientos_caja WHERE fecha BETWEEN ? AND ? GROUP BY tipo", (fecha_inicio, fecha_fin))
    rows = cur.fetchall()
    con.close()
    total_ing = 0.0
    total_egr = 0.0
    for tipo, total in rows:
        t = float(total or 0)
        if str(tipo or "").upper() == "INGRESO":
            total_ing += t
        elif str(tipo or "").upper() == "EGRESO":
            total_egr += t
    return total_ing, total_egr

