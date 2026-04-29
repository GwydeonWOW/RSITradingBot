import { get, post, del, patch } from "./client";
import type { Wallet, WalletBalance, ConnectWalletRequest } from "@/types";

export function connectWallet(data: ConnectWalletRequest) {
  return post<Wallet>("/v1/wallets", data);
}

export function getWallets() {
  return get<Wallet[]>("/v1/wallets");
}

export function updateWallet(id: string, data: { master_address?: string }) {
  return patch<Wallet>(`/v1/wallets/${id}`, data);
}

export function deleteWallet(id: string) {
  return del<void>(`/v1/wallets/${id}`);
}

export function getWalletBalance(id: string) {
  return get<WalletBalance>(`/v1/wallets/${id}/balance`);
}
