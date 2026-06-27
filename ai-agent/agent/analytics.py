"""
Analytics Engine — performs arithmetic calculations and KPI metrics generation in Python.

Calculates collection amounts, customer growth, area performance, and subscription summaries
from raw datasets without using LLMs for math.
"""

import logging
from datetime import datetime, date
from typing import Any, Optional

from agent.query_processor import parse_date, get_numeric_value

logger = logging.getLogger(__name__)


def is_today(d: datetime) -> bool:
    return d.date() == date.today()


def is_yesterday(d: datetime) -> bool:
    return d.date() == date.today() - datetime.resolution  # Or just date.today() - timedelta(days=1)


def is_this_month(d: datetime) -> bool:
    today = date.today()
    return d.year == today.year and d.month == today.month


def is_last_month(d: datetime) -> bool:
    today = date.today()
    target_year = today.year
    target_month = today.month - 1
    if target_month == 0:
        target_month = 12
        target_year -= 1
    return d.year == target_year and d.month == target_month


class Analytics:
    """Computes stats and metrics on datasets (payments, customers, complaints)."""

    def today_collection(self, payments: list[dict]) -> dict:
        """Calculate total collection for today."""
        today_payments = []
        total = 0.0
        
        for p in payments:
            dt = p.get("payment_date", p.get("date", p.get("created_at")))
            if dt:
                parsed_dt = parse_date(dt)
                # Check if same date
                if parsed_dt.date() == date.today():
                    today_payments.append(p)
                    total += get_numeric_value(p, ["amount", "paid_amount", "amount_paid", "total"])
                    
        return {
            "total_amount": total,
            "count": len(today_payments),
            "payments": today_payments[:5]
        }

    def yesterday_collection(self, payments: list[dict]) -> dict:
        """Calculate total collection for yesterday."""
        yesterday_payments = []
        total = 0.0
        yesterday_date = date.today()
        # Handle timedelta safely in Python date subtraction
        from datetime import timedelta
        yesterday_date = date.today() - timedelta(days=1)
        
        for p in payments:
            dt = p.get("payment_date", p.get("date", p.get("created_at")))
            if dt:
                parsed_dt = parse_date(dt)
                if parsed_dt.date() == yesterday_date:
                    yesterday_payments.append(p)
                    total += get_numeric_value(p, ["amount", "paid_amount", "amount_paid", "total"])
                    
        return {
            "total_amount": total,
            "count": len(yesterday_payments),
            "payments": yesterday_payments[:5]
        }

    def monthly_collection(self, payments: list[dict]) -> dict:
        """Calculate total collection for this month."""
        this_month_payments = []
        total = 0.0
        
        for p in payments:
            dt = p.get("payment_date", p.get("date", p.get("created_at")))
            if dt:
                parsed_dt = parse_date(dt)
                if is_this_month(parsed_dt):
                    this_month_payments.append(p)
                    total += get_numeric_value(p, ["amount", "paid_amount", "amount_paid", "total"])
                    
        return {
            "total_amount": total,
            "count": len(this_month_payments),
            "payments_summary": this_month_payments[:5]
        }

    def last_month_collection(self, payments: list[dict]) -> dict:
        """Calculate total collection for last month."""
        last_month_payments = []
        total = 0.0
        
        for p in payments:
            dt = p.get("payment_date", p.get("date", p.get("created_at")))
            if dt:
                parsed_dt = parse_date(dt)
                if is_last_month(parsed_dt):
                    last_month_payments.append(p)
                    total += get_numeric_value(p, ["amount", "paid_amount", "amount_paid", "total"])
                    
        return {
            "total_amount": total,
            "count": len(last_month_payments)
        }

    def active_customer_count(self, customers: list[dict]) -> int:
        """Get count of active customers."""
        return sum(1 for c in customers if str(c.get("status", c.get("customer_status", ""))).lower() == "active")

    def inactive_customer_count(self, customers: list[dict]) -> int:
        """Get count of inactive customers."""
        return sum(1 for c in customers if str(c.get("status", c.get("customer_status", ""))).lower() == "inactive")

    def new_customer_count(self, customers: list[dict]) -> int:
        """Get count of customers who joined this month."""
        count = 0
        for c in customers:
            join = c.get("join_date", c.get("created_at", c.get("join")))
            if join:
                parsed_dt = parse_date(join)
                if is_this_month(parsed_dt):
                    count += 1
        return count

    def top_revenue_area(self, payments: list[dict]) -> str:
        """Determine which area has the highest sum of payments."""
        area_revenue = {}
        for p in payments:
            area = p.get("area_name", p.get("area", "No Area")).strip()
            amount = get_numeric_value(p, ["amount", "paid_amount", "amount_paid", "total"])
            area_revenue[area] = area_revenue.get(area, 0.0) + amount
            
        if not area_revenue:
            return "No data"
            
        return max(area_revenue, key=area_revenue.get)

    def top_paying_customers(self, payments: list[dict], limit: int = 5) -> list[dict]:
        """Get top paying customers by accumulated payment amount."""
        cust_revenue = {}
        for p in payments:
            name = p.get("customer_name", p.get("name", p.get("customer", "Unknown"))).strip()
            amount = get_numeric_value(p, ["amount", "paid_amount", "amount_paid", "total"])
            cust_revenue[name] = cust_revenue.get(name, 0.0) + amount
            
        sorted_custs = sorted(cust_revenue.items(), key=lambda x: x[1], reverse=True)
        return [{"name": name, "total_paid": amount} for name, amount in sorted_custs[:limit]]

    def complaint_summary(self, complaints: list[dict]) -> dict:
        """Generate a summary of complaints."""
        total = len(complaints)
        open_count = sum(1 for c in complaints if str(c.get("status", "")).lower() in ["open", "pending", "active"])
        resolved_count = sum(1 for c in complaints if str(c.get("status", "")).lower() in ["resolved", "closed", "completed"])
        other_count = total - open_count - resolved_count
        
        return {
            "total": total,
            "open": open_count,
            "resolved": resolved_count,
            "other": other_count
        }

    def subscription_summary(self, subscriptions: list[dict]) -> dict:
        """Generate a summary of subscriptions."""
        total = len(subscriptions)
        active_count = sum(1 for s in subscriptions if str(s.get("status", s.get("subscription_status", ""))).lower() == "active")
        expired_count = sum(1 for s in subscriptions if str(s.get("status", s.get("subscription_status", ""))).lower() in ["expired", "inactive"])
        
        return {
            "total": total,
            "active": active_count,
            "expired": expired_count
        }


# Singleton instance
analytics = Analytics()
