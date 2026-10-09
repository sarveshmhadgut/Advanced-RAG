"""
Custom exception definitions and error formatting utilities.
"""

import types

__all__: list[str] = ["MyException", "error_message_detail"]


def error_message_detail(error: Exception | str, error_detail: types.ModuleType) -> str:
    """
    Extracts detailed error message including file name, line number, and the error.

    Args:
        error (Exception | str): The exception that was raised.
        error_detail (types.ModuleType): The sys module to extract traceback details.

    Returns:
        str: A formatted error message containing the location and description of the error.
    """
    _, _, exc_tb = error_detail.exc_info()
    file_name: str = "unknown"
    line_number: int = -1
    if exc_tb is not None:
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno

    error_message: str = f"Error in {file_name} at line {line_number}: {error}"
    return error_message


class MyException(Exception):
    def __init__(
        self, error_message: Exception | str, error_detail: types.ModuleType
    ) -> None:
        """
        Initializes the custom exception with detailed error information.

        Args:
            error_message (Exception | str): The original exception raised.
            error_detail (types.ModuleType): The sys module to extract traceback details.
        """
        super().__init__(str(error_message))
        self.error_message: str = error_message_detail(
            error_message, error_detail=error_detail
        )

    def __str__(self) -> str:
        """
        Returns the string representation of the custom exception.

        Returns:
            str: The detailed error message string.
        """
        return self.error_message
