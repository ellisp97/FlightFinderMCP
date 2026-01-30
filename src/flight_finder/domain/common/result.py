"""Result monad for functional error handling.

This module provides a Result type that enables explicit error handling
without relying on exceptions for control flow. This pattern:
- Makes error cases explicit in function signatures
- Enables composition of operations that may fail
- Provides a consistent interface for error handling
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Awaitable

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E", bound=Exception)
F = TypeVar("F", bound=Exception)


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Represents a successful result containing a value."""

    value: T

    def is_ok(self) -> bool:
        """Check if this is a successful result."""
        return True

    def is_err(self) -> bool:
        """Check if this is an error result."""
        return False


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Represents a failed result containing an error."""

    error: E

    def is_ok(self) -> bool:
        """Check if this is a successful result."""
        return False

    def is_err(self) -> bool:
        """Check if this is an error result."""
        return True


# Result is a union type - either Ok[T] or Err[E]
Result = Ok[T] | Err[E]


def unwrap(result: Result[T, E]) -> T:
    """Extract the value from a result, raising the error if present.

    Args:
        result: The result to unwrap

    Returns:
        The contained value if Ok

    Raises:
        The contained error if Err
    """
    match result:
        case Ok(value):
            return value
        case Err(error):
            raise error


def unwrap_or(result: Result[T, E], default: T) -> T:
    """Extract the value from a result, returning a default if error.

    Args:
        result: The result to unwrap
        default: Default value to return if result is an error

    Returns:
        The contained value if Ok, otherwise the default
    """
    match result:
        case Ok(value):
            return value
        case Err():
            return default


def unwrap_or_else(result: Result[T, E], default_fn: Callable[[E], T]) -> T:
    """Extract the value, computing a default from the error if present.

    Args:
        result: The result to unwrap
        default_fn: Function to compute default value from error

    Returns:
        The contained value if Ok, otherwise computed default
    """
    match result:
        case Ok(value):
            return value
        case Err(error):
            return default_fn(error)


def map_result(result: Result[T, E], fn: Callable[[T], U]) -> Result[U, E]:
    """Apply a function to the contained value if Ok.

    Args:
        result: The result to transform
        fn: Function to apply to the value

    Returns:
        Result with transformed value, or original error
    """
    match result:
        case Ok(value):
            return Ok(fn(value))
        case Err() as err:
            return err


def map_err(result: Result[T, E], fn: Callable[[E], F]) -> Result[T, F]:
    """Apply a function to the contained error if Err.

    Args:
        result: The result to transform
        fn: Function to apply to the error

    Returns:
        Original value, or result with transformed error
    """
    match result:
        case Ok() as ok:
            return ok
        case Err(error):
            return Err(fn(error))


def and_then(result: Result[T, E], fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
    """Chain operations that return Results (flatMap/bind).

    Args:
        result: The result to chain from
        fn: Function that returns a Result

    Returns:
        The chained result, or original error
    """
    match result:
        case Ok(value):
            return fn(value)
        case Err() as err:
            return err


def or_else(result: Result[T, E], fn: Callable[[E], Result[T, F]]) -> Result[T, F]:
    """Provide fallback for errors (error recovery).

    Args:
        result: The result to recover from
        fn: Function that attempts recovery

    Returns:
        Original value, or recovery result
    """
    match result:
        case Ok() as ok:
            return ok
        case Err(error):
            return fn(error)


@overload
def collect_results(results: list[Result[T, E]]) -> Result[list[T], E]: ...


@overload
def collect_results(results: tuple[Result[T, E], ...]) -> Result[tuple[T, ...], E]: ...


def collect_results(
    results: list[Result[T, E]] | tuple[Result[T, E], ...],
) -> Result[list[T], E] | Result[tuple[T, ...], E]:
    """Collect a sequence of Results into a Result of a sequence.

    Returns the first error encountered, or all values if successful.

    Args:
        results: Sequence of Results to collect

    Returns:
        Result containing all values, or first error
    """
    values: list[T] = []
    for result in results:
        match result:
            case Ok(value):
                values.append(value)
            case Err() as err:
                return err

    if isinstance(results, tuple):
        return Ok(tuple(values))
    return Ok(values)


def from_exception(fn: Callable[[], T], *exceptions: type[Exception]) -> Result[T, Exception]:
    """Execute a function and capture specified exceptions as Err.

    Args:
        fn: Function to execute
        *exceptions: Exception types to catch (defaults to Exception)

    Returns:
        Ok with result, or Err with caught exception
    """
    exception_types = exceptions if exceptions else (Exception,)
    try:
        return Ok(fn())
    except exception_types as e:
        return Err(e)


async def from_exception_async(
    fn: Callable[[], Awaitable[T]], *exceptions: type[Exception]
) -> Result[T, Exception]:
    """Execute an async function and capture specified exceptions as Err.

    Args:
        fn: Async function to execute
        *exceptions: Exception types to catch (defaults to Exception)

    Returns:
        Ok with result, or Err with caught exception
    """
    exception_types = exceptions if exceptions else (Exception,)
    try:
        return Ok(await fn())
    except exception_types as e:
        return Err(e)


def is_ok(result: Result[T, E]) -> bool:
    """Check if result is Ok."""
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> bool:
    """Check if result is Err."""
    return isinstance(result, Err)


def get_ok(result: Result[T, E]) -> T | None:
    """Get the Ok value or None."""
    match result:
        case Ok(value):
            return value
        case Err():
            return None


def get_err(result: Result[T, E]) -> E | None:
    """Get the Err value or None."""
    match result:
        case Ok():
            return None
        case Err(error):
            return error
