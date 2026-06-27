def ok(data=None):
    return {"success": True, "data": data, "error": None}


def error(message: str):
    return {"success": False, "data": None, "error": message}
