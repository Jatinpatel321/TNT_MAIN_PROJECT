import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { Cart } from '../types/models';
import {
  addCartItem,
  clearCart as clearCartApi,
  getCartByUserId,
  removeCartItem,
  updateCartItem,
} from '../services/cartService';
import { useAuth } from '../hooks/useAuth';

export type CartContextState = {
  cart: Cart | null;
  loading: boolean;
  addItem: (menuItemId: number, quantity?: number) => Promise<void>;
  removeItem: (menuItemId: number) => Promise<void>;
  updateQuantity: (menuItemId: number, quantity: number) => Promise<void>;
  clearCart: () => Promise<void>;
};

const CartContext = createContext<CartContextState | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        if (!user?.id) {
          setCart({ vendor_id: null, items: [], total_items: 0, total_amount: 0 });
          return;
        }

        const c = await getCartByUserId(user.id);
        setCart(c);
      } catch (e) {
        setCart({ vendor_id: null, items: [], total_items: 0, total_amount: 0 });
      } finally {
        setLoading(false);
      }
    })();
  }, [user?.id]);

  const addItem = async (menuItemId: number, quantity = 1) => {
    // quantity here is a DELTA (matches POST /cart/add semantics)
    const c = await addCartItem(menuItemId, quantity);
    setCart(c);
  };

  const removeItem = async (menuItemId: number) => {
    const c = await removeCartItem(menuItemId);
    setCart(c);
  };

  const updateQuantity = async (menuItemId: number, quantity: number) => {
    if (quantity <= 0) {
      await removeItem(menuItemId);
      return;
    }
    const c = await updateCartItem(menuItemId, quantity);
    setCart(c);
  };

  const clearCart = async () => {
    await clearCartApi();
    if (user?.id) {
      const c = await getCartByUserId(user.id);
      setCart(c);
    } else {
      setCart({ vendor_id: null, items: [], total_items: 0, total_amount: 0 });
    }
  };

  const value = useMemo(
    () => ({ cart, loading, addItem, removeItem, updateQuantity, clearCart }),
    [cart, loading]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextState {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
}
