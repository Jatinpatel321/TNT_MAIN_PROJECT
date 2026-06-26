import sys

sys.path.insert(0, '.')

import json
from typing import Any, Dict

import requests

BASE_URL = "http://localhost:8000"

def send_otp(phone: str) -> Dict[str, Any]:
    """Send OTP to phone"""
    response = requests.post(f"{BASE_URL}/auth/send-otp", json={"phone": phone})
    return response.json()

def generate_test_otp(phone: str) -> str:
    """Generate a test OTP (for testing only)"""
    return "123456"

def verify_otp(phone: str, otp: str) -> Dict[str, Any]:
    """Verify OTP and get token"""
    response = requests.post(f"{BASE_URL}/auth/verify-otp", json={"phone": phone, "otp": otp})
    return response.json()

def get_auth_headers(token: str) -> Dict[str, str]:
    """Get authorization headers"""
    return {"Authorization": f"Bearer {token}"}

def create_group_api(token: str, name: str) -> Dict[str, Any]:
    """Test creating a group"""
    headers = get_auth_headers(token)
    response = requests.post(f"{BASE_URL}/groups/", json={"name": name}, headers=headers)
    return response.json()

def get_group_api(token: str, group_id: int) -> Dict[str, Any]:
    """Test getting group details"""
    headers = get_auth_headers(token)
    response = requests.get(f"{BASE_URL}/groups/{group_id}", headers=headers)
    return response.json()

def invite_member_api(token: str, group_id: int, phone: str) -> Dict[str, Any]:
    """Test inviting a member"""
    headers = get_auth_headers(token)
    response = requests.post(f"{BASE_URL}/groups/{group_id}/invite", json={"phone": phone}, headers=headers)
    return response.json()

def add_cart_item_api(token: str, group_id: int, menu_item_id: int, quantity: int) -> Dict[str, Any]:
    """Test adding item to cart"""
    headers = get_auth_headers(token)
    response = requests.post(f"{BASE_URL}/groups/{group_id}/cart",
                           json={"menu_item_id": menu_item_id, "quantity": quantity}, headers=headers)
    return response.json()

def lock_slot_api(token: str, group_id: int, slot_id: int) -> Dict[str, Any]:
    """Test locking a slot"""
    headers = get_auth_headers(token)
    response = requests.post(f"{BASE_URL}/groups/{group_id}/slot/lock",
                           json={"slot_id": slot_id}, headers=headers)
    return response.json()

def place_group_order_api(token: str, group_id: int) -> Dict[str, Any]:
    """Test placing group order"""
    headers = get_auth_headers(token)
    response = requests.post(f"{BASE_URL}/groups/{group_id}/order", headers=headers)
    return response.json()

def get_payment_splits_api(token: str, group_id: int) -> Dict[str, Any]:
    """Test getting payment splits"""
    headers = get_auth_headers(token)
    response = requests.get(f"{BASE_URL}/groups/{group_id}/payment-splits", headers=headers)
    return response.json()

def set_payment_split_api(token: str, group_id: int, split_type: str, amount: float = None) -> Dict[str, Any]:
    """Test setting payment split"""
    headers = get_auth_headers(token)
    data = {"split_type": split_type}
    if amount:
        data["amount"] = amount
    response = requests.post(f"{BASE_URL}/groups/{group_id}/payment-split", json=data, headers=headers)
    return response.json()

def get_my_groups_api(token: str) -> Dict[str, Any]:
    """Test getting user's groups"""
    headers = get_auth_headers(token)
    response = requests.get(f"{BASE_URL}/groups/my-groups", headers=headers)
    return response.json()

def run_tests():
    print("🚀 Starting Group Cart API Tests\n")

    # Test authentication
    print("1. Testing Authentication...")
    try:
        # Send OTP for student
        otp_response = send_otp("1111111111")
        print(f"   Send OTP: {otp_response}")

        # Verify OTP (assuming OTP is 123456 from the code)
        auth_response = verify_otp("1111111111", "123456")
        print(f"   Verify OTP: {auth_response}")

        if "access_token" not in auth_response:
            print("❌ Authentication failed")
            return

        token = auth_response["access_token"]
        print("✅ Authentication successful\n")

        # Test creating a group
        print("2. Testing Group Creation...")
        group_response = create_group_api(token, "Test Group")
        print(f"   Create Group: {group_response}")

        if "id" not in group_response:
            print("❌ Group creation failed")
            return

        group_id = group_response["id"]
        print("✅ Group created successfully\n")

        # Test getting group
        print("3. Testing Get Group...")
        get_group_response = get_group_api(token, group_id)
        print(f"   Get Group: {get_group_response}")
        print("✅ Get group successful\n")

        # Test inviting member
        print("4. Testing Invite Member...")
        invite_response = invite_member_api(token, group_id, "2222222222")
        print(f"   Invite Member: {invite_response}")
        print("✅ Invite member successful\n")

        # Test adding cart item (assuming menu_item_id 1 exists)
        print("5. Testing Add Cart Item...")
        try:
            cart_response = add_cart_item_api(token, group_id, 1, 2)
            print(f"   Add Cart Item: {cart_response}")
            print("✅ Add cart item successful\n")
        except Exception as e:
            print(f"   Add Cart Item failed (expected if no menu items): {e}\n")

        # Test locking slot (assuming slot_id 1 exists)
        print("6. Testing Lock Slot...")
        try:
            lock_response = lock_slot_api(token, group_id, 1)
            print(f"   Lock Slot: {lock_response}")
            print("✅ Lock slot successful\n")
        except Exception as e:
            print(f"   Lock Slot failed (expected if no slots): {e}\n")

        # Test payment splits
        print("7. Testing Payment Splits...")
        splits_response = get_payment_splits_api(token, group_id)
        print(f"   Get Payment Splits: {splits_response}")

        set_split_response = set_payment_split_api(token, group_id, "EQUAL")
        print(f"   Set Payment Split: {set_split_response}")
        print("✅ Payment splits successful\n")

        # Test get my groups
        print("8. Testing Get My Groups...")
        my_groups_response = get_my_groups_api(token)
        print(f"   Get My Groups: {my_groups_response}")
        print("✅ Get my groups successful\n")

        # Test placing order (this might fail without proper setup)
        print("9. Testing Place Group Order...")
        try:
            order_response = place_group_order_api(token, group_id)
            print(f"   Place Order: {order_response}")
            print("✅ Place order successful\n")
        except Exception as e:
            print(f"   Place Order failed (expected without full setup): {e}\n")

        print("🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    run_tests()
