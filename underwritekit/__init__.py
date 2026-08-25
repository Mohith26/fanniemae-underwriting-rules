"""UnderwriteKit: a declarative eligibility rules engine for synthetic loans."""
from .engine import RuleEngine, load_rules
from .models import APPROVE, REFER, Decision, LoanApplication, Reason
from .oracle import oracle_decide

__all__ = [
    "APPROVE",
    "REFER",
    "Decision",
    "LoanApplication",
    "Reason",
    "RuleEngine",
    "load_rules",
    "oracle_decide",
]
