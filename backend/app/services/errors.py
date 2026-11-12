"""Erros de domínio.

Os serviços levantam estes erros com mensagens prontas para o usuário; a API
os converte em respostas HTTP (ver app/main.py) e o bot da Fase 2 pode
responder a mesma mensagem no WhatsApp.
"""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409
