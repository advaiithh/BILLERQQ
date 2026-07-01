"""
Analyzer — processes raw BillerQ API data into business KPIs and summaries.
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def parse_amount(val: Any) -> float:
    """Parse a currency string like '5,521.22' or number to float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    # Strip non-numeric characters except dots and minus signs
    cleaned = re.sub(r"[^\d.-]", "", str(val))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


class Analyzer:
    """Performs metric calculations and business intelligence analysis."""

    def __init__(self, llm=None):
        self.llm = llm

    def compute_kpis(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute structured KPI metrics from multiple raw BillerQ API payloads.

        Args:
            raw_data: Mapped raw results containing dashboard, connection, package, status, and complaint counts.

        Returns:
            Computed KPI dictionary.
        """
        # 1. Collection metrics
        dashboard = raw_data.get("dashboard") or raw_data.get("get_dashboard_data") or {}
        connection = raw_data.get("connections") or raw_data.get("get_connection_data") or {}
        
        # Dashboard details
        pay_coll = dashboard.get("data", {}).get("payment_collection", {}) if "data" in dashboard else dashboard.get("payment_collection", {})
        pay_coll = pay_coll or {}
        
        coll_meter = connection.get("data", {}).get("collection_meter", {}) if "data" in connection else connection.get("collection_meter", {})
        coll_meter = coll_meter or {}
        
        this_month_meter = connection.get("data", {}).get("collection_this_month_meter", {}) if "data" in connection else connection.get("collection_this_month_meter", {})
        this_month_meter = this_month_meter or {}
        
        today_collection = parse_amount(pay_coll.get("today", coll_meter.get("today", 0.0)))
        this_month_collection = parse_amount(pay_coll.get("this_month", this_month_meter.get("collection", 0.0)))
        total_dues = parse_amount(pay_coll.get("dues", coll_meter.get("dues", 0.0)))
        wallet_amount = parse_amount(pay_coll.get("wallet_amount", 0.0))
        
        # Calculate yesterday's collection from chart if possible, else default to 0
        chart_data = connection.get("data", {}).get("collection_chart", {}) if "data" in connection else connection.get("collection_chart", {})
        chart_data = chart_data or {}
        chart_points = chart_data.get("data", [])
        
        yesterday_collection = 0.0
        # If we have weekly collections, maybe we can display recent collections
        recent_collections = [parse_amount(pt) for pt in chart_points]

        # 2. Customer metrics
        status_data = raw_data.get("customer_status") or raw_data.get("get_customer_status_count") or {}
        status_list = status_data.get("data", []) if isinstance(status_data, dict) and "data" in status_data else (status_data if isinstance(status_data, list) else [])
        
        total_cust = 0
        active_cust = 0
        inactive_cust = 0
        suspended_cust = 0
        archived_cust = 0
        
        for item in status_list:
            status = str(item.get("status", "")).lower()
            count = int(item.get("count", 0))
            if status == "total":
                total_cust = count
            elif status == "active":
                active_cust = count
            elif status == "inactive":
                inactive_cust = count
            elif status == "suspended":
                suspended_cust = count
            elif status == "archived":
                archived_cust = count

        # If counts are empty, fallback to check_condition in dashboard
        check_cond = dashboard.get("data", {}).get("check_condition", {}) if "data" in dashboard else dashboard.get("check_condition", {})
        check_cond = check_cond or {}
        if total_cust == 0:
            active_cust = int(check_cond.get("customers", 0))
            total_cust = active_cust + inactive_cust

        # 3. Complaint metrics
        complaint_status_data = raw_data.get("complaints_status") or raw_data.get("complaint_status_count") or {}
        complaint_status_list = complaint_status_data.get("data", []) if isinstance(complaint_status_data, dict) and "data" in complaint_status_data else (complaint_status_data if isinstance(complaint_status_data, list) else [])
        
        open_complaints = 0
        in_progress_complaints = 0
        closed_complaints = 0
        
        for item in complaint_status_list:
            status = str(item.get("status", "")).lower()
            count = int(item.get("count", 0))
            if status == "open":
                open_complaints = count
            elif status in ["in progress", "in_progress"]:
                in_progress_complaints = count
            elif status == "closed":
                closed_complaints = count

        # Fallback to dashboard complaints key if counts are empty
        dashboard_complaints = dashboard.get("data", {}).get("complaints", {}) if "data" in dashboard else dashboard.get("complaints", {})
        dashboard_complaints = dashboard_complaints or {}
        total_complaints = int(dashboard_complaints.get("total", open_complaints + in_progress_complaints + closed_complaints))
        if open_complaints == 0 and total_complaints > 0:
            open_complaints = int(dashboard_complaints.get("un_resolved", 0))
            in_progress_complaints = int(dashboard_complaints.get("in_process", 0))
            closed_complaints = int(dashboard_complaints.get("resolved", 0))

        # 4. Subscription/Package metrics
        package_rep_data = raw_data.get("package_report", {}) or {}
        pkg_data = package_rep_data.get("data", {}).get("packages", {}) if "data" in package_rep_data else package_rep_data.get("packages", {})
        pkg_list = pkg_data.get("data", []) if isinstance(pkg_data, dict) and "data" in pkg_data else (pkg_data if isinstance(pkg_data, list) else [])
        
        popular_packages = []
        for pkg in pkg_list:
            name = pkg.get("package_name")
            count = int(pkg.get("invoice_count", 0))
            revenue = parse_amount(pkg.get("grand_total", 0.0))
            if name:
                popular_packages.append({
                    "package_name": name,
                    "subscribers": count,
                    "revenue": revenue
                })
        
        # Sort by subscriber count descending
        popular_packages.sort(key=lambda x: x["subscribers"], reverse=True)
        
        dashboard_sub = dashboard.get("data", {}).get("subscriptions", {}) if "data" in dashboard else dashboard.get("subscriptions", {})
        dashboard_sub = dashboard_sub or {}
        expiring_soon = int(dashboard_sub.get("in_five_days", 0))
        expired_sub = int(dashboard_sub.get("expired", 0))

        # Output payload
        return {
            "collection": {
                "today": today_collection,
                "yesterday": yesterday_collection,
                "this_month": this_month_collection,
                "dues": total_dues,
                "wallet_amount": wallet_amount,
                "recent": recent_collections
            },
            "customer": {
                "total": total_cust if total_cust > 0 else (active_cust + inactive_cust),
                "active": active_cust,
                "inactive": inactive_cust,
                "suspended": suspended_cust,
                "archived": archived_cust
            },
            "complaints": {
                "total": total_complaints,
                "open": open_complaints,
                "in_progress": in_progress_complaints,
                "resolved": closed_complaints
            },
            "subscription": {
                "expired": expired_sub,
                "expiring_soon": expiring_soon,
                "popular_packages": popular_packages[:5]  # Top 5
            }
        }

    async def generate_business_insights(self, metrics: Dict[str, Any]) -> str:
        """Call the LLM to generate qualitative business insights based on the calculated KPIs."""
        if not self.llm:
            return "Analytics engine is active, but LLM is offline. Review the computed KPIs below."

        import os
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "prompts" / "analyst_prompt.txt"
        
        if prompt_path.exists():
            analyst_prompt_template = prompt_path.read_text(encoding="utf-8")
        else:
            analyst_prompt_template = (
                "You are a cable TV business analyst.\n"
                "Analyze the provided KPI metrics:\n"
                "{metrics}\n"
                "Provide:\n"
                "1. Summary\n"
                "2. Insights\n"
                "3. Concerns\n"
                "4. Recommendations\n"
            )

        import json
        formatted_metrics = json.dumps(metrics, indent=2)
        prompt = analyst_prompt_template.replace("{metrics}", formatted_metrics)
        
        system_instruction = "You are a professional Business Intelligence analyst for BillerQ, a cable TV and subscription billing company. Be concise, direct, and highlight actionable financial metrics."
        
        try:
            insights = await self.llm.generate(
                prompt=prompt,
                system=system_instruction,
                temperature=0.3
            )
            return insights.strip()
        except Exception as e:
            logger.error("Failed to generate business insights: %s", str(e))
            return "Failed to compile AI business analyst insights. Please check raw metrics below."
