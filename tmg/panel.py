from flask import Flask, render_template_string, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebase_config.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

PASSWORD = "senhaadmin"  # 🔒 Mude aqui sua senha de acesso

# Template básico
template = """
<!DOCTYPE html>
<html>
<head>
<title>Painel Admin - EsperançaBot</title>
</head>
<body style="background-color:#121212;color:white;font-family:sans-serif;">
<h1>Painel Admin - EsperançaBot</h1>
{% if not auth %}
  <form method="POST">
    <input name="password" placeholder="Senha" type="password"/>
    <input type="submit" value="Entrar"/>
  </form>
{% else %}
  <h3>Dashboard</h3>
  <a href="/users">👥 Usuários</a> |
  <a href="/ranking">🏆 Ranking</a> |
  <a href="/reset-ranking">🗑️ Reset Ranking</a> |
  <a href="/logout">🚪 Logout</a>
  <hr/>
  {{ content|safe }}
{% endif %}
</body>
</html>
"""

# Autenticação simples
@app.before_request
def check_login():
    if request.path == '/login' or request.path == '/logout':
        return
    if 'auth' not in request.cookies and request.path != '/':
        return redirect('/')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            resp = redirect('/users')
            resp.set_cookie('auth', '1')
            return resp
    return render_template_string(template, auth='auth' in request.cookies, content='')

@app.route('/logout')
def logout():
    resp = redirect('/')
    resp.delete_cookie('auth')
    return resp

@app.route('/users')
def users():
    users = db.collection('users').stream()
    content = "<h3>👥 Lista de Usuários</h3><ul>"
    for user in users:
        u = user.to_dict()
        content += f"<li>{u['name']} | Saldo: {u['saldo']} ESP | Level: {u.get('level',1)} | Energia: {u.get('energia',500)}</li>"
    content += "</ul>"
    return render_template_string(template, auth='auth' in request.cookies, content=content)

@app.route('/ranking')
def ranking():
    users = db.collection('users').stream()
    ranking = sorted(
        [(u.to_dict()['name'], u.to_dict().get('saldo',0)) for u in users],
        key=lambda x: x[1], reverse=True
    )
    content = "<h3>🏆 Ranking</h3><ol>"
    for name, saldo in ranking:
        content += f"<li>{name} - {saldo} ESP</li>"
    content += "</ol>"
    return render_template_string(template, auth='auth' in request.cookies, content=content)

@app.route('/reset-ranking')
def reset_ranking():
    users = db.collection('users').stream()
    for user in users:
        db.collection('users').document(user.id).update({'saldo': 0, 'cliques': 0})
    return redirect('/ranking')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
