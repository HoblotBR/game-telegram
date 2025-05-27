import telebot
import firebase_admin
from firebase_admin import credentials, firestore
import time
import threading

# 🔗 Token do bot
TOKEN = 'SEU_TOKEN_DO_BOT'

# 🔑 Inicializando Firebase
cred = credentials.Certificate('firebase_config.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

bot = telebot.TeleBot(TOKEN)

# 🔋 Configuração de energia
ENERGIA_MAX = 500
REGEN_TEMPO = 108  # segundos (1 energia a cada 108 segundos)

# 🎯 Função de regeneração de energia
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

# 🚀 Comando /start
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
        bot.send_message(message.chat.id, f"🤑 Bem-vindo, {message.from_user.first_name}! Você foi cadastrado no sistema.")
    else:
        bot.send_message(message.chat.id, "👋 Você já está cadastrado!")

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🖱️ CLICAR POR ESP", callback_data="click"))
    bot.send_message(message.chat.id, "Clique no botão para ganhar ESP:", reply_markup=markup)

# 📲 Callback do botão de clique
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "click":
        user_id = str(call.from_user.id)
        ref = db.collection('users').document(user_id)
        user = ref.get().to_dict()

        if user['energia'] <= 0:
            bot.answer_callback_query(call.id, "⚡ Energia insuficiente!")
            return

        ganho = 1  # Pode ser aumentado por upgrades ou NFTs
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

# 📑 Comando /perfil
@bot.message_handler(commands=['perfil'])
def perfil(message):
    user_id = str(message.from_user.id)
    ref = db.collection('users').document(user_id)
    user = ref.get().to_dict()

    bot.send_message(message.chat.id, 
    f"""👤 Perfil de {user['name']}
💰 Saldo: {user['saldo']} ESP
🖱️ Cliques: {user['cliques']}
⚡ Energia: {user['energia']}/{ENERGIA_MAX}
⭐ XP: {user['xp']} | Level: {user['level']}
🎨 NFTs: {', '.join(user.get('nfts', [])) or 'Nenhum'}""")

# 💰 /depositar
@bot.message_handler(commands=['depositar'])
def depositar(message):
    bot.send_message(message.chat.id, 
    "🔗 Envie o valor para o PIX: 39707972840\nApós pagamento, envie o comprovante para um admin.")

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

# 🚀 Rodar o bot
bot.infinity_polling()
