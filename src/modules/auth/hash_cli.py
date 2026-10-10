"""
Generate a PBKDF2 hash for the MC_PASSWORD_HASH environment variable.

Usage:
    python -m src.modules.auth.hash_cli "your-password"
"""
import sys

from src.modules.auth.password import hash_password


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python -m src.modules.auth.hash_cli <password>",
            file=sys.stderr,
        )
        raise SystemExit(2)
    print(hash_password(sys.argv[1]))


if __name__ == "__main__":
    main()
