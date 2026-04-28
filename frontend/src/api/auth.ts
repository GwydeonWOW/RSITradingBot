import { post, get } from "./client";
import type { AuthResponse, User } from "@/types";

export function register(email: string, password: string) {
  return post<AuthResponse>("/v1/auth/register", { email, password });
}

export function login(email: string, password: string) {
  return post<AuthResponse>("/v1/auth/login", { email, password });
}

export function getMe() {
  return get<User>("/v1/auth/me");
}
