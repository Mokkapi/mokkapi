// src/types.ts

export interface Endpoint {
  id: string;
  name: string;
  url: string;
  /* …other fields… */
}

export interface Handler {
  id: string;
  endpointId: string;
  method: string;
  /* … */
}

export interface AuthProfile {
  id: string;
  provider: string;
  /* … */
}
