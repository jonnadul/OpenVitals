"""Synthetic data connector.

Generates a deterministic, realistic-looking :class:`HealthData` so VitalFrame
runs end-to-end with zero private data and zero network. Used by the sample
config, the test-suite, and the quickstart. Never used to produce real insights.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta

from ..config import SourceConfig
from ..models import (
    DailyNutrition,
    GlucoseReading,
    HealthData,
    Meal,
    Medication,
    Observation,
    SleepSession,
    Workout,
)
from ..types import MedicationStatus
from .base import SourceConnector


class SyntheticConnector(SourceConnector):
    type_key = "synthetic"

    def fetch(self) -> HealthData:
        params = self.params
        days = int(params.get("days", 120))
        seed = int(params.get("seed", 7))
        end = date.today()
        rng = random.Random(seed)
        data = HealthData()
        data.meta["generated_by"] = "synthetic"
        data.meta["seed"] = seed

        meals_text = [
            "Greek yogurt + berries + walnuts",
            "Egg + cheese muffin + half avocado",
            "Chicken curry + rice + vegetables",
            "Salmon + quinoa + broccoli",
            "Lentil soup + sourdough", "Turkey wrap + side salad",
            "Tofu stir-fry + noodles", "Oatmeal + peanut butter + banana",
        ]

        for d in range(days):
            day = end - timedelta(days=days - 1 - d)
            # seasonal-ish slow drift on weight
            weight = 78.0 + 2.5 * math.sin(d / 30.0) + rng.uniform(-0.4, 0.4)
            rhr = 58.0 + 4 * math.sin(d / 14.0) + rng.gauss(0, 1.5)
            hrv = 62.0 - 8 * math.sin(d / 14.0) + rng.gauss(0, 6)
            steps = int(max(1500, 9000 + 4000 * math.sin(d / 9.0) + rng.gauss(0, 2200)))
            active = round(steps * 0.04 + rng.uniform(50, 250), 1)

            base = datetime(day.year, day.month, day.day)
            data.observations.append(Observation("resting_heart_rate", round(rhr, 1), "bpm",
                                                  base.replace(hour=7), self.name))
            data.observations.append(Observation("heart_rate_variability", round(hrv, 1), "ms",
                                                  base.replace(hour=7), self.name))
            data.observations.append(Observation("step_count", float(steps), "count",
                                                  base.replace(hour=23), self.name))
            data.observations.append(Observation("active_energy", active, "kcal",
                                                  base.replace(hour=23), self.name))
            data.observations.append(Observation("body_mass", round(weight, 2), "kg",
                                                  base.replace(hour=7), self.name))

            # Sleep: one main session + occasional nap
            sleep_start = base.replace(hour=23, minute=rng.choice([0, 15, 30, 45]))
            slept = rng.uniform(6.2, 8.4)
            sleep_end = sleep_start + timedelta(hours=slept)
            rem = round(slept * 0.20, 2)
            deep = round(slept * 0.18, 2)
            core = round(slept - rem - deep, 2)
            data.sleep.append(SleepSession(sleep_start, sleep_end, round(slept, 2), self.name,
                                           rem_h=rem, deep_h=deep, core_h=core))

            # Workouts ~4x/week
            if rng.random() < 0.57:
                wstart = base.replace(hour=rng.choice([6, 12, 17, 18]), minute=rng.choice([0, 15, 30]))
                dur = rng.choice([35, 45, 50, 60, 75])
                data.workouts.append(Workout(
                    wstart, wstart + timedelta(minutes=dur), dur * 60,
                    rng.choice(["Walk", "Run", "Strength", "Cycling", "Rowing"]), self.name,
                    energy_kcal=round(dur * rng.uniform(7, 11), 1),
                    distance_km=round(dur * rng.uniform(0.1, 0.18), 2) if rng.random() < 0.6 else None,
                    hr_avg=round(rng.uniform(110, 150), 0),
                ))

            # Medication: metformin daily (mostly taken)
            status = MedicationStatus.TAKEN if rng.random() < 0.9 else MedicationStatus.SKIPPED
            data.medications.append(Medication("Metformin", day, status,
                                               base.replace(hour=8) if status == MedicationStatus.TAKEN else None,
                                               self.name))

            # Meals (3/day), some inside/outside a 9:00-17:00 window
            meal_specs = [
                (9, "Breakfast", meals_text[d % len(meals_text)]),
                (13, "Lunch", meals_text[(d + 3) % len(meals_text)]),
                (19, "Dinner", meals_text[(d + 5) % len(meals_text)]),
            ]
            for hh, label, txt in meal_specs:
                mtime = base.replace(hour=hh, minute=rng.choice([0, 10, 20, 30, 45]))
                cal = round(rng.uniform(350, 850), 0)
                data.meals.append(Meal(mtime, f"{label}: {txt}", self.name,
                                       calories=cal, items=[]))

            # Glucose: 10-min readings across waking hours, meal-driven spikes
            wake = base.replace(hour=6, minute=30)
            bed = base.replace(hour=23, minute=0)
            t = wake
            while t <= bed:
                base_gl = 92.0 + 6 * math.sin((t.hour - 6) / 16 * math.pi) + rng.gauss(0, 4)
                # meal spikes
                spike = 0.0
                for hh, _, _ in meal_specs:
                    mt = base.replace(hour=hh)
                    delta = (t - mt).total_seconds() / 60.0
                    if 0 <= delta <= 90:
                        spike = max(spike, 55 * math.exp(-((delta - 35) ** 2) / 900))
                val = base_gl + spike
                # rare mild hypo overnight
                if t.hour in (2, 3) and rng.random() < 0.04:
                    val = rng.uniform(58, 68)
                data.glucose.append(GlucoseReading(t, round(val, 1), self.name))
                t += timedelta(minutes=10)

            # Daily nutrition
            data.nutrition.append(DailyNutrition(
                day, calories=round(sum(m.calories or 0 for m in data.meals if m.day == day), 0),
                protein_g=round(rng.uniform(90, 160), 0),
                carbs_g=round(rng.uniform(180, 280), 0),
                fat_g=round(rng.uniform(60, 110), 0),
                fiber_g=round(rng.uniform(18, 34), 0),
                water_ml=round(rng.uniform(1500, 2800), 0),
                source=self.name,
            ))

        return data


register = SyntheticConnector.register
