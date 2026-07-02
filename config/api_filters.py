def filter_only_get_methods(endpoints):
    """
    Filtra os endpoints para mostrar apenas métodos GET na documentação.
    """
    filtered = []
    for (path, path_regex, method, callback) in endpoints:
        if method.upper() == 'GET':
            filtered.append((path, path_regex, method, callback))
    return filtered