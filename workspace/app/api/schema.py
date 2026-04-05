"""
JSON Schema for chores.json validation
"""

INTERVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "n": {"type": "integer", "minimum": 1},
        "unit": {"type": "string", "enum": ["day", "week", "month", "year"]},
    },
    "required": ["n", "unit"],
    "additionalProperties": False,
}

REQUIREMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "interval": INTERVAL_SCHEMA,
        "lastAligned": {"type": ["string", "null"]},
    },
    "required": ["id", "name", "interval", "lastAligned"],
    "additionalProperties": False,
}

CADENCE_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "startDate": {"type": "string", "pattern": "^\\d{2}-\\d{2}$"},
        "interval": INTERVAL_SCHEMA,
        "status": {"type": "string", "enum": ["inactive"]},
    },
    "required": ["startDate"],
    "additionalProperties": False,
}

CHORE_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "interval": INTERVAL_SCHEMA,
        "weekend": {"type": "boolean"},
        "dayConfigurable": {"type": "boolean"},
        "weekPin": {"type": ["string", "null"], "enum": ["odd", "even", None]},
        "dayPin": {"type": ["integer", "null"], "enum": [1, 15, None]},
        "lastAligned": {"type": ["string", "null"], "enum": ["pending"] + [None]},
        "notes": {"type": "array", "items": {"type": "string"}},
        "synchronizedWith": {"type": "array", "items": {"type": "string"}},
        "requirements": {"type": "array", "items": REQUIREMENT_SCHEMA},
        "annualCadence": {"type": "array", "items": CADENCE_ENTRY_SCHEMA},
    },
    "required": [
        "id",
        "name",
        "interval",
        "weekend",
        "dayConfigurable",
        "weekPin",
        "dayPin",
        "lastAligned",
        "notes",
        "synchronizedWith",
        "requirements",
        "annualCadence",
    ],
    "additionalProperties": False,
}

CHORE_SCHEMA = {
    "type": "object",
    "properties": {
        "chores": {
            "type": "array",
            "items": CHORE_ENTRY_SCHEMA,
        }
    },
    "required": ["chores"],
    "additionalProperties": False,
}
