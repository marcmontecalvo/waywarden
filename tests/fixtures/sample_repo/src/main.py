"""Sample project used in coding-profile e2e integration tests."""


def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("world"))
