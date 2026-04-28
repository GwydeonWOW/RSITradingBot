import { post } from "./client";
import type {
  ExceptionClassifyRequest,
  ExceptionClassifyResponse,
} from "@/types";

export function classifyException(req: ExceptionClassifyRequest) {
  return post<ExceptionClassifyResponse>("/v1/ai/exceptions/classify", req);
}
