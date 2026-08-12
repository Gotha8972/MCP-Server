"""
Splitwise MCP Server
====================
A read-only MCP server for querying your Splitwise account.
Provides tools for viewing expenses, balances, and category-wise spending (INR only).
"""

import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
from splitwise import Splitwise

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("splitwise-mcp")

CONSUMER_KEY = os.getenv("SPLITWISE_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("SPLITWISE_CONSUMER_SECRET", "")
API_KEY = os.getenv("SPLITWISE_API_KEY", "")

if not all([CONSUMER_KEY, CONSUMER_SECRET, API_KEY]):
    logger.warning(
        "Splitwise credentials not fully set. "
        "Please set SPLITWISE_CONSUMER_KEY, SPLITWISE_CONSUMER_SECRET, and SPLITWISE_API_KEY in your .env file."
    )

mcp = FastMCP("Splitwise MCP", instructions=(
    "You are a helpful assistant that can query a user's Splitwise account. "
    "All monetary amounts are in INR (₹). Use the available tools to answer "
    "questions about expenses, balances, and spending patterns."
))


def _get_client() -> Splitwise:
    """Return an authenticated Splitwise client."""
    if not all([CONSUMER_KEY, CONSUMER_SECRET, API_KEY]):
        raise ValueError(
            "Missing Splitwise API credentials in .env file. "
            "Please set SPLITWISE_CONSUMER_KEY, SPLITWISE_CONSUMER_SECRET, and SPLITWISE_API_KEY."
        )
    return Splitwise(CONSUMER_KEY, CONSUMER_SECRET, api_key=API_KEY)


# ---------------------------------------------------------------------------
# Tool 1: Get My Profile
# ---------------------------------------------------------------------------

@mcp.tool()
def get_my_profile() -> dict:
    """
    Get the current authenticated Splitwise user's profile.
    Returns name, email, ID, and registration status.
    """
    try:
        client = _get_client()
        user = client.getCurrentUser()
        return {
            "id": user.getId(),
            "first_name": user.getFirstName(),
            "last_name": user.getLastName(),
            "email": user.getEmail(),
            "default_currency": "INR",
        }
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool 2: Get Friends & Balances
# ---------------------------------------------------------------------------

@mcp.tool()
def get_friends_balances() -> list[dict]:
    """
    Get all Splitwise friends and their current balances in INR.
    Shows who owes you and whom you owe.
    A positive amount means they owe you; negative means you owe them.
    """
    try:
        client = _get_client()
        friends = client.getFriends()
        result = []
        for friend in friends:
            balances = friend.getBalances()
            inr_balance = "0.00"
            for b in balances:
                if b.getCurrencyCode() == "INR":
                    inr_balance = b.getAmount()
                    break

            result.append({
                "id": friend.getId(),
                "name": f"{friend.getFirstName()} {friend.getLastName() or ''}".strip(),
                "email": friend.getEmail(),
                "balance_inr": inr_balance,
                "status": "they owe you" if float(inr_balance) > 0
                          else "you owe them" if float(inr_balance) < 0
                          else "settled up",
            })
        return result
    except Exception as e:
        logger.error(f"Error fetching friends: {e}")
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# Tool 3: Get Groups
# ---------------------------------------------------------------------------

@mcp.tool()
def get_groups() -> list[dict]:
    """
    Get all Splitwise groups you belong to, with member names and group balances in INR.
    """
    try:
        client = _get_client()
        groups = client.getGroups()
        result = []
        for group in groups:
            # Skip the non-group expenses (group id 0)
            if group.getId() == 0:
                continue

            members = []
            for member in group.getMembers():
                member_balances = member.getBalances()
                inr_bal = "0.00"
                for b in member_balances:
                    if b.getCurrencyCode() == "INR":
                        inr_bal = b.getAmount()
                        break
                members.append({
                    "name": f"{member.getFirstName()} {member.getLastName() or ''}".strip(),
                    "balance_inr": inr_bal,
                })

            result.append({
                "id": group.getId(),
                "name": group.getName(),
                "type": group.getType() if hasattr(group, "getType") else "unknown",
                "member_count": len(members),
                "members": members,
                "updated_at": str(group.getUpdatedAt()) if group.getUpdatedAt() else None,
            })
        return result
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# Tool 4: Get Expenses
# ---------------------------------------------------------------------------

@mcp.tool()
def get_expenses(
    group_id: Optional[int] = None,
    friend_id: Optional[int] = None,
    dated_after: Optional[str] = None,
    dated_before: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Fetch recent expenses from Splitwise with optional filters.
    Only returns INR expenses.

    Args:
        group_id: Filter by a specific group ID.
        friend_id: Filter by a specific friend ID.
        dated_after: ISO date string (YYYY-MM-DD). Only expenses after this date.
        dated_before: ISO date string (YYYY-MM-DD). Only expenses before this date.
        limit: Number of expenses to return (default 20, max 100).
    """
    try:
        client = _get_client()
        current_user = client.getCurrentUser()
        my_id = current_user.getId()

        kwargs = {"limit": min(limit, 100)}
        if group_id is not None:
            kwargs["group_id"] = group_id
        if friend_id is not None:
            kwargs["friend_id"] = friend_id
        if dated_after:
            kwargs["dated_after"] = dated_after
        if dated_before:
            kwargs["dated_before"] = dated_before

        expenses = client.getExpenses(**kwargs)
        result = []
        for exp in expenses:
            # Filter to INR only
            if exp.getCurrencyCode() != "INR":
                continue
            # Skip deleted expenses
            if exp.getDeletedAt() is not None:
                continue

            # Find current user's share
            my_share = "0.00"
            for u in exp.getUsers():
                if u.getId() == my_id:
                    my_share = u.getOwedShare()
                    break

            result.append({
                "id": exp.getId(),
                "description": exp.getDescription(),
                "cost": exp.getCost(),
                "my_share": my_share,
                "currency": "INR",
                "category": exp.getCategory().getName() if exp.getCategory() else "Uncategorized",
                "date": str(exp.getDate()),
                "created_by": exp.getCreatedBy().getFirstName() if exp.getCreatedBy() else "Unknown",
                "group_id": exp.getGroupId(),
            })
        return result
    except Exception as e:
        logger.error(f"Error fetching expenses: {e}")
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# Tool 5: Get Spending by Category (⭐ Key Tool)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_spending_by_category(
    dated_after: Optional[str] = None,
    dated_before: Optional[str] = None,
    group_id: Optional[int] = None,
) -> dict:
    """
    Aggregate your total spending in INR, broken down by category.
    This is the most useful tool for understanding where your money goes.

    Args:
        dated_after: ISO date string (YYYY-MM-DD). Start of date range.
        dated_before: ISO date string (YYYY-MM-DD). End of date range.
        group_id: Optional group ID to filter expenses.

    Returns a dictionary with:
        - total_spent: Your total share of expenses in INR
        - category_breakdown: Spending per category sorted highest to lowest
        - expense_count: Total number of expenses analyzed
        - date_range: The date range used
    """
    try:
        client = _get_client()
        current_user = client.getCurrentUser()
        my_id = current_user.getId()

        # Fetch expenses in batches (API returns max ~100 at a time)
        all_expenses = []
        offset = 0
        batch_size = 100

        while True:
            kwargs = {"limit": batch_size, "offset": offset}
            if group_id is not None:
                kwargs["group_id"] = group_id
            if dated_after:
                kwargs["dated_after"] = dated_after
            if dated_before:
                kwargs["dated_before"] = dated_before

            batch = client.getExpenses(**kwargs)
            if not batch:
                break

            all_expenses.extend(batch)
            offset += batch_size

            # Safety cap at 500 expenses to avoid excessive API calls
            if offset >= 500:
                break

        # Aggregate by category
        category_totals = defaultdict(float)
        expense_count = 0

        for exp in all_expenses:
            # Skip non-INR and deleted
            if exp.getCurrencyCode() != "INR":
                continue
            if exp.getDeletedAt() is not None:
                continue

            # Find my share
            my_share = 0.0
            for u in exp.getUsers():
                if u.getId() == my_id:
                    my_share = float(u.getOwedShare())
                    break

            if my_share > 0:
                category_name = exp.getCategory().getName() if exp.getCategory() else "Uncategorized"
                category_totals[category_name] += my_share
                expense_count += 1

        # Sort by amount (highest first)
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        total_spent = sum(category_totals.values())

        return {
            "total_spent_inr": f"₹{total_spent:,.2f}",
            "expense_count": expense_count,
            "date_range": {
                "from": dated_after or "all time",
                "to": dated_before or "now",
            },
            "category_breakdown": [
                {
                    "category": cat,
                    "amount_inr": f"₹{amt:,.2f}",
                    "percentage": f"{(amt / total_spent * 100):.1f}%" if total_spent > 0 else "0%",
                }
                for cat, amt in sorted_categories
            ],
        }
    except Exception as e:
        logger.error(f"Error computing spending summary: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool 6: Get Category List
# ---------------------------------------------------------------------------

@mcp.tool()
def get_category_list() -> list[dict]:
    """
    List all Splitwise expense categories and their subcategories.
    Useful for understanding what categories are available.
    """
    try:
        client = _get_client()
        categories = client.getCategories()
        result = []
        for cat in categories:
            subcategories = []
            if cat.getSubcategories():
                for sub in cat.getSubcategories():
                    subcategories.append({
                        "id": sub.getId(),
                        "name": sub.getName(),
                    })
            result.append({
                "id": cat.getId(),
                "name": cat.getName(),
                "subcategories": subcategories,
            })
        return result
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
