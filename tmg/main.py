import telebot
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import time
import threading

# 🔗 Carregar variáveis da nuvem Railway
TOKEN = os.getenv('TOKEN')
PIX = os.getenv('PIX')

# 🔥 Firebase via variável de ambiente
firebase_config = json.loads(os.getenv("FIREBASE_CONFIG"))
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

bot = telebot.TeleBot(TOKEN)

# ⚡ Energia
ENERGIA_MAX = 500
REGEN_TEMPO = 108  # 1 energia a cada 108 segundos

# 🔋 Regeneração de energia
def regenerar_energia():
    while True:
        users = db.collection('users').stream()
        for user in users:
            data = user.to_dict()
            energia = data.get('energia', ENERGIA_MAX)
            if energia < ENERGIA_MAX:
                nova_energia = min(energia + 1, ENERGIA_MAX)
                db.collection('users').document(user.id).update({'energia': nova_energia})
        time.sleep(REGEN_TEMPO)

threading.Thread(target=regenerar_energia, daemon=True).start()

# 🚀 /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    ref = db.collection('users').document(user_id)

    if not ref.get().exists:
        ref.set({
            'name': message.from_user.first_name,
            'saldo': 0,
            'cliques': 0,
            'energia': ENERGIA_MAX,
            'xp': 0,
            'level': 1,
            'nfts': [],
        })
        bot.send_message(message.chat.id, f"🤑 Bem-vindo, {message.from_user.first_name}! Você foi cadastrado.")
    else:
        bot.send_message(message.chat.id, "👋 Você já está cadastrado!")

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🖱️ CLICAR POR ESP", callback_data="click"))
    bot.send_message(message.chat.id, "Clique no botão para ganhar ESP:", reply_markup=markup)

# 🖱️ Clique
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "click":
        user_id = str(call.from_user.id)
        ref = db.collection('users').document(user_id)
        user = ref.get().to_dict()

        if user['energia'] <= 0:
            bot.answer_callback_query(call.id, "⚡ Energia insuficiente!")
            return

        ganho = 1
        if 'LENDARIO' in user.get('nfts', []):
            ganho *= 2
        if 'MITICO' in user.get('nfts', []):
            ganho *= 3

        ref.update({
            'saldo': user['saldo'] + ganho,
            'cliques': user['cliques'] + 1,
            'energia': user['energia'] - 1,
            'xp': user['xp'] + 1
        })

        bot.answer_callback_query(call.id, f"💰 +{ganho} ESP! ⚡ Energia restante: {user['energia'] - 1}")

# 👤 Perfil
@bot.message_handler(commands=['perfil'])
def perfil(message):
    user_id = str(message.from_user.id)
    ref = db.collection('users').document(user_id)
    user = ref.get().to_dict()

    bot.send_message(message.chat.id, 
    f"""👤 {user['name']}
💰 Saldo: {user['saldo']} ESP
🖱️ Cliques: {user['cliques']}
⚡ Energia: {user['energia']}/{ENERGIA_MAX}
⭐ XP: {user['xp']} | Level: {user['level']}
🎨 NFTs: {', '.join(user.get('nfts', [])) or 'Nenhum'}""")

# 💰 /depositar
@bot.message_handler(commands=['depositar'])
def depositar(message):
    bot.send_message(message.chat.id, 
    f"🔗 Envie o valor para o PIX: {PIX}\nApós pagamento, envie o comprovante para um admin.")

# 🏦 /sacar
@bot.message_handler(commands=['sacar'])
def sacar(message):
    user_id = str(message.from_user.id)
    ref = db.collection('users').document(user_id)
    user = ref.get().to_dict()

    if user['saldo'] < 20:
        bot.send_message(message.chat.id, "🚫 Saldo insuficiente para saque (mínimo 20 ESP).")
        return

    taxa = int(user['saldo'] * 0.20)
    saque = user['saldo'] - taxa

    ref.update({'saldo': 0})

    bot.send_message(message.chat.id, 
    f"🏦 Saque solicitado!\n💸 Valor líquido: {saque} ESP\n💸 Taxa: {taxa} ESP\n✅ Envie sua chave PIX para um admin.")

# 🔥 Rodar bot
bot.infinity_polling()
