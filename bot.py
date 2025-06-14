import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Configura el logging para ver errores (opcional pero útil)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Carga de Datos del JSON ---
# Asegúrate de que 'db.json' está en la misma carpeta que este script
try:
    with open('db.json', 'r', encoding='utf-8') as f:
        datos_pizzeria = json.load(f)
    datos_la_bella_italia = datos_pizzeria.get('laBellaItalia', {})
    datos_menu_solopizza = datos_pizzeria.get('solopizza', {})
    if not datos_la_bella_italia and not datos_menu_solopizza:
        logger.error("El archivo db.json parece estar vacío o no contiene las claves 'laBellaItalia' o 'solopizza'.")
        exit()
except FileNotFoundError:
    logger.error("Error: No se encontró el archivo db.json. Asegúrate de que está en el mismo directorio que bot.py.")
    exit()
except json.JSONDecodeError:
    logger.error("Error: El archivo db.json no tiene un formato JSON válido.")
    exit()

# --- Token del Bot ---
# ¡¡¡REEMPLAZA ESTO CON EL TOKEN QUE TE DIO BOTFATHER!!!
TELEGRAM_TOKEN = '7131382416:AAH7rvtF3NRMFqD4zqsBBtE0FbweKoIgubs'

# --- Funciones para Formatear Respuestas ---

def formatear_promociones_html():
    promociones = datos_la_bella_italia.get('promociones', [])
    if not promociones:
        return "Actualmente no tenemos promociones especiales. ¡Vuelve pronto!"
    
    respuesta = "<b>📢 PROMOCIONES ESPECIALES 📢</b>\n\n"
    for promo in promociones:
        respuesta += f"<b>🔹 {promo.get('nombre', 'Promoción')}</b>\n"
        respuesta += f"   <i>{promo.get('descripcion', '')}</i>\n"
        if promo.get('precio') and promo.get('precio') != "No especificado directamente, se infiere de la oferta de Miércoles": # Evitar este texto específico
            respuesta += f"   <b>Precio:</b> {promo.get('precio')}\n"
        respuesta += "\n"
    return respuesta

def formatear_horario_html():
    horario_str = datos_la_bella_italia.get('horario', '')
    if not horario_str:
        return "No hemos podido encontrar la información del horario."
    return f"<b>🕒 NUESTRO HORARIO 🕒</b>\n\n{horario_str}"

def formatear_contacto_html():
    contactos_list = datos_la_bella_italia.get('contacto', [])
    if not contactos_list:
        return "No podemos mostrar la información de contacto en este momento."
    respuesta = "<b>📞 CONTACTO 📞</b>\n\n"
    for contacto in contactos_list:
        respuesta += f"▫️ Tel: {contacto}\n"
    return respuesta

def formatear_info_adicional_html():
    info_list = datos_la_bella_italia.get('informacion_adicional', [])
    if not info_list:
        return "" # No es crítico si no hay
    respuesta = "<b>ℹ️ INFORMACIÓN ADICIONAL ℹ️</b>\n\n"
    for info in info_list:
        respuesta += f"▪️ {info}\n"
    return respuesta

def obtener_categorias_menu():
    categorias_data = datos_menu_solopizza.get('categorias', [])
    if not categorias_data:
        return "El menú no está disponible en este momento.", None

    keyboard = []
    for i, categoria in enumerate(categorias_data):
        # callback_data es lo que se envía cuando se presiona el botón
        keyboard.append([InlineKeyboardButton(categoria['nombre'], callback_data=f"cat_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    return "<b>🍕 MENÚ - ELIGE UNA CATEGORÍA 🍕</b>", reply_markup

def obtener_productos_de_categoria_html(indice_categoria_str):
    try:
        indice_categoria = int(indice_categoria_str)
        categoria = datos_menu_solopizza['categorias'][indice_categoria]
        nombre_categoria = categoria['nombre']
        productos = categoria.get('productos', [])

        if not productos:
            return f"No hay productos en la categoría: <b>{nombre_categoria}</b>", None

        respuesta = f"📜 <b>{nombre_categoria.upper()}</b> 📜\n\n"
        for prod in productos:
            respuesta += f"🔸 <b>{prod.get('nombre', 'Producto')}</b>"
            if prod.get('precio'):
                respuesta += f" - {prod.get('precio')}"
            respuesta += "\n"
            if prod.get('ingredientes') and isinstance(prod['ingredientes'], list) and len(prod['ingredientes']) > 0:
                ing_str = ", ".join(prod['ingredientes'])
                respuesta += f"   <i>Ingredientes: {ing_str}</i>\n"
            respuesta += "\n"
        
        # Botón para volver a las categorías
        keyboard = [[InlineKeyboardButton("⬅️ Volver a Categorías", callback_data="menu_principal")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return respuesta, reply_markup

    except (ValueError, IndexError, KeyError) as e:
        logger.error(f"Error al procesar categoría '{indice_categoria_str}': {e}")
        return "Error al mostrar los productos de esta categoría. Intenta de nuevo.", None

# --- Comandos del Bot (Handlers) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje de bienvenida cuando se usa /start."""
    user = update.effective_user
    mensaje_bienvenida = (
        f"¡Hola {user.mention_html()}! 👋\n"
        "Soy el bot de la <b>Pizzería La Bella Italia Menorca</b>.\n\n"
        "Aquí tienes los comandos disponibles:\n"
        "  /menu - 🍕 Ver nuestro delicioso menú\n"
        "  /promociones - 📢 Ver promociones\n"
        "  /horario - 🕒 Consultar horario\n"
        "  /contacto - 📞 Información de contacto\n"
        "  /info - ℹ️ Más sobre nosotros\n\n"
        "¡Buen provecho!"
    )
    await update.message.reply_html(mensaje_bienvenida)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las categorías del menú como botones inline."""
    texto, reply_markup = obtener_categorias_menu()
    await update.message.reply_html(texto, reply_markup=reply_markup)

async def promociones_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las promociones."""
    respuesta = formatear_promociones_html()
    await update.message.reply_html(respuesta)

async def horario_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el horario."""
    respuesta = formatear_horario_html()
    await update.message.reply_html(respuesta)

async def contacto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la información de contacto."""
    respuesta = formatear_contacto_html()
    await update.message.reply_html(respuesta)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra información adicional."""
    respuesta = formatear_info_adicional_html()
    await update.message.reply_html(respuesta)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las pulsaciones de los botones inline (callbacks)."""
    query = update.callback_query
    await query.answer()  # Es importante responder al callback

    data = query.data # Esto es lo que pusimos en callback_data

    if data == "menu_principal":
        texto, reply_markup = obtener_categorias_menu()
        await query.edit_message_text(text=texto, reply_markup=reply_markup, parse_mode='HTML')
    elif data.startswith("cat_"):
        indice_categoria_str = data.split("_")[1]
        texto, reply_markup = obtener_productos_de_categoria_html(indice_categoria_str)
        if texto:
            await query.edit_message_text(text=texto, reply_markup=reply_markup, parse_mode='HTML')
        else: # Si hay un error, al menos informa
            await query.edit_message_text(text="Lo siento, no pude cargar esa categoría.", parse_mode='HTML')


# --- Función Principal ---
def main() -> None:
    """Inicia el bot."""
    if TELEGRAM_TOKEN == 'TU_TOKEN_DE_TELEGRAM_AQUI' or not TELEGRAM_TOKEN:
        logger.error("¡ERROR! Debes reemplazar 'TU_TOKEN_DE_TELEGRAM_AQUI' con tu token real en el archivo bot.py")
        return

    # Crea la Application y pásale el token de tu bot.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registra los manejadores de comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("promociones", promociones_command))
    application.add_handler(CommandHandler("horario", horario_command))
    application.add_handler(CommandHandler("contacto", contacto_command))
    application.add_handler(CommandHandler("info", info_command))
    
    # Registra el manejador para los botones inline
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Inicia el bot.
    logger.info("Bot iniciado. Presiona Ctrl+C para detenerlo.")
    application.run_polling()

if __name__ == '__main__':
    main()