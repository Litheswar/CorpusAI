-- ==============================================================================
-- CorpusAI — Migration 001: Initial Core Schema & Multi-Tenant Isolation
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Companies Table (Tenants)
CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL CHECK (char_length(name) >= 2 AND char_length(name) <= 255),
    slug TEXT NOT NULL UNIQUE CHECK (char_length(slug) >= 2 AND char_length(slug) <= 100),
    subscription_tier TEXT NOT NULL DEFAULT 'starter' CHECK (subscription_tier IN ('starter', 'growth', 'enterprise')),
    max_documents INTEGER NOT NULL DEFAULT 100 CHECK (max_documents >= 0),
    max_storage_bytes BIGINT NOT NULL DEFAULT 5368709120 CHECK (max_storage_bytes >= 0),
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for companies
CREATE INDEX IF NOT EXISTS idx_companies_slug ON public.companies(slug);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON public.companies(created_at);

-- 3. Departments Table
CREATE TABLE IF NOT EXISTS public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (char_length(name) >= 1 AND char_length(name) <= 100),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_departments_company_name UNIQUE (company_id, name)
);

-- Indexes for departments
CREATE INDEX IF NOT EXISTS idx_departments_company_id ON public.departments(company_id);

-- 4. Profiles Table (Binds Supabase auth.users to a Company Tenant)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL CHECK (char_length(full_name) >= 1 AND char_length(full_name) <= 255),
    role TEXT NOT NULL DEFAULT 'employee' CHECK (role IN ('owner', 'admin', 'employee')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_company_id ON public.profiles(company_id);
CREATE INDEX IF NOT EXISTS idx_profiles_department_id ON public.profiles(department_id);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);

-- 5. Updated At Trigger Function
CREATE OR REPLACE FUNCTION public.set_current_timestamp_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_companies_updated_at ON public.companies;
CREATE TRIGGER trg_companies_updated_at
BEFORE UPDATE ON public.companies
FOR EACH ROW
EXECUTE FUNCTION public.set_current_timestamp_updated_at();

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.set_current_timestamp_updated_at();

-- ==============================================================================
-- 6. Anti-Recursion Helper Functions for Row Level Security (RLS)
-- ==============================================================================
-- Querying `profiles` directly inside an RLS policy on `profiles` triggers 
-- infinite policy recursion.
-- We use minimal SECURITY DEFINER functions with fixed search_path to resolve 
-- the authenticated user's company and role cleanly without recursive evaluation.

CREATE OR REPLACE FUNCTION public.get_auth_user_company_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT company_id FROM public.profiles WHERE id = auth.uid() AND is_active = TRUE;
$$;

CREATE OR REPLACE FUNCTION public.get_auth_user_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role FROM public.profiles WHERE id = auth.uid() AND is_active = TRUE;
$$;

-- Grant execution to authenticated users
GRANT EXECUTE ON FUNCTION public.get_auth_user_company_id() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_auth_user_role() TO authenticated;

-- ==============================================================================
-- 7. Row Level Security (RLS) Policies
-- ==============================================================================

-- Enable RLS on all tenant-owned tables
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- Companies Policies
-- ------------------------------------------------------------------------------
-- Authenticated users can view only their own company
CREATE POLICY companies_select_tenant ON public.companies
FOR SELECT
TO authenticated
USING (
    id = public.get_auth_user_company_id()
);

-- Company owners can update their own company settings
CREATE POLICY companies_update_owner ON public.companies
FOR UPDATE
TO authenticated
USING (
    id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() = 'owner'
)
WITH CHECK (
    id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() = 'owner'
);

-- Authenticated users can create a new company during registration onboarding
CREATE POLICY companies_insert_authenticated ON public.companies
FOR INSERT
TO authenticated
WITH CHECK (
    TRUE
);

-- ------------------------------------------------------------------------------
-- Departments Policies
-- ------------------------------------------------------------------------------
-- Employees can view departments within their own company
CREATE POLICY departments_select_tenant ON public.departments
FOR SELECT
TO authenticated
USING (
    company_id = public.get_auth_user_company_id()
);

-- Owners and Admins can create departments within their company
CREATE POLICY departments_insert_admin ON public.departments
FOR INSERT
TO authenticated
WITH CHECK (
    company_id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() IN ('owner', 'admin')
);

-- Owners and Admins can update departments within their company
CREATE POLICY departments_update_admin ON public.departments
FOR UPDATE
TO authenticated
USING (
    company_id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() IN ('owner', 'admin')
)
WITH CHECK (
    company_id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() IN ('owner', 'admin')
);

-- Owners and Admins can delete departments within their company
CREATE POLICY departments_delete_admin ON public.departments
FOR DELETE
TO authenticated
USING (
    company_id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() IN ('owner', 'admin')
);

-- ------------------------------------------------------------------------------
-- Profiles Policies
-- ------------------------------------------------------------------------------
-- Users can see their own profile OR colleagues in the same company
-- (Using auth.uid() directly for self-read avoids function call for common path)
CREATE POLICY profiles_select_tenant ON public.profiles
FOR SELECT
TO authenticated
USING (
    id = auth.uid()
    OR company_id = public.get_auth_user_company_id()
);

-- Users can insert their own profile during initial signup/onboarding
CREATE POLICY profiles_insert_self ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (
    id = auth.uid()
);

-- Users can update their own profile name, or Owners/Admins can manage members
CREATE POLICY profiles_update_self_or_admin ON public.profiles
FOR UPDATE
TO authenticated
USING (
    id = auth.uid()
    OR (
        company_id = public.get_auth_user_company_id()
        AND public.get_auth_user_role() IN ('owner', 'admin')
    )
)
WITH CHECK (
    id = auth.uid()
    OR (
        company_id = public.get_auth_user_company_id()
        AND public.get_auth_user_role() IN ('owner', 'admin')
    )
);

-- Owners can remove members from their company
CREATE POLICY profiles_delete_owner ON public.profiles
FOR DELETE
TO authenticated
USING (
    company_id = public.get_auth_user_company_id()
    AND public.get_auth_user_role() = 'owner'
    AND id != auth.uid() -- Owner cannot delete their own profile directly
);
