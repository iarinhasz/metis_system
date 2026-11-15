"""Erros de curadoria exibidos pelo admin sem expor respostas do provedor."""


class CurationError(ValueError):
    pass


class CurationConflict(CurationError):
    pass
