"""
Cron Expression Parser.

Provides cron expression parsing and next run time calculation.

Supports standard 5-field cron expressions:
    minute hour day-of-month month day-of-week

Examples:
    * * * * *       Every minute
    0 * * * *       Every hour
    0 0 * * *       Every day at midnight
    0 0 * * 0       Every Sunday at midnight
    */15 * * * *    Every 15 minutes
    0 9-17 * * 1-5  Every hour 9am-5pm, Monday-Friday
    0 0 1 * *       First day of every month
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple
import re


class CronParseError(Exception):
    """Error parsing cron expression."""
    pass


@dataclass
class CronField:
    """Represents a single cron field."""
    values: Set[int]
    min_value: int
    max_value: int

    def matches(self, value: int) -> bool:
        """Check if value matches this field."""
        return value in self.values


class CronExpression:
    """
    Parses and evaluates cron expressions.

    Standard 5-field format: minute hour day month weekday

    Field values:
        - minute: 0-59
        - hour: 0-23
        - day of month: 1-31
        - month: 1-12
        - day of week: 0-6 (0=Sunday) or 1-7 (1=Monday)

    Special characters:
        - *: Any value
        - ,: Value list separator
        - -: Range of values
        - /: Step values
    """

    # Field definitions: (min, max, names)
    FIELD_SPECS = [
        (0, 59, None),  # minute
        (0, 23, None),  # hour
        (1, 31, None),  # day of month
        (1, 12, {  # month
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }),
        (0, 6, {  # day of week (0=Sunday)
            'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3,
            'thu': 4, 'fri': 5, 'sat': 6
        }),
    ]

    # Common expression aliases
    ALIASES = {
        '@yearly': '0 0 1 1 *',
        '@annually': '0 0 1 1 *',
        '@monthly': '0 0 1 * *',
        '@weekly': '0 0 * * 0',
        '@daily': '0 0 * * *',
        '@midnight': '0 0 * * *',
        '@hourly': '0 * * * *',
    }

    def __init__(self, expression: str):
        """
        Initialize with a cron expression.

        Args:
            expression: Cron expression string.
        """
        self.expression = expression
        self.fields: List[CronField] = []
        self._parse()

    def _parse(self) -> None:
        """Parse the cron expression."""
        expr = self.expression.strip().lower()

        # Check for aliases
        if expr in self.ALIASES:
            expr = self.ALIASES[expr]

        parts = expr.split()
        if len(parts) != 5:
            raise CronParseError(
                f"Invalid cron expression: expected 5 fields, got {len(parts)}"
            )

        for i, (part, (min_val, max_val, names)) in enumerate(zip(parts, self.FIELD_SPECS)):
            try:
                values = self._parse_field(part, min_val, max_val, names)
                self.fields.append(CronField(values, min_val, max_val))
            except Exception as e:
                field_names = ['minute', 'hour', 'day', 'month', 'weekday']
                raise CronParseError(
                    f"Invalid {field_names[i]} field '{part}': {e}"
                )

    def _parse_field(
        self,
        field: str,
        min_val: int,
        max_val: int,
        names: Optional[dict] = None,
    ) -> Set[int]:
        """Parse a single cron field."""
        values: Set[int] = set()

        # Replace names with numbers
        if names:
            for name, num in names.items():
                field = field.replace(name, str(num))

        # Handle comma-separated list
        for part in field.split(','):
            part = part.strip()

            # Handle step values (*/n or range/n)
            step = 1
            if '/' in part:
                part, step_str = part.split('/', 1)
                step = int(step_str)
                if step < 1:
                    raise ValueError(f"Step must be positive, got {step}")

            # Handle range or wildcard
            if part == '*':
                start, end = min_val, max_val
            elif '-' in part:
                start_str, end_str = part.split('-', 1)
                start = int(start_str)
                end = int(end_str)
            else:
                # Single value
                val = int(part)
                if not min_val <= val <= max_val:
                    raise ValueError(f"Value {val} out of range [{min_val}-{max_val}]")
                if step == 1:
                    values.add(val)
                    continue
                start, end = val, max_val

            # Validate range
            if not min_val <= start <= max_val:
                raise ValueError(f"Start {start} out of range [{min_val}-{max_val}]")
            if not min_val <= end <= max_val:
                raise ValueError(f"End {end} out of range [{min_val}-{max_val}]")

            # Add values with step
            for v in range(start, end + 1, step):
                values.add(v)

        return values

    @property
    def minute(self) -> CronField:
        """Get minute field."""
        return self.fields[0]

    @property
    def hour(self) -> CronField:
        """Get hour field."""
        return self.fields[1]

    @property
    def day(self) -> CronField:
        """Get day of month field."""
        return self.fields[2]

    @property
    def month(self) -> CronField:
        """Get month field."""
        return self.fields[3]

    @property
    def weekday(self) -> CronField:
        """Get day of week field."""
        return self.fields[4]

    def matches(self, dt: datetime) -> bool:
        """
        Check if a datetime matches this cron expression.

        Args:
            dt: Datetime to check.

        Returns:
            True if the datetime matches.
        """
        # Convert Sunday from 6 to 0 if using Python's weekday()
        weekday = (dt.weekday() + 1) % 7  # Python: Mon=0, Cron: Sun=0

        return (
            self.minute.matches(dt.minute) and
            self.hour.matches(dt.hour) and
            self.day.matches(dt.day) and
            self.month.matches(dt.month) and
            self.weekday.matches(weekday)
        )

    def get_next(self, after: Optional[datetime] = None) -> datetime:
        """
        Get the next datetime that matches this cron expression.

        Args:
            after: Start searching after this time. Defaults to now.

        Returns:
            Next matching datetime.
        """
        if after is None:
            after = datetime.utcnow()

        # Start from the next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search up to 4 years ahead (covers leap years and all combinations)
        max_iterations = 365 * 24 * 60 * 4
        iterations = 0

        while iterations < max_iterations:
            if self.matches(current):
                return current

            # Increment by one minute
            current += timedelta(minutes=1)
            iterations += 1

        raise CronParseError(
            f"Could not find next run time for expression: {self.expression}"
        )

    def get_next_n(
        self,
        n: int,
        after: Optional[datetime] = None,
    ) -> List[datetime]:
        """
        Get the next N datetimes that match this cron expression.

        Args:
            n: Number of times to return.
            after: Start searching after this time.

        Returns:
            List of next N matching datetimes.
        """
        results = []
        current = after

        for _ in range(n):
            next_time = self.get_next(current)
            results.append(next_time)
            current = next_time

        return results

    def get_previous(self, before: Optional[datetime] = None) -> datetime:
        """
        Get the previous datetime that matched this cron expression.

        Args:
            before: Start searching before this time. Defaults to now.

        Returns:
            Previous matching datetime.
        """
        if before is None:
            before = datetime.utcnow()

        # Start from the previous minute
        current = before.replace(second=0, microsecond=0) - timedelta(minutes=1)

        # Search up to 4 years back
        max_iterations = 365 * 24 * 60 * 4
        iterations = 0

        while iterations < max_iterations:
            if self.matches(current):
                return current

            current -= timedelta(minutes=1)
            iterations += 1

        raise CronParseError(
            f"Could not find previous run time for expression: {self.expression}"
        )

    def __str__(self) -> str:
        return self.expression

    def __repr__(self) -> str:
        return f"CronExpression('{self.expression}')"


def parse_cron(expression: str) -> CronExpression:
    """
    Parse a cron expression.

    Args:
        expression: Cron expression string.

    Returns:
        Parsed CronExpression object.
    """
    return CronExpression(expression)


def get_next_cron_time(
    expression: str,
    after: Optional[datetime] = None,
) -> datetime:
    """
    Get the next time a cron expression will trigger.

    Args:
        expression: Cron expression string.
        after: Start searching after this time.

    Returns:
        Next trigger datetime.
    """
    cron = CronExpression(expression)
    return cron.get_next(after)


def validate_cron(expression: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a cron expression.

    Args:
        expression: Cron expression string.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        CronExpression(expression)
        return True, None
    except CronParseError as e:
        return False, str(e)


def describe_cron(expression: str) -> str:
    """
    Generate a human-readable description of a cron expression.

    Args:
        expression: Cron expression string.

    Returns:
        Human-readable description.
    """
    try:
        cron = CronExpression(expression)
    except CronParseError as e:
        return f"Invalid: {e}"

    parts = []

    # Minute
    if cron.minute.values == set(range(60)):
        parts.append("Every minute")
    elif len(cron.minute.values) == 1:
        val = list(cron.minute.values)[0]
        if val == 0:
            parts.append("At the start of the hour")
        else:
            parts.append(f"At minute {val}")
    else:
        parts.append(f"At minutes {sorted(cron.minute.values)}")

    # Hour
    if cron.hour.values == set(range(24)):
        parts.append("every hour")
    elif len(cron.hour.values) == 1:
        val = list(cron.hour.values)[0]
        parts.append(f"at {val:02d}:00")
    else:
        parts.append(f"during hours {sorted(cron.hour.values)}")

    # Day of month
    if cron.day.values != set(range(1, 32)):
        if len(cron.day.values) == 1:
            val = list(cron.day.values)[0]
            parts.append(f"on day {val}")
        else:
            parts.append(f"on days {sorted(cron.day.values)}")

    # Month
    if cron.month.values != set(range(1, 13)):
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        months = [month_names[m-1] for m in sorted(cron.month.values)]
        parts.append(f"in {', '.join(months)}")

    # Day of week
    if cron.weekday.values != set(range(7)):
        day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        days = [day_names[d] for d in sorted(cron.weekday.values)]
        parts.append(f"on {', '.join(days)}")

    return " ".join(parts)
