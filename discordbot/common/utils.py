from typing import Union


def format_exception(e: Exception) -> Union[str, Exception]:
    return str(e).replace("\n", ". ")
