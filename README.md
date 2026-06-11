# Estágio - Projeto Django

Projeto desenvolvido em Django no âmbito de estágio/projeto académico.

## Tecnologias Utilizadas

- Python 3
- Django
- SQLite3
- HTML/CSS
- Git & GitHub
- Docker
- MinIO

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/Moonphaase/estagio
cd estagio
```

### 2. Criar ambiente virtual

```bash
python -m venv venv
```

### 3. Ativar ambiente virtual

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

## Executar o Projeto

### Aplicar migrações

```bash
python manage.py migrate
```

### Iniciar servidor

```bash
python manage.py runserver
```

O projeto ficará disponível em:

```text
http://127.0.0.1:8000/
```

## Estrutura do Projeto

```text
estagio/
│
├── accounts/              # Gestão de utilizadores e autenticação
├── api_keys/              # Gestão de chaves de API
├── categories/            # Categorias de produtos/dados
├── config/                # Configurações principais do Django
├── core/                  # Funcionalidades centrais da aplicação
├── datasets/              # Conjuntos de dados utilizados pelo sistema
├── frontend/              # Interface frontend
├── logs/                  # Ficheiros de logs
├── media/                 # Uploads e ficheiros multimédia
├── venv/                  # Ambiente virtual Python
│
├── .env                   # Variáveis de ambiente
├── .gitignore             # Ficheiros ignorados pelo Git
├── backup_clean.json      # Backup de dados limpo
├── backup.json            # Backup de dados
├── backup.sqlite3         # Base de dados SQLite de backup
├── docker-compose.yml     # Configuração Docker Compose
├── manage.py              # Comando principal do Django
├── README.md              # Documentação do projeto
└── requirements.txt       # Dependências Python
```

## Funcionalidades

- Estrutura base em Django
- Configuração inicial do projeto
- Sistema preparado para desenvolvimento web
- Organização modular

## Autor

Desenvolvido por João, Chico e Marco.
qualquer duvida so ver o tutorial no youtube de como fazer setup https://www.youtube.com/watch?v=koRsyjMcJYY
**

<img width="960" height="640" alt="bonnie" src="https://github.com/user-attachments/assets/76e30f65-8b41-4f09-b9c6-169d4fd239cf" />


