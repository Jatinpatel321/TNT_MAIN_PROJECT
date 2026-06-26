import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Provider as PaperProvider } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import messaging from '@react-native-firebase/messaging';
import { registerFCMToken } from './src/services/pushRegistrationService';

// Screens
import LoginScreen from './src/screens/auth/LoginScreen';
import DashboardScreen from './src/screens/home/DashboardScreen';
import OrdersScreen from './src/screens/orders/OrdersScreen';
import MenuScreen from './src/screens/menu/MenuScreen';
import ProfileScreen from './src/screens/profile/ProfileScreen';
import NotificationsScreen from './src/screens/notifications/NotificationsScreen';
import NotificationDetailScreen from './src/screens/notifications/NotificationDetailScreen';
import { QRScanScreen } from './src/screens/orders/QRScanScreen';
import AnalyticsDashboard from './src/screens/analytics/AnalyticsDashboard';
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

// Context
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { PermissionsProvider } from './src/context/PermissionsContext';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function TabNavigator({ navigation }: { navigation: any }) {
  const { user } = useAuth();
  const role = user?.role || 'staff';
  
  // Define which tabs are visible for each role
  const getVisibleTabs = () => {
    switch (role) {
      case 'owner':
        return ['Dashboard', 'Orders', 'Menu', 'Analytics', 'Profile'];
      case 'manager':
        return ['Dashboard', 'Orders', 'Menu', 'Analytics', 'Profile'];
      case 'staff':
        return ['Dashboard', 'Orders', 'Menu', 'Profile'];
      default:
        return ['Dashboard', 'Orders', 'Menu', 'Profile'];
    }
  };
  
  const visibleTabs = getVisibleTabs();

  return (
    <Tab.Navigator
      screenOptions={({ route }: { route: { name: string } }) => ({
        tabBarIcon: ({ focused, color, size }: { focused: boolean; color: string; size: number }) => {
          let iconName: string = '';

          if (route.name === 'Dashboard') {
            iconName = focused ? 'dashboard' : 'dashboard';
          } else if (route.name === 'Orders') {
            iconName = focused ? 'receipt-long' : 'receipt-long';
          } else if (route.name === 'Menu') {
            iconName = focused ? 'restaurant-menu' : 'restaurant-menu';
          } else if (route.name === 'Analytics') {
            iconName = focused ? 'analytics' : 'analytics';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'person' : 'person';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#10B981',
        tabBarInactiveTintColor: '#6B7280',
        headerShown: false,
      })}
    >
      {visibleTabs.includes('Dashboard') && (
        <Tab.Screen 
          name="Dashboard" 
          component={DashboardScreen}
          options={{ title: 'Home' }}
        />
      )}
      {visibleTabs.includes('Orders') && (
        <Tab.Screen 
          name="Orders" 
          component={OrdersScreen}
          options={{ title: 'Orders' }}
        />
      )}
      {visibleTabs.includes('Menu') && (
        <Tab.Screen 
          name="Menu" 
          component={MenuScreen}
          options={{ title: 'Menu' }}
        />
      )}
      {visibleTabs.includes('Analytics') && (
        <Tab.Screen 
          name="Analytics" 
          component={AnalyticsDashboard}
          options={{ title: 'Analytics' }}
        />
      )}
      {visibleTabs.includes('Profile') && (
        <Tab.Screen 
          name="Profile" 
          component={ProfileScreen}
          options={{ title: 'Profile' }}
        />
      )}
    </Tab.Navigator>
  );
}

export default function App() {
  useEffect(() => {
    const unsubscribe = messaging().onTokenRefresh(() => {
      registerFCMToken();
    });
    return unsubscribe;
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
                options={{ title: 'Scan QR', headerStyle: { backgroundColor: '#000' }, headerTintColor: '#fff' }}
              />
              <Stack.Screen
                name="NotificationDetail"
                component={NotificationDetailScreen}
                options={{ title: 'Notification Details' }}
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
                options={{ title: 'Peak Hour Settings' }}
              />
              <Stack.Screen
                name="FacultyPrioritySettings"
                component={FacultyPrioritySettingsScreen}
                options={{ title: 'Faculty Priority' }}
              />
              <Stack.Screen
                name="StaffManagement"
                component={StaffListScreen}
                options={{ title: 'Staff Management' }}
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
            </Stack.Navigator>
          </NavigationContainer>
          </PermissionsProvider>
        </AuthProvider>
      </PaperProvider>
    </SafeAreaProvider>
  );
}
