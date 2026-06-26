import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, extract, cast, Date as SADate, Integer, case, text
from sqlalchemy.orm import Session

from app.core.redis_cache import cache_service
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.users.model import User, UserRole
from app.modules.rewards.model import RewardRedemption, VoucherRedemption
from app.modules.slots.model import Slot, SlotBooking
from app.modules.feedback.model import Feedback, VendorReview

logger = logging.getLogger("tnt.admin.kpi_service")


class KPIService:
    """Service to compute high-performance Institutional KPIs using database aggregations."""

    def __init__(self, db: Session):
        self.db = db

    def _parse_dates(self, date_from: Optional[str], date_to: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse dates into start-of-day and end-of-day datetime objects."""
        date_from_dt = None
        date_to_dt = None

        if date_from:
            try:
                if "T" not in date_from:
                    date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                else:
                    date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                logger.warning("Invalid date_from format: %s", date_from)

        if date_to:
            try:
                if "T" not in date_to:
                    date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    )
                else:
                    date_to_dt = datetime.fromisoformat(date_to)
            except ValueError:
                logger.warning("Invalid date_to format: %s", date_to)

        return date_from_dt, date_to_dt

    def _apply_order_filters(
        self, query, date_from_dt: Optional[datetime], date_to_dt: Optional[datetime],
        department: Optional[str], vendor_id: Optional[int]
    ):
        """Apply date, department, and vendor filters to an Order query."""
        if date_from_dt:
            query = query.filter(Order.created_at >= date_from_dt)
        if date_to_dt:
            query = query.filter(Order.created_at <= date_to_dt)
        if vendor_id:
            query = query.filter(Order.vendor_id == vendor_id)
        if department:
            query = query.join(User, Order.user_id == User.id).filter(User.department == department)
        return query

    def get_aggregated_kpis(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        department: Optional[str] = None,
        vendor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch and aggregate all KPI metrics."""
        # 1. Date defaults (last 30 days if not set)
        if not date_from and not date_to:
            now = utcnow_naive()
            date_from = (now - timedelta(days=30)).date().isoformat()
            date_to = now.date().isoformat()

        # Parse filters
        date_from_dt, date_to_dt = self._parse_dates(date_from, date_to)

        # ── UNIVERSITY KPIs ───────────────────────────────────────────────────
        # Food vs Stationery counts
        food_query = self.db.query(func.count(Order.id)).filter(Order.booking_type == "food")
        food_query = self._apply_order_filters(food_query, date_from_dt, date_to_dt, department, vendor_id)
        food_orders = food_query.scalar() or 0

        stat_query = self.db.query(func.count(Order.id)).filter(Order.booking_type == "stationery")
        stat_query = self._apply_order_filters(stat_query, date_from_dt, date_to_dt, department, vendor_id)
        stationery_orders = stat_query.scalar() or 0

        # Check database dialect (SQLite vs PostgreSQL)
        is_sqlite = self.db.bind.dialect.name == "sqlite"

        # Daily Trend
        if is_sqlite:
            day_field = func.strftime("%Y-%m-%d", Order.created_at).label("day")
            daily_query = self.db.query(day_field, func.count(Order.id).label("count"))
            daily_query = self._apply_order_filters(daily_query, date_from_dt, date_to_dt, department, vendor_id)
            daily_rows = daily_query.group_by(day_field).order_by(day_field).all()
            daily_orders = [{"date": str(r[0]), "count": r[1]} for r in daily_rows]
        else:
            daily_query = self.db.query(
                cast(Order.created_at, SADate).label("day"),
                func.count(Order.id).label("count")
            )
            daily_query = self._apply_order_filters(daily_query, date_from_dt, date_to_dt, department, vendor_id)
            daily_rows = daily_query.group_by(cast(Order.created_at, SADate)).order_by(cast(Order.created_at, SADate)).all()
            daily_orders = [{"date": str(r.day), "count": r.count} for r in daily_rows]

        # Weekly Trend
        if is_sqlite:
            week_field = func.strftime("%Y-W%W", Order.created_at).label("week")
            weekly_query = self.db.query(week_field, func.count(Order.id).label("count"))
            weekly_query = self._apply_order_filters(weekly_query, date_from_dt, date_to_dt, department, vendor_id)
            weekly_rows = weekly_query.group_by(week_field).order_by(week_field).all()
            weekly_orders = [{"date": str(r[0]), "count": r[1]} for r in weekly_rows]
        else:
            weekly_query = self.db.query(
                func.date_trunc(text("'week'"), Order.created_at).label("week"),
                func.count(Order.id).label("count")
            )
            weekly_query = self._apply_order_filters(weekly_query, date_from_dt, date_to_dt, department, vendor_id)
            weekly_rows = weekly_query.group_by(func.date_trunc(text("'week'"), Order.created_at)).order_by(func.date_trunc(text("'week'"), Order.created_at)).all()
            weekly_orders = [{"date": str(r.week.date() if hasattr(r.week, 'date') else r.week), "count": r.count} for r in weekly_rows]

        # Monthly Trend
        if is_sqlite:
            month_field = func.strftime("%Y-%m", Order.created_at).label("month")
            monthly_query = self.db.query(month_field, func.count(Order.id).label("count"))
            monthly_query = self._apply_order_filters(monthly_query, date_from_dt, date_to_dt, department, vendor_id)
            monthly_rows = monthly_query.group_by(month_field).order_by(month_field).all()
            monthly_orders = [{"date": str(r[0]), "count": r[1]} for r in monthly_rows]
        else:
            monthly_query = self.db.query(
                func.date_trunc(text("'month'"), Order.created_at).label("month"),
                func.count(Order.id).label("count")
            )
            monthly_query = self._apply_order_filters(monthly_query, date_from_dt, date_to_dt, department, vendor_id)
            monthly_rows = monthly_query.group_by(func.date_trunc(text("'month'"), Order.created_at)).order_by(func.date_trunc(text("'month'"), Order.created_at)).all()
            monthly_orders = [{"date": str(r.month.date() if hasattr(r.month, 'date') else r.month), "count": r.count} for r in monthly_rows]

        total_orders = food_orders + stationery_orders

        # ── OPERATIONAL KPIs ──────────────────────────────────────────────────
        # Avg Waiting Time (actual completion time)
        wait_query = self.db.query(func.avg(Order.actual_completion_minutes)).filter(Order.actual_completion_minutes.isnot(None))
        wait_query = self._apply_order_filters(wait_query, date_from_dt, date_to_dt, department, vendor_id)
        avg_wait = wait_query.scalar()
        avg_waiting_time = round(float(avg_wait), 1) if avg_wait else 0.0

        # Queue Reduction %: percentage of non-cancelled orders that are prepared or picked
        all_non_cancelled_query = self.db.query(func.count(Order.id)).filter(Order.status != OrderStatus.CANCELLED)
        all_non_cancelled_query = self._apply_order_filters(all_non_cancelled_query, date_from_dt, date_to_dt, department, vendor_id)
        total_active_orders = all_non_cancelled_query.scalar() or 0

        cleared_query = self.db.query(func.count(Order.id)).filter(Order.status.in_([OrderStatus.READY, OrderStatus.PICKED, OrderStatus.COMPLETED]))
        cleared_query = self._apply_order_filters(cleared_query, date_from_dt, date_to_dt, department, vendor_id)
        cleared_orders = cleared_query.scalar() or 0
        queue_reduction_pct = round((cleared_orders / total_active_orders) * 100, 1) if total_active_orders > 0 else 100.0

        # Avg Pickup Time (duration from order ready/created to picked, in minutes)
        if is_sqlite:
            pickup_query = self.db.query(
                func.avg((func.julianday(Order.pickup_confirmed_at) - func.julianday(Order.created_at)) * 1440)
            ).filter(Order.pickup_confirmed_at.isnot(None))
            pickup_query = self._apply_order_filters(pickup_query, date_from_dt, date_to_dt, department, vendor_id)
            avg_pickup = pickup_query.scalar()
            avg_pickup_time = round(float(avg_pickup), 1) if avg_pickup else 0.0
        else:
            pickup_query = self.db.query(
                func.avg(extract("epoch", Order.pickup_confirmed_at - Order.created_at) / 60)
            ).filter(Order.pickup_confirmed_at.isnot(None))
            pickup_query = self._apply_order_filters(pickup_query, date_from_dt, date_to_dt, department, vendor_id)
            avg_pickup = pickup_query.scalar()
            avg_pickup_time = round(float(avg_pickup), 1) if avg_pickup else 0.0

        # Slot Utilization
        slot_query = self.db.query(func.sum(Slot.current_orders), func.sum(Slot.max_orders))
        if vendor_id:
            slot_query = slot_query.filter(Slot.vendor_id == vendor_id)
        if date_from_dt:
            slot_query = slot_query.filter(Slot.start_time >= date_from_dt)
        if date_to_dt:
            slot_query = slot_query.filter(Slot.start_time <= date_to_dt)
        slot_res = slot_query.first()
        current_slots_sum = slot_res[0] or 0
        max_slots_sum = slot_res[1] or 0
        slot_utilization = round((current_slots_sum / max_slots_sum) * 100, 1) if max_slots_sum > 0 else 0.0

        # Vendor Performance list (Optimized to prevent N+1 query loop)
        from sqlalchemy import case

        # Aggregate stats for all vendors in a single query
        vendor_stats_query = self.db.query(
            Order.vendor_id,
            func.count(Order.id).label("orders_count"),
            func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)).label("cancelled_count"),
            func.avg(Order.actual_completion_minutes).label("avg_wait")
        ).group_by(Order.vendor_id)
        vendor_stats_query = self._apply_order_filters(vendor_stats_query, date_from_dt, date_to_dt, department, None)
        vendor_stats_res = vendor_stats_query.all()

        stats_map = {
            r.vendor_id: {
                "orders_count": r.orders_count,
                "cancelled_count": int(r.cancelled_count or 0),
                "avg_wait": r.avg_wait
            }
            for r in vendor_stats_res
        }

        # Aggregate feedback overall ratings for all vendors in a single query
        ratings_query = self.db.query(
            Feedback.vendor_id,
            func.avg(Feedback.overall_rating).label("avg_rating")
        ).group_by(Feedback.vendor_id)
        if date_from_dt:
            ratings_query = ratings_query.filter(Feedback.created_at >= date_from_dt)
        if date_to_dt:
            ratings_query = ratings_query.filter(Feedback.created_at <= date_to_dt)
        ratings_res = ratings_query.all()
        ratings_map = {r.vendor_id: r.avg_rating for r in ratings_res}

        vendor_perf = []
        vendors = self.db.query(User).filter(User.role == UserRole.VENDOR).all()
        for v in vendors:
            v_stats = stats_map.get(v.id, {"orders_count": 0, "cancelled_count": 0, "avg_wait": None})
            v_orders = v_stats["orders_count"]

            if v_orders == 0 and vendor_id and vendor_id != v.id:
                continue

            v_cancelled = v_stats["cancelled_count"]
            v_comp_rate = round(((v_orders - v_cancelled) / v_orders) * 100, 1) if v_orders > 0 else 100.0
            v_wait = v_stats["avg_wait"]
            avg_rating = ratings_map.get(v.id, 5.0) or 5.0

            vendor_perf.append({
                "vendor_id": v.id,
                "vendor_name": v.name or v.full_name or f"Vendor #{v.id}",
                "orders_count": v_orders,
                "completion_rate": v_comp_rate,
                "avg_wait_minutes": round(float(v_wait), 1) if v_wait else 12.0,
                "rating": round(float(avg_rating), 1),
            })

        # Calculate a weighted Vendor Ranking Score
        max_orders_val = max((x["orders_count"] for x in vendor_perf), default=1) or 1
        for vp in vendor_perf:
            rating_score = vp["rating"] * 20.0
            volume_score = (vp["orders_count"] / max_orders_val) * 100.0
            vp["score"] = round(rating_score * 0.4 + vp["completion_rate"] * 0.3 + volume_score * 0.3, 1)

        # Sort performance list by rank score desc (Vendor Ranking)
        vendor_perf.sort(key=lambda x: x["score"], reverse=True)

        # ── BUSINESS KPIs ────────────────────────────────────────────────────
        # Revenue (successful payment sums in paise, returned in INR)
        rev_query = self.db.query(func.sum(Payment.amount)).join(Order, Payment.order_id == Order.id).filter(Payment.status == PaymentStatus.SUCCESS)
        rev_query = self._apply_order_filters(rev_query, date_from_dt, date_to_dt, department, vendor_id)
        revenue_paise = rev_query.scalar() or 0
        revenue = float(revenue_paise) / 100.0

        # Refunds
        ref_query = self.db.query(func.sum(Payment.amount)).join(Order, Payment.order_id == Order.id).filter(Payment.status == PaymentStatus.REFUNDED)
        ref_query = self._apply_order_filters(ref_query, date_from_dt, date_to_dt, department, vendor_id)
        refunds_paise = ref_query.scalar() or 0
        refunds = float(refunds_paise) / 100.0

        # Cancellation Rate
        canc_query = self.db.query(func.count(Order.id)).filter(Order.status == OrderStatus.CANCELLED)
        canc_query = self._apply_order_filters(canc_query, date_from_dt, date_to_dt, department, vendor_id)
        cancelled_orders_count = canc_query.scalar() or 0
        cancellation_rate = round((cancelled_orders_count / total_orders) * 100, 1) if total_orders > 0 else 0.0

        # User Growth
        user_growth_query = self.db.query(func.count(User.id)).filter(User.role != UserRole.VENDOR)
        if date_from_dt:
            user_growth_query = user_growth_query.filter(User.created_at >= date_from_dt)
        if date_to_dt:
            user_growth_query = user_growth_query.filter(User.created_at <= date_to_dt)
        if department:
            user_growth_query = user_growth_query.filter(User.department == department)
        user_growth = user_growth_query.scalar() or 0

        # Vendor Growth
        vendor_growth_query = self.db.query(func.count(User.id)).filter(User.role == UserRole.VENDOR)
        if date_from_dt:
            vendor_growth_query = vendor_growth_query.filter(User.created_at >= date_from_dt)
        if date_to_dt:
            vendor_growth_query = vendor_growth_query.filter(User.created_at <= date_to_dt)
        vendor_growth = vendor_growth_query.scalar() or 0

        # ── ENGAGEMENT KPIs ───────────────────────────────────────────────────
        # Active Users
        act_query = self.db.query(func.count(func.distinct(Order.user_id)))
        act_query = self._apply_order_filters(act_query, date_from_dt, date_to_dt, department, vendor_id)
        active_users = act_query.scalar() or 0

        # Returning Users (>= 2 orders in period)
        ret_sub = self.db.query(Order.user_id).group_by(Order.user_id).having(func.count(Order.id) >= 2)
        ret_sub = self._apply_order_filters(ret_sub, date_from_dt, date_to_dt, department, vendor_id).subquery()
        returning_users = self.db.query(func.count(ret_sub.c.user_id)).scalar() or 0

        # Peak Hours (0-23)
        if is_sqlite:
            peak_query = self.db.query(
                cast(func.strftime("%H", Order.created_at), Integer).label("hour"),
                func.count(Order.id).label("count")
            )
            peak_query = self._apply_order_filters(peak_query, date_from_dt, date_to_dt, department, vendor_id)
            peak_rows = peak_query.group_by(func.strftime("%H", Order.created_at)).order_by(func.strftime("%H", Order.created_at)).all()
        else:
            peak_query = self.db.query(
                extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("count")
            )
            peak_query = self._apply_order_filters(peak_query, date_from_dt, date_to_dt, department, vendor_id)
            peak_rows = peak_query.group_by(extract("hour", Order.created_at)).order_by(extract("hour", Order.created_at)).all()
        
        peak_hours = {int(r.hour or 0): r.count for r in peak_rows}
        # fill in missing hours
        for h in range(24):
            if h not in peak_hours:
                peak_hours[h] = 0

        # Day of week vs Hour of day (for Heatmap)
        if is_sqlite:
            heatmap_query = self.db.query(
                cast(func.strftime("%w", Order.created_at), Integer).label("dow"),
                cast(func.strftime("%H", Order.created_at), Integer).label("hour"),
                func.count(Order.id).label("count")
            )
            heatmap_query = self._apply_order_filters(heatmap_query, date_from_dt, date_to_dt, department, vendor_id)
            heatmap_rows = heatmap_query.group_by(
                func.strftime("%w", Order.created_at),
                func.strftime("%H", Order.created_at)
            ).all()
        else:
            heatmap_query = self.db.query(
                extract("dow", Order.created_at).label("dow"),
                extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("count")
            )
            heatmap_query = self._apply_order_filters(heatmap_query, date_from_dt, date_to_dt, department, vendor_id)
            heatmap_rows = heatmap_query.group_by(
                extract("dow", Order.created_at),
                extract("hour", Order.created_at)
            ).all()

        heatmap_data = {}
        for r in heatmap_rows:
            dow = int(r.dow or 0)
            hour = int(r.hour or 0)
            if dow not in heatmap_data:
                heatmap_data[dow] = {}
            heatmap_data[dow][hour] = r.count

        # Rewards Usage (points redeemed and voucher redemptions count)
        voucher_redeemed_q = self.db.query(func.count(VoucherRedemption.id)).join(Order, VoucherRedemption.order_id == Order.id)
        voucher_redeemed_q = self._apply_order_filters(voucher_redeemed_q, date_from_dt, date_to_dt, department, vendor_id)
        vouchers_redeemed_count = voucher_redeemed_q.scalar() or 0

        points_redeemed_q = self.db.query(func.sum(RewardRedemption.points_used)).join(Order, RewardRedemption.order_id == Order.id)
        points_redeemed_q = self._apply_order_filters(points_redeemed_q, date_from_dt, date_to_dt, department, vendor_id)
        points_redeemed = points_redeemed_q.scalar() or 0.0

        # ── DEPARTMENT ANALYTICS (Optimized into a single query)
        from sqlalchemy import case, and_
        dept_q = self.db.query(
            User.department,
            func.count(Order.id).label("order_count"),
            func.count(func.distinct(Order.user_id)).label("active_users"),
            func.coalesce(func.sum(case((Payment.status == PaymentStatus.SUCCESS, Payment.amount), else_=0)), 0).label("revenue_paise")
        ).join(Order, User.id == Order.user_id)\
         .outerjoin(Payment, Order.id == Payment.order_id)
        dept_q = self._apply_order_filters(dept_q, date_from_dt, date_to_dt, None, vendor_id)
        dept_res = dept_q.group_by(User.department).all()

        department_analytics = [
            {
                "department": r.department or "Other/Unknown",
                "order_count": r.order_count,
                "active_users": r.active_users,
                "revenue_inr": float(r.revenue_paise) / 100.0
            }
            for r in dept_res
        ]

        # ── FOOD, STATIONERY & REVENUE TRENDS (Optimized into a single combined query)
        if is_sqlite:
            day_field = func.strftime("%Y-%m-%d", Order.created_at).label("day")
        else:
            day_field = cast(Order.created_at, SADate).label("day")

        combined_trend_q = self.db.query(
            day_field,
            func.sum(case((and_(Order.booking_type == "food", Payment.status == PaymentStatus.SUCCESS), 1), else_=0)).label("food_orders"),
            func.sum(case((and_(Order.booking_type == "food", Payment.status == PaymentStatus.SUCCESS), Payment.amount), else_=0)).label("food_revenue_paise"),
            func.sum(case((and_(Order.booking_type == "stationery", Payment.status == PaymentStatus.SUCCESS), 1), else_=0)).label("stat_orders"),
            func.sum(case((and_(Order.booking_type == "stationery", Payment.status == PaymentStatus.SUCCESS), Payment.amount), else_=0)).label("stat_revenue_paise"),
            func.sum(case((Payment.status == PaymentStatus.SUCCESS, Payment.amount), else_=0)).label("total_revenue_paise")
        ).outerjoin(Payment, Order.id == Payment.order_id)
        
        combined_trend_q = self._apply_order_filters(combined_trend_q, date_from_dt, date_to_dt, department, vendor_id)
        
        if is_sqlite:
            combined_trend_rows = combined_trend_q.group_by(func.strftime("%Y-%m-%d", Order.created_at)).order_by(day_field).all()
        else:
            combined_trend_rows = combined_trend_q.group_by(cast(Order.created_at, SADate)).order_by(day_field).all()

        food_trends = []
        stationery_trends = []
        revenue_trends = []
        for r in combined_trend_rows:
            day_str = str(r[0])
            food_trends.append({
                "date": day_str,
                "orders": int(r.food_orders or 0),
                "revenue_inr": float(r.food_revenue_paise or 0) / 100.0
            })
            stationery_trends.append({
                "date": day_str,
                "orders": int(r.stat_orders or 0),
                "revenue_inr": float(r.stat_revenue_paise or 0) / 100.0
            })
            revenue_trends.append({
                "date": day_str,
                "revenue_inr": float(r.total_revenue_paise or 0) / 100.0
            })

        # ── PEAK HOUR ANALYSIS ────────────────────────────────────────────────
        if is_sqlite:
            hour_field = cast(func.strftime("%H", Order.created_at), Integer).label("hour")
            peak_analysis_q = self.db.query(
                hour_field,
                func.sum(case((Order.booking_type == "food", 1), else_=0)).label("food_count"),
                func.sum(case((Order.booking_type == "stationery", 1), else_=0)).label("stat_count")
            )
            peak_analysis_q = self._apply_order_filters(peak_analysis_q, date_from_dt, date_to_dt, department, vendor_id)
            peak_analysis_rows = peak_analysis_q.group_by(func.strftime("%H", Order.created_at)).order_by(hour_field).all()
        else:
            hour_field = extract("hour", Order.created_at).label("hour")
            peak_analysis_q = self.db.query(
                hour_field,
                func.sum(case((Order.booking_type == "food", 1), else_=0)).label("food_count"),
                func.sum(case((Order.booking_type == "stationery", 1), else_=0)).label("stat_count")
            )
            peak_analysis_q = self._apply_order_filters(peak_analysis_q, date_from_dt, date_to_dt, department, vendor_id)
            peak_analysis_rows = peak_analysis_q.group_by(extract("hour", Order.created_at)).order_by(hour_field).all()

        peak_hour_analysis = {int(r.hour or 0): {"food_orders": int(r.food_count or 0), "stationery_orders": int(r.stat_count or 0)} for r in peak_analysis_rows}
        for h in range(24):
            if h not in peak_hour_analysis:
                peak_hour_analysis[h] = {"food_orders": 0, "stationery_orders": 0}
        peak_hour_analysis_list = [{"hour": h, "food_orders": peak_hour_analysis[h]["food_orders"], "stationery_orders": peak_hour_analysis[h]["stationery_orders"]} for h in range(24)]

        # ── SLOT USAGE ANALYSIS ───────────────────────────────────────────────
        if is_sqlite:
            slot_hour = cast(func.strftime("%H", Slot.start_time), Integer).label("hour")
            slot_usage_q = self.db.query(
                slot_hour,
                func.sum(Slot.current_orders).label("booked"),
                func.sum(Slot.max_orders).label("capacity")
            )
            if vendor_id:
                slot_usage_q = slot_usage_q.filter(Slot.vendor_id == vendor_id)
            if date_from_dt:
                slot_usage_q = slot_usage_q.filter(Slot.start_time >= date_from_dt)
            if date_to_dt:
                slot_usage_q = slot_usage_q.filter(Slot.start_time <= date_to_dt)
            slot_usage_rows = slot_usage_q.group_by(func.strftime("%H", Slot.start_time)).order_by(slot_hour).all()
        else:
            slot_hour = extract("hour", Slot.start_time).label("hour")
            slot_usage_q = self.db.query(
                slot_hour,
                func.sum(Slot.current_orders).label("booked"),
                func.sum(Slot.max_orders).label("capacity")
            )
            if vendor_id:
                slot_usage_q = slot_usage_q.filter(Slot.vendor_id == vendor_id)
            if date_from_dt:
                slot_usage_q = slot_usage_q.filter(Slot.start_time >= date_from_dt)
            if date_to_dt:
                slot_usage_q = slot_usage_q.filter(Slot.start_time <= date_to_dt)
            slot_usage_rows = slot_usage_q.group_by(extract("hour", Slot.start_time)).order_by(slot_hour).all()

        slot_usage_analysis = []
        for r in slot_usage_rows:
            h = int(r.hour or 0)
            booked = int(r.booked or 0)
            capacity = int(r.capacity or 0)
            utilization_pct = round((booked / capacity) * 100, 1) if capacity > 0 else 0.0
            slot_usage_analysis.append({
                "hour": h,
                "booked_orders": booked,
                "total_capacity": capacity,
                "utilization_pct": utilization_pct
            })

        # ── CANCELLATION TRENDS ───────────────────────────────────────────────
        if is_sqlite:
            day_field = func.strftime("%Y-%m-%d", Order.created_at).label("day")
            canc_trend_q = self.db.query(
                day_field,
                func.count(Order.id).label("total"),
                func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)).label("cancelled")
            )
            canc_trend_q = self._apply_order_filters(canc_trend_q, date_from_dt, date_to_dt, department, vendor_id)
            canc_trend_rows = canc_trend_q.group_by(day_field).order_by(day_field).all()
            cancellation_trends = [
                {
                    "date": str(r[0]),
                    "cancelled_count": int(r[2] or 0),
                    "total_count": int(r[1] or 0),
                    "cancellation_rate": round((int(r[2] or 0) / int(r[1] or 1)) * 100, 1)
                }
                for r in canc_trend_rows
            ]
        else:
            day_field = cast(Order.created_at, SADate).label("day")
            canc_trend_q = self.db.query(
                day_field,
                func.count(Order.id).label("total"),
                func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)).label("cancelled")
            )
            canc_trend_q = self._apply_order_filters(canc_trend_q, date_from_dt, date_to_dt, department, vendor_id)
            canc_trend_rows = canc_trend_q.group_by(day_field).order_by(day_field).all()
            cancellation_trends = [
                {
                    "date": str(r.day),
                    "cancelled_count": int(r.cancelled or 0),
                    "total_count": int(r.total or 0),
                    "cancellation_rate": round((int(r.cancelled or 0) / int(r.total or 1)) * 100, 1)
                }
                for r in canc_trend_rows
            ]

        # ── AI INSIGHTS GENERATION ────────────────────────────────────────────
        ai_insights = []

        max_hour_orders = 0
        peak_hour = 12
        for h, count in peak_hours.items():
            if count > max_hour_orders:
                max_hour_orders = count
                peak_hour = h

        if max_hour_orders > 0:
            peak_util = slot_utilization
            if peak_util > 75:
                ai_insights.append({
                    "type": "warning",
                    "title": "Peak Hour Slot Congestion",
                    "detail": f"Rush intensity peaks at {peak_hour:02d}:00 with slot utilization at {peak_util}%.",
                    "recommendation": "Advise vendors to enable dynamic capacities or pre-pack popular combos to speed up handovers."
                })
            else:
                ai_insights.append({
                    "type": "info",
                    "title": "Peak Traffic Distribution",
                    "detail": f"Daily traffic peaks at {peak_hour:02d}:00 with {max_hour_orders} concurrent orders.",
                    "recommendation": "Maintain standard slot configuration; capacities are currently sufficient."
                })

        if cancellation_rate > 8.0:
            ai_insights.append({
                "type": "danger",
                "title": "Elevated Cancellation Rate",
                "detail": f"Overall cancellation rate has spiked to {cancellation_rate}%.",
                "recommendation": "Trigger operational speed audit for canteens showing preparation delays."
            })
        elif cancellation_rate > 3.0:
            ai_insights.append({
                "type": "warning",
                "title": "Moderate Order Cancellations",
                "detail": f"Order cancellation rate is at {cancellation_rate}%.",
                "recommendation": "Notify vendors to update active menu stock levels to prevent cancels due to out-of-stock items."
            })
        else:
            ai_insights.append({
                "type": "success",
                "title": "Healthy Operational Throughput",
                "detail": f"Cancellations are low ({cancellation_rate}%) and orders are completed smoothly.",
                "recommendation": "Keep standard slots configuration and maintain current vendor parameters."
            })

        if department_analytics:
            top_dept = max(department_analytics, key=lambda x: x["order_count"])
            total_orders_all = sum(x["order_count"] for x in department_analytics) or 1
            pct = round((top_dept["order_count"] / total_orders_all) * 100, 1)
            if pct > 30:
                ai_insights.append({
                    "type": "info",
                    "title": "Department Demand Surge",
                    "detail": f"The {top_dept['department']} department accounts for {pct}% of overall orders.",
                    "recommendation": "Distribute promo vouchers during off-peak hours to this department's users to balance peak canteens load."
                })

        if vendor_perf:
            top_v = vendor_perf[0]
            if top_v["orders_count"] > 0:
                ai_insights.append({
                    "type": "success",
                    "title": "Top Performing Vendor",
                    "detail": f"{top_v['vendor_name']} leads with {top_v['orders_count']} orders and a rating of {top_v['rating']}/5.",
                    "recommendation": "Feature this vendor on new admission guidelines or the app homepage."
                })

        # Construct final payload
        res_payload = {
            "filters": {
                "date_from": date_from,
                "date_to": date_to,
                "department": department,
                "vendor_id": vendor_id
            },
            "university_kpis": {
                "total_orders": total_orders,
                "food_orders": food_orders,
                "stationery_orders": stationery_orders,
                "daily_trend": daily_orders,
                "weekly_trend": weekly_orders,
                "monthly_trend": monthly_orders
            },
            "operational_kpis": {
                "avg_waiting_time_minutes": avg_waiting_time,
                "queue_reduction_pct": queue_reduction_pct,
                "avg_pickup_time_minutes": avg_pickup_time,
                "slot_utilization_pct": slot_utilization,
                "vendor_performance": vendor_perf
            },
            "business_kpis": {
                "revenue_inr": revenue,
                "refunds_inr": refunds,
                "cancellation_rate_pct": cancellation_rate,
                "user_growth_count": user_growth,
                "vendor_growth_count": vendor_growth
            },
            "engagement_kpis": {
                "active_users": active_users,
                "returning_users": returning_users,
                "peak_hours": [peak_hours[h] for h in range(24)],
                "heatmap_grid": heatmap_data,
                "vouchers_redeemed_count": vouchers_redeemed_count,
                "points_redeemed": float(points_redeemed)
            },
            "department_analytics": department_analytics,
            "food_trends": food_trends,
            "stationery_trends": stationery_trends,
            "revenue_trends": revenue_trends,
            "peak_hour_analysis": peak_hour_analysis_list,
            "slot_usage_analysis": slot_usage_analysis,
            "cancellation_trends": cancellation_trends,
            "ai_insights": ai_insights
        }

        return res_payload
