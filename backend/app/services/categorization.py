import re
from collections.abc import Sequence

from app.models.categorization_rule import CategorizationRule
from sqlalchemy import select
from sqlalchemy.orm import Session


_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Income", ("payroll", "salary", "wages", "paycheck")),
    (
        "Groceries",
        ("grocery", "groceries", "supermarket", "trader joe", "whole foods", "safeway", "kroger", "aldi"),
    ),
    (
        "Dining",
        ("restaurant", "cafe", "coffee", "starbucks", "doordash", "uber eats", "ubereats", "grubhub", "takeout"),
    ),
    ("Housing", ("rent", "mortgage")),
    ("Utilities", ("electric bill", "electricity", "water bill", "internet", "utility", "phone bill")),
    (
        "Transportation",
        ("uber", "lyft", "gas station", "fuel", "metro", "transit", "parking", "shell", "exxon"),
    ),
    ("Healthcare", ("pharmacy", "walgreens", "cvs", "clinic", "hospital", "medical")),
    ("Subscriptions", ("netflix", "spotify", "hulu", "disney+", "icloud", "subscription")),
    ("Entertainment", ("cinema", "movie theater", "concert", "theater")),
    ("Shopping", ("amazon", "target", "retail")),
)


def categorize_transaction(description: str, merchant: str | None = None) -> str | None:
    text = f"{merchant or ''} {description}".casefold()
    for category, keywords in _RULES:
        for keyword in keywords:
            pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
            if re.search(pattern, text):
                return category
    return None


def categorize_with_rules(
    description: str,
    merchant: str | None,
    rules: Sequence[CategorizationRule],
) -> tuple[str | None, str | None]:
    description_text = description.casefold()
    merchant_text = (merchant or "").casefold()
    for rule in rules:
        if rule.match_field == "merchant":
            haystack = merchant_text
        elif rule.match_field == "description":
            haystack = description_text
        else:
            haystack = f"{merchant_text} {description_text}"
        if rule.keyword.casefold() in haystack:
            return rule.category, "rule"

    category = categorize_transaction(description, merchant)
    return category, "automatic" if category else None


def load_user_rules(db: Session, user_id: str) -> list[CategorizationRule]:
    statement = (
        select(CategorizationRule)
        .where(CategorizationRule.user_id == user_id)
        .order_by(CategorizationRule.priority.desc(), CategorizationRule.created_at)
    )
    return list(db.scalars(statement))
