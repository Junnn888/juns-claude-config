from names import tidy_name

GREETING = "hi"


def greet(name):
    return f"{GREETING} {tidy_name(name)}"
