import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import type { Business } from '@/types/business';
import type { BusinessMembershipRole } from '@/types/businessMembership';
import { apiClient } from '@/services/apiClient';
import { useAuth } from './AuthContext';

interface BusinessContextType {
  businessId: string | null;
  business: Business | null;
  role: BusinessMembershipRole | null;
  isLoading: boolean;
  error: string | null;
  refreshBusiness: () => Promise<void>;
}

const BusinessContext = createContext<BusinessContextType | undefined>(undefined);

export const BusinessProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { businessId: routeBusinessId } = useParams<{ businessId: string }>();
  const location = useLocation();
  const { user } = useAuth();

  // Extract businessId from URL pathname if useParams doesn't capture it (e.g. in layout wrappers)
  const extractBusinessId = (): string | null => {
    if (routeBusinessId) return routeBusinessId;
    const match = location.pathname.match(/\/businesses\/([^/]+)/);
    return match ? match[1] : null;
  };

  const currentBusinessId = extractBusinessId();

  const [business, setBusiness] = useState<Business | null>(null);
  const [role, setRole] = useState<BusinessMembershipRole | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBusinessData = useCallback(async () => {
    if (!currentBusinessId || !user) {
      setBusiness(null);
      setRole(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Fetch business details
      const bizData = await apiClient.getBusiness(currentBusinessId);
      setBusiness(bizData);

      // Determine role:
      if (bizData.owner_user_id === user.id) {
        setRole('OWNER');
      } else {
        try {
          // Attempt to list members to find own role
          const members = await apiClient.listBusinessMembers(currentBusinessId);
          const myMembership = members.find((m) => m.user_id === user.id);
          setRole(myMembership?.role || 'MEMBER');
        } catch {
          // If listing members is denied (e.g., MEMBER role), fallback to MEMBER
          setRole('MEMBER');
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data bisnis.';
      setError(msg);
      setBusiness(null);
      setRole(null);
    } finally {
      setIsLoading(false);
    }
  }, [currentBusinessId, user]);

  useEffect(() => {
    fetchBusinessData();
  }, [fetchBusinessData]);

  return (
    <BusinessContext.Provider
      value={{
        businessId: currentBusinessId,
        business,
        role,
        isLoading,
        error,
        refreshBusiness: fetchBusinessData,
      }}
    >
      {children}
    </BusinessContext.Provider>
  );
};

export const useBusiness = (): BusinessContextType => {
  const context = useContext(BusinessContext);
  if (!context) {
    throw new Error('useBusiness must be used within a BusinessProvider');
  }
  return context;
};
