import os
import json
import logging
from glob import glob
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# --- Cargar variables de entorno del archivo .env ---
load_dotenv()

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Carga de datos y traducciones ---
try:
    with open('db/menu-principal.json', 'r', encoding='utf-8') as f:
        menu_data = json.load(f)
    translation_files = glob('db/i18n/[a-z][a-z].json')
    translations = {}
    for file_path in translation_files:
        lang_code = os.path.splitext(os.path.basename(file_path))[0]
        with open(file_path, 'r', encoding='utf-8') as f:
            translations[lang_code] = json.load(f)
    SUPPORTED_LANGUAGES = list(translations.keys())
    DEFAULT_LANGUAGE = 'es' if 'es' in SUPPORTED_LANGUAGES else SUPPORTED_LANGUAGES[0]
    logger.info(f"Idiomas cargados: {SUPPORTED_LANGUAGES}")
except FileNotFoundError as e:
    logger.error(f"Error: No se encontró el archivo JSON: {e}")
    exit()
except json.JSONDecodeError as e:
    logger.error(f"Error: El archivo JSON no tiene un formato válido: {e}")
    exit()

# --- Gestión del Token ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# --- Funciones de utilidad ---
def _(key: str, lang_code: str):
    lang_code = lang_code if lang_code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    keys = key.split('.')
    value = translations.get(lang_code)
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        logger.warning(f"Clave de traducción no encontrada para '{lang_code}': {key}")
        return key

def get_user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get('language', DEFAULT_LANGUAGE)

# --- Comandos del Bot ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lang = get_user_lang(context)
    user = update.effective_user
    
    menu_text = f"<b>{_('navegacion.menu', user_lang)}</b>"
    contact_text = f"<b>{_('navegacion.contacto', user_lang)}</b>"
    
    # --- LA CORRECCIÓN FINAL ESTÁ AQUÍ ---
    # La clave en el JSON es {contacto} (con 'o'), por lo que el código debe usar contacto=...
    # para que coincida.
    line1 = _('general.welcome_line1', user_lang).format(menu=menu_text, contacto=contact_text)
    line2 = _('general.welcome_line2', user_lang)

    welcome_message = (
        f"{_('general.greeting', user_lang)} {user.mention_html()}! 👋\n"
        f"<b>{_('pizzeria', user_lang)} La Bella Italia Menorca</b>\n\n"
        f"{line1}\n\n"
        f"{line2}"
    )
    
    if update.message:
        await update.message.reply_html(welcome_message)
    elif update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message,
            parse_mode='HTML'
        )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lang = get_user_lang(context)
    keyboard = []
    for category_key in menu_data.keys():
        translated_name = _(f"menu.{category_key}", user_lang)
        keyboard.append([InlineKeyboardButton(translated_name, callback_data=f"show_category_{category_key}")])
    title = f"<b>{_('navegacion.menu', user_lang).upper()}</b>"
    await update.message.reply_html(title, reply_markup=InlineKeyboardMarkup(keyboard))

async def contacto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lang = get_user_lang(context)
    info = (
        f"<b>📍 {_('contacto.ubicacion', user_lang)}</b>\n"
        f"{_('contacto.direccion', user_lang)}, {_('contacto.pueblo', user_lang)}\n\n"
        f"<b>🕒 {_('contacto.horario', user_lang)}</b>\n"
        f"{_('contacto.horario-abierto', user_lang)}\n"
        f"{_('contacto.horarioVerano', user_lang)}\n"
        f"{_('contacto.hora-cierre', user_lang)}\n\n"
        f"<b>📞 {_('contacto.telefonos-de-contacto', user_lang)}</b>\n"
        f"871 020 595 / 685 177 889"
    )
    await update.message.reply_html(info)
    
    await context.bot.send_location(
        chat_id=update.effective_chat.id,
        latitude=40.00192,
        longitude=3.84088
    )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = []
    for lang_code in SUPPORTED_LANGUAGES:
        lang_name = _('general.language_name', lang_code)
        keyboard.append([InlineKeyboardButton(lang_name, callback_data=f'set_lang_{lang_code}')])
    
    await update.message.reply_text(f"{_('navegacion.idioma', get_user_lang(context))}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_lang = get_user_lang(context)
    response_text = _('general.unknown_command', user_lang)
    await update.message.reply_text(response_text)

# --- Callbacks para los botones ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data

    if data.startswith("set_lang_"):
        lang_code = data.split('_')[2]
        context.user_data['language'] = lang_code
        confirmation_text = f"{_('navegacion.idioma', lang_code)}: {_('general.language_name', lang_code)}"
        await query.edit_message_text(text=confirmation_text)
        await start_command(update, context) 
        return

    user_lang = get_user_lang(context)

    if data.startswith("show_category_"):
        category_key = data.replace("show_category_", "")
        items = menu_data.get(category_key, [])
        category_name = _(f"menu.{category_key}", user_lang)
        response = f"<b>--- {category_name.upper()} ---</b>\n\n"
        for item in items:
            item_name_key = item.get("nombre")
            item_name = _(item_name_key, user_lang)
            response += f"<b>{item_name}</b> - {item.get('precio', '')}\n"
            if "ingredientes" in item:
                ingredient_keys = item.get("ingredientes", [])
                translated_ingredients = [_ (ing_key, user_lang) for ing_key in ingredient_keys]
                response += f"<i>{', '.join(translated_ingredients)}</i>\n"
            response += "\n"
        
        keyboard = [[InlineKeyboardButton(f"⬅️ {_('navegacion.menu', user_lang)}", callback_data="main_menu")]]
        await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    if data == "main_menu":
        keyboard = []
        for category_key in menu_data.keys():
            translated_name = _(f"menu.{category_key}", user_lang)
            keyboard.append([InlineKeyboardButton(translated_name, callback_data=f"show_category_{category_key}")])
        title = f"<b>{_('navegacion.menu', user_lang).upper()}</b>"
        await query.edit_message_text(title, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# --- Función Principal ---
def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("¡ERROR CRÍTICO! La variable de entorno TELEGRAM_TOKEN no está configurada.")
        return
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("contacto", contacto_command))
    application.add_handler(CommandHandler("idioma", language_command))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown_text))
    logger.info("Bot multi-idioma iniciado.")
    application.run_polling()

if __name__ == '__main__':
    main()