
import re


def matchLettersAndNumbersOnly(value):
    """Match strings of letters and numbers."""
    if re.match('^[a-zA-Z0-9]+$', value):
        return True
    return False


def matchNoSpecialCharactersOnly(value):
    """Match strings containing letters, numbers, '-', and '_'"""
    if re.match('^[a-zA-Z0-9-_ ]+$', value):
        return True
    return False


def matchLettersOnly(value):
    """Match strings container letters only."""
    if re.match('^[a-zA-Z]+$', value):
        return True
    return False


def matchNumbersOnly(value):
    """Match strings with numbers and '.' only."""
    if re.match('^[0-9.]+$', value):
        return True
    return False


def matchPositiveIntegers(value):
    """Match integers greater than 0."""
    if re.match('^[0-9]+$', value) and int(value) >= 1:
        return True
    return False
