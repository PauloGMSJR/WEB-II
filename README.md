# logGYM

Aplicação web de blog sobre academia desenvolvida em Flask + SQLite com autenticação e sistema de curtidas.

## Requisitos

- Python 3.10+
- Ambiente virtual recomendado

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Uso

1. (Opcional) Para recriar a base do zero:
   ```bash
   flask --app app init-db
   ```
2. Inicie o servidor (a base SQLite é criada automaticamente com um usuário administrador e alguns posts exemplo caso não exista):
   ```bash
   python app.py
   ```
3. Acesse http://localhost:5000 no navegador.
4. Entre com o usuário de demonstração (`coach@loggym.com` / senha `loggym123`) ou crie uma conta pelo link "Criar conta".
5. Utilize o menu "Novo post" para publicar conteúdos autenticados. Você pode editar ou excluir seus próprios posts e curtir materiais publicados por outros autores.

## Estrutura

- `app.py`: aplicação Flask, rotas e integração com SQLite.
- `loggym/templates`: templates HTML.
- `loggym/static`: arquivos estáticos (CSS).
- `loggym.db`: banco SQLite criado na primeira execução.
- Tabelas principais:
  - `users`: perfis com nome, sobrenome, e-mail, senha (hash), biografia e avatar.
  - `posts`: conteúdos do blog associados a um autor.
  - `likes`: curtidas relacionando usuários aos posts.

## Ajustes

- Atualize `SECRET_KEY` em `app.py` para um valor seguro em produção.
- Remova ou adapte os dados de demonstração configurados em `init_db` conforme necessário.
