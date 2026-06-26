import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { retentionApi } from '../../services/retentionApi';

type TabType = 'overview' | 'offers' | 'campaigns' | 'customers' | 'ai';

export default function PromotionsDashboard({ navigation }: any) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [promotions, setPromotions] = useState<any>(null);
  const [offers, setOffers] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any>(null);
  const [repeatCustomers, setRepeatCustomers] = useState<any>(null);
  const [aiSuggestions, setAiSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [promoRes, offersRes, campaignsRes, customersRes, repeatRes, aiRes] = await Promise.all([
        retentionApi.getPromotions(),
        retentionApi.getOffers(),
        retentionApi.getCampaigns(),
        retentionApi.getCustomers(),
        retentionApi.getRepeatCustomers(),
        retentionApi.getAiSuggestions(),
      ]);
      setPromotions(promoRes.data);
      setOffers(offersRes.data.offers || []);
      setCampaigns(campaignsRes.data.campaigns || []);
      setCustomers(customersRes.data);
      setRepeatCustomers(repeatRes.data);
      setAiSuggestions(aiRes.data.suggestions || []);
    } catch (error) {
      console.error('Failed to load retention data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNotifyCustomers = async (offerId: number) => {
    try {
      const res = await retentionApi.notifyCustomers(offerId);
      Alert.alert('Success', `Notified ${res.data.notified} customers`);
    } catch (error) {
      Alert.alert('Error', 'Failed to send notifications');
    }
  };

  const getSegmentColor = (segment: string) => {
    switch (segment) {
      case 'loyal': return '#10B981';
      case 'repeat': return '#3B82F6';
      case 'new': return '#8B5CF6';
      case 'at_risk': return '#F59E0B';
      case 'lapsed': return '#EF4444';
      default: return '#6B7280';
    }
  };

  const renderOverviewTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Promotions Summary */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🎯 Active Promotions</Text>
        <Text style={styles.cardSubtitle}>{promotions?.total_active || 0} currently active</Text>
        <View style={styles.promoGrid}>
          <View style={styles.promoStat}>
            <Text style={styles.promoValue}>{promotions?.active_campaigns?.length || 0}</Text>
            <Text style={styles.promoLabel}>Campaigns</Text>
          </View>
          <View style={styles.promoStat}>
            <Text style={styles.promoValue}>{promotions?.active_offers?.length || 0}</Text>
            <Text style={styles.promoLabel}>Offers</Text>
          </View>
        </View>
      </View>

      {/* Customer Segments */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>👥 Customer Segments</Text>
        <Text style={styles.cardSubtitle}>{customers?.total_customers || 0} total customers</Text>
        {customers?.segments && Object.entries(customers.segments).map(([segment, count]: any) => (
          <View key={segment} style={styles.segmentRow}>
            <View style={[styles.segmentDot, { backgroundColor: getSegmentColor(segment) }]} />
            <Text style={styles.segmentName}>{segment.charAt(0).toUpperCase() + segment.slice(1)}</Text>
            <Text style={styles.segmentCount}>{count}</Text>
          </View>
        ))}
      </View>

      {/* Repeat Rate */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🔄 Repeat Customer Rate</Text>
        <View style={styles.repeatRateContainer}>
          <Text style={styles.repeatRateValue}>{repeatCustomers?.repeat_rate || 0}%</Text>
          <Text style={styles.repeatRateLabel}>of customers order again</Text>
        </View>
        <Text style={styles.repeatDetail}>
          {repeatCustomers?.total_repeat_customers || 0} repeat customers out of {customers?.total_customers || 0}
        </Text>
      </View>

      {/* AI Suggestions Preview */}
      {aiSuggestions.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🤖 AI Suggestions</Text>
          {aiSuggestions.slice(0, 2).map((suggestion: any, index: number) => (
            <View key={index} style={styles.aiSuggestionRow}>
              <Text style={styles.aiSuggestionIcon}>
                {suggestion.type === 'win_back' ? '🔄' : suggestion.type === 'off_peak' ? '⏰' : suggestion.type === 'combo' ? '📦' : '⭐'}
              </Text>
              <View style={styles.aiSuggestionInfo}>
                <Text style={styles.aiSuggestionTitle}>{suggestion.title}</Text>
                <Text style={styles.aiSuggestionDesc}>{suggestion.description}</Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );

  const renderOffersTab = () => (
    <ScrollView style={styles.tabContent}>
      <TouchableOpacity style={styles.createButton} onPress={() => Alert.alert('Create Offer', 'Offer creation form')}>
        <Text style={styles.createButtonText}>+ Create New Offer</Text>
      </TouchableOpacity>

      {offers.map((offer: any, index: number) => (
        <View key={index} style={styles.offerCard}>
          <View style={styles.offerHeader}>
            <Text style={styles.offerTitle}>{offer.title}</Text>
            <View style={[styles.offerStatus, { backgroundColor: offer.is_active ? '#10B981' : '#6B7280' }]}>
              <Text style={styles.offerStatusText}>{offer.is_active ? 'Active' : 'Inactive'}</Text>
            </View>
          </View>
          <Text style={styles.offerType}>{offer.discount_type.replace(/_/g, ' ')}</Text>
          <View style={styles.offerDetails}>
            <Text style={styles.offerDiscount}>{offer.discount_value}% off</Text>
            <Text style={styles.offerRedeemed}>{offer.times_redeemed} redeemed</Text>
          </View>
          {offer.is_dynamic && <Text style={styles.aiBadge}>🤖 AI Suggested ({(offer.ai_confidence * 100).toFixed(0)}% confidence)</Text>}
          <TouchableOpacity style={styles.notifyButton} onPress={() => handleNotifyCustomers(offer.id)}>
            <Text style={styles.notifyButtonText}>🔔 Notify Customers</Text>
          </TouchableOpacity>
        </View>
      ))}
    </ScrollView>
  );

  const renderCampaignsTab = () => (
    <ScrollView style={styles.tabContent}>
      <TouchableOpacity style={styles.createButton} onPress={() => Alert.alert('Create Campaign', 'Campaign creation form')}>
        <Text style={styles.createButtonText}>+ Create New Campaign</Text>
      </TouchableOpacity>

      {campaigns.map((campaign: any, index: number) => (
        <View key={index} style={styles.campaignCard}>
          <View style={styles.campaignHeader}>
            <Text style={styles.campaignName}>{campaign.name}</Text>
            <View style={[styles.campaignStatus, { backgroundColor: campaign.status === 'active' ? '#10B981' : campaign.status === 'draft' ? '#6B7280' : '#F59E0B' }]}>
              <Text style={styles.campaignStatusText}>{campaign.status}</Text>
            </View>
          </View>
          <Text style={styles.campaignType}>{campaign.offer_type.replace(/_/g, ' ')}</Text>
          <View style={styles.campaignDetails}>
            <Text style={styles.campaignDiscount}>{campaign.discount_value}% off</Text>
            <Text style={styles.campaignUsed}>{campaign.times_used} used</Text>
          </View>
          {campaign.is_combo && <Text style={styles.comboBadge}>📦 Combo Deal</Text>}
          {campaign.is_off_peak && <Text style={styles.offPeakBadge}>⏰ Off-Peak ({campaign.off_peak_start}:00 - {campaign.off_peak_end}:00)</Text>}
          <Text style={styles.campaignDate}>
            {new Date(campaign.start_date).toLocaleDateString()} - {new Date(campaign.end_date).toLocaleDateString()}
          </Text>
        </View>
      ))}
    </ScrollView>
  );

  const renderCustomersTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Frequent Buyers */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⭐ Frequent Buyers</Text>
        {repeatCustomers?.frequent_buyers?.slice(0, 5).map((customer: any, index: number) => (
          <View key={index} style={styles.customerRow}>
            <View style={styles.customerRank}>
              <Text style={styles.customerRankText}>#{index + 1}</Text>
            </View>
            <View style={styles.customerInfo}>
              <Text style={styles.customerName}>{customer.name}</Text>
              <Text style={styles.customerOrders}>{customer.total_orders} orders · ₹{customer.total_spent}</Text>
            </View>
            <View style={[styles.segmentBadge, { backgroundColor: getSegmentColor(customer.segment) }]}>
              <Text style={styles.segmentBadgeText}>{customer.segment}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* All Customers */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>👥 All Customers</Text>
        {customers?.customers?.slice(0, 10).map((customer: any, index: number) => (
          <View key={index} style={styles.customerRow}>
            <View style={styles.customerInfo}>
              <Text style={styles.customerName}>{customer.name}</Text>
              <Text style={styles.customerOrders}>{customer.total_orders} orders · Last: {customer.days_since_last_order}d ago</Text>
            </View>
            <View style={[styles.segmentBadge, { backgroundColor: getSegmentColor(customer.segment) }]}>
              <Text style={styles.segmentBadgeText}>{customer.segment}</Text>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  const renderAiTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🤖 AI Suggested Discounts</Text>
        <Text style={styles.cardSubtitle}>Data-driven recommendations to boost retention</Text>
        {aiSuggestions.map((suggestion: any, index: number) => (
          <View key={index} style={styles.aiCard}>
            <View style={styles.aiHeader}>
              <Text style={styles.aiIcon}>
                {suggestion.type === 'win_back' ? '🔄' : suggestion.type === 'off_peak' ? '⏰' : suggestion.type === 'combo' ? '📦' : '⭐'}
              </Text>
              <View style={styles.aiInfo}>
                <Text style={styles.aiTitle}>{suggestion.title}</Text>
                <Text style={styles.aiDesc}>{suggestion.description}</Text>
              </View>
            </View>
            <View style={styles.aiMeta}>
              <Text style={styles.aiDiscount}>{suggestion.suggested_discount}% off</Text>
              <Text style={styles.aiTarget}>🎯 {suggestion.target_segment}</Text>
              <Text style={styles.aiConfidence}>{(suggestion.confidence * 100).toFixed(0)}% confidence</Text>
            </View>
            <TouchableOpacity style={styles.applyButton}>
              <Text style={styles.applyButtonText}>Apply Suggestion</Text>
            </TouchableOpacity>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading retention data...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📈 Promotions</Text>
        <Text style={styles.headerSubtitle}>Retain & grow your customer base</Text>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity style={[styles.tab, activeTab === 'overview' && styles.activeTab]} onPress={() => setActiveTab('overview')}>
          <Text style={[styles.tabText, activeTab === 'overview' && styles.activeTabText]}>📊 Overview</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'offers' && styles.activeTab]} onPress={() => setActiveTab('offers')}>
          <Text style={[styles.tabText, activeTab === 'offers' && styles.activeTabText]}>🎁 Offers</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'campaigns' && styles.activeTab]} onPress={() => setActiveTab('campaigns')}>
          <Text style={[styles.tabText, activeTab === 'campaigns' && styles.activeTabText]}>📢 Campaigns</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'customers' && styles.activeTab]} onPress={() => setActiveTab('customers')}>
          <Text style={[styles.tabText, activeTab === 'customers' && styles.activeTabText]}>👥 Customers</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'ai' && styles.activeTab]} onPress={() => setActiveTab('ai')}>
          <Text style={[styles.tabText, activeTab === 'ai' && styles.activeTabText]}>🤖 AI</Text>
        </TouchableOpacity>
      </View>

      {activeTab === 'overview' && renderOverviewTab()}
      {activeTab === 'offers' && renderOffersTab()}
      {activeTab === 'campaigns' && renderCampaignsTab()}
      {activeTab === 'customers' && renderCustomersTab()}
      {activeTab === 'ai' && renderAiTab()}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { fontSize: 16, color: '#6B7280' },
  header: { padding: 20, paddingTop: 60, backgroundColor: '#10B981' },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: 'white' },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 4 },
  tabContainer: { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 12, gap: 4, backgroundColor: 'white', borderBottomWidth: 1, borderBottomColor: '#E5E7EB' },
  tab: { flex: 1, paddingVertical: 8, borderRadius: 8, backgroundColor: '#F3F5F9', alignItems: 'center' },
  activeTab: { backgroundColor: '#10B981' },
  tabText: { fontSize: 11, fontWeight: '600', color: '#6B7280' },
  activeTabText: { color: 'white' },
  tabContent: { padding: 16 },
  card: { backgroundColor: 'white', borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  cardTitle: { fontSize: 18, fontWeight: 'bold', color: '#111827', marginBottom: 4 },
  cardSubtitle: { fontSize: 12, color: '#6B7280', marginBottom: 12 },
  promoGrid: { flexDirection: 'row', gap: 12 },
  promoStat: { flex: 1, backgroundColor: '#F3F5F9', borderRadius: 8, padding: 16, alignItems: 'center' },
  promoValue: { fontSize: 28, fontWeight: 'bold', color: '#10B981' },
  promoLabel: { fontSize: 12, color: '#6B7280', marginTop: 4 },
  segmentRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  segmentDot: { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  segmentName: { flex: 1, fontSize: 14, color: '#374151' },
  segmentCount: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
  repeatRateContainer: { alignItems: 'center', paddingVertical: 16 },
  repeatRateValue: { fontSize: 48, fontWeight: 'bold', color: '#10B981' },
  repeatRateLabel: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  repeatDetail: { fontSize: 14, color: '#6B7280', textAlign: 'center' },
  aiSuggestionRow: { flexDirection: 'row', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  aiSuggestionIcon: { fontSize: 24, marginRight: 12 },
  aiSuggestionInfo: { flex: 1 },
  aiSuggestionTitle: { fontSize: 14, fontWeight: '600', color: '#111827' },
  aiSuggestionDesc: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  createButton: { backgroundColor: '#10B981', borderRadius: 12, padding: 16, alignItems: 'center', marginBottom: 16 },
  createButtonText: { color: 'white', fontSize: 16, fontWeight: '600' },
  offerCard: { backgroundColor: 'white', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  offerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  offerTitle: { fontSize: 16, fontWeight: '600', color: '#111827' },
  offerStatus: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  offerStatusText: { color: 'white', fontSize: 11, fontWeight: '600' },
  offerType: { fontSize: 12, color: '#6B7280', textTransform: 'capitalize', marginBottom: 8 },
  offerDetails: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  offerDiscount: { fontSize: 18, fontWeight: 'bold', color: '#10B981' },
  offerRedeemed: { fontSize: 14, color: '#6B7280' },
  aiBadge: { fontSize: 12, color: '#8B5CF6', marginBottom: 8 },
  notifyButton: { backgroundColor: '#3B82F6', borderRadius: 8, padding: 10, alignItems: 'center' },
  notifyButtonText: { color: 'white', fontSize: 14, fontWeight: '600' },
  campaignCard: { backgroundColor: 'white', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  campaignHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  campaignName: { fontSize: 16, fontWeight: '600', color: '#111827' },
  campaignStatus: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  campaignStatusText: { color: 'white', fontSize: 11, fontWeight: '600' },
  campaignType: { fontSize: 12, color: '#6B7280', textTransform: 'capitalize', marginBottom: 8 },
  campaignDetails: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  campaignDiscount: { fontSize: 18, fontWeight: 'bold', color: '#10B981' },
  campaignUsed: { fontSize: 14, color: '#6B7280' },
  comboBadge: { fontSize: 12, color: '#8B5CF6', marginBottom: 4 },
  offPeakBadge: { fontSize: 12, color: '#F59E0B', marginBottom: 4 },
  campaignDate: { fontSize: 12, color: '#9CA3AF' },
  customerRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  customerRank: { width: 28, height: 28, borderRadius: 14, backgroundColor: '#FEF3C7', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  customerRankText: { fontSize: 12, fontWeight: 'bold', color: '#D97706' },
  customerInfo: { flex: 1 },
  customerName: { fontSize: 14, fontWeight: '600', color: '#111827' },
  customerOrders: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  segmentBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  segmentBadgeText: { color: 'white', fontSize: 10, fontWeight: '600' },
  aiCard: { backgroundColor: '#F9FAFB', borderRadius: 8, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#E5E7EB' },
  aiHeader: { flexDirection: 'row', marginBottom: 8 },
  aiIcon: { fontSize: 24, marginRight: 12 },
  aiInfo: { flex: 1 },
  aiTitle: { fontSize: 14, fontWeight: '600', color: '#111827' },
  aiDesc: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  aiMeta: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  aiDiscount: { fontSize: 14, fontWeight: 'bold', color: '#10B981' },
  aiTarget: { fontSize: 12, color: '#8B5CF6' },
  aiConfidence: { fontSize: 12, color: '#6B7280' },
  applyButton: { backgroundColor: '#10B981', borderRadius: 8, padding: 10, alignItems: 'center' },
  applyButtonText: { color: 'white', fontSize: 14, fontWeight: '600' },
});