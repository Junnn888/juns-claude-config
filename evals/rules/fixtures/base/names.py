def tidy_name(name):
    cleaned = " ".join(name.split())
    return cleaned.title() if cleaned else "friend"
