import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCurrentUser,
  signIn as signInRequest,
  signOut as signOutRequest,
} from "@/api/auth";
import type { CurrentUser } from "@/types/documents";

const CURRENT_USER_KEY = ["auth", "me"];

interface AuthContextValue {
  user: CurrentUser | null;
  groups: string[];
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<unknown>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const currentUserQuery = useQuery({
    queryKey: CURRENT_USER_KEY,
    queryFn: fetchCurrentUser,
    enabled: true,
    retry: false,
  });

  const signIn = useCallback(
    async (username: string, password: string) => {
      const user = await signInRequest(username, password);
      queryClient.setQueryData(CURRENT_USER_KEY, user);
    },
    [queryClient],
  );

  const signOut = useCallback(async () => {
    try {
      await signOutRequest();
    } finally {
      queryClient.setQueryData(CURRENT_USER_KEY, null);
      queryClient.clear();
    }
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(() => {
    const user = currentUserQuery.data ?? null;

    return {
      user,
      groups: user?.groups ?? [],
      isAuthenticated: Boolean(user),
      isLoading: currentUserQuery.isLoading,
      signIn,
      signOut,
      refreshUser: currentUserQuery.refetch,
    };
  }, [
    currentUserQuery.data,
    currentUserQuery.isLoading,
    currentUserQuery.refetch,
    signIn,
    signOut,
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
