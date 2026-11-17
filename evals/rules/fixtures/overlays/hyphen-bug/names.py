def tidy_name(name):
    cleaned = " ".join(name.split())
    return cleaned.capitalize() if cleaned else "friend"
