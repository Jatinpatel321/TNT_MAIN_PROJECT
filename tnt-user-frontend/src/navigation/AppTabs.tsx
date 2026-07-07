import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import type { AppTabsParamList } from '../types/navigation';

import { HomeScreen } from '../screens/HomeScreen';
import { OrdersScreen } from '../screens/OrdersScreen';
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

export function AppTabs() {
  const unread = useUnreadNotifications();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarShowLabel: true,
        tabBarIcon: ({ color, size }) => {
          const iconName =
            route.name === 'HomeTab'
              ? 'home-variant'
              : route.name === 'OrdersTab'
                ? 'clipboard-text'
                : route.name === 'NotificationsTab'
                  ? 'bell-outline'
                  : 'account-circle';
          return <MaterialCommunityIcons name={iconName} color={color} size={size} />;
        },
      })}
    >
      <Tab.Screen name="HomeTab" component={HomeScreen} options={{ title: 'Home' }} />
      <Tab.Screen name="OrdersTab" component={OrdersScreen} options={{ title: 'Orders' }} />
      <Tab.Screen
        name="NotificationsTab"
        component={NotificationsScreen}
        options={{ title: 'Notifications', tabBarBadge: unread > 0 ? unread : undefined }}
      />
      <Tab.Screen name="ProfileTab" component={ProfileScreen} options={{ title: 'Profile' }} />
    </Tab.Navigator>
  );
}
