import json
import math
import unittest

from setwise.core import calibrate_risk, summarize_risk, validate_calibration


class CoreTests(unittest.TestCase):
    def test_hand_calculated_nonincreasing(self):
        losses = [[1.0, .4, .1], [.8, .2, 0.0]]
        result = calibrate_risk(losses, [1, 2, 3], alpha=.5)
        self.assertEqual(result["selected_parameter"], 3.0)
        self.assertAlmostEqual(result["empirical_risk"], .05)
        self.assertAlmostEqual(result["correction"], 19 / 60)
        self.assertAlmostEqual(result["corrected_bound"], 11 / 30)

    def test_no_solution(self):
        result = calibrate_risk([[1, 1], [1, 1]], [1, 2], alpha=.5)
        self.assertEqual(result["status"], "no_solution")
        self.assertIsNone(result["selected_index"])
        self.assertTrue(all(not x["admissible"] for x in result["grid"]))

    def test_nondecreasing_selects_largest_feasible(self):
        result = calibrate_risk([[.1, .3, .8], [.1, .3, .8]], [1, 2, 3], alpha=.55,
                                monotone="nondecreasing")
        self.assertEqual(result["selected_index"], 1)

    def test_validation_rejects_bad_inputs(self):
        cases = [
            (lambda: validate_calibration([[0, 2]], [1, 2], alpha=.5), "range"),
            (lambda: validate_calibration([[0]], [1], alpha=0), "alpha"),
            (lambda: validate_calibration([[0]], [1], alpha=float("nan")), "finite"),
            (lambda: validate_calibration([[0, 1]], [1, 2], alpha=.5), "monotonicity"),
            (lambda: validate_calibration([[0, 0]], [1, 1], alpha=.5), "unique"),
            (lambda: validate_calibration([[0], [1, 2]], [1], alpha=.5), "rectangular"),
        ]
        for call, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                call()

    def test_nan_and_bool_rejected(self):
        with self.assertRaises(ValueError):
            summarize_risk([[math.nan]], [1])
        with self.assertRaises(ValueError):
            summarize_risk([[True]], [1])
        with self.assertRaises(ValueError):
            calibrate_risk([[0]], [True], alpha=.5)

    def test_ties_and_input_immutability(self):
        losses = [[.2, .2], [.2, .2]]
        params = [1, 2]
        original = [row[:] for row in losses]
        result = calibrate_risk(losses, params, alpha=.5)
        self.assertEqual(result["selected_index"], 0)
        self.assertEqual(losses, original)
        self.assertEqual(params, [1, 2])

    def test_json_finite_and_exact_schema(self):
        result = calibrate_risk([[.4, .2], [.2, .1]], [.1, .2], alpha=.5)
        json.dumps(result, allow_nan=False)
        self.assertEqual(set(result), {"schema_version", "status", "n_calibration", "n_parameters",
                                       "alpha", "monotone", "selected_parameter", "selected_index",
                                       "empirical_risk", "correction", "corrected_bound", "grid"})


if __name__ == "__main__":
    unittest.main()
