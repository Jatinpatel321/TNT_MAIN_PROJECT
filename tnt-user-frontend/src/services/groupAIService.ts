import { apiClient, authHeaders } from './apiClient';

export type MemberAvailability = {
  user_id: number;
  user_name: string;
  role: string;
  availability_score: number;
  preferred_hours: number[];
  preferred_days: number[];
  conflicts: string[];
};

export type GroupAISuggestions = {
  group_id: number;
  group_name: string;
  member_count: number;
  member_availability: {
    group_id: number;
    members: MemberAvailability[];
    optimal_ordering_time: {
      suggested_hour: number;
      suggested_day: number;
      reasoning: string;
      confidence: number;
      is_peak_hour: boolean;
    };
    availability_score: number;
    conflicts: string[];
    member_count: number;
  };
  optimal_ordering_time: {
    suggested_hour: number;
    suggested_day: number;
    reasoning: string;
    confidence: number;
    is_peak_hour: boolean;
  };
  suggested_pickup_slot: {
    group_id: number;
    suggested_slot_id: number | null;
    suggested_slot_time: string | null;
    suggested_slot_score: number;
    reasoning: string[];
    confidence: number;
    alternatives: any[];
    member_availability: any;
  } | null;
  common_menu_items: {
    group_id: number;
    suggested_items: Array<{
      item_id: number;
      item_name: string;
      vendor_id: number;
      price: number;
      category: string;
      liking_members: number;
      total_members: number;
      popularity_score: number;
      image_url: string | null;
    }>;
    member_preferences: Record<number, number[]>;
    conflicts: string[];
    total_suggestions: number;
  };
  ordering_conflicts: {
    group_id: number;
    conflicts: any[];
    severity: string;
    suggestions: string[];
    total_conflicts: number;
  };
  pickup_synchronization: {
    group_id: number;
    synchronization_score: number;
    estimated_pickup_time: string;
    pickup_windows: any[];
    synchronization_plan: string;
    strategy: string;
    eta_range: number;
  };
  overall_recommendations: string[];
};

export async function getGroupAISuggestions(groupId: number): Promise<GroupAISuggestions> {
  const res = await apiClient.get(`/groups/${groupId}/ai/suggestions`, {
    headers: await authHeaders(),
  });
  return res.data as GroupAISuggestions;
}

export async function getMemberAvailability(groupId: number): Promise<any> {
  const res = await apiClient.get(`/groups/${groupId}/ai/availability`, {
    headers: await authHeaders(),
  });
  return res.data;
}

export async function getPickupSlotSuggestion(groupId: number, vendorId: number): Promise<any> {
  const res = await apiClient.get(
    `/groups/${groupId}/ai/pickup-slot?vendor_id=${vendorId}`,
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}

export async function getCommonMenuItems(
  groupId: number,
  vendorId: number,
  limit: number = 10
): Promise<any> {
  const res = await apiClient.get(
    `/groups/${groupId}/ai/common-items?vendor_id=${vendorId}&limit=${limit}`,
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}

export async function getOrderingConflicts(groupId: number): Promise<any> {
  const res = await apiClient.get(`/groups/${groupId}/ai/conflicts`, {
    headers: await authHeaders(),
  });
  return res.data;
}

export async function getPickupSynchronization(groupId: number): Promise<any> {
  const res = await apiClient.get(`/groups/${groupId}/ai/synchronization`, {
    headers: await authHeaders(),
  });
  return res.data;
}

export async function saveGroupAISuggestions(
  groupId: number,
  suggestions: any
): Promise<{ saved: boolean; group_id: number }> {
  const res = await apiClient.post(
    `/groups/${groupId}/ai/save-suggestions`,
    suggestions,
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}
</write_to_file>
<task_progress>
- [x] Explore existing group cart implementation
- [x] Analyze group cart models and services
- [x] Create group_ai_service backend
- [x] Implement member availability analysis
- [x] Implement ordering conflict detection
- [x] Implement pickup synchronization
- [x] Suggest best ordering time
- [x] Suggest best common pickup slot
- [x] Suggest common menu items
- [x] Create API endpoints
- [x] Create frontend service
- [ ] Create documentation
</task_progress>
</write_to_file>