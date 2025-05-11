class AccountDomainError(Exception):
    pass


class UserAlreadyExistsError(AccountDomainError):
    pass


class InvalidCredentialsError(AccountDomainError):
    pass


class UserNotFoundError(AccountDomainError):
    pass
