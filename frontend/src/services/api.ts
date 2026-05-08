import axios, { AxiosError, type AxiosInstance } from "axios";

import { env } from "@/lib/env";
import type { ApiErrorDetail, ApiErrorResponse } from "@/types/api";

const fallbackError: ApiErrorDetail = {
  code: "NETWORK_ERROR",
  message: "Unable to reach the TradeSignal API.",
  fields: []
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value)) {
    return false;
  }

  const error = value.error;
  if (!isRecord(error)) {
    return false;
  }

  return (
    value.success === false &&
    typeof error.code === "string" &&
    typeof error.message === "string" &&
    Array.isArray(error.fields)
  );
}

function detailFromAxiosError(error: AxiosError<unknown>): ApiErrorDetail {
  const responseData = error.response?.data;

  if (isApiErrorResponse(responseData)) {
    return responseData.error;
  }

  if (error.response) {
    return {
      code: `HTTP_${error.response.status}`,
      message: error.response.statusText || "The API returned an error.",
      fields: []
    };
  }

  return fallbackError;
}

export class ApiClientError extends Error {
  readonly detail: ApiErrorDetail;
  readonly status?: number;

  constructor(detail: ApiErrorDetail, status?: number) {
    super(detail.message);
    this.name = "ApiClientError";
    this.detail = detail;
    this.status = status;
  }
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
  headers: {
    Accept: "application/json"
  },
  timeout: 10_000
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      return Promise.reject(new ApiClientError(detailFromAxiosError(error), error.response?.status));
    }

    return Promise.reject(
      new ApiClientError({
        code: "UNKNOWN_CLIENT_ERROR",
        message: "An unexpected client error occurred.",
        fields: []
      })
    );
  }
);
