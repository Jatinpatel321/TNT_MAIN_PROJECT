import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Notification } from '../../services/notificationApi';

type RootStackParamList = {
  NotificationDetail: { notification: Notification };
};

type NotificationDetailScreenRouteProp = RouteProp<RootStackParamList, 'NotificationDetail'>;
type NotificationDetailScreenNavigationProp = StackNavigationProp<RootStackParamList, 'NotificationDetail'>;

interface Props {
  route: NotificationDetailScreenRouteProp;
  navigation: NotificationDetailScreenNavigationProp;
}

export default function NotificationDetailScreen({ route, navigation }: Props) {
  const { notification } = route.params;

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'order_ready': return '✅';
      case 'order_accepted': return '📋';
      case 'order_preparing': return '👨‍🍳';
      case 'delay_alert': return '⚠️';
      case 'order_cancelled': return '❌';
      case 'pickup_reminder': return '🔔';
      case 'promo': return '🎉';
      default: return '📢';
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'order_ready': return '#10B981';
      case 'delay_alert': return '#F59E0B';
      case 'order_cancelled': return '#EF4444';
      default: return '#3B82F6';
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={[styles.iconContainer, { backgroundColor: getNotificationColor(notification.notification_type) }]}>
        <Text style={styles.icon}>{getNotificationIcon(notification.notification_type)}</Text>
      </View>

      <View style={styles.content}>
        <Text style={styles.title}>{notification.title}</Text>
        <Text style={styles.timestamp}>
          {new Date(notification.created_at).toLocaleString()}
        </Text>

        <View style={styles.messageContainer}>
          <Text style={styles.message}>{notification.message}</Text>
        </View>

        <View style={styles.infoContainer}>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Type:</Text>
            <Text style={styles.infoValue}>{notification.notification_type}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Status:</Text>
            <Text style={[styles.infoValue, { color: notification.is_read ? '#6B7280' : '#10B981' }]}>
              {notification.is_read ? 'Read' : 'Unread'}
            </Text>
          </View>
          {notification.reference_id && (
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Reference ID:</Text>
              <Text style={styles.infoValue}>#{notification.reference_id}</Text>
            </View>
          )}
        </View>

        {!notification.is_read && (
          <TouchableOpacity style={styles.markReadButton}>
            <Text style={styles.markReadButtonText}>Mark as Read</Text>
          </TouchableOpacity>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    alignSelf: 'center',
    marginTop: 60,
    marginBottom: 24,
  },
  icon: {
    fontSize: 40,
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
    textAlign: 'center',
  },
  timestamp: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 24,
  },
  messageContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  message: {
    fontSize: 16,
    color: '#374151',
    lineHeight: 24,
  },
  infoContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  infoLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  infoValue: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '600',
  },
  markReadButton: {
    backgroundColor: '#10B981',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  markReadButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});