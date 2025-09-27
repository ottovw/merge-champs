import unittest
from datetime import datetime, timedelta

from src.utils import (
    get_week_date_range,
    get_month_date_range,
    get_week_display_text,
    get_month_display_text,
    create_sample_data,
)


class UtilsDateRangeTests(unittest.TestCase):
    def test_week_range_is_monday_through_sunday(self) -> None:
        reference = datetime(2025, 9, 26, 15, 30)  # Friday
        start, end = get_week_date_range(reference=reference)

        self.assertEqual(start.weekday(), 0)  # Monday
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.minute, 0)
        self.assertEqual(start.second, 0)

        self.assertEqual(end.weekday(), 6)  # Sunday
        self.assertEqual(end.hour, 23)
        self.assertEqual(end.minute, 59)
        self.assertEqual(end.second, 59)

        self.assertEqual((end - start).days, 6)

    def test_week_range_offset_moves_back_in_time(self) -> None:
        reference = datetime(2025, 9, 26)
        start_current, _ = get_week_date_range(reference=reference)
        start_previous, _ = get_week_date_range(offset_weeks=1, reference=reference)

        self.assertEqual(start_previous, start_current - timedelta(weeks=1))

    def test_month_range_spans_full_month(self) -> None:
        reference = datetime(2025, 2, 10)
        start, end = get_month_date_range(reference=reference)

        self.assertEqual(start.day, 1)
        self.assertEqual(start.hour, 0)
        self.assertEqual(end.day, 28)
        self.assertEqual(end.hour, 23)
        self.assertEqual(end.minute, 59)
        self.assertEqual(end.second, 59)

    def test_month_offset_moves_back_one_month(self) -> None:
        reference = datetime(2025, 9, 26)
        start_current, _ = get_month_date_range(reference=reference)
        start_previous, _ = get_month_date_range(offset_months=1, reference=reference)
        self.assertEqual(start_current, datetime(2025, 9, 1))
        self.assertEqual(start_previous, datetime(2025, 8, 1))

    def test_week_display_text_includes_range(self) -> None:
        start = datetime(2025, 9, 22)
        end = datetime(2025, 9, 28, 23, 59, 59)
        label = get_week_display_text(start, end)
        self.assertIn('Sep 22', label)
        self.assertIn('Sep 28, 2025', label)

    def test_month_display_text_includes_month_and_year(self) -> None:
        start = datetime(2025, 9, 1)
        label = get_month_display_text(start)
        self.assertIn('September 2025', label)

    def test_sample_data_is_deterministic_with_seed(self) -> None:
        seed = 202509
        sample_one = create_sample_data(seed=seed)
        sample_two = create_sample_data(seed=seed)
        self.assertEqual(sample_one, sample_two)


if __name__ == '__main__':
    unittest.main()
