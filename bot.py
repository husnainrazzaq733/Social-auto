import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_TOKEN, GEMINI_API_KEY
from platforms.facebook import post_to_facebook
from platforms.instagram import post_to_instagram
from platforms.youtube import post_to_youtube
from platforms.tiktok import post_to_tiktok

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SELECT_PLATFORMS, GET_CAPTION = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assalam o Alaikum! Mujhe koi Image ya Video bhejen taake main usay aapke social media par post kar sakun.")

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    file_id = None
    is_video = False
    is_text_only = False
    
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        if message.video.file_size > 20 * 1024 * 1024:
            await message.reply_text("❌ Error: Video 20MB se badi hai! Telegram Bot API maximum 20MB ki video allow karti hai. Koi choti video bhejen.")
            return ConversationHandler.END
        file_id = message.video.file_id
        is_video = True
    elif message.animation:
        file_id = message.animation.file_id
        is_video = True
    elif message.document and message.document.mime_type and ('video' in message.document.mime_type or 'image' in message.document.mime_type):
        if message.document.file_size > 20 * 1024 * 1024:
            await message.reply_text("❌ Error: File 20MB se badi hai! Telegram Bot API maximum 20MB ki file allow karti hai. Koi choti file bhejen.")
            return ConversationHandler.END
        file_id = message.document.file_id
        is_video = 'video' in message.document.mime_type
    elif message.text and not message.text.startswith('/'):
        is_text_only = True
        context.user_data['text_content'] = message.text
    else:
        await message.reply_text("Bhai, please koi Image, Video ya Text bhejen.")
        return ConversationHandler.END
        
    context.user_data['file_id'] = file_id
    context.user_data['is_video'] = is_video
    context.user_data['is_text_only'] = is_text_only
    
    from config import ACCOUNTS
    platforms = {}
    for fb in ACCOUNTS.get('facebook', []):
        platforms[f"fb_{fb['id']}"] = {'selected': False, 'name': fb['name'], 'id': fb['id'], 'type': 'facebook'}
    for ig in ACCOUNTS.get('instagram', []):
        platforms[f"ig_{ig['id']}"] = {'selected': False, 'name': ig['name'], 'id': ig['id'], 'type': 'instagram'}
        
    platforms['youtube'] = {'selected': False, 'type': 'youtube'}
    platforms['tiktok'] = {'selected': False, 'type': 'tiktok'}
    context.user_data['platforms'] = platforms

    await show_platform_menu(update, context)
    return SELECT_PLATFORMS

async def show_platform_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platforms = context.user_data['platforms']
    is_video = context.user_data['is_video']
    is_text_only = context.user_data.get('is_text_only', False)
    
    keyboard = []
    for key, data in platforms.items():
        if data['type'] == 'facebook':
            keyboard.append([InlineKeyboardButton(f"{'✅ ' if data['selected'] else ''}Facebook: {data['name']}", callback_data=f"toggle_{key}")])
        elif data['type'] == 'instagram' and not is_text_only:
            keyboard.append([InlineKeyboardButton(f"{'✅ ' if data['selected'] else ''}Instagram: {data['name']}", callback_data=f"toggle_{key}")])
            
    if is_video:
        keyboard.append([
            InlineKeyboardButton(f"{'✅ ' if platforms['youtube']['selected'] else ''}YouTube", callback_data='toggle_youtube'),
            InlineKeyboardButton(f"{'✅ ' if platforms['tiktok']['selected'] else ''}TikTok", callback_data='toggle_tiktok')
        ])
        
    keyboard.append([InlineKeyboardButton("➡️ Next (Caption likhen ya Auto Generate karen)", callback_data='next')])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Kis kis platform par post karna hai? (Select karen aur Next dabayen)"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def handle_platform_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'cancel':
        await query.edit_message_text("Process cancel kar diya gaya hai.")
        context.user_data.clear()
        return ConversationHandler.END
        
    if data == 'next':
        platforms = context.user_data['platforms']
        if not any(p['selected'] for p in platforms.values()):
            await query.answer("Kam az kam ek platform select karen!", show_alert=True)
            return SELECT_PLATFORMS
            
        is_text_only = context.user_data.get('is_text_only', False)
        if is_text_only:
            await query.edit_message_text("Text post upload ho rahi hai...")
            return await get_caption_and_post(update, context)
            
        await query.edit_message_text("Behtareen! Ab agar aap khud Caption likhna chahte hain toh type karke bhejen. \n\nAgar aap chahte hain ke AI khud Caption likhe, toh sirf **Auto** likh kar bhej den.")
        return GET_CAPTION
        
    if data.startswith('toggle_'):
        platform_key = data.replace('toggle_', '')
        if platform_key in context.user_data['platforms']:
            context.user_data['platforms'][platform_key]['selected'] = not context.user_data['platforms'][platform_key]['selected']
        await show_platform_menu(update, context)
        return SELECT_PLATFORMS

async def get_caption_and_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_text_only = context.user_data.get('is_text_only', False)
    if is_text_only:
        user_caption = context.user_data.get('text_content', '')
        message_obj = update.callback_query.message
    else:
        user_caption = update.message.text
        message_obj = update.message
        
    file_id = context.user_data.get('file_id')
    is_video = context.user_data.get('is_video', False)
    platforms = context.user_data['platforms']
    
    media_path = None
    new_file = None
    
    status_msg = await message_obj.reply_text("⏳ **Progress Tracker:**\n📥 Start ho raha hai...")
    
    if not is_text_only:
        await status_msg.edit_text("⏳ **Progress Tracker:**\n📥 Telegram se Media download ho raha hai (is mein thora time lag sakta hai)...")
        try:
            # Download file
            new_file = await context.bot.get_file(file_id)
            ext = ".mp4" if is_video else ".jpg"
            media_path = f"temp_media{ext}"
            await new_file.download_to_drive(media_path)
        except Exception as e:
            await status_msg.edit_text(f"❌ **Download Failed!**\n\nTelegram API Error: {str(e)}\n\nBot sirf 20MB tak ki files download kar sakta hai. Baraye meharbani koi choti video bhejen.")
            context.user_data.clear()
            return ConversationHandler.END
    
    caption = user_caption
    
    # Auto Caption using Gemini
    if user_caption.strip().lower() == 'auto' and GEMINI_API_KEY:
        await status_msg.edit_text("⏳ **Progress Tracker:**\n📥 Media Ready!\n🧠 AI (Google Gemini) Hashtags bana raha hai...")
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            if is_video:
                # AI cant see video without extracting frames, so use generic viral tags
                caption = "#video #viral #trending #foryou #explorepage #reels #shorts"
            else:
                import PIL.Image
                with PIL.Image.open(media_path) as img:
                    response = model.generate_content(["Is image ko dekh kar sirf 10-15 viral aur popular hashtags likho (e.g. #viral #trending). Koi aur lafaz, sentence ya details mat likhna, sirf hashtags hone chahiye.", img])
                    caption = response.text
                
            await message_obj.reply_text(f"**AI ne ye Caption likha hai:**\n\n{caption}")
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            caption = "Amazing content! #post #trending"
            await message_obj.reply_text("AI error, default caption used.")
    elif user_caption.strip().lower() == 'auto':
        caption = "Awesome post! #trending #viral"
    
    file_url = None
    if not is_text_only and new_file:
        file_url = new_file.file_path if new_file.file_path.startswith('http') else f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{new_file.file_path}"
    
    await status_msg.edit_text("⏳ **Progress Tracker:**\n🚀 Uploading shuru ho rahi hai...")
    
    results = []
    
    for key, data in platforms.items():
        if not data['selected']: continue
        
        platform_type = data['type']
        if platform_type == 'facebook':
            await status_msg.edit_text(f"⏳ **Progress Tracker:**\n🔵 Facebook ({data['name']}) par upload ho raha hai...")
            res = post_to_facebook(media_path, is_video, caption, data['id'], custom_token=data.get('token'))
            results.append(f"Facebook ({data['name']}): {'✅ Success' if res['success'] else f'❌ Error: {res.get('error')}'}")
            
        elif platform_type == 'instagram':
            await status_msg.edit_text(f"⏳ **Progress Tracker:**\n🟣 Instagram ({data['name']}) par upload ho raha hai (Video hai toh 1-2 minute lag sakte hain)...")
            res = post_to_instagram(file_url, is_video, caption, data['id'], custom_token=data.get('token'))
            results.append(f"Instagram ({data['name']}): {'✅ Success' if res['success'] else f'❌ Error: {res.get('error')}'}")
            
        elif platform_type == 'youtube' and is_video:
            await status_msg.edit_text("⏳ **Progress Tracker:**\n🔴 YouTube par upload ho raha hai...")
            res = post_to_youtube(media_path, caption, caption)
            results.append(f"YouTube: {'✅ Success' if res['success'] else f'❌ Error: {res.get('error')}'}")
            
        elif platform_type == 'tiktok' and is_video:
            await status_msg.edit_text("⏳ **Progress Tracker:**\n⚫ TikTok par upload ho raha hai...")
            res = post_to_tiktok(media_path, caption)
            results.append(f"TikTok: {'✅ Success' if res['success'] else f'❌ Error: {res.get('error')}'}")
        
    # Clean up temp file
    if media_path and os.path.exists(media_path):
        os.remove(media_path)
        
    final_text = "✅ **Upload Results:**\n\n" + "\n".join(results)
    await status_msg.edit_text(final_text)
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Process cancel kar diya gaya hai.")
    context.user_data.clear()
    return ConversationHandler.END

async def add_fb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Sahi tariqa: /addfb [Page_ID] [Page_Name] [Token_Optional]\n\nMissal: /addfb 123456789 Mera Naya Page\nYa phir token ke sath: /addfb 123456789 Mera Naya Page EAAaCC...")
        return
    
    page_id = context.args[0]
    if len(context.args[-1]) > 50 and context.args[-1].startswith('EA'):
        token = context.args[-1]
        page_name = " ".join(context.args[1:-1])
    else:
        token = None
        page_name = " ".join(context.args[1:])
        
    from config import ACCOUNTS, ACCOUNTS_FILE
    import json
    new_acc = {'name': page_name, 'id': page_id}
    if token:
        new_acc['token'] = token
    ACCOUNTS.setdefault('facebook', []).append(new_acc)
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(ACCOUNTS, f, indent=4)
    await update.message.reply_text(f"✅ Naya Facebook Page '{page_name}' add ho gaya hai!" + (" (Alag Token ke sath!)" if token else ""))

async def add_ig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Sahi tariqa: /addig [Insta_ID] [Insta_Name] [Token_Optional]\n\nMissal: /addig 987654321 mera_insta\nYa phir token ke sath: /addig 987654321 mera_insta EAAaCC...")
        return
    
    ig_id = context.args[0]
    if len(context.args[-1]) > 50 and context.args[-1].startswith('EA'):
        token = context.args[-1]
        ig_name = " ".join(context.args[1:-1])
    else:
        token = None
        ig_name = " ".join(context.args[1:])
        
    from config import ACCOUNTS, ACCOUNTS_FILE
    import json
    new_acc = {'name': ig_name, 'id': ig_id}
    if token:
        new_acc['token'] = token
    ACCOUNTS.setdefault('instagram', []).append(new_acc)
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(ACCOUNTS, f, indent=4)
    await update.message.reply_text(f"✅ Naya Instagram Account '{ig_name}' add ho gaya hai!" + (" (Alag Token ke sath!)" if token else ""))

async def set_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Sahi tariqa: /settoken [Naya_Token]\n\nMissal: /settoken EAAaCC...")
        return
    new_token = context.args[0]
    
    import re
    env_file = '.env'
    with open(env_file, 'r') as file:
        content = file.read()
    
    content = re.sub(r'FB_ACCESS_TOKEN=.*', f'FB_ACCESS_TOKEN={new_token}', content)
    
    with open(env_file, 'w') as file:
        file.write(content)
        
    # Update in memory across modules
    import config
    from platforms import facebook, instagram
    config.FB_ACCESS_TOKEN = new_token
    facebook.FB_ACCESS_TOKEN = new_token
    instagram.FB_ACCESS_TOKEN = new_token
    
    await update.message.reply_text("✅ Naya Token successfully update ho gaya hai! Ab aap post kar sakte hain.")

async def remove_fb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Sahi tariqa: /removefb [Page_ID]\n\nMissal: /removefb 123456789")
        return
    page_id = context.args[0]
    
    from config import ACCOUNTS, ACCOUNTS_FILE
    import json
    
    initial_count = len(ACCOUNTS.get('facebook', []))
    ACCOUNTS['facebook'] = [p for p in ACCOUNTS.get('facebook', []) if p['id'] != page_id]
    
    if len(ACCOUNTS['facebook']) < initial_count:
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(ACCOUNTS, f, indent=4)
        await update.message.reply_text(f"✅ Facebook Page ID {page_id} remove kar diya gaya hai!")
    else:
        await update.message.reply_text(f"❌ Page ID {page_id} list mein nahi mila.")

async def remove_ig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Sahi tariqa: /removeig [Insta_ID]\n\nMissal: /removeig 987654321")
        return
    ig_id = context.args[0]
    
    from config import ACCOUNTS, ACCOUNTS_FILE
    import json
    
    initial_count = len(ACCOUNTS.get('instagram', []))
    ACCOUNTS['instagram'] = [p for p in ACCOUNTS.get('instagram', []) if p['id'] != ig_id]
    
    if len(ACCOUNTS['instagram']) < initial_count:
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(ACCOUNTS, f, indent=4)
        await update.message.reply_text(f"✅ Instagram Account ID {ig_id} remove kar diya gaya hai!")
    else:
        await update.message.reply_text(f"❌ Insta ID {ig_id} list mein nahi mili.")

def main():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN environment variable not set.")
        return
        
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), receive_media)],
        states={
            SELECT_PLATFORMS: [CallbackQueryHandler(handle_platform_selection)],
            GET_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_caption_and_post)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addfb", add_fb))
    application.add_handler(CommandHandler("addig", add_ig))
    application.add_handler(CommandHandler("removefb", remove_fb))
    application.add_handler(CommandHandler("removeig", remove_ig))
    application.add_handler(CommandHandler("settoken", set_token))
    application.add_handler(conv_handler)

    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
