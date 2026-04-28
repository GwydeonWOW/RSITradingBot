import { create } from "zustand";

interface AuthState {
  apiKey: string;
  walletAddress: string;
  setApiKey: (key: string) => void;
  setWalletAddress: (addr: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  apiKey: "",
  walletAddress: "",
  setApiKey: (key) => set({ apiKey: key }),
  setWalletAddress: (addr) => set({ walletAddress: addr }),
}));
