"""
Sistema de registro de contactos telefónicos
Colegio Técnico Profesional de Puriscal - Especialidad: Programación
Estudiante: Amed José Fallas Jiménez - Sección 10-7

EXPLICACIÓN TÉCNICA GENERAL PARA EXPOSICIÓN:
Este script implementa una aplicación web monolítica utilizando el framework Flask de Python
y persistencia de datos basada en archivos JSON (sin base de datos relacional). Aplica principios
de modularidad, manejo de excepciones, validación de entradas con expresiones regulares (seguridad)
y enrutamiento HTTP RESTful (GET, POST).
"""

import json
import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash

# =========================================================================
# CONFIGURACIÓN INICIAL DE FLASK Y RUTAS SEGURAS
# =========================================================================
# app = Flask(__name__): Inicializa la instancia principal de la aplicación web.
# app.secret_key: Requisito fundamental de ciberseguridad en Flask para firmar 
# criptográficamente las cookies de sesión y permitir mensajes flash seguros.
app = Flask(__name__)
app.secret_key = "agenda-contactos-clave-secreta"

# Manejo de rutas absolutas independientes del SO (Windows/Linux/macOS) 
# utilizando os.path para asegurar que el archivo JSON esté siempre en "data/contactos.json".
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_JSON = os.path.join(BASE_DIR, "data", "contactos.json")


# =========================================================================
# BLOQUE DE FUNCIONES AUXILIARES (LÓGICA DE NEGOCIO Y PERSISTENCIA)
# =========================================================================

def cargar_contactos():
    """
    Lee el archivo JSON de disco y deserializa los datos a una lista de diccionarios en Python.
    Incluye manejo de excepciones (try-except) para capturar errores de archivos corruptos 
    (json.JSONDecodeError) o problemas de lectura del sistema operativo (OSError), 
    evitando que la aplicación colapse (crash) y devolviendo una lista vacía por seguridad.
    """
    if not os.path.exists(ARCHIVO_JSON):
        return []
    try:
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def guardar_contactos(contactos):
    """
    Serializa la lista actual de contactos a formato JSON y la escribe en el disco.
    Utiliza os.makedirs(..., exist_ok=True) para garantizar dinámicamente la existencia
    del directorio 'data'. Emplea codificación utf-8 para preservar tildes y caracteres especiales.
    """
    os.makedirs(os.path.dirname(ARCHIVO_JSON), exist_ok=True)
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(contactos, f, ensure_ascii=False, indent=4)


def siguiente_id(contactos):
    """
    Genera un identificador único autoincremental para un nuevo contacto.
    Calcula el ID máximo actual utilizando una comprensión de generadores y le suma 1,
    garantizando que no existan duplicados (comienza en 1 si la lista está vacía).
    """
    return max((c["id"] for c in contactos), default=0) + 1


def validar(nombre, telefono):
    """
    Componente clave de validación de entradas (Input Validation) y ciberseguridad.
    - Verifica la longitud mínima del nombre (al menos 2 caracteres).
    - Utiliza expresiones regulares (re.fullmatch) para asegurar estrictamente que el 
      teléfono solo contenga dígitos numéricos, espacios, guiones o un '+' inicial, 
      con una longitud de entre 7 y 15 caracteres, mitigando inyecciones de datos basura.
    Devuelve una lista de errores (vacía si todo es correcto).
    """
    errores = []
    if len(nombre) < 2:
        errores.append("El nombre debe tener al menos 2 caracteres.")
    if not re.fullmatch(r"[+]?[\d\s\-]{7,15}", telefono):
        errores.append("El teléfono solo puede tener números, espacios, guiones o un + al inicio (entre 7 y 15 caracteres).")
    return errores


# =========================================================================
# RUTAS Y CONTROLADORES DE LA APLICACIÓN WEB (ENDPOINTS)
# =========================================================================

@app.route("/")
def inicio():
    """
    Ruta Raíz ('/'): Muestra la página principal de bienvenida.
    Carga los contactos actuales del archivo JSON y calcula el total de registros 
    empleando la función nativa len() para enviarlo como métrica dinámica a la vista HTML.
    """
    contactos = cargar_contactos()
    return render_template("inicio.html", total=len(contactos))


@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    """
    Ruta de Registro (CREATE): Gestiona la inserción de nuevos contactos.
    - Método GET: Renderiza el formulario vacío.
    - Método POST: Captura los datos del formulario, aplica limpieza (.strip()), 
      ejecuta la validación de seguridad y, si no hay errores, asigna un ID único, 
      guarda los cambios en el JSON, emite un mensaje flash de éxito y redirige a la lista.
    """
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        telefono = request.form.get("telefono", "").strip()
        errores = validar(nombre, telefono)
        if errores:
            for e in errores:
                flash(e, "danger")
            return render_template("registrar.html", nombre=nombre, telefono=telefono)

        contactos = cargar_contactos()
        contactos.append({"id": siguiente_id(contactos), "nombre": nombre, "telefono": telefono})
        guardar_contactos(contactos)
        flash(f"Contacto «{nombre}» registrado correctamente.", "success")
        return redirect(url_for("contactos"))
    return render_template("registrar.html", nombre="", telefono="")


@app.route("/contactos")
def contactos():
    """
    Ruta de Lectura y Búsqueda (READ): Muestra y filtra el directorio de contactos.
    - Captura parámetros opcionales de la URL ('q') para la búsqueda.
    - Convierte el texto a minúsculas y utiliza una comprensión de listas filtrando 
      coincidencias tanto en el nombre como en el teléfono.
    - Ordena alfabéticamente los resultados antes de pasarlos al HTML.
    """
    busqueda = request.args.get("q", "").strip().lower()
    lista = cargar_contactos()
    if busqueda:
        lista = [c for c in lista
                 if busqueda in c["nombre"].lower() or busqueda in c["telefono"]]
    lista.sort(key=lambda c: c["nombre"].lower())
    return render_template("contactos.html", contactos=lista, busqueda=busqueda)


@app.route("/editar/<int:id_contacto>", methods=["GET", "POST"])
def editar(id_contacto):
    """
    Ruta de Edición (UPDATE): Modifica un registro existente mediante parámetros de URL (<int:id_contacto>).
    Busca el contacto por su ID único. Si no existe, previene errores emitiendo una advertencia.
    Si recibe una petición POST, valida los nuevos datos, actualiza el diccionario en memoria 
    y sobrescribe el archivo JSON de manera segura.
    """
    lista = cargar_contactos()
    contacto = next((c for c in lista if c["id"] == id_contacto), None)
    if contacto is None:
        flash("El contacto no existe.", "warning")
        return redirect(url_for("contactos"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        telefono = request.form.get("telefono", "").strip()
        errores = validar(nombre, telefono)
        if errores:
            for e in errores:
                flash(e, "danger")
            return render_template("editar.html", contacto={"id": id_contacto,
                                       "nombre": nombre, "telefono": telefono})
        contacto["nombre"] = nombre
        contacto["telefono"] = telefono
        guardar_contactos(lista)
        flash("Contacto actualizado correctamente.", "success")
        return redirect(url_for("contactos"))
    return render_template("editar.html", contacto=contacto)


@app.route("/eliminar/<int:id_contacto>", methods=["POST"])
def eliminar(id_contacto):
    """
    Ruta de Eliminación (DELETE): Borra un contacto específico según su ID.
    Configurada estrictamente para aceptar el método HTTP POST (evitando ataques CSRF accidentales 
    o eliminaciones por enlaces GET directos). Reconstruye la lista filtrando y excluyendo 
    el ID seleccionado, guardando la nueva estructura en el disco.
    """
    lista = cargar_contactos()
    nueva = [c for c in lista if c["id"] != id_contacto]
    if len(nueva) == len(lista):
        flash("El contacto no existe.", "warning")
    else:
        guardar_contactos(nueva)
        flash("Contacto eliminado correctamente.", "success")
    return redirect(url_for("contactos"))


# =========================================================================
# PUNTO DE ENTRADA DE LA APLICACIÓN
# =========================================================================
if __name__ == "__main__":
    # app.run(debug=True): Inicia el servidor web de desarrollo local.
    # El modo debug=True activa la recarga en vivo de cambios y un depurador interactivo en navegador.
    app.run(debug=True)