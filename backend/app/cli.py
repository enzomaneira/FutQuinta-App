"""Comandos administrativos.

Uso:
    python -m app.cli create-organizer --email voce@exemplo.com [--admin]

A senha é pedida no terminal (não fica no histórico do shell).
"""

import argparse
import getpass
import sys

from app.core.db import SessionLocal
from app.models.enums import UserRole
from app.services.auth import EmailAlreadyUsedError, create_user

MIN_PASSWORD_LENGTH = 8


def cmd_create_organizer(args: argparse.Namespace) -> int:
    password = getpass.getpass("Senha: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")
        return 1
    if getpass.getpass("Repita a senha: ") != password:
        print("As senhas não conferem.")
        return 1
    role = UserRole.ADMIN if args.admin else UserRole.ORGANIZER
    with SessionLocal() as db:
        try:
            user = create_user(db, args.email, password, role)
        except EmailAlreadyUsedError:
            print(f"Já existe um usuário com o e-mail {args.email}.")
            return 1
    print(f"Organizador criado: {user.email} ({user.role.value})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-organizer", help="cria um login de organizador")
    create.add_argument("--email", required=True)
    create.add_argument("--admin", action="store_true", help="papel admin")
    create.set_defaults(func=cmd_create_organizer)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
