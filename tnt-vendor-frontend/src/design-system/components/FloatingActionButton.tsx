// ─── FloatingActionButton ─────────────────────────────────────────
// Premium FAB with expandable menu

import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  ViewStyle,
  Modal,
  Pressable,
} from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface FABAction {
  icon: string;
  label: string;
  color?: string;
  onPress: () => void;
}

interface FloatingActionButtonProps {
  actions: FABAction[];
  mainIcon?: string;
  color?: string;
  style?: ViewStyle;
}

export default function FloatingActionButton({
  actions,
  mainIcon = '⚡',
  color = colors.primary,
  style,
}: FloatingActionButtonProps) {
  const [open, setOpen] = useState(false);
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(rotateAnim, {
        toValue: open ? 1 : 0,
        useNativeDriver: true,
        friction: 6,
        tension: 100,
      }),
      Animated.timing(fadeAnim, {
        toValue: open ? 1 : 0,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start();
  }, [open]);

  const rotation = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '45deg'],
  });

  return (
    <>
      {/* Overlay */}
      {open && (
        <Pressable style={styles.overlay} onPress={() => setOpen(false)} />
      )}

      {/* Action Items */}
      {open && (
        <View style={styles.actionsContainer}>
          {actions.map((action, index) => (
            <Animated.View
              key={index}
              style={[
                styles.actionItem,
                {
                  opacity: fadeAnim,
                  transform: [
                    {
                      translateY: fadeAnim.interpolate({
                        inputRange: [0, 1],
                        outputRange: [20, 0],
                      }),
                    },
                  ],
                },
              ]}
            >
              <TouchableOpacity
                style={[styles.actionCircle, { backgroundColor: action.color || color }]}
                onPress={() => {
                  action.onPress();
                  setOpen(false);
                }}
                activeOpacity={0.8}
              >
                <Text style={styles.actionIcon}>{action.icon}</Text>
              </TouchableOpacity>
              <Text style={styles.actionLabel}>{action.label}</Text>
            </Animated.View>
          ))}
        </View>
      )}

      {/* Main FAB Button */}
      <TouchableOpacity
        style={[styles.fab, { backgroundColor: color }, style]}
        onPress={() => setOpen(!open)}
        activeOpacity={0.85}
      >
        <Animated.Text style={[styles.fabIcon, { transform: [{ rotate: rotation }] }]}>
          {mainIcon}
        </Animated.Text>
      </TouchableOpacity>
    </>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.3)',
    zIndex: 998,
  },
  actionsContainer: {
    position: 'absolute',
    bottom: 100,
    right: 20,
    zIndex: 999,
    gap: 12,
    alignItems: 'flex-end',
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  actionCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.fab,
  },
  actionIcon: {
    fontSize: 22,
  },
  actionLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textInverse,
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    overflow: 'hidden',
  },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
    ...shadows.fab,
  },
  fabIcon: {
    fontSize: 26,
  },
});
