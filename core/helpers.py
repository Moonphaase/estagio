import hashlib
import os
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import uuid

ALLOWED_EXTENSIONS = ['.csv', '.json', '.xlsx', '.parquet', '.zip']
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


# Gera checksum SHA-256 de um ficheiro
def generate_checksum(file):
    sha256 = hashlib.sha256()
    for chunk in file.chunks():
        sha256.update(chunk)
    return sha256.hexdigest()


# Valida extensão do ficheiro
def validate_file_extension(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Extensão não permitida: {ext}. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return ext


# Valida tamanho do ficheiro (default: 100MB)
def validate_file_size(file, max_size=MAX_FILE_SIZE):
    if file.size > max_size:
        raise ValidationError(
            f"Ficheiro demasiado grande. Máximo: {max_size // (1024*1024)}MB"
        )


# Gera nome seguro para o ficheiro
def safe_filename(filename):
    name, ext = os.path.splitext(filename)
    safe = slugify(name)
    unique = uuid.uuid4().hex[:8]
    return f"{safe}_{unique}{ext}"


# Gera caminho de upload organizado por dataset e versão
def dataset_upload_path(dataset_id, version, filename):
    safe = safe_filename(filename)
    return f"datasets/dataset_{dataset_id}/{version}/{safe}"