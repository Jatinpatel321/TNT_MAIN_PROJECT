// ─── TNT Vendor App ─────────────────────────────────────────────────
// Premium commercial-grade vendor application

import React, { useEffect, useState } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Provider as PaperProvider } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, shadows, spacing, borderRadius } from './src/design-system';
import { registerFCMToken } from './src/services/pushRegistrationService';

// Context
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { PermissionsProvider } from './src/context/PermissionsContext';

// ── Screen Imports ────────────────────────────────────────────────
import LoginScreen from './src/screens/auth/LoginScreen';
import DashboardScreen from './src/screens/home/DashboardScreen';
import OrdersScreen from './src/screens/orders/OrdersScreen';
import MenuScreen from './src/screens/menu/MenuScreen';
import AnalyticsDashboard from './src/screens/analytics/AnalyticsDashboard';
import MoreScreen from './src/screens/more/MoreScreen';
import NotificationsScreen from './src/screens/notifications/NotificationsScreen';
import NotificationDetailScreen from './src/screens/notifications/NotificationDetailScreen';
import { QRScanScreen } from './src/screens/orders/QRScanScreen';
import SettlementDashboard from './src/screens/settlement/SettlementDashboard';
import PromotionsDashboard from './src/screens/promotions/PromotionsDashboard';
import AIDashboardScreen from './src/screens/ai/AIDashboardScreen';
import SmartDemandDashboard from './src/screens/analytics/SmartDemandDashboard';
import SlotDashboardScreen from './src/screens/slots/SlotDashboardScreen';
import SlotConfigurationScreen from './src/screens/slots/SlotConfigurationScreen';
import CapacitySettingsScreen from './src/screens/slots/CapacitySettingsScreen';
import PeakHourSettingsScreen from './src/screens/slots/PeakHourSettingsScreen';
import FacultyPrioritySettingsScreen from './src/screens/slots/FacultyPrioritySettingsScreen';
import StaffListScreen from './src/screens/staff/StaffListScreen';
import AddStaffScreen from './src/screens/staff/AddStaffScreen';
import EditStaffScreen from './src/screens/staff/EditStaffScreen';
import StaffPermissionsScreen from './src/screens/staff/StaffPermissionsScreen';
import ProfileScreen from './src/screens/profile/ProfileScreen';
import BusinessHoursScreen from './src/screens/business/BusinessHoursScreen';
import HolidaySettingsScreen from './src/screens/business/HolidaySettingsScreen';
import AIInventoryPlanningDashboard from './src/screens/inventory/AIInventoryPlanningDashboard';
import CoverImageUploadScreen from './src/screens/media/CoverImageUploadScreen';
import LogoUploadScreen from './src/screens/media/LogoUploadScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const iconMap: Record<string, string> = {
    Dashboard: 'dashboard',
    Orders: 'receipt-long',
    Menu: 'restaurant-menu',
    Analytics: 'analytics',
    More: 'more-horiz',
  };

  return (
    <View style={tabStyles.iconContainer}>
      <Icon
        name={iconMap[name] || 'circle'}
        size={focused ? 24 : 22}
        color={focused ? colors.primary : colors.textMuted}
      />
      {focused && <View style={tabStyles.activeDot} />}
    </View>
  );
}

function TabLabel({ label, focused }: { label: string; focused: boolean }) {
  return (
    <Text style={[tabStyles.label, focused && tabStyles.labelActive]}>
      {label}
    </Text>
  );
}

function TabNavigator() {
  const { user } = useAuth();
  const role = user?.role || 'staff';

  const getVisibleTabs = () => {
    switch (role) {
      case 'owner':
        return ['Dashboard', 'Orders', 'Menu', 'Analytics', 'More'];
      case 'manager':
        return ['Dashboard', 'Orders', 'Menu', 'Analytics', 'More'];
      default:
        return ['Dashboard', 'Orders', 'Menu', 'More'];
    }
  };

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => (
          <TabIcon name={route.name} focused={focused} />
        ),
        tabBarLabel: ({ focused }) => (
          <TabLabel label={route.name} focused={focused} />
        ),
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: tabStyles.tabBar,
        tabBarItemStyle: tabStyles.tabItem,
        headerShown: false,
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Orders" component={OrdersScreen} />
      <Tab.Screen name="Menu" component={MenuScreen} />
      {getVisibleTabs().includes('Analytics') && (
        <Tab.Screen name="Analytics" component={AnalyticsDashboard} />
      )}
      <Tab.Screen name="More" component={MoreScreen} />
    </Tab.Navigator>
  );
}

const tabStyles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.bgCard,
    borderTopWidth: 0,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    height: 70,
    paddingBottom: 8,
    paddingTop: 8,
    ...shadows.lg,
    elevation: 12,
  },
  tabItem: {
    paddingTop: 4,
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    height: 28,
  },
  activeDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.primary,
    marginTop: 2,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    color: colors.textMuted,
    marginTop: 2,
  },
  labelActive: {
    color: colors.primary,
    fontWeight: '700',
  },
});

export default function App() {
  useEffect(() => {
    // Push notifications are disabled in this vendor preview build until a real Firebase
    // project is configured. Avoid touching Firebase at startup to prevent render crashes.
    return undefined;
  }, []);

  return (
    <SafeAreaProvider>
      <PaperProvider>
        <AuthProvider>
          <PermissionsProvider>
            <NavigationContainer>
              <Stack.Navigator
                initialRouteName="Login"
                screenOptions={{
                  headerShown: true,
                  headerBackTitle: 'Back',
                  headerStyle: {
                    backgroundColor: colors.bgCard,
                  },
                  headerTintColor: colors.textPrimary,
                  headerTitleStyle: {
                    fontWeight: '600',
                    fontSize: 17,
                  },
                  headerShadowVisible: false,
                  contentStyle: {
                    backgroundColor: colors.bg,
                  },
                }}
              >
                <Stack.Screen
                  name="Login"
                  component={LoginScreen}
                  options={{ headerShown: false }}
                />
                <Stack.Screen
                  name="Main"
                  component={TabNavigator}
                  options={{ headerShown: false }}
                />
                <Stack.Screen
                  name="QRScanner"
                  component={QRScanScreen}
                  options={{
                    title: 'Scan QR Code',
                    headerStyle: { backgroundColor: '#000' },
                    headerTintColor: '#fff',
                  }}
                />
                <Stack.Screen
                  name="Notifications"
                  component={NotificationsScreen}
                  options={{ title: 'Notifications' }}
                />
                <Stack.Screen
                  name="NotificationDetail"
                  component={NotificationDetailScreen}
                  options={{ title: 'Details' }}
                />
                <Stack.Screen
                  name="Settlements"
                  component={SettlementDashboard}
                  options={{ title: 'Settlements' }}
                />
                <Stack.Screen
                  name="Promotions"
                  component={PromotionsDashboard}
                  options={{ title: 'Promotions' }}
                />
                <Stack.Screen
                  name="AI"
                  component={AIDashboardScreen}
                  options={{ title: 'AI Insights' }}
                />
                <Stack.Screen
                  name="DemandDashboard"
                  component={SmartDemandDashboard}
                  options={{ title: 'Smart Demand' }}
                />
                <Stack.Screen
                  name="SlotManagement"
                  component={SlotDashboardScreen}
                  options={{ title: 'Slot Management' }}
                />
                <Stack.Screen
                  name="SlotConfiguration"
                  component={SlotConfigurationScreen}
                  options={{ title: 'Create Slot' }}
                />
                <Stack.Screen
                  name="CapacitySettings"
                  component={CapacitySettingsScreen}
                  options={{ title: 'Capacity Settings' }}
                />
                <Stack.Screen
                  name="PeakHourSettings"
                  component={PeakHourSettingsScreen}
                  options={{ title: 'Peak Hours' }}
                />
                <Stack.Screen
                  name="FacultyPrioritySettings"
                  component={FacultyPrioritySettingsScreen}
                  options={{ title: 'Faculty Priority' }}
                />
                <Stack.Screen
                  name="StaffManagement"
                  component={StaffListScreen}
                  options={{ title: 'Staff' }}
                />
                <Stack.Screen
                  name="AddStaff"
                  component={AddStaffScreen}
                  options={{ title: 'Add Staff' }}
                />
                <Stack.Screen
                  name="EditStaff"
                  component={EditStaffScreen}
                  options={{ title: 'Edit Staff' }}
                />
                <Stack.Screen
                  name="StaffPermissions"
                  component={StaffPermissionsScreen}
                  options={{ title: 'Permissions' }}
                />
                <Stack.Screen
                  name="Profile"
                  component={ProfileScreen}
                  options={{ title: 'Profile' }}
                />
                <Stack.Screen
                  name="BusinessHours"
                  component={BusinessHoursScreen}
                  options={{ title: 'Business Hours' }}
                />
                <Stack.Screen
                  name="HolidaySettings"
                  component={HolidaySettingsScreen}
                  options={{ title: 'Holidays' }}
                />
                <Stack.Screen
                  name="InventoryPlanning"
                  component={AIInventoryPlanningDashboard}
                  options={{ title: 'Inventory AI' }}
                />
                <Stack.Screen
                  name="CoverImageUpload"
                  component={CoverImageUploadScreen}
                  options={{ title: 'Cover Image' }}
                />
                <Stack.Screen
                  name="LogoUpload"
                  component={LogoUploadScreen}
                  options={{ title: 'Upload Logo' }}
                />
              </Stack.Navigator>
            </NavigationContainer>
          </PermissionsProvider>
        </AuthProvider>
      </PaperProvider>
    </SafeAreaProvider>
  );
}
