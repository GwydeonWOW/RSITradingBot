import { get, post, del } from "./client";
import type { Wallet, WalletBalance, ConnectWalletRequest } from "@/types";

export function connectWallet(data: ConnectWalletRequest) {
  return post<Wallet>("/v1/wallets", data);
}

export function getWallets() {
  return get<Wallet[]>("/v1/wallets");
}

export function deleteWallet(id: string) {
  return del<void>(`/v1/wallets/${id}`);
}

export function getWalletBalance(id: string) {
  return get<WalletBalance>(`/v1/wallets/${id}/balance`);
}
