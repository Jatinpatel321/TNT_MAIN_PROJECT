import api from './axios';
import type {
  RushHourSignal,
  VendorRanking,
  DemandPlan,
  SlotSuggestion,
  ReorderPrompt,
  ETAMetrics,
  AISignals,
  ModelAccuracySummary,
  ModelAccuracyDetail,
} from '../types';

export const aiApi = {
  getDemandPlanning: (vendorId?: number) =>
    api.get<DemandPlan[]>('/v1/ai/demand-planning', { params: vendorId ? { vendor_id: vendorId } : {} }),

  getCapacityRecommendation: () =>
    api.get('/v1/ai/capacity-recommendation'),

  getSlotRecommendations: () =>
    api.get<SlotSuggestion[]>('/v1/ai/slot-recommendations'),

  getPredictiveETA: (slotId?: number, vendorId?: number) =>
    api.get<ETAMetrics[]>('/v1/ai/predictive-eta', { params: slotId && vendorId ? { slot_id: slotId, vendor_id: vendorId } : {} }),

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

  getAccuracySummary: () =>
    api.get<ModelAccuracySummary>('/v1/ml/accuracy/summary'),

  getModelAccuracy: (modelType: string) =>
    api.get<ModelAccuracyDetail>(`/v1/ml/accuracy/${modelType}`),
};


