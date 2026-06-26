import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';

interface MenuItem {
  id: number;
  name: string;
  price: number;
  category: string;
  available: boolean;
}

export default function MenuScreen() {
  const menuItems: MenuItem[] = [
    { id: 1, name: 'Masala Dosa', price: 80, category: 'Breakfast', available: true },
    { id: 2, name: 'Idli Sambar', price: 50, category: 'Breakfast', available: true },
    { id: 3, name: 'Filter Coffee', price: 20, category: 'Beverages', available: true },
  ];

  return (
    <View style={styles.container}>
      <FlatList
        data={menuItems}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.menuCard}>
            <View style={styles.menuInfo}>
              <Text style={styles.menuName}>{item.name}</Text>
              <Text style={styles.menuCategory}>{item.category}</Text>
              <Text style={styles.menuPrice}>₹{item.price}</Text>
            </View>
            <View style={[styles.availabilityBadge, { backgroundColor: item.available ? '#10B981' : '#EF4444' }]}>
              <Text style={styles.availabilityText}>{item.available ? 'Available' : 'Unavailable'}</Text>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    padding: 16,
  },
  menuCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  menuInfo: {
    flex: 1,
  },
  menuName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  menuCategory: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 4,
  },
  menuPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#10B981',
  },
  availabilityBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  availabilityText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
});