"""
Query Processor — processes and refines datasets returned from BillerQ APIs.

Includes filtering, sorting, grouping, limiting, and aggregation.
All operations run client-side in Python to guarantee speed and efficiency.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


def parse_date(date_val: Any) -> datetime:
    """Helper to parse various date string formats into datetime objects for sorting."""
    if not date_val:
        return datetime.min
    if isinstance(date_val, datetime):
        return date_val

    date_str = str(date_val).strip().replace("\\", "")
    
    # Try common formats
    formats = [
        "%d/%m/%Y",       # 24/06/2026
        "%d-%m-%Y",       # 24-06-2026
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",       # 2026-06-24
        "%b %d, %Y",      # Jun 24, 2026
        "%d %B %Y",       # 24 June 2026
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    # Try parsing first 10 characters for YYYY-MM-DD or DD/MM/YYYY
    if len(date_str) >= 10:
        short_str = date_str[:10]
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(short_str, fmt)
            except ValueError:
                continue
                
    logger.debug("Failed to parse date string: '%s', using datetime.min", date_val)
    return datetime.min


def get_numeric_value(item: dict, fields: list[str]) -> float:
    """Extract a numeric value from a dictionary checking multiple fallback keys."""
    for field in fields:
        val = item.get(field)
        if val is not None:
            try:
                # Remove currency symbols or commas
                clean_val = str(val).replace("₹", "").replace(",", "").strip()
                return float(clean_val)
            except ValueError:
                continue
    return 0.0


class QueryProcessor:
    """Processes, filters, sorts, limits, groups, and aggregates datasets."""

    def process(
        self,
        dataset: list[dict],
        filters: Optional[dict] = None,
        sort: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Apply filters, sorting, and limits to a dataset in one pipeline.

        Args:
            dataset: List of raw record dictionaries.
            filters: Dictionary of filters to apply.
            sort: Sorting parameters (e.g. {"field": "join_date", "order": "desc"}).
            limit: Maximum number of records to return.

        Returns:
            The processed list of records.
        """
        result = list(dataset)
        
        if filters:
            result = self.apply_filters(result, filters)
            
        if sort:
            result = self.apply_sort(result, sort)
            
        if limit is not None:
            result = self.apply_limit(result, limit)
            
        return result

    def apply_filters(self, dataset: list[dict], filters: dict) -> list[dict]:
        """Apply filters to a dataset.

        Supported filters:
            - status: active / inactive / suspended / etc.
            - area_name: Upper-case area name (substring match)
            - customer_type: general / corporate / etc.
            - pending_due: True (checks if due_amount/balance > 0)
            - subscription_status: active / expired
            - complaint_status: open / resolved / pending
        """
        filtered = []
        
        for item in dataset:
            match = True
            
            # 1. Filter by Status
            status_filter = filters.get("status")
            if status_filter:
                item_status = item.get("status", item.get("customer_status", ""))
                if str(status_filter).lower() != str(item_status).lower():
                    match = False

            # 2. Filter by Area Name
            area_filter = filters.get("area_name")
            if area_filter and match:
                item_area = item.get("area_name", item.get("area", ""))
                if str(area_filter).lower() not in str(item_area).lower():
                    match = False

            # 3. Filter by Customer Type
            type_filter = filters.get("customer_type")
            if type_filter and match:
                item_type = item.get("customer_type", item.get("type", ""))
                if str(type_filter).lower() != str(item_type).lower():
                    match = False

            # 4. Filter by Pending Due (due_amount > 0 or balance > 0)
            pending_due_filter = filters.get("pending_due")
            if pending_due_filter is not None and match:
                due_val = get_numeric_value(item, ["due_amount", "due", "balance", "total_due", "pending_amount"])
                has_due = due_val > 0
                if bool(pending_due_filter) != has_due:
                    match = False

            # 5. Filter by Subscription Status
            sub_status_filter = filters.get("subscription_status")
            if sub_status_filter and match:
                item_sub_status = item.get("subscription_status", item.get("sub_status", ""))
                if str(sub_status_filter).lower() != str(item_sub_status).lower():
                    match = False

            # 6. Filter by Complaint Status
            complaint_status_filter = filters.get("complaint_status")
            if complaint_status_filter and match:
                item_comp_status = item.get("status", item.get("complaint_status", ""))
                if str(complaint_status_filter).lower() != str(item_comp_status).lower():
                    match = False

            if match:
                filtered.append(item)
                
        logger.debug("Filtered dataset from %d to %d records", len(dataset), len(filtered))
        return filtered

    def apply_sort(self, dataset: list[dict], sort: dict) -> list[dict]:
        """Sort the dataset based on field and order.

        Supported sorting:
            - join_date: sorts by join_date/created_at
            - name: alphabetical by customer/payment name
            - due_amount: sorts by due_amount/balance numeric value
            - payment_date: sorts by payment date/payment_date/created_at
        """
        field = sort.get("field")
        if not field:
            return dataset
        order = sort.get("order")
        if not order:
            order = "asc"
        order = str(order).lower()
        reverse = (order == "desc")

        def sort_key(item: dict) -> Any:
            if field == "join_date":
                val = item.get("join_date", item.get("created_at", item.get("join", "")))
                return parse_date(val)
                
            elif field == "payment_date":
                val = item.get("payment_date", item.get("date", item.get("created_at", "")))
                return parse_date(val)
                
            elif field == "due_amount":
                return get_numeric_value(item, ["due_amount", "due", "balance", "total_due"])
                
            elif field == "name":
                return str(item.get("name", item.get("customer_name", ""))).lower()
                
            # Default sorting key
            return str(item.get(field, "")).lower()

        try:
            sorted_dataset = sorted(dataset, key=sort_key, reverse=reverse)
            logger.debug("Sorted dataset by %s (%s)", field, order)
            return sorted_dataset
        except Exception as e:
            logger.error("Sorting dataset failed for field '%s': %s", field, str(e))
            return dataset

    def apply_limit(self, dataset: list[dict], limit: int) -> list[dict]:
        """Limit the dataset to N records."""
        result = dataset[:limit]
        logger.debug("Limited dataset from %d to %d records", len(dataset), len(result))
        return result

    def apply_grouping(self, dataset: list[dict], group_by: str) -> dict[str, list[dict]]:
        """Group a dataset by a specific key.

        Example:
            grouping by "area_name" returns {"DEMO": [records], "APPOLO": [records]}
        """
        grouped = {}
        for item in dataset:
            val = str(item.get(group_by, "Unknown")).strip()
            if val not in grouped:
                grouped[val] = []
            grouped[val].append(item)
        return grouped

    def aggregate(self, dataset: list[dict], field: str, operation: str) -> float:
        """Perform numeric aggregation (sum, avg, min, max, count) on a dataset field."""
        if not dataset:
            return 0.0

        vals = []
        for item in dataset:
            val = item.get(field)
            if val is not None:
                try:
                    vals.append(float(str(val).replace("₹", "").replace(",", "").strip()))
                except ValueError:
                    continue

        if not vals:
            return 0.0

        operation = operation.lower()
        if operation == "sum":
            return sum(vals)
        elif operation == "avg" or operation == "mean":
            return sum(vals) / len(vals)
        elif operation == "min":
            return min(vals)
        elif operation == "max":
            return max(vals)
        elif operation == "count":
            return float(len(vals))
            
        return 0.0


# Singleton instance
query_processor = QueryProcessor()
