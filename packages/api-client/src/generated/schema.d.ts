// GENERATED from contracts/openapi/openapi.json; DO NOT EDIT.
export interface paths {
  "/health": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["healthCheck"];
  };
}

export interface components {
  schemas: {
    HealthResponse: {
      capabilities: string[];
      service: string;
      status: string;
    };
  };
}

export interface operations {
  healthCheck: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: Record<string, unknown>;
        content: {
          "application/json": components["schemas"]["HealthResponse"];
        };
      };
    };
  };
}
