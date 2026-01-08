
// src/hooks/useAuth.ts
import { useState, useEffect } from "react";

export interface User {
  is_authenticated: boolean;
  is_staff: boolean;
  username: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);

  // TODO eventually move this util endpoint to the API spec?
  useEffect(() => {
    fetch("/_mokkapi_api/whoami/", {
      credentials: "include",
    })
      .then(res => res.json())
      .then((data: User) => setUser(data))
      .catch(() => setUser({ is_authenticated: false, is_staff: false, username: "" }));
  }, []);

  return { user, setUser };
}
