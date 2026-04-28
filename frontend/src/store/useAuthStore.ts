import { create } from "zustand";
import * as authApi from "@/api/auth";
import type { User } from "@/types";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem("token"),
  user: null,
  isAuthenticated: !!localStorage.getItem("token"),

  login: async (email, password) => {
    const res = await authApi.login(email, password);
    localStorage.setItem("token", res.token);
    set({ token: res.token, user: res.user, isAuthenticated: true });
  },

  register: async (email, password) => {
    const res = await authApi.register(email, password);
    localStorage.setItem("token", res.token);
    set({ token: res.token, user: res.user, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null, isAuthenticated: false });
    window.location.href = "/login";
  },

  loadUser: async () => {
    const { token } = get();
    if (!token) return;

    try {
      const user = await authApi.getMe();
      set({ user, isAuthenticated: true });
    } catch {
      // Token is invalid/expired -- clear it
      localStorage.removeItem("token");
      set({ token: null, user: null, isAuthenticated: false });
    }
  },
}));
