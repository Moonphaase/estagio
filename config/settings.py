from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY           = config('SECRET_KEY', default='django-insecure-ba1nx#5aqw4jc7z-n%%mj*)ik4&3j7q!7o8w-1t0t$@kd9(s)3')
DEBUG                = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS        = str(config('ALLOWED_HOSTS', default='*')).split(',')
CSRF_TRUSTED_ORIGINS = str(config('CSRF_TRUSTED_ORIGINS', default='http://localhost')).split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'storages',
    'core',
    'accounts',
    'categories',
    'datasets',
    'frontend',
    'api_keys',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     config('DB_NAME',     default='estagio'),
        'USER':     config('DB_USER',     default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='chico'),
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}

if config('DATABASE_URL', default=None):
    DATABASES['default'] = dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
    )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL        = 'accounts.CustomUser'
LOGIN_URL              = 'login'
LOGIN_REDIRECT_URL     = 'dashboard'
LOGOUT_REDIRECT_URL    = 'login'

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

STATIC_URL  = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    _use_https = config('MINIO_USE_HTTPS', default=False, cast=bool)
    _scheme    = 'https' if _use_https else 'http'

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    AWS_ACCESS_KEY_ID        = config('MINIO_ACCESS_KEY')
    AWS_SECRET_ACCESS_KEY    = config('MINIO_SECRET_KEY')
    AWS_STORAGE_BUCKET_NAME  = config('MINIO_BUCKET')
    AWS_S3_ENDPOINT_URL      = f"{_scheme}://{config('MINIO_ENDPOINT')}"
    AWS_S3_USE_SSL           = _use_https
    AWS_DEFAULT_ACL          = None
    AWS_S3_FILE_OVERWRITE    = False
    AWS_QUERYSTRING_AUTH     = True
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_REGION_NAME       = 'us-east-1'

else:
    MEDIA_URL  = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api_keys.authentication.APIKeyAuthentication',
       
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'api_keys.permissions.HasValidApiKey',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Dataset Manager API',
    'DESCRIPTION': (
        'Documentação oficial da API para gestão de datasets, versões e categorias.\n\n'
        '## Autenticação\n'
        'Esta API requer uma **API Key** válida gerada no site.\n\n'
        'Inclui o header: `Authorization: Token <a_tua_chave>`'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'PREPROCESSING_HOOKS': ['config.spectacular_hooks.only_get_methods'],
    'SECURITY': [{'apiKeyAuth': []}],
    'COMPONENTS': {
        'securitySchemes': {
            'apiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Formato: **Token <a_tua_chave>**',
            }
        }
    },
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM':    'HS256',
    'SIGNING_KEY':  SECRET_KEY,
}

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'app.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'datasets': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}