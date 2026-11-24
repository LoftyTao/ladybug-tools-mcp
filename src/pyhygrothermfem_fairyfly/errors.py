"""Exception family for the THMZ contract and solver.

Validation failures raise ``ContractError`` subclasses carrying a stable
``THMZ-Exxxx`` code aligned with the code ranges in ``docs/thmz-contract.md``.
Kernel and publication failures raise ``SolveError``; solver failures do not
occupy the validation code space, so their ``code`` is None.

``ContractError`` is a ``ValueError`` and ``SolveError`` is a ``RuntimeError``
so callers written against the original run_thmz contract keep working.
"""


# THERM's behavior for active boundaries without TransientData is not bound.
TRANSIENT_BOUNDARY_WITHOUT_DATA = 'THMZ-E5017'


class THMZError(Exception):
    """Base class for all pyhygrothermfem_fairyfly errors; carries a stable code.

    Attributes:
        code: Stable error code string like ``THMZ-E4001``, or None for
            runtime failures that do not occupy the contract code space.
    """

    def __init__(self, message, code=None):
        self.code = code
        super().__init__(message)

    def __str__(self):
        message = super().__str__()
        return '{}: {}'.format(self.code, message) if self.code else message


class ContractError(THMZError, ValueError):
    """A THMZ contract violation (code ranges E1xxx-E5xxx)."""


class MeshError(ContractError):
    """A geometry or mesh topology violation (code range E3xxx)."""


class UnsupportedError(ContractError):
    """A declarable model that the solving surface must reject (E5xxx)."""


class SolveError(THMZError, RuntimeError):
    """Kernel non-convergence, incomplete results or publication inconsistency."""


def make_error(code, message):
    """Build the ContractError subclass matching a ``THMZ-Exxxx`` code.

    The single factory for code-based error classification: messages are the
    bare text (the code is attached separately and rendered by ``__str__``).
    """
    if code.startswith('THMZ-E5'):
        return UnsupportedError(message, code)
    if code.startswith('THMZ-E3'):
        return MeshError(message, code)
    return ContractError(message, code)
