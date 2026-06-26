from datetime import timedelta
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.core.time_utils import utcnow_naive
from app.modules.group_cart.model import (
    Group,
    GroupCartItem,
    GroupMember,
    GroupMemberRole,
    GroupPaymentSplit,
    GroupSlotLock,
    GroupStatus,
    PaymentSplitType,
)
from app.modules.menu.model import MenuItem
from app.modules.orders.item_schemas import OrderItemCreate
from app.modules.orders.item_service import add_items_to_order
from app.modules.orders.model import Order, OrderStatus
from app.modules.notifications.service import notify_user
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User


class GroupCartService:
    def __init__(self, db: Session):
        self.db = db

    def _notify_group(
        self,
        group_id: int,
        title: str,
        message: str,
        exclude_user_ids: Optional[set[int]] = None,
    ) -> None:
        member_rows = self.db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
        if not member_rows:
            return

        excluded = exclude_user_ids or set()
        member_ids = [member_row.user_id for member_row in member_rows if member_row.user_id not in excluded]
        if not member_ids:
            return

        users = self.db.query(User).filter(User.id.in_(member_ids)).all()
        users_by_id = {user.id: user for user in users}

        for member_id in member_ids:
            user = users_by_id.get(member_id)
            if not user:
                continue
            notify_user(
                user_id=user.id,
                phone=user.phone,
                title=title,
                message=message,
                db=self.db,
                send_sms_flag=False,
            )

    def create_group(self, name: str, owner_id: int) -> Group:
        """Create a new group cart"""
        group = Group(
            name=name,
            owner_id=owner_id
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)

        # Add owner as first member
        owner_member = GroupMember(
            group_id=group.id,
            user_id=owner_id,
            role=GroupMemberRole.OWNER
        )
        self.db.add(owner_member)
        self.db.commit()

        return group

    def get_group(self, group_id: int, user_id: int) -> Group:
        """Get group with access check"""
        group = self.db.query(Group).options(
            joinedload(Group.members).joinedload(GroupMember.user),
            joinedload(Group.cart_items).joinedload(GroupCartItem.menu_item),
            joinedload(Group.cart_items).joinedload(GroupCartItem.owner),
            joinedload(Group.slot_lock).joinedload(GroupSlotLock.slot)
        ).filter(Group.id == group_id).first()

        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Check if user is member
        member = self.db.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        ).first()

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this group")

        return group

    def invite_member(self, group_id: int, inviter_id: int, invitee_phone: str) -> GroupMember:
        """Invite a user to join the group"""
        # Check if inviter is owner or member
        inviter_member = self.db.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == inviter_id)
        ).first()

        if not inviter_member:
            raise HTTPException(status_code=403, detail="Not authorized to invite members")

        # Find user by phone
        invitee = self.db.query(User).filter(User.phone == invitee_phone).first()
        if not invitee:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already a member
        existing_member = self.db.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == invitee.id)
        ).first()

        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a member")

        # Add as member
        member = GroupMember(
            group_id=group_id,
            user_id=invitee.id,
            role=GroupMemberRole.MEMBER
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)

        inviter = self.db.query(User).filter(User.id == inviter_id).first()
        invitee_name = invitee.name or invitee.phone
        inviter_name = inviter.name if inviter else "A group member"

        self._notify_group(
            group_id=group_id,
            title="Group Updated",
            message=f"{invitee_name} joined the group cart.",
        )
        self._notify_group(
            group_id=group_id,
            title="Group Invite Accepted",
            message=f"You were added to the group cart by {inviter_name}.",
            exclude_user_ids={inviter_id},
        )

        self.db.commit()

        return member

    def add_cart_item(self, group_id: int, user_id: int, menu_item_id: int, quantity: int) -> GroupCartItem:
        """Add item to group cart"""
        # Verify user is member
        member = self.db.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        ).first()

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this group")

        # Get menu item and current price
        menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        # Check if item already exists in cart
        existing_item = self.db.query(GroupCartItem).filter(
            and_(
                GroupCartItem.group_id == group_id,
                GroupCartItem.menu_item_id == menu_item_id,
                GroupCartItem.owner_id == user_id
            )
        ).first()

        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
            self.db.commit()
            self.db.refresh(existing_item)
            self._notify_group(
                group_id=group_id,
                title="Group Cart Updated",
                message=f"{member.user.name} updated {menu_item.name} quantity to {existing_item.quantity}.",
            )
            self.db.commit()
            return existing_item
        else:
            # Add new item
            cart_item = GroupCartItem(
                group_id=group_id,
                menu_item_id=menu_item_id,
                owner_id=user_id,
                quantity=quantity,
                price_at_time=menu_item.price
            )
            self.db.add(cart_item)
            self.db.commit()
            self.db.refresh(cart_item)
            self._notify_group(
                group_id=group_id,
                title="Group Cart Updated",
                message=f"{member.user.name} added {quantity} x {menu_item.name} to the group cart.",
            )
            self.db.commit()
            return cart_item

    def lock_slot(self, group_id: int, user_id: int, slot_id: int, duration_minutes: int = 30) -> GroupSlotLock:
        """Lock a slot for the group"""
        # Verify user is member
        member = self.db.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        ).first()

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this group")

        # Check if slot is available
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        # Check for existing locks
        existing_lock = self.db.query(GroupSlotLock).filter(
            and_(
                GroupSlotLock.slot_id == slot_id,
                GroupSlotLock.expires_at > utcnow_naive()
            )
        ).first()

        if existing_lock and existing_lock.group_id != group_id:
            raise HTTPException(status_code=409, detail="Slot is locked by another group")

        # Create or update lock
        lock = self.db.query(GroupSlotLock).filter(GroupSlotLock.group_id == group_id).first()

        if lock:
            # Update existing lock
            lock.slot_id = slot_id
            lock.locked_by_id = user_id
            lock.locked_at = utcnow_naive()
            lock.expires_at = utcnow_naive() + timedelta(minutes=duration_minutes)
        else:
            # Create new lock
            lock = GroupSlotLock(
                group_id=group_id,
                slot_id=slot_id,
                locked_by_id=user_id,
                expires_at=utcnow_naive() + timedelta(minutes=duration_minutes)
            )
            self.db.add(lock)

        self.db.commit()
        self.db.refresh(lock)

        self._notify_group(
            group_id=group_id,
            title="Pickup Slot Locked",
            message=(
                f"{member.user.name} locked a pickup slot from "
                f"{slot.start_time.strftime('%H:%M')} to {slot.end_time.strftime('%H:%M')}."
            ),
        )
        self.db.commit()

        return lock

    def place_group_order(self, group_id: int, user_id: int) -> dict:
        """Place order for the entire group"""
        # Verify user is owner
        group = self.get_group(group_id, user_id)
        if group.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Only group owner can place order")

        if not group.cart_items:
            raise HTTPException(status_code=400, detail="Group cart is empty")

        if not group.slot_lock:
            raise HTTPException(status_code=400, detail="No slot locked for the group")

        slot = self.db.query(Slot).filter(Slot.id == group.slot_lock.slot_id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Locked slot not found")

        orders = []
        total_amount = 0

        try:
            member_totals: dict[int, int] = {}
            member_items_map: dict[int, list[GroupCartItem]] = {}

            for member in group.members:
                member_items = [item for item in group.cart_items if item.owner_id == member.user_id]
                if not member_items:
                    continue

                member_items_map[member.user_id] = member_items

                if any(item.menu_item.vendor_id != slot.vendor_id for item in member_items):
                    raise HTTPException(
                        status_code=400,
                        detail="All group cart items must belong to the locked slot vendor",
                    )

                order = Order(
                    user_id=member.user_id,
                    slot_id=slot.id,
                    vendor_id=slot.vendor_id,
                    status=OrderStatus.PENDING,
                )
                self.db.add(order)
                self.db.flush()

                order_items = [
                    OrderItemCreate(menu_item_id=item.menu_item_id, quantity=item.quantity)
                    for item in member_items
                ]

                member_total = add_items_to_order(order, order_items, self.db)
                order.total_amount = int(member_total)
                member_totals[member.user_id] = int(member_total)

                orders.append(
                    {
                        "member_id": member.user_id,
                        "order_id": order.id,
                        "amount": member_total,
                    }
                )
                total_amount += member_total

            if not orders:
                raise HTTPException(status_code=400, detail="No member items found to place order")

            payable_by_user = self._build_split_reconciliation(
                group_id=group.id,
                member_totals=member_totals,
                owner_id=group.owner_id,
            )

            for order_result in orders:
                member_id = order_result["member_id"]
                order_id = order_result["order_id"]
                payable_amount = int(payable_by_user.get(member_id, 0))

                payment_status = PaymentStatus.SUCCESS if payable_amount == 0 else PaymentStatus.INITIATED
                payment = Payment(
                    order_id=order_id,
                    amount=payable_amount,
                    status=payment_status,
                )
                self.db.add(payment)
                self.db.flush()

                order_row = self.db.query(Order).filter(Order.id == order_id).first()
                if order_row:
                    order_row.status = OrderStatus.CONFIRMED if payment_status == PaymentStatus.SUCCESS else OrderStatus.PENDING

                order_result["payment_id"] = payment.id
                order_result["payable_amount"] = payable_amount
                order_result["payment_status"] = payment.status.value

            aggregate_payment_status = "paid" if all(
                order_result["payment_status"] == PaymentStatus.SUCCESS.value for order_result in orders
            ) else "pending"

            group.status = GroupStatus.ORDERED
            self._notify_group(
                group_id=group_id,
                title="Group Order Placed",
                message=f"Group order placed successfully. Total amount: ₹{int(total_amount)}.",
            )

            users = self.db.query(User).filter(User.id.in_(payable_by_user.keys())).all()
            users_by_id = {user.id: user for user in users}
            for member_id, payable_amount in payable_by_user.items():
                user = users_by_id.get(member_id)
                if not user:
                    continue
                notify_user(
                    user_id=user.id,
                    phone=user.phone,
                    title="Payment Split Finalized",
                    message=f"Your payable amount for this group order is ₹{int(payable_amount)}.",
                    db=self.db,
                    send_sms_flag=False,
                )

            self.db.commit()
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to place group order: {str(exc)}") from exc

        return {
            "group_id": group_id,
            "orders": orders,
            "total_amount": total_amount,
            "payment_reconciliation": {
                "per_member_payable": payable_by_user,
                "aggregate_status": aggregate_payment_status,
            },
            "slot_time": {
                "start_time": group.slot_lock.slot.start_time.isoformat(),
                "end_time": group.slot_lock.slot.end_time.isoformat()
            }
        }

    def _build_split_reconciliation(self, group_id: int, member_totals: dict[int, int], owner_id: int) -> dict[int, int]:
        total_amount = sum(member_totals.values())
        member_ids = list(member_totals.keys())
        splits = self.db.query(GroupPaymentSplit).filter(GroupPaymentSplit.group_id == group_id).all()

        if not member_ids:
            return {}

        if not splits:
            return self._equal_split(member_ids, total_amount)

        split_type = splits[0].split_type

        if split_type == PaymentSplitType.EQUAL:
            return self._equal_split(member_ids, total_amount)

        if split_type == PaymentSplitType.UNIFIED:
            if owner_id not in member_ids:
                raise HTTPException(status_code=400, detail="Group owner has no items for unified split")
            return {member_id: (total_amount if member_id == owner_id else 0) for member_id in member_ids}

        if split_type == PaymentSplitType.CUSTOM:
            custom_amounts = {split.user_id: int(split.amount or 0) for split in splits if split.user_id in member_ids}
            if set(custom_amounts.keys()) != set(member_ids):
                raise HTTPException(status_code=400, detail="Custom split amounts required for all members with items")
            if sum(custom_amounts.values()) != total_amount:
                raise HTTPException(status_code=400, detail="Custom split total must match group total amount")
            return custom_amounts

        return self._equal_split(member_ids, total_amount)

    def _equal_split(self, member_ids: list[int], total_amount: int) -> dict[int, int]:
        if not member_ids:
            return {}

        base_share = total_amount // len(member_ids)
        remainder = total_amount % len(member_ids)

        result = {}
        for idx, member_id in enumerate(member_ids):
            result[member_id] = base_share + (1 if idx < remainder else 0)
        return result

    def get_payment_splits(self, group_id: int, user_id: int) -> List[GroupPaymentSplit]:
        """Get payment split configuration for the group"""
        # Verify user is member
        self.get_group(group_id, user_id)  # Access check

        splits = self.db.query(GroupPaymentSplit).filter(
            GroupPaymentSplit.group_id == group_id
        ).all()

        return splits

    def set_payment_split(self, group_id: int, user_id: int, split_type: PaymentSplitType,
                         amount: Optional[float] = None, percentage: Optional[float] = None) -> GroupPaymentSplit:
        """Set payment split for a user"""
        # Verify user is member
        self.get_group(group_id, user_id)  # Access check

        if split_type == PaymentSplitType.CUSTOM and (amount is None or amount < 0):
            raise HTTPException(status_code=400, detail="Custom split requires a non-negative amount")

        # Remove existing split
        self.db.query(GroupPaymentSplit).filter(
            and_(GroupPaymentSplit.group_id == group_id, GroupPaymentSplit.user_id == user_id)
        ).delete()

        # Create new split
        split = GroupPaymentSplit(
            group_id=group_id,
            user_id=user_id,
            split_type=split_type,
            amount=amount,
            percentage=percentage
        )

        self.db.add(split)
        self.db.commit()
        self.db.refresh(split)

        member = self.db.query(GroupMember).filter(
            and_(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        ).first()
        actor_name = member.user.name if member and member.user else "A group member"
        message = f"{actor_name} set payment split to {split_type.value}."
        if split_type == PaymentSplitType.CUSTOM and amount is not None:
            message = f"{actor_name} set custom payable amount to ₹{int(amount)}."

        self._notify_group(
            group_id=group_id,
            title="Payment Split Updated",
            message=message,
        )
        self.db.commit()

        return split
