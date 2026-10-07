def greet(name, shout=False):
    if name is None or str(name).strip() == "":
        raise ValueError("name is required")

    who = str(name).strip()
    if shout:
        return f"HELLO, {who.upper()}!"
    return f"Hello, {who}."
