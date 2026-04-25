from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime
import psycopg
from psycopg.rows import dict_row
from config import USUARIO_ADMIN, PASSWORD_ADMIN, SECRET_KEY, DATABASE_URL

app = Flask(__name__)
app.secret_key = SECRET_KEY

CATEGORIAS_POR_DEFECTO = [
    {"nombre": "Verdulería", "slug": "verduleria", "icono": "🥦", "color": "#2E7D32"},
    {"nombre": "Lácteos", "slug": "lacteos", "icono": "🥛", "color": "#1976D2"},
    {"nombre": "Carnes", "slug": "carnes", "icono": "🥩", "color": "#C62828"},
    {"nombre": "Pollo", "slug": "pollo", "icono": "🍗", "color": "#EF6C00"},
    {"nombre": "Enlatados", "slug": "enlatados", "icono": "🥫", "color": "#6D4C41"},
    {"nombre": "Agranel", "slug": "agranel", "icono": "🛒", "color": "#00897B"},
    {"nombre": "Panificados", "slug": "panificados", "icono": "🍞", "color": "#8D6E63"},
    {"nombre": "Confites", "slug": "confites", "icono": "🍬", "color": "#D81B60"},
    {"nombre": "Dulces y salados", "slug": "dulces-salados", "icono": "🍪", "color": "#5E35B1"},
    {"nombre": "Bebidas", "slug": "bebidas", "icono": "🥤", "color": "#039BE5"},
    {"nombre": "Productos de limpieza", "slug": "productos-limpieza", "icono": "🧴", "color": "#00838F"},
    {"nombre": "Especias", "slug": "especias", "icono": "🌶️", "color": "#E53935"},
    {"nombre": "Embutidos", "slug": "embutidos", "icono": "🌭", "color": "#AD1457"},
    {"nombre": "Cigarrillos", "slug": "cigarrillos", "icono": "🚬", "color": "#546E7A"},
    {"nombre": "Perfumería", "slug": "perfumeria", "icono": "🧼", "color": "#7B1FA2"},
]


def login_requerido(funcion):
    @wraps(funcion)
    def decorada(*args, **kwargs):
        if not session.get("logueado"):
            return redirect(url_for("login"))
        return funcion(*args, **kwargs)
    return decorada


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def slugify(texto):
    texto = texto.strip().lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u"
    }
    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    resultado = []
    for char in texto:
        if char.isalnum():
            resultado.append(char)
        elif char in [" ", "-", "_", "/"]:
            resultado.append("-")

    slug = "".join(resultado)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE,
                    icono TEXT NOT NULL,
                    color TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id SERIAL PRIMARY KEY,
                    categoria TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    precio_compra NUMERIC(12,2) NOT NULL,
                    precio_reventa NUMERIC(12,2) NOT NULL,
                    lugar_compra TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)

            cursor.execute("SELECT COUNT(*) AS total FROM categorias")
            total_categorias = cursor.fetchone()["total"]

            if total_categorias == 0:
                for categoria in CATEGORIAS_POR_DEFECTO:
                    cursor.execute("""
                        INSERT INTO categorias (nombre, slug, icono, color)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        categoria["nombre"],
                        categoria["slug"],
                        categoria["icono"],
                        categoria["color"]
                    ))


def obtener_categorias():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, slug, icono, color
                FROM categorias
                ORDER BY nombre ASC
            """)
            return cursor.fetchall()


def obtener_categoria_por_slug(slug):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, slug, icono, color
                FROM categorias
                WHERE slug = %s
            """, (slug,))
            return cursor.fetchone()


def obtener_categoria_por_id(categoria_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, slug, icono, color
                FROM categorias
                WHERE id = %s
            """, (categoria_id,))
            return cursor.fetchone()


def obtener_producto_por_id(producto_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, categoria, descripcion, precio_compra, precio_reventa, lugar_compra, created_at, updated_at
                FROM productos
                WHERE id = %s
            """, (producto_id,))
            return cursor.fetchone()


def obtener_lugares_compra():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT lugar_compra
                FROM productos
                WHERE lugar_compra IS NOT NULL
                  AND TRIM(lugar_compra) <> ''
                ORDER BY lugar_compra ASC
            """)
            return [fila["lugar_compra"] for fila in cursor.fetchall()]


def obtener_categorias_con_conteo():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT categoria, COUNT(*) AS total
                FROM productos
                GROUP BY categoria
            """)
            conteos_raw = cursor.fetchall()

            cursor.execute("""
                SELECT id, nombre, slug, icono, color
                FROM categorias
                ORDER BY nombre ASC
            """)
            categorias = cursor.fetchall()

    conteos = {fila["categoria"]: fila["total"] for fila in conteos_raw}
    resultado = []

    for categoria in categorias:
        item = dict(categoria)
        item["total_productos"] = conteos.get(categoria["nombre"], 0)
        resultado.append(item)

    return resultado


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        if usuario == USUARIO_ADMIN and password == PASSWORD_ADMIN:
            session["logueado"] = True
            session["usuario"] = usuario
            flash("Sesión iniciada correctamente.", "success")
            return redirect(url_for("index"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_requerido
def index():
    categorias = obtener_categorias_con_conteo()
    return render_template("index.html", categorias=categorias)


@app.route("/categorias", methods=["GET", "POST"])
@login_requerido
def gestionar_categorias():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        icono = request.form.get("icono", "").strip() or "📦"
        color = request.form.get("color", "").strip() or "#1F7A4C"

        if not nombre:
            flash("Debes completar el nombre de la categoría.", "error")
            return redirect(url_for("gestionar_categorias"))

        slug = slugify(nombre)

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id
                    FROM categorias
                    WHERE nombre = %s OR slug = %s
                """, (nombre, slug))
                existente = cursor.fetchone()

                if existente:
                    flash("Ya existe una categoría con ese nombre.", "error")
                    return redirect(url_for("gestionar_categorias"))

                cursor.execute("""
                    INSERT INTO categorias (nombre, slug, icono, color)
                    VALUES (%s, %s, %s, %s)
                """, (nombre, slug, icono, color))

        flash("Categoría creada correctamente.", "success")
        return redirect(url_for("gestionar_categorias"))

    categorias = obtener_categorias_con_conteo()
    return render_template("categorias.html", categorias=categorias)


@app.route("/categorias/editar/<int:categoria_id>", methods=["GET", "POST"])
@login_requerido
def editar_categoria(categoria_id):
    categoria = obtener_categoria_por_id(categoria_id)

    if not categoria:
        return "Categoría no encontrada", 404

    if request.method == "POST":
        nombre_nuevo = request.form.get("nombre", "").strip()
        icono_nuevo = request.form.get("icono", "").strip() or "📦"
        color_nuevo = request.form.get("color", "").strip() or "#1F7A4C"

        if not nombre_nuevo:
            flash("Debes completar el nombre de la categoría.", "error")
            return redirect(url_for("editar_categoria", categoria_id=categoria_id))

        slug_nuevo = slugify(nombre_nuevo)

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id
                    FROM categorias
                    WHERE (nombre = %s OR slug = %s) AND id <> %s
                """, (nombre_nuevo, slug_nuevo, categoria_id))
                repetida = cursor.fetchone()

                if repetida:
                    flash("Ya existe otra categoría con ese nombre.", "error")
                    return redirect(url_for("editar_categoria", categoria_id=categoria_id))

                cursor.execute("""
                    UPDATE categorias
                    SET nombre = %s, slug = %s, icono = %s, color = %s
                    WHERE id = %s
                """, (nombre_nuevo, slug_nuevo, icono_nuevo, color_nuevo, categoria_id))

                if nombre_nuevo != categoria["nombre"]:
                    cursor.execute("""
                        UPDATE productos
                        SET categoria = %s, updated_at = %s
                        WHERE categoria = %s
                    """, (
                        nombre_nuevo,
                        datetime.now(),
                        categoria["nombre"]
                    ))

        flash("Categoría editada correctamente.", "success")
        return redirect(url_for("gestionar_categorias"))

    return render_template("editar_categoria.html", categoria=categoria)


@app.route("/categorias/eliminar/<int:categoria_id>")
@login_requerido
def eliminar_categoria(categoria_id):
    categoria = obtener_categoria_por_id(categoria_id)

    if not categoria:
        return "Categoría no encontrada", 404

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM productos
                WHERE categoria = %s
            """, (categoria["nombre"],))
            total = cursor.fetchone()["total"]

            if total > 0:
                flash("No puedes eliminar una categoría que tiene productos cargados.", "error")
                return redirect(url_for("gestionar_categorias"))

            cursor.execute("DELETE FROM categorias WHERE id = %s", (categoria_id,))

    flash("Categoría eliminada correctamente.", "success")
    return redirect(url_for("gestionar_categorias"))


@app.route("/categoria/<slug>", methods=["GET", "POST"])
@login_requerido
def ver_categoria(slug):
    categoria = obtener_categoria_por_slug(slug)

    if not categoria:
        return "Categoría no encontrada", 404

    if request.method == "POST":
        descripcion = request.form.get("descripcion", "").strip()
        precio_compra = request.form.get("precio_compra", "").strip()
        precio_reventa = request.form.get("precio_reventa", "").strip()
        lugar_compra = request.form.get("lugar_compra", "").strip()

        if not descripcion or not precio_compra or not precio_reventa or not lugar_compra:
            flash("Completa todos los campos para guardar el producto.", "error")
            return redirect(url_for("ver_categoria", slug=slug))

        ahora = datetime.now()

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO productos (
                        categoria, descripcion, precio_compra, precio_reventa,
                        lugar_compra, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    categoria["nombre"],
                    descripcion,
                    float(precio_compra),
                    float(precio_reventa),
                    lugar_compra,
                    ahora,
                    ahora
                ))

        flash("Producto guardado correctamente.", "success")
        return redirect(url_for("ver_categoria", slug=slug))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, categoria, descripcion, precio_compra, precio_reventa, lugar_compra, created_at, updated_at
                FROM productos
                WHERE categoria = %s
                ORDER BY descripcion ASC
            """, (categoria["nombre"],))
            filas = cursor.fetchall()

    productos = []
    total_compra = 0
    total_reventa = 0

    for fila in filas:
        producto = dict(fila)
        producto["precio_compra"] = float(producto["precio_compra"])
        producto["precio_reventa"] = float(producto["precio_reventa"])
        producto["ganancia"] = producto["precio_reventa"] - producto["precio_compra"]
        total_compra += producto["precio_compra"]
        total_reventa += producto["precio_reventa"]
        productos.append(producto)

    resumen = {
        "cantidad": len(productos),
        "total_compra": total_compra,
        "total_reventa": total_reventa,
        "ganancia_total": total_reventa - total_compra
    }

    lugares_compra = obtener_lugares_compra()
    categorias = obtener_categorias()

    return render_template(
        "categoria.html",
        categoria=categoria,
        productos=productos,
        resumen=resumen,
        lugares_compra=lugares_compra,
        categorias=categorias
    )


@app.route("/editar/<int:producto_id>", methods=["GET", "POST"])
@login_requerido
def editar_producto(producto_id):
    producto = obtener_producto_por_id(producto_id)

    if not producto:
        return "Producto no encontrado", 404

    categorias = obtener_categorias()
    lugares_compra = obtener_lugares_compra()

    if request.method == "POST":
        descripcion = request.form.get("descripcion", "").strip()
        precio_compra = request.form.get("precio_compra", "").strip()
        precio_reventa = request.form.get("precio_reventa", "").strip()
        lugar_compra = request.form.get("lugar_compra", "").strip()
        nueva_categoria_nombre = request.form.get("categoria", "").strip()

        if not descripcion or not precio_compra or not precio_reventa or not lugar_compra or not nueva_categoria_nombre:
            flash("Completa todos los campos para editar el producto.", "error")
            return redirect(url_for("editar_producto", producto_id=producto_id))

        categoria_destino = None
        for categoria in categorias:
            if categoria["nombre"] == nueva_categoria_nombre:
                categoria_destino = categoria
                break

        if not categoria_destino:
            flash("La categoría seleccionada no existe.", "error")
            return redirect(url_for("editar_producto", producto_id=producto_id))

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE productos
                    SET categoria = %s,
                        descripcion = %s,
                        precio_compra = %s,
                        precio_reventa = %s,
                        lugar_compra = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (
                    nueva_categoria_nombre,
                    descripcion,
                    float(precio_compra),
                    float(precio_reventa),
                    lugar_compra,
                    datetime.now(),
                    producto_id
                ))

        flash("Producto editado correctamente.", "success")
        return redirect(url_for("ver_categoria", slug=categoria_destino["slug"]))

    categoria_actual = None
    for categoria in categorias:
        if categoria["nombre"] == producto["categoria"]:
            categoria_actual = categoria
            break

    return render_template(
        "editar_producto.html",
        producto=producto,
        categorias=categorias,
        categoria_actual=categoria_actual,
        lugares_compra=lugares_compra
    )


@app.route("/eliminar/<int:producto_id>")
@login_requerido
def eliminar_producto(producto_id):
    producto = obtener_producto_por_id(producto_id)

    if not producto:
        return "Producto no encontrado", 404

    categorias = obtener_categorias()
    categoria = None
    for item in categorias:
        if item["nombre"] == producto["categoria"]:
            categoria = item
            break

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM productos WHERE id = %s", (producto_id,))

    flash("Producto eliminado correctamente.", "success")

    if categoria:
        return redirect(url_for("ver_categoria", slug=categoria["slug"]))
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)