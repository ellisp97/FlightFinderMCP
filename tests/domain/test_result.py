"""Tests for Result monad implementation."""

import pytest

from flight_finder.domain.common.result import (
    Err,
    Ok,
    Result,
    and_then,
    collect_results,
    from_exception,
    from_exception_async,
    get_err,
    get_ok,
    is_err,
    is_ok,
    map_err,
    map_result,
    or_else,
    unwrap,
    unwrap_or,
    unwrap_or_else,
)


class TestError(Exception):
    """Test exception for testing."""

    pass


class OtherError(Exception):
    """Another test exception."""

    pass


class TestOk:
    """Tests for Ok variant."""

    def test_ok_creation(self) -> None:
        """Test creating an Ok result."""
        result: Result[int, Exception] = Ok(42)
        assert isinstance(result, Ok)
        assert result.value == 42

    def test_ok_is_ok(self) -> None:
        """Test is_ok returns True for Ok."""
        result = Ok(42)
        assert result.is_ok() is True

    def test_ok_is_err(self) -> None:
        """Test is_err returns False for Ok."""
        result = Ok(42)
        assert result.is_err() is False

    def test_ok_with_none_value(self) -> None:
        """Test Ok can contain None."""
        result: Result[None, Exception] = Ok(None)
        assert result.is_ok()
        assert result.value is None

    def test_ok_with_complex_value(self) -> None:
        """Test Ok with complex value."""
        data = {"key": [1, 2, 3], "nested": {"a": "b"}}
        result: Result[dict, Exception] = Ok(data)
        assert result.value == data


class TestErr:
    """Tests for Err variant."""

    def test_err_creation(self) -> None:
        """Test creating an Err result."""
        error = TestError("test error")
        result: Result[int, TestError] = Err(error)
        assert isinstance(result, Err)
        assert result.error is error

    def test_err_is_ok(self) -> None:
        """Test is_ok returns False for Err."""
        result: Result[int, TestError] = Err(TestError("test"))
        assert result.is_ok() is False

    def test_err_is_err(self) -> None:
        """Test is_err returns True for Err."""
        result: Result[int, TestError] = Err(TestError("test"))
        assert result.is_err() is True


class TestUnwrap:
    """Tests for unwrap functions."""

    def test_unwrap_ok(self) -> None:
        """Test unwrap returns value for Ok."""
        result: Result[int, Exception] = Ok(42)
        assert unwrap(result) == 42

    def test_unwrap_err_raises(self) -> None:
        """Test unwrap raises error for Err."""
        error = TestError("test error")
        result: Result[int, TestError] = Err(error)
        with pytest.raises(TestError, match="test error"):
            unwrap(result)

    def test_unwrap_or_ok(self) -> None:
        """Test unwrap_or returns value for Ok."""
        result: Result[int, Exception] = Ok(42)
        assert unwrap_or(result, 0) == 42

    def test_unwrap_or_err(self) -> None:
        """Test unwrap_or returns default for Err."""
        result: Result[int, TestError] = Err(TestError("test"))
        assert unwrap_or(result, 0) == 0

    def test_unwrap_or_else_ok(self) -> None:
        """Test unwrap_or_else returns value for Ok."""
        result: Result[int, Exception] = Ok(42)
        assert unwrap_or_else(result, lambda _: 0) == 42

    def test_unwrap_or_else_err(self) -> None:
        """Test unwrap_or_else computes default for Err."""
        result: Result[int, TestError] = Err(TestError("test"))
        assert unwrap_or_else(result, lambda e: len(str(e))) > 0


class TestMapResult:
    """Tests for map_result function."""

    def test_map_ok(self) -> None:
        """Test map_result transforms Ok value."""
        result: Result[int, Exception] = Ok(42)
        mapped = map_result(result, lambda x: x * 2)
        assert isinstance(mapped, Ok)
        assert unwrap(mapped) == 84

    def test_map_err_unchanged(self) -> None:
        """Test map_result preserves Err."""
        error = TestError("test")
        result: Result[int, TestError] = Err(error)
        mapped = map_result(result, lambda x: x * 2)
        assert isinstance(mapped, Err)
        assert mapped.error is error

    def test_map_changes_type(self) -> None:
        """Test map_result can change the value type."""
        result: Result[int, Exception] = Ok(42)
        mapped: Result[str, Exception] = map_result(result, str)
        assert unwrap(mapped) == "42"


class TestMapErr:
    """Tests for map_err function."""

    def test_map_err_transforms_error(self) -> None:
        """Test map_err transforms Err."""
        result: Result[int, TestError] = Err(TestError("test"))
        mapped = map_err(result, lambda e: OtherError(f"wrapped: {e}"))
        assert isinstance(mapped, Err)
        assert isinstance(mapped.error, OtherError)
        assert "wrapped" in str(mapped.error)

    def test_map_err_preserves_ok(self) -> None:
        """Test map_err preserves Ok."""
        result: Result[int, TestError] = Ok(42)
        mapped = map_err(result, lambda e: OtherError(str(e)))
        assert isinstance(mapped, Ok)
        assert unwrap(mapped) == 42


class TestAndThen:
    """Tests for and_then (flatMap) function."""

    def test_and_then_ok_returns_ok(self) -> None:
        """Test and_then chains Ok results."""
        result: Result[int, Exception] = Ok(42)
        chained = and_then(result, lambda x: Ok(x * 2))
        assert unwrap(chained) == 84

    def test_and_then_ok_returns_err(self) -> None:
        """Test and_then can produce Err from Ok."""
        result: Result[int, TestError] = Ok(42)
        chained = and_then(result, lambda _: Err(TestError("failed")))
        assert isinstance(chained, Err)

    def test_and_then_err_short_circuits(self) -> None:
        """Test and_then short-circuits on Err."""
        error = TestError("original")
        result: Result[int, TestError] = Err(error)
        called = False

        def should_not_call(x: int) -> Result[int, TestError]:
            nonlocal called
            called = True
            return Ok(x)

        chained = and_then(result, should_not_call)
        assert not called
        assert isinstance(chained, Err)
        assert chained.error is error


class TestOrElse:
    """Tests for or_else (error recovery) function."""

    def test_or_else_ok_unchanged(self) -> None:
        """Test or_else preserves Ok."""
        result: Result[int, TestError] = Ok(42)
        recovered = or_else(result, lambda _: Ok(0))
        assert unwrap(recovered) == 42

    def test_or_else_err_recovers(self) -> None:
        """Test or_else recovers from Err."""
        result: Result[int, TestError] = Err(TestError("test"))
        recovered = or_else(result, lambda _: Ok(0))
        assert unwrap(recovered) == 0

    def test_or_else_err_can_fail_again(self) -> None:
        """Test or_else can produce another Err."""
        result: Result[int, TestError] = Err(TestError("first"))
        recovered = or_else(result, lambda _: Err(OtherError("second")))
        assert isinstance(recovered, Err)
        assert isinstance(recovered.error, OtherError)


class TestCollectResults:
    """Tests for collect_results function."""

    def test_collect_all_ok_list(self) -> None:
        """Test collecting all Ok results from a list."""
        results: list[Result[int, Exception]] = [Ok(1), Ok(2), Ok(3)]
        collected = collect_results(results)
        assert isinstance(collected, Ok)
        assert unwrap(collected) == [1, 2, 3]

    def test_collect_all_ok_tuple(self) -> None:
        """Test collecting all Ok results from a tuple."""
        results: tuple[Result[int, Exception], ...] = (Ok(1), Ok(2), Ok(3))
        collected = collect_results(results)
        assert isinstance(collected, Ok)
        assert unwrap(collected) == (1, 2, 3)

    def test_collect_first_err(self) -> None:
        """Test collecting returns first Err."""
        error = TestError("first error")
        results: list[Result[int, TestError]] = [
            Ok(1),
            Err(error),
            Ok(3),
            Err(TestError("second")),
        ]
        collected = collect_results(results)
        assert isinstance(collected, Err)
        assert collected.error is error

    def test_collect_empty_list(self) -> None:
        """Test collecting empty list returns empty Ok."""
        results: list[Result[int, Exception]] = []
        collected = collect_results(results)
        assert isinstance(collected, Ok)
        assert unwrap(collected) == []


class TestFromException:
    """Tests for from_exception function."""

    def test_from_exception_success(self) -> None:
        """Test from_exception captures successful result."""
        result = from_exception(lambda: 42)
        assert isinstance(result, Ok)
        assert unwrap(result) == 42

    def test_from_exception_catches_specified(self) -> None:
        """Test from_exception catches specified exceptions."""

        def raise_error() -> int:
            raise TestError("test")

        result = from_exception(raise_error, TestError)
        assert isinstance(result, Err)
        assert isinstance(result.error, TestError)

    def test_from_exception_catches_default(self) -> None:
        """Test from_exception catches Exception by default."""

        def raise_error() -> int:
            raise ValueError("test")

        result = from_exception(raise_error)
        assert isinstance(result, Err)
        assert isinstance(result.error, ValueError)

    def test_from_exception_propagates_unspecified(self) -> None:
        """Test from_exception propagates unspecified exceptions."""

        def raise_error() -> int:
            raise TypeError("test")

        with pytest.raises(TypeError):
            from_exception(raise_error, ValueError)


class TestFromExceptionAsync:
    """Tests for from_exception_async function."""

    @pytest.mark.anyio
    async def test_from_exception_async_success(self) -> None:
        """Test from_exception_async captures successful result."""

        async def async_fn() -> int:
            return 42

        result = await from_exception_async(async_fn)
        assert isinstance(result, Ok)
        assert unwrap(result) == 42

    @pytest.mark.anyio
    async def test_from_exception_async_catches(self) -> None:
        """Test from_exception_async catches exceptions."""

        async def async_raise() -> int:
            raise TestError("async error")

        result = await from_exception_async(async_raise, TestError)
        assert isinstance(result, Err)
        assert isinstance(result.error, TestError)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_ok_function(self) -> None:
        """Test is_ok function."""
        assert is_ok(Ok(42)) is True
        assert is_ok(Err(TestError("test"))) is False

    def test_is_err_function(self) -> None:
        """Test is_err function."""
        assert is_err(Ok(42)) is False
        assert is_err(Err(TestError("test"))) is True

    def test_get_ok_returns_value(self) -> None:
        """Test get_ok returns value for Ok."""
        assert get_ok(Ok(42)) == 42

    def test_get_ok_returns_none_for_err(self) -> None:
        """Test get_ok returns None for Err."""
        assert get_ok(Err(TestError("test"))) is None

    def test_get_err_returns_error(self) -> None:
        """Test get_err returns error for Err."""
        error = TestError("test")
        result: Result[int, TestError] = Err(error)
        assert get_err(result) is error

    def test_get_err_returns_none_for_ok(self) -> None:
        """Test get_err returns None for Ok."""
        assert get_err(Ok(42)) is None


class TestResultComposition:
    """Tests for composing multiple Result operations."""

    def test_chain_multiple_operations(self) -> None:
        """Test chaining multiple Result operations."""
        result: Result[int, Exception] = Ok(5)

        # Chain: add 10, multiply by 2, convert to string
        final = and_then(
            and_then(
                map_result(result, lambda x: x + 10),
                lambda x: Ok(x * 2),
            ),
            lambda x: Ok(str(x)),
        )

        assert unwrap(final) == "30"

    def test_short_circuit_on_error(self) -> None:
        """Test that chains short-circuit on first error."""
        call_count = 0

        def increment_and_fail(x: int) -> Result[int, TestError]:
            nonlocal call_count
            call_count += 1
            if x > 5:
                return Err(TestError("too big"))
            return Ok(x + 1)

        result: Result[int, TestError] = Ok(1)

        # Chain multiple operations, one will fail
        # Starts at 1, increments to 2, 3, 4, 5, 6
        # At x=6, condition x > 5 triggers error
        # So function called 6 times total: (1→2), (2→3), (3→4), (4→5), (5→6), (6→Err)
        for _ in range(10):
            result = and_then(result, increment_and_fail)

        assert isinstance(result, Err)
        assert call_count == 6  # Called 6 times: 1→2→3→4→5→6→Err


class TestResultImmutability:
    """Tests for Result immutability."""

    def test_ok_is_frozen(self) -> None:
        """Test Ok is immutable."""
        result = Ok(42)
        with pytest.raises(AttributeError):
            result.value = 100  # type: ignore[misc]

    def test_err_is_frozen(self) -> None:
        """Test Err is immutable."""
        result = Err(TestError("test"))
        with pytest.raises(AttributeError):
            result.error = TestError("other")  # type: ignore[misc]
