import os
import sqlite3
from datetime import datetime
from functools import wraps
from urllib.parse import urljoin, urlparse

import click
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "loggym.db")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "loggym", "templates"),
    static_folder=os.path.join(BASE_DIR, "loggym", "static"),
)
app.config["SECRET_KEY"] = "change-me-in-production"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(with_seed: bool = True) -> None:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sobrenome TEXT NOT NULL,
            senha TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            biografia TEXT,
            avatar_url TEXT,
            data_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            level TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS likes (
            id_user INTEGER NOT NULL,
            id_post INTEGER NOT NULL,
            PRIMARY KEY (id_user, id_post),
            FOREIGN KEY (id_user) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (id_post) REFERENCES posts(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """
    )

    posts_info = db.execute("PRAGMA table_info(posts)").fetchall()
    post_columns = {row["name"] for row in posts_info}
    has_user_id = "user_id" in post_columns
    if posts_info and not has_user_id:
        db.execute("ALTER TABLE posts ADD COLUMN user_id INTEGER")
        has_user_id = True

    if with_seed:
        existing_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing_users == 0:
            default_password = generate_password_hash("loggym123")
            cursor = db.execute(
                """
                INSERT INTO users (nome, sobrenome, senha, email, biografia, avatar_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "Marina",
                    "Cardoso",
                    default_password,
                    "coach@loggym.com",
                    "Coach especialista em treinos funcionais e condicionamento cardiorrespiratório.",
                    "https://images.unsplash.com/photo-1526402466433-28074b3e77c3?auto=format&fit=facearea&w=120&h=120&q=80",
                ),
            )
            user_id = cursor.lastrowid

            seed_posts = [
                {
                    "title": "Treino HIIT Energizante",
                    "slug": "treino-hiit-energizante",
                    "category": "Treinos",
                    "level": "Intermediário",
                    "content": (
                        "Descubra como turbinar seu condicionamento com uma sequência de HIIT"
                        " inspirada em circuitos funcionais. Inclui aquecimento, 4 blocos"
                        " de exercícios de alta intensidade e orientações de respiração"
                        " para manter a frequência cardíaca sob controle."
                    ),
                },
                {
                    "title": "Nutrição Pré-Treino Inteligente",
                    "slug": "nutricao-pre-treino",
                    "category": "Nutrição",
                    "level": "Todos",
                    "content": (
                        "Saiba como combinar carboidratos complexos e proteínas magras"
                        " para garantir energia constante durante o treino. A matéria"
                        " também traz opções veganas e dicas de hidratação."
                    ),
                },
                {
                    "title": "Guia de Recuperação Muscular",
                    "slug": "guia-recuperacao-muscular",
                    "category": "Recuperação",
                    "level": "Avançado",
                    "content": (
                        "O descanso faz parte do progresso! Veja como intercalar"
                        " treinos de força com mobilidade, alongamentos ativos"
                        " e rotinas de sono para maximizar resultados sem risco"
                        " de lesões."
                    ),
                },
            ]

            now = datetime.utcnow().isoformat(timespec="seconds")
            for post in seed_posts:
                db.execute(
                    """
                    INSERT INTO posts (title, slug, category, level, content, created_at, user_id)
                    VALUES (:title, :slug, :category, :level, :content, :created_at, :user_id)
                    """,
                    {**post, "created_at": now, "user_id": user_id},
                )

    if has_user_id:
        default_user_row = db.execute(
            "SELECT id FROM users ORDER BY id LIMIT 1"
        ).fetchone()
        if default_user_row is not None:
            db.execute(
                "UPDATE posts SET user_id = ? WHERE user_id IS NULL",
                (default_user_row["id"],),
            )
    db.commit()
    db.close()


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.utcnow().year,
        "current_user": getattr(g, "user", None),
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("user") is None:
            flash("Faça login para acessar esta área.", "error")
            next_target = (
                request.full_path if request.method == "GET" else request.referrer
            )
            next_url = safe_next_url(next_target)
            return redirect(url_for("login", next=next_url))
        return view(*args, **kwargs)

    return wrapped_view


def safe_next_url(target: str | None) -> str:
    if not target:
        return url_for("index")
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    if test_url.netloc != ref_url.netloc:
        return url_for("index")
    path = test_url.path or "/"
    if test_url.query:
        path = f"{path}?{test_url.query}"
    return path


@app.cli.command("init-db")
def init_db_command():
    """Inicializa o banco de dados e popula com posts demonstrativos."""
    init_db()
    click.echo("Banco de dados inicializado com sucesso!")


@app.route("/")
def index():
    category = request.args.get("categoria")
    level = request.args.get("nivel")
    db = get_db()

    query = (
        "SELECT posts.*, "
        "users.nome || ' ' || users.sobrenome AS author_name, "
        "users.avatar_url AS author_avatar, "
        "COUNT(likes.id_post) AS likes_total "
        "FROM posts "
        "JOIN users ON posts.user_id = users.id "
        "LEFT JOIN likes ON likes.id_post = posts.id"
    )
    filters = []
    params = []

    if category:
        filters.append("posts.category = ?")
        params.append(category)
    if level:
        filters.append("posts.level = ?")
        params.append(level)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " GROUP BY posts.id ORDER BY datetime(posts.created_at) DESC"

    posts = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM posts ORDER BY category").fetchall()
    levels = db.execute("SELECT DISTINCT level FROM posts ORDER BY level").fetchall()

    return render_template(
        "index.html",
        posts=posts,
        categories=[row[0] for row in categories],
        levels=[row[0] for row in levels],
        selected_category=category,
        selected_level=level,
    )


@app.route("/post/<slug>")
def post_detail(slug: str):
    db = get_db()
    post = db.execute(
        """
        SELECT posts.*, 
               users.nome || ' ' || users.sobrenome AS author_name,
               users.biografia AS author_bio,
               users.avatar_url AS author_avatar,
               COUNT(likes.id_post) AS likes_total
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN likes ON likes.id_post = posts.id
        WHERE posts.slug = ?
        GROUP BY posts.id
        """,
        (slug,),
    ).fetchone()
    if post is None:
        abort(404)

    liked = False
    if g.user is not None:
        liked = (
            db.execute(
                "SELECT 1 FROM likes WHERE id_user = ? AND id_post = ?",
                (g.user["id"], post["id"]),
            ).fetchone()
            is not None
        )

    return render_template(
        "post_detail.html",
        post=post,
        liked=liked,
        is_owner=g.user is not None and post["user_id"] == g.user["id"],
    )


@app.route("/admin/novo", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        category = request.form.get("category", "").strip()
        level = request.form.get("level", "").strip()
        content = request.form.get("content", "").strip()

        if not all([title, slug, category, level, content]):
            flash("Preencha todos os campos para publicar.", "error")
        else:
            db = get_db()
            try:
                db.execute(
                    """
                    INSERT INTO posts (title, slug, category, level, content, created_at, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        slug,
                        category,
                        level,
                        content,
                        datetime.utcnow().isoformat(timespec="seconds"),
                        g.user["id"],
                    ),
                )
                db.commit()
                flash("Novo post publicado com sucesso!", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("Já existe um post com esse slug. Escolha outro identificador.", "error")

    return render_template("post_form.html", post=None)


@app.route("/admin/<slug>/editar", methods=["GET", "POST"])
@login_required
def edit_post(slug: str):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE slug = ?", (slug,)).fetchone()
    if post is None:
        abort(404)
    if post["user_id"] != g.user["id"]:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        new_slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        category = request.form.get("category", "").strip()
        level = request.form.get("level", "").strip()
        content = request.form.get("content", "").strip()

        if not all([title, new_slug, category, level, content]):
            flash("Preencha todos os campos para atualizar.", "error")
        else:
            try:
                db.execute(
                    """
                    UPDATE posts
                    SET title = ?, slug = ?, category = ?, level = ?, content = ?
                    WHERE id = ?
                    """,
                    (title, new_slug, category, level, content, post["id"]),
                )
                db.commit()
                flash("Post atualizado!", "success")
                return redirect(url_for("post_detail", slug=new_slug))
            except sqlite3.IntegrityError:
                flash("Já existe um post com esse slug. Escolha outro identificador.", "error")

    return render_template("post_form.html", post=post)


@app.route("/admin/<slug>/excluir", methods=["POST"])
@login_required
def delete_post(slug: str):
    db = get_db()
    post = db.execute("SELECT id, user_id FROM posts WHERE slug = ?", (slug,)).fetchone()
    if post is None:
        abort(404)
    if post["user_id"] != g.user["id"]:
        abort(403)

    db.execute("DELETE FROM posts WHERE id = ?", (post["id"],))
    db.commit()
    flash("Post removido do LogGYM.", "success")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = safe_next_url(request.form.get("next"))

        if not email or not password:
            flash("Informe e-mail e senha.", "error")
        else:
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user and check_password_hash(user["senha"], password):
                session.clear()
                session["user_id"] = user["id"]
                flash("Login realizado com sucesso!", "success")
                return redirect(next_url)
            flash("Credenciais inválidas.", "error")

    return render_template(
        "auth/login.html",
        next=safe_next_url(request.form.get("next") or request.args.get("next")),
    )


@app.route("/registrar", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        sobrenome = request.form.get("sobrenome", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        bio = request.form.get("biografia", "").strip() or None
        avatar_url = request.form.get("avatar_url", "").strip() or None

        if not all([nome, sobrenome, email, password]):
            flash("Preencha nome, sobrenome, e-mail e senha.", "error")
        else:
            db = get_db()
            existing = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                flash("Já existe uma conta com este e-mail.", "error")
            else:
                hashed = generate_password_hash(password)
                cursor = db.execute(
                    """
                    INSERT INTO users (nome, sobrenome, senha, email, biografia, avatar_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (nome, sobrenome, hashed, email, bio, avatar_url),
                )
                db.commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                flash("Cadastro realizado! Bem-vindo ao logGYM.", "success")
                return redirect(url_for("index"))

    return render_template("auth/register.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Sessão encerrada. Até a próxima!", "info")
    return redirect(url_for("index"))


@app.route("/post/<slug>/curtir", methods=["POST"])
@login_required
def toggle_like(slug: str):
    db = get_db()
    post = db.execute("SELECT id FROM posts WHERE slug = ?", (slug,)).fetchone()
    if post is None:
        abort(404)

    user_id = g.user["id"]
    liked = db.execute(
        "SELECT 1 FROM likes WHERE id_user = ? AND id_post = ?",
        (user_id, post["id"]),
    ).fetchone()

    if liked:
        db.execute(
            "DELETE FROM likes WHERE id_user = ? AND id_post = ?",
            (user_id, post["id"]),
        )
        flash("Você removeu seu like deste post.", "info")
    else:
        db.execute(
            "INSERT INTO likes (id_user, id_post) VALUES (?, ?)",
            (user_id, post["id"]),
        )
        flash("Você curtiu este post!", "success")

    db.commit()
    return redirect(url_for("post_detail", slug=slug))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
