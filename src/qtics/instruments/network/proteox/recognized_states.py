"""Recognized state evaluator for Proteox.

This module evaluates whether the cryostat is in one of the recognized
states defined by the Proteox truth table.

IMPORTANT:
- Matching is EXCLUSIVE:
  a state is matched only if all its required TRUE conditions are true
  AND all its required FALSE conditions are false.
- This avoids "subset matches" such as matching "Idle And Vented"
  while the system is actually in "Circulating Compressor Bypassed".

NOTES:
- Some getters referenced here may not yet exist in your driver.
  Missing getters are handled gracefully and return None.
- You should progressively replace placeholder getters with real URIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

# ============================================================
# Helpers
# ============================================================


def _safe_float(x, default=None):
    """Convert value to float safely."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _safe_bool_from_state(x) -> bool:
    """
    Normalize ON/OFF or OPEN/CLOSED style values to bool.

    Accepted values:
    - bool
    - int / float
    - str in {"on", "open", "true", "1", "enabled"}
    """
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x != 0
    if isinstance(x, str):
        return x.strip().lower() in {"on", "open", "true", "1", "enabled"}
    return False


# ============================================================
# Data structures
# ============================================================


@dataclass(frozen=True)
class Condition:
    """A boolean condition used to identify a recognized cryostat state."""

    key: str
    label: str
    evaluator: Callable[[dict[str, Any]], bool]
    suggestion_if_false: str
    suggestion_if_true: str | None = None


@dataclass(frozen=True)
class StateMatch:
    """Result for one candidate state."""

    state_name: str
    matched: bool
    missing_true_conditions: list[str]
    violating_false_conditions: list[str]
    satisfied_true_conditions: list[str]
    satisfied_false_conditions: list[str]
    mismatch_count: int


# ============================================================
# Condition definitions
# ============================================================


def build_conditions() -> dict[str, Condition]:
    """
    Define all boolean conditions used by the Proteox recognized-state table.

    You should adapt / refine these once the exact raw API signals are confirmed.
    """
    return {
        "PTR_IS_ON": Condition(
            key="PTR_IS_ON",
            label="3CL-PTR-01 is On",
            evaluator=lambda s: _safe_bool_from_state(s.get("PTR_ON")),
            suggestion_if_false="Turn ON pulse tube (3CL-PTR-01).",
            suggestion_if_true="Turn OFF pulse tube (3CL-PTR-01).",
        ),
        "FOREPUMP_IS_ON": Condition(
            key="FOREPUMP_IS_ON",
            label="3CL-FP-01 is On",
            evaluator=lambda s: _safe_bool_from_state(s.get("FP_ON")),
            suggestion_if_false="Turn ON forepump (3CL-FP-01).",
            suggestion_if_true="Turn OFF forepump (3CL-FP-01).",
        ),
        "COMPRESSOR_IS_ON": Condition(
            key="COMPRESSOR_IS_ON",
            label="3CL-CP-01 is On",
            evaluator=lambda s: _safe_bool_from_state(s.get("CP_ON")),
            suggestion_if_false="Turn ON compressor (3CL-CP-01).",
            suggestion_if_true="Turn OFF compressor (3CL-CP-01).",
        ),
        "TURBO_IS_ON": Condition(
            key="TURBO_IS_ON",
            label="3CL-TP-01 is On",
            evaluator=lambda s: _safe_bool_from_state(s.get("TP_ON")),
            suggestion_if_false="Turn ON turbo pump (3CL-TP-01).",
            suggestion_if_true="Turn OFF turbo pump (3CL-TP-01).",
        ),
        "OVC_EVACUATED": Condition(
            key="OVC_EVACUATED",
            label="OVC-PG-01 < 1 Pa",
            evaluator=lambda s: (
                _safe_float(s.get("OVC_P")) is not None
                and _safe_float(s.get("OVC_P")) < 1.0
            ),
            suggestion_if_false="Evacuate OVC until OVC-PG-01 < 1 Pa.",
            suggestion_if_true="Vent OVC so that OVC-PG-01 is not < 1 Pa.",
        ),
        "MIXTURE_CONDENSED": Condition(
            key="MIXTURE_CONDENSED",
            label="3CL-PG-01 < 1500 Pa",
            evaluator=lambda s: (
                _safe_float(s.get("P1_P")) is not None
                and _safe_float(s.get("P1_P")) < 1500.0
            ),
            suggestion_if_false="Condense mixture until 3CL-PG-01 < 1500 Pa.",
            suggestion_if_true="Bring 3CL-PG-01 above 1500 Pa.",
        ),
        "PT2_STAGE_COLD": Condition(
            key="PT2_STAGE_COLD",
            label="DRI-PT2-S < 5 K",
            evaluator=lambda s: (
                _safe_float(s.get("DR2_T")) is not None
                and _safe_float(s.get("DR2_T")) < 5.0
            ),
            suggestion_if_false="Wait/cool until PT2 stage temperature (DRI-PT2-S) < 5 K.",
            suggestion_if_true="Warm PT2 stage so that DRI-PT2-S is not < 5 K.",
        ),
        "MIX_CHAMBER_COLD": Condition(
            key="MIX_CHAMBER_COLD",
            label="DRI-MIX-S < 2 K",
            evaluator=lambda s: (
                _safe_float(s.get("MC_T")) is not None
                and _safe_float(s.get("MC_T")) < 2.0
            ),
            suggestion_if_false="Cool mixing chamber until DRI-MIX-S < 2 K.",
            suggestion_if_true="Warm mixing chamber so that DRI-MIX-S is not < 2 K.",
        ),
        "OVC_VALVE_OPEN": Condition(
            key="OVC_VALVE_OPEN",
            label="OVC-AV-01 is Open",
            evaluator=lambda s: not _safe_bool_from_state(s.get("OVC_AV_01_CLOSED")),
            suggestion_if_false="Open OVC valve (OVC-AV-01).",
            suggestion_if_true="Close OVC valve (OVC-AV-01).",
        ),
        "HIGH_TEMP_CTRL_MODE": Condition(
            key="HIGH_TEMP_CTRL_MODE",
            label="DRI-MIX-CL is On @ > 2K",
            evaluator=lambda s: (
                _safe_bool_from_state(s.get("MC_CTRL_ON"))
                and (
                    _safe_float(s.get("MC_T")) is not None
                    and _safe_float(s.get("MC_T")) > 2.0
                )
            ),
            suggestion_if_false="Enable mixing chamber temperature control above 2 K.",
            suggestion_if_true="Disable high temperature control mode.",
        ),
        "TRAP_BYPASSED": Condition(
            key="TRAP_BYPASSED",
            label="V9, V10 Closed & V4 Open",
            evaluator=lambda s: (
                (
                    _safe_bool_from_state(
                        s.get("V9_error")
                        == _safe_bool_from_state(s.get("V10_error") == 0)
                    )
                )
                and (not _safe_bool_from_state(s.get("V4_CLOSED")))
            ),
            suggestion_if_false="Set trap bypass: close V9, close V10, open V4.",
            suggestion_if_true="Disable trap bypass and restore normal valve configuration.",
        ),
        "OVC_VENTED": Condition(
            key="OVC_VENTED",
            label="OVC-PG-01 > 100 Pa",
            evaluator=lambda s: (
                _safe_float(s.get("OVC_P")) is not None
                and _safe_float(s.get("OVC_P")) > 100.0
            ),
            suggestion_if_false="Vent OVC until OVC-PG-01 > 100 Pa.",
            suggestion_if_true="Pump OVC so that OVC-PG-01 is not > 100 Pa.",
        ),
        "EMPTYING_TRAP": Condition(
            key="EMPTYING_TRAP",
            label="3CL-AV-08 is Open",
            evaluator=lambda s: _safe_bool_from_state(s.get("AV_08_CLOSED")),
            suggestion_if_false="Open 3CL-AV-08 to empty trap.",
            suggestion_if_true="Close 3CL-AV-08.",
        ),
        "MIX_CHAMBER_PRECOOLED": Condition(
            key="MIX_CHAMBER_PRECOOLED",
            label="DRI-MIX-S < 6 K",
            evaluator=lambda s: (
                _safe_float(s.get("MC_T")) is not None
                and _safe_float(s.get("MC_T")) < 6.0
            ),
            suggestion_if_false="Wait/cool until DRI-MIX-S < 6 K.",
            suggestion_if_true="Warm mixing chamber so that DRI-MIX-S is not < 6 K.",
        ),
        "SORB_COLD": Condition(
            key="SORB_COLD",
            label="SRB-GGS-S < 6 K",
            evaluator=lambda s: (
                _safe_float(s.get("SRB_T")) is not None
                and _safe_float(s.get("SRB_T")) < 6.0
            ),
            suggestion_if_false="Wait/cool until SRB-GGS-S < 6 K.",
            suggestion_if_true="Warm sorb so that SRB-GGS-S is not < 6 K.",
        ),
    }


ALL_CONDITIONS = [
    "PTR_IS_ON",
    "FOREPUMP_IS_ON",
    "COMPRESSOR_IS_ON",
    "TURBO_IS_ON",
    "OVC_EVACUATED",
    "MIXTURE_CONDENSED",
    "PT2_STAGE_COLD",
    "MIX_CHAMBER_COLD",
    "OVC_VALVE_OPEN",
    "HIGH_TEMP_CTRL_MODE",
    "TRAP_BYPASSED",
    "OVC_VENTED",
    "EMPTYING_TRAP",
    "PRECOOL_ENABLED",
    "EMPTYING_PRECOOL",
    "MIX_CHAMBER_PRECOOLED",
    "SORB_COLD",
]


def state(true_conditions: list[str]) -> dict[str, list[str]]:
    """
    Exclusive-state helper.

    Every condition not explicitly listed as True is assumed False.
    This is the correct interpretation if your Proteox truth table is exclusive.
    """
    true_set = set(true_conditions)
    false_conditions = [c for c in ALL_CONDITIONS if c not in true_set]
    return {
        "true": list(true_set),
        "false": false_conditions,
    }


# ============================================================
# Recognized state table (EXCLUSIVE)
# ============================================================

# IMPORTANT:
# This is only as good as the truth table transcription.
# If two states are physically different but have the same boolean pattern here,
# they will still both match. In that case the issue is the table transcription,
# not the matching algorithm.

RECOGNIZED_STATES: dict[str, dict[str, list[str]]] = {
    "Idle And Warming": state([]),
    "Idle And Vented": state(
        [
            "OVC_VENTED",
        ]
    ),
    "Idle And Evacuated": state(
        [
            "OVC_EVACUATED",
        ]
    ),
    "Pumping": state(
        [
            "OVC_VENTED",
            "OVC_VALVE_OPEN",
        ]
    ),
    "Pumping And Soft": state(
        [
            "OVC_VALVE_OPEN",
        ]
    ),
    "Pumping And Evacuated": state(
        [
            "OVC_EVACUATED",
            "OVC_VALVE_OPEN",
        ]
    ),
    "Precooling": state(
        [
            "PTR_IS_ON",
            "OVC_EVACUATED",
            "OVC_VALVE_OPEN",
        ]
    ),
    "Precooled": state(
        [
            "PTR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "OVC_VALVE_OPEN",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Precooled OVC Closed": state(
        [
            "PTR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Condensing": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_COLD",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Circulating": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "TURBO_IS_ON",
            "OVC_EVACUATED",
            "MIXTURE_CONDENSED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_COLD",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Circulating Compressor Bypassed": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "TURBO_IS_ON",
            "OVC_EVACUATED",
            "MIXTURE_CONDENSED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_COLD",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Circulating Trap Bypassed": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "TURBO_IS_ON",
            "OVC_EVACUATED",
            "MIXTURE_CONDENSED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_COLD",
            "TRAP_BYPASSED",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Circulating Trap and Comp. Bypassed": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "TURBO_IS_ON",
            "OVC_EVACUATED",
            "MIXTURE_CONDENSED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_COLD",
            "TRAP_BYPASSED",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "High Temp.": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "HIGH_TEMP_CTRL_MODE",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "High Temp. Compressor Bypassed": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "HIGH_TEMP_CTRL_MODE",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "High Temp Trap Bypassed": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "HIGH_TEMP_CTRL_MODE",
            "TRAP_BYPASSED",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "High Temp Trap and Comp. Bypassed": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "HIGH_TEMP_CTRL_MODE",
            "TRAP_BYPASSED",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Collecting mix. Warm": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "SORB_COLD",
        ]
    ),
    "Collecting mix. cold": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "OVC_EVACUATED",
            "PT2_STAGE_COLD",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Emptying Trap (Bypass option)": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "TURBO_IS_ON",
            "OVC_EVACUATED",
            "MIXTURE_CONDENSED",
            "PT2_STAGE_COLD0",
            "MIX_CHAMBER_COLD0",
            "TRAP_BYPASSED",
            "EMPTYING_TRAP",
            "MIX_CHAMBER_PRECOOLED",
            "SORB_COLD",
        ]
    ),
    "Precool loop running": state(
        ["PTR_IS_ON", "COMPRESSOR_IS_ON", "OVC_EVACUATED", "PRECOOL_ENABLED"]
    ),
    "Emptying precool loop": state(
        [
            "PTR_IS_ON",
            "FOREPUMP_IS_ON",
            "COMPRESSOR_IS_ON",
            "TURBO_IS_ON",
            "OVC_EVACUATED",
            "EMPTYING_PRECOOL",
        ]
    ),
}


# ============================================================
# Evaluator class
# ============================================================


class RecognizedStateManager:
    """Evaluates whether the cryostat is in a recognized state."""

    def __init__(self, proteox):
        """Build considitions for state recognition."""
        self.proteox = proteox
        self.conditions = build_conditions()

    # --------------------------------------------------------
    # Raw signal acquisition
    # --------------------------------------------------------

    async def read_signals(self) -> dict[str, Any]:
        """Collect all raw values needed to evaluate state conditions."""
        signals = {
            "OVC_P": await self._maybe_get("OVC_P"),
            "P1_P": await self._maybe_get("P1_P"),
            "DR2_T": await self._maybe_get("DR2_T"),
            "MC_T": await self._maybe_get("MC_T"),
            "SRB_T": await self._maybe_get("SRB_T"),
            "PTR_ON": await self._maybe_get("PTR_ON"),
            "FP_ON": await self._maybe_get("FP_ON"),
            "CP_ON": await self._maybe_get("CP_ON"),
            "TP_ON": await self._maybe_get("TP_ON"),
            "OVC_AV_01_CLOSED": await self._maybe_get("OVC_AV_01_CLOSED"),
            "MC_CTRL_ON": await self._maybe_get("MC_CTRL_ON"),
            "V4_CLOSED": await self._maybe_get("V4_CLOSED"),
            "V9_error": await self._maybe_get("V9_error"),
            "V10_error": await self._maybe_get("V10_error"),
            "AV_08_CLOSED": await self._maybe_get("AV_08_CLOSED"),
        }

        return signals

    async def _maybe_get(self, key: str):
        """
        Try to call proteox.get_<key>() dynamically.

        Return None if getter is unavailable or fails.
        """
        try:
            getter = getattr(self.proteox, f"get_{key}")
            return await getter()
        except Exception:
            return None

    # --------------------------------------------------------
    # Condition evaluation
    # --------------------------------------------------------

    async def evaluate_conditions(self) -> dict[str, bool]:
        """Evaluate all defined conditions."""
        signals = await self.read_signals()
        result = {}

        for key, condition in self.conditions.items():
            try:
                result[key] = bool(condition.evaluator(signals))
            except Exception:
                result[key] = False

        return result

    async def get_condition_report(self) -> dict[str, dict[str, Any]]:
        """
        Return a diagnostic condition report.

        Example:
        {
            "PTR_IS_ON": {
                "label": "3CL-PTR-01 is On",
                "value": True,
            },
            ...
        }
        """
        values = await self.evaluate_conditions()
        return {
            key: {
                "label": cond.label,
                "value": values.get(key, False),
            }
            for key, cond in self.conditions.items()
        }

    # --------------------------------------------------------
    # State matching
    # --------------------------------------------------------

    async def match_all_states(self) -> list[StateMatch]:
        """Evaluate all recognized states using EXCLUSIVE matching."""
        condition_values = await self.evaluate_conditions()
        matches: list[StateMatch] = []

        for state_name, state_def in RECOGNIZED_STATES.items():
            required_true = state_def["true"]
            required_false = state_def["false"]

            missing_true = [
                c for c in required_true if not condition_values.get(c, False)
            ]
            violating_false = [
                c for c in required_false if condition_values.get(c, False)
            ]

            satisfied_true = [
                c for c in required_true if condition_values.get(c, False)
            ]
            satisfied_false = [
                c for c in required_false if not condition_values.get(c, False)
            ]

            mismatch_count = len(missing_true) + len(violating_false)

            matches.append(
                StateMatch(
                    state_name=state_name,
                    matched=(mismatch_count == 0),
                    missing_true_conditions=missing_true,
                    violating_false_conditions=violating_false,
                    satisfied_true_conditions=satisfied_true,
                    satisfied_false_conditions=satisfied_false,
                    mismatch_count=mismatch_count,
                )
            )

        matches.sort(key=lambda x: x.mismatch_count)
        return matches

    async def get_recognized_states(self) -> list[str]:
        """Return all currently matched recognized states."""
        matches = await self.match_all_states()
        return [m.state_name for m in matches if m.matched]

    async def is_in_recognized_state(self) -> bool:
        """Return True if current conditions match at least one recognized state."""
        states = await self.get_recognized_states()
        return len(states) > 0

    async def get_closest_state(self) -> StateMatch | None:
        """Return the closest recognized state (minimum total mismatches)."""
        matches = await self.match_all_states()
        return matches[0] if matches else None

    async def get_state_gap(self, target_state: str) -> StateMatch:
        """Return mismatches relative to a specific target state."""
        if target_state not in RECOGNIZED_STATES:
            raise ValueError(
                f"Unknown recognized state '{target_state}'. "
                f"Available: {list(RECOGNIZED_STATES.keys())}"
            )

        condition_values = await self.evaluate_conditions()
        state_def = RECOGNIZED_STATES[target_state]

        required_true = state_def["true"]
        required_false = state_def["false"]

        missing_true = [c for c in required_true if not condition_values.get(c, False)]
        violating_false = [c for c in required_false if condition_values.get(c, False)]

        satisfied_true = [c for c in required_true if condition_values.get(c, False)]
        satisfied_false = [
            c for c in required_false if not condition_values.get(c, False)
        ]

        mismatch_count = len(missing_true) + len(violating_false)

        return StateMatch(
            state_name=target_state,
            matched=(mismatch_count == 0),
            missing_true_conditions=missing_true,
            violating_false_conditions=violating_false,
            satisfied_true_conditions=satisfied_true,
            satisfied_false_conditions=satisfied_false,
            mismatch_count=mismatch_count,
        )

    # --------------------------------------------------------
    # Human-readable suggestions
    # --------------------------------------------------------

    async def how_to_go_to_recognized_state(
        self, target_state: str | None = None
    ) -> str:
        """
        Return a human-readable suggestion to reach.

        In particular:
        - the closest recognized state
        - or a user-requested target state
        """
        if target_state is None:
            match = await self.get_closest_state()
            if match is None:
                return "No recognized states are configured."
        else:
            match = await self.get_state_gap(target_state)

        if match.matched:
            return f"System is already in recognized state: '{match.state_name}'."

        lines = [
            (
                f"Closest target state: '{match.state_name}'"
                if target_state is None
                else f"Target state: '{match.state_name}'"
            ),
            f"Total mismatches: {match.mismatch_count}",
            "",
            "Required actions:",
        ]

        # Conditions that should be TRUE but are FALSE
        for cond_key in match.missing_true_conditions:
            cond = self.conditions[cond_key]
            lines.append(f" - {cond.label} -> {cond.suggestion_if_false}")

        # Conditions that should be FALSE but are TRUE
        for cond_key in match.violating_false_conditions:
            cond = self.conditions[cond_key]
            if cond.suggestion_if_true:
                lines.append(
                    f" - {cond.label} should be FALSE -> {cond.suggestion_if_true}"
                )
            else:
                lines.append(f" - {cond.label} should be FALSE.")

        return "\n".join(lines)

    # --------------------------------------------------------
    # Structured suggestions (useful for GUI / automation)
    # --------------------------------------------------------

    async def get_transition_plan(
        self, target_state: str | None = None
    ) -> dict[str, Any]:
        """
        Return a structured transition plan.

        Useful if you later want to drive a GUI or automatic action planner.
        """
        if target_state is None:
            match = await self.get_closest_state()
            if match is None:
                return {
                    "target_state": None,
                    "matched": False,
                    "mismatch_count": None,
                    "actions": [],
                }
        else:
            match = await self.get_state_gap(target_state)

        actions = []

        for cond_key in match.missing_true_conditions:
            cond = self.conditions[cond_key]
            actions.append(
                {
                    "condition": cond_key,
                    "label": cond.label,
                    "target_value": True,
                    "suggestion": cond.suggestion_if_false,
                }
            )

        for cond_key in match.violating_false_conditions:
            cond = self.conditions[cond_key]
            actions.append(
                {
                    "condition": cond_key,
                    "label": cond.label,
                    "target_value": False,
                    "suggestion": cond.suggestion_if_true
                    or f"Make condition '{cond.label}' false.",
                }
            )

        return {
            "target_state": match.state_name,
            "matched": match.matched,
            "mismatch_count": match.mismatch_count,
            "missing_true_conditions": match.missing_true_conditions,
            "violating_false_conditions": match.violating_false_conditions,
            "actions": actions,
        }
