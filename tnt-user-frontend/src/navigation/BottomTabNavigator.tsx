import React from 'react';
import { createBottomTabNavigator, type BottomTabNavigationOptions } from '@react-navigation/bottom-tabs';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import type { RouteProp } from '@react-navigation/native';

import type { AppTabsParamList } from '../types/navigation';
import { HomeScreen } from '../screens/home/HomeScreen';
import { OrdersScreen } from '../screens/orders/OrdersScreen';
import { RewardsScreen } from '../screens/rewards/RewardsScreen';
import { NotificationsScreen } from '../screens/notifications/NotificationsScreen';
import { ProfileScreen } from '../screens/profile/ProfileScreen';
import { getNotifications } from '../services/notificationService';

function useUnreadNotifications() {
  const [unread, setUnread] = React.useState(0);

  React.useEffect(() => {
    let alive = true;
    const fetchUnread = async () => {
      try {
        const list = await getNotifications();
        if (!alive) return;
        const count = list.filter((n) => !n.is_read).length;
        setUnread(count);
      } catch {
        // ignore badge failures
      }
    };

    fetchUnread();
    const id = setInterval(fetchUnread, 30000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return unread;
}

const Tab = createBottomTabNavigator<AppTabsParamList>();

export function BottomTabNavigator() {
  const unread = useUnreadNotifications();

  return (
    <Tab.Navigator
      screenOptions={({ route }: { route: RouteProp<AppTabsParamList, keyof AppTabsParamList> }): BottomTabNavigationOptions => ({
        headerShown: false,
        tabBarShowLabel: true,
        tabBarActiveTintColor: '#3B82F6',
        tabBarInactiveTintColor: '#6B7280',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopColor: '#E5E7EB',
          shadowColor: 'rgba(0,0,0,0.1)',
          shadowOpacity: 0.1,
          shadowOffset: { width: 0, height: 2 },
          shadowRadius: 6,
          elevation: 6,
        },
        tabBarIcon: ({ color, size }: { color: string; size: number }) => {
          const iconName =
            route.name === 'HomeTab'
              ? 'home-variant'
              : route.name === 'OrdersTab'
                ? 'clipboard-text'
                : route.name === 'RewardsTab'
                  ? 'star-circle'
                  : route.name === 'NotificationsTab'
                    ? 'bell-outline'
                    : 'account-circle';
          return <MaterialCommunityIcons name={iconName as any} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="HomeTab" component={HomeScreen} options={{ title: 'Home' }} />
      <Tab.Screen name="OrdersTab" component={OrdersScreen} options={{ title: 'Orders' }} />
      <Tab.Screen name="RewardsTab" component={RewardsScreen} options={{ title: 'Rewards' }} />
      <Tab.Screen
        name="NotificationsTab"
        component={NotificationsScreen}
        options={{ title: 'Notifications', tabBarBadge: unread > 0 ? unread : undefined }}
      />
      <Tab.Screen name="ProfileTab" component={ProfileScreen} options={{ title: 'Profile' }} />
    </Tab.Navigator>
  );
}
