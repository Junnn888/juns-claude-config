from hello import greet


def test_greet_uses_name():
    assert greet("sam") == "hi Sam"


def test_greet_blank_name():
    assert greet("   ") == "hi friend"


def test_greet_hyphenated_name():
    assert greet("mary-jane") == "hi Mary-Jane"
