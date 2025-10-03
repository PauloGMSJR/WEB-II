import os
import sqlite3
from datetime import datetime

import click
from flask import Flask, g, redirect, render_template, request, url_for, flash, abort

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
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(with_seed: bool = True) -> None:
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            author TEXT NOT NULL,
            level TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    if with_seed:
        existing = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        if existing == 0:
            seed_posts = [
                {
                    "title": "Treino HIIT Energizante",
                    "slug": "treino-hiit-energizante",
                    "category": "Treinos",
                    "author": "Coach Marina",
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
                    "author": "Nutri Carla",
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
                    "author": "Fisioterapeuta Leo",
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
                    INSERT INTO posts (title, slug, category, author, level, content, created_at)
                    VALUES (:title, :slug, :category, :author, :level, :content, :created_at)
                    """,
                    {**post, "created_at": now},
                )
    db.commit()
    db.close()


@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}


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

    query = "SELECT * FROM posts"
    filters = []
    params = []

    if category:
        filters.append("category = ?")
        params.append(category)
    if level:
        filters.append("level = ?")
        params.append(level)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY datetime(created_at) DESC"

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
    post = db.execute("SELECT * FROM posts WHERE slug = ?", (slug,)).fetchone()
    if post is None:
        abort(404)

    return render_template("post_detail.html", post=post)


@app.route("/admin/novo", methods=["GET", "POST"])
def create_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        category = request.form.get("category", "").strip()
        author = request.form.get("author", "").strip()
        level = request.form.get("level", "").strip()
        content = request.form.get("content", "").strip()

        if not all([title, slug, category, author, level, content]):
            flash("Preencha todos os campos para publicar.", "error")
        else:
            db = get_db()
            try:
                db.execute(
                    """
                    INSERT INTO posts (title, slug, category, author, level, content, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        slug,
                        category,
                        author,
                        level,
                        content,
                        datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                )
                db.commit()
                flash("Novo post publicado com sucesso!", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("Já existe um post com esse slug. Escolha outro identificador.", "error")

    return render_template("post_form.html", post=None)


@app.route("/admin/<slug>/editar", methods=["GET", "POST"])
def edit_post(slug: str):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE slug = ?", (slug,)).fetchone()
    if post is None:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        new_slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        category = request.form.get("category", "").strip()
        author = request.form.get("author", "").strip()
        level = request.form.get("level", "").strip()
        content = request.form.get("content", "").strip()

        if not all([title, new_slug, category, author, level, content]):
            flash("Preencha todos os campos para atualizar.", "error")
        else:
            try:
                db.execute(
                    """
                    UPDATE posts
                    SET title = ?, slug = ?, category = ?, author = ?, level = ?, content = ?
                    WHERE id = ?
                    """,
                    (title, new_slug, category, author, level, content, post["id"]),
                )
                db.commit()
                flash("Post atualizado!", "success")
                return redirect(url_for("post_detail", slug=new_slug))
            except sqlite3.IntegrityError:
                flash("Já existe um post com esse slug. Escolha outro identificador.", "error")

    return render_template("post_form.html", post=post)


@app.route("/admin/<slug>/excluir", methods=["POST"])
def delete_post(slug: str):
    db = get_db()
    post = db.execute("SELECT id FROM posts WHERE slug = ?", (slug,)).fetchone()
    if post is None:
        abort(404)

    db.execute("DELETE FROM posts WHERE id = ?", (post["id"],))
    db.commit()
    flash("Post removido do LogGYM.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
