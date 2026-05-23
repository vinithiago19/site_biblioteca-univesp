from flask import Flask, render_template_string, request, redirect, url_for, g
import sqlite3

app = Flask(__name__)
DATABASE = 'biblioteca.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, senha TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS livros (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, autor TEXT, quantidade INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS emprestimos (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, livro_id INTEGER)''')
        db.commit()

# --- TEMPLATES HTML/CSS ---
# ATUALIZADO: CSS modificado para estilizar a tag <select> igual aos inputs
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sistema de Biblioteca</title>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; display: flex; height: 100vh; background-color: #f4f6f9; }
        .sidebar { width: 250px; background-color: #1a2530; color: white; display: flex; flex-direction: column; padding-top: 20px; }
        .sidebar a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
        .sidebar a:hover { background-color: #2c3e50; }
        .main-content { flex-grow: 1; display: flex; flex-direction: column; }
        .topbar { background-color: #4285f4; color: white; padding: 20px; font-size: 1.2em; }
        .content { padding: 40px; display: flex; justify-content: center; }
        .card { background: white; padding: 40px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); width: 100%; max-width: 600px; border: 1px solid #ddd; }
        input[type="text"], input[type="password"], input[type="number"], select { width: 100%; padding: 10px; margin: 10px 0 20px; border: 1px solid #4285f4; box-sizing: border-box; background-color: white; font-size: 1em;}
        button { background-color: #4285f4; color: white; border: none; padding: 15px 30px; cursor: pointer; width: 100%; font-size: 1em; }
        button:hover { background-color: #3367d6; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #4285f4; padding: 10px; text-align: left; }
    </style>
</head>
<body>
    <div class="sidebar">
        <a href="/">Login</a>
        <a href="/livros">Consulta de Livros</a>
        <a href="/cadastro_livro">Cadastro de Livros</a>
        <a href="/cadastro_usuario">Cadastro de Usuários</a>
        <a href="/emprestimo">Registro de Empréstimo</a>
    </div>
    <div class="main-content">
        <div class="topbar">{{ titulo_pagina }}</div>
        <div class="content">
            <div class="card">
                {% block content %}{% endblock %}
            </div>
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <form method="POST">
        <label>E-mail</label>
        <input type="text" name="email" required>
        <label>Senha</label>
        <input type="password" name="senha" required>
        <button type="submit">Entrar</button>
    </form>
    {% if erro %}<p style="color: red; text-align: center; margin-top: 15px;"><b>{{ erro }}</b></p>{% endif %}
""")

CONSULTA_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <form method="POST">
        <label>Buscar livro (Título)</label>
        <input type="text" name="busca">
        <button type="submit">Buscar</button>
    </form>
    <table>
        <tr><th>ID</th><th>Título</th><th>Autor</th><th>Qtd</th></tr>
        {% for livro in livros %}
        <tr><td>{{ livro.id }}</td><td>{{ livro.titulo }}</td><td>{{ livro.autor }}</td><td>{{ livro.quantidade }}</td></tr>
        {% endfor %}
    </table>
""")

CADASTRO_LIVRO_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <form method="POST">
        <label>Título</label>
        <input type="text" name="titulo" required>
        <label>Autor</label>
        <input type="text" name="autor" required>
        <label>Quantidade</label>
        <input type="number" name="quantidade" required>
        <button type="submit">Salvar</button>
    </form>
    {% if mensagem %}<p style="color: green; text-align: center;">{{ mensagem }}</p>{% endif %}
""")

CADASTRO_USUARIO_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <form method="POST">
        <label>E-mail do Usuário</label>
        <input type="text" name="email" required>
        <label>Senha</label>
        <input type="password" name="senha" required>
        <button type="submit">Salvar Usuário</button>
    </form>
    {% if mensagem %}<p style="color: green; text-align: center;">{{ mensagem }}</p>{% endif %}
""")

# ATUALIZADO: Utilizando as tags <select> e populando com o banco de dados
EMPRESTIMO_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <form method="POST">
        <label>Selecione o Usuário</label>
        <select name="usuario_id" required>
            <option value="">-- Escolha um usuário --</option>
            {% for u in usuarios %}
            <option value="{{ u.id }}">{{ u.email }}</option>
            {% endfor %}
        </select>
        
        <label>Selecione o Livro</label>
        <select name="livro_id" required>
            <option value="">-- Escolha um livro --</option>
            {% for l in livros %}
            <option value="{{ l.id }}">{{ l.titulo }} (Disponíveis: {{ l.quantidade }})</option>
            {% endfor %}
        </select>
        
        <button type="submit">Salvar Empréstimo</button>
    </form>
    {% if mensagem %}<p style="color: green; text-align: center;"><b>{{ mensagem }}</b></p>{% endif %}
    {% if erro %}<p style="color: red; text-align: center;"><b>{{ erro }}</b></p>{% endif %}
""")

# --- ROTAS DA APLICAÇÃO ---

@app.route('/', methods=['GET', 'POST'])
def login():
    erro = ""
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        db = get_db()
        usuario = db.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha)).fetchone()
        
        if usuario:
            return redirect(url_for('consulta_livros'))
        else:
            erro = "Usuário ou senha incorretos."
            
    return render_template_string(LOGIN_TEMPLATE, titulo_pagina="Login do Sistema", erro=erro)

@app.route('/livros', methods=['GET', 'POST'])
def consulta_livros():
    db = get_db()
    livros = []
    if request.method == 'POST':
        busca = request.form['busca']
        livros = db.execute("SELECT * FROM livros WHERE titulo LIKE ?", ('%'+busca+'%',)).fetchall()
    else:
        livros = db.execute("SELECT * FROM livros").fetchall()
    return render_template_string(CONSULTA_TEMPLATE, titulo_pagina="Consulta de Livros", livros=livros)

@app.route('/cadastro_livro', methods=['GET', 'POST'])
def cadastro_livro():
    mensagem = ""
    if request.method == 'POST':
        titulo = request.form['titulo']
        autor = request.form['autor']
        quantidade = request.form['quantidade']
        db = get_db()
        db.execute("INSERT INTO livros (titulo, autor, quantidade) VALUES (?, ?, ?)", (titulo, autor, quantidade))
        db.commit()
        mensagem = "Livro cadastrado com sucesso!"
    return render_template_string(CADASTRO_LIVRO_TEMPLATE, titulo_pagina="Cadastro de Livro", mensagem=mensagem)

@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    mensagem = ""
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        db = get_db()
        db.execute("INSERT INTO usuarios (email, senha) VALUES (?, ?)", (email, senha))
        db.commit()
        mensagem = "Usuário cadastrado com sucesso!"
    return render_template_string(CADASTRO_USUARIO_TEMPLATE, titulo_pagina="Cadastro de Usuário", mensagem=mensagem)

# ATUALIZADO: Busca os dados e valida a quantidade antes do empréstimo
@app.route('/emprestimo', methods=['GET', 'POST'])
def emprestimo():
    mensagem = ""
    erro = ""
    db = get_db()
    
    if request.method == 'POST':
        usuario_id = request.form['usuario_id']
        livro_id = request.form['livro_id']
        
        # Verifica se o livro tem quantidade disponível
        livro = db.execute("SELECT quantidade FROM livros WHERE id = ?", (livro_id,)).fetchone()
        
        if livro and livro['quantidade'] > 0:
            db.execute("INSERT INTO emprestimos (usuario_id, livro_id) VALUES (?, ?)", (usuario_id, livro_id))
            db.execute("UPDATE livros SET quantidade = quantidade - 1 WHERE id = ?", (livro_id,))
            db.commit()
            mensagem = "Empréstimo registrado com sucesso!"
        else:
            erro = "Operação negada: Livro sem estoque disponível."

    # Busca as listas atualizadas para preencher os menus suspensos
    usuarios = db.execute("SELECT id, email FROM usuarios").fetchall()
    livros = db.execute("SELECT id, titulo, quantidade FROM livros").fetchall()
    
    return render_template_string(EMPRESTIMO_TEMPLATE, titulo_pagina="Registro de Empréstimo", mensagem=mensagem, erro=erro, usuarios=usuarios, livros=livros)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)