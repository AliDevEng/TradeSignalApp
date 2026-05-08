export type ComponentState = "ok" | "degraded" | "down" | "not_configured";
export type OverallState = Exclude<ComponentState, "not_configured">;

export type ComponentStatus = {
  status: ComponentState;
  detail?: string | null;
};

export type HealthResponse = {
  status: OverallState;
  version: string;
  environment: string;
  timestamp: string;
  python_version: string;
  components: Record<string, ComponentStatus>;
};
