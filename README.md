# logGYM

Aplicação web de blog sobre academia desenvolvida em Flask + SQLite.

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
2. Inicie o servidor (a base SQLite é criada automaticamente com alguns posts exemplo caso não exista):
   ```bash
   python app.py
   ```
3. Acesse http://localhost:5000 no navegador.
4. Utilize o menu "Novo post" para publicar conteúdos. É possível editar ou excluir posts em cada página individual.

## Estrutura

- `app.py`: aplicação Flask, rotas e integração com SQLite.
- `loggym/templates`: templates HTML.
- `loggym/static`: arquivos estáticos (CSS).
- `loggym.db`: banco SQLite criado na primeira execução.

## Ajustes

- Atualize `SECRET_KEY` em `app.py` para um valor seguro em produção.
- Remova ou adapte os dados de demonstração configurados em `init_db` conforme necessário.
