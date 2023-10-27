import datajoint as dj


def get_schema_prefix():
    user = dj.config.get("database.user")
    custom = dj.config.get("custom", {}).get("database.prefix")

    if user == "root":
        user = None

    return user or custom or "temp"


schema_prefix = get_schema_prefix()
