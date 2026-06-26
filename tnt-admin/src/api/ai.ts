import api from './axios';
import type {
  RushHourSignal,
  VendorRanking,
  DemandPlan,
  SlotSuggestion,
  ReorderPrompt,
  ETAMetrics,
  AISignals,
} from '../types';

export const aiApi = {
  // Backend requires query param: vendor_id
  // See: app/modules/ai_intelligence/router.py -> /ai/demand-planning?vendor_id=...
  getDemandPlanning: (vendorId: number) =>
    api.get<DemandPlan[]>('/v1/ai/demand-planning', { params: { vendor_id: vendorId } }),


  getCapacityRecommendation: () =>
    api.get('/v1/ai/capacity-recommendation'),

  getSlotRecommendations: () =>
    api.get<SlotSuggestion[]>('/v1/ai/slot-recommendations'),

  getPredictiveETA: (slotId: number, vendorId: number) =>
    api.get<ETAMetrics[]>('/v1/ai/predictive-eta', { params: { slot_id: slotId, vendor_id: vendorId } }),


  getVendorRanking: () =>
    api.get<VendorRanking[]>('/v1/ai/vendor-ranking'),

  getSignals: () =>
    api.get<AISignals>('/v1/ai/signals'),

  getRushHour: () =>
    api.get<RushHourSignal>('/v1/ai/signals/rush-hour'),

  getSlotSuggestions: () =>
    api.get<SlotSuggestion[]>('/v1/ai/signals/slot-suggestions'),

  getReorderPrompts: () =>
    api.get<ReorderPrompt[]>('/v1/ai/signals/reorder-prompts'),
};
