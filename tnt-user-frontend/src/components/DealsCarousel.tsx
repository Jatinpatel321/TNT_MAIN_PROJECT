import React, { useEffect, useRef, useState } from 'react';
import { Dimensions, FlatList, ImageBackground, StyleSheet, View, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import LinearGradient from 'react-native-linear-gradient';
import { DEAL_IMAGES } from '../assets/images';

const { width } = Dimensions.get('window');
// Card takes up most of the screen width minus padding
const CARD_WIDTH = width - 40; 

type Deal = {
  id: string;
  title: string;
  description: string;
  discount: string;
  image: any;
};

const DEALS: Deal[] = [
  {
    id: '1',
    title: 'Burger Combo',
    description: 'Veg Burger + Fries + Coke',
    discount: '25% OFF',
    image: DEAL_IMAGES.burger_combo,
  },
  {
    id: '2',
    title: 'Cafe Breakfast',
    description: 'Coffee + Sandwich',
    discount: '20% OFF',
    image: DEAL_IMAGES.coffee_sandwich,
  },
  {
    id: '3',
    title: 'Student Stationery Pack',
    description: 'Notebook + Pens',
    discount: '15% OFF',
    image: DEAL_IMAGES.stationery_combo,
  },
];

export function DealsCarousel() {
  const flatListRef = useRef<FlatList>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  // Autoplay
  const activeIndexRef = useRef(0);

  useEffect(() => {
    activeIndexRef.current = activeIndex;
  }, [activeIndex]);

  useEffect(() => {
    const interval = setInterval(() => {
      const next = (activeIndexRef.current + 1) % DEALS.length;
      flatListRef.current?.scrollToIndex({
        index: next,
        animated: true,
      });
      setActiveIndex(next);
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const renderItem = ({ item }: { item: Deal }) => {
    return (
      <TouchableOpacity activeOpacity={0.9} style={styles.cardContainer}>
        <ImageBackground source={item.image} style={styles.imageBackground} imageStyle={styles.imageStyle}>
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.85)']}
            style={styles.gradient}
          >
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{item.discount}</Text>
            </View>
            <View style={styles.textContainer}>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.description}>{item.description}</Text>
            </View>
          </LinearGradient>
        </ImageBackground>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        ref={flatListRef}
        data={DEALS}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        horizontal
        showsHorizontalScrollIndicator={false}
        pagingEnabled
        snapToInterval={CARD_WIDTH + 10} // Width + margin
        decelerationRate="fast"
        contentContainerStyle={styles.listContent}
        onMomentumScrollEnd={(e) => {
            const x = e.nativeEvent.contentOffset.x;
            setActiveIndex(Math.round(x / (CARD_WIDTH + 10)));
        }}
      />
      
      {/* Dots Indicator */}
      <View style={styles.dotsContainer}>
        {DEALS.map((_, i) => (
            <View 
                key={i} 
                style={[
                    styles.dot, 
                    activeIndex === i ? styles.activeDot : styles.inactiveDot
                ]} 
            />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 10,
  },
  listContent: {
    paddingHorizontal: 20,
    // Add gap via styles or ItemSeparatorComponent if needed, 
    // but here margin on card is easier for paging alignment
  },
  cardContainer: {
    width: CARD_WIDTH,
    height: 180,
    borderRadius: 18,
    overflow: 'hidden',
    marginRight: 10, // Spacing between cards
    backgroundColor: '#f0f0f0', // Placeholder while loading
  },
  imageBackground: {
    width: '100%',
    height: '100%',
    justifyContent: 'flex-end',
  },
  imageStyle: {
    borderRadius: 18,
  },
  gradient: {
    height: '100%',
    justifyContent: 'flex-end',
    padding: 16,
    borderRadius: 18,
  },
  badge: {
    position: 'absolute',
    top: 16,
    right: 16,
    backgroundColor: '#FF4757',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  badgeText: {
    color: '#FFF',
    fontWeight: '700',
    fontSize: 12,
  },
  textContainer: {
    gap: 4,
  },
  title: {
    color: '#FFF',
    fontSize: 22,
    fontWeight: '800',
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  description: {
    color: '#E0E0E0',
    fontSize: 14,
    fontWeight: '500',
  },
  dotsContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      marginTop: 10,
      gap: 6
  },
  dot: {
      height: 8,
      borderRadius: 4,
  },
  activeDot: {
      width: 24,
      backgroundColor: '#6C63FF',
  },
  inactiveDot: {
      width: 8,
      backgroundColor: '#D1D5DB',
  }
});
