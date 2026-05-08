export type FieldError = {
  loc: string[];
  msg: string;
  type: string;
};

export type ApiErrorDetail = {
  code: string;
  message: string;
  fields: FieldError[];
};

export type ApiSuccessResponse<TData> = {
  success: true;
  data: TData;
};

export type ApiErrorResponse = {
  success: false;
  error: ApiErrorDetail;
};

export type PaginationMeta = {
  total: number;
  page: number;
  per_page: number;
  pages: number;
};

export type PaginatedResponse<TData> = {
  success: true;
  data: TData[];
  pagination: PaginationMeta;
};
