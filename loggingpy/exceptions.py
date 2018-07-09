class ExceptionInfo:

    def __init__(self, exception_type: str, error_message: str, stack_trace: str, exception_hash: str):
        self.exception_type = exception_type
        """Unqualified exception type name"""

        self.error_message = error_message
        """See exception.message"""

        self.stack_trace = stack_trace
        """Full stack trace."""

        self.exception_hash = exception_hash
        """
        A hash of the exception, built from the exception's stack
        trace(plus nested / hidden exceptions).Can be used
        to aggregate / count similar exceptions.
        """