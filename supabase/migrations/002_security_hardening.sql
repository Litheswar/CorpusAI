-- ==============================================================================
-- CorpusAI — Migration 002: Security Hardening, Anti-Escalation & Atomic Onboarding
-- ==============================================================================

-- 1. Drop Vulnerable Policies from Migration 001
DROP POLICY IF EXISTS profiles_insert_self ON public.profiles;
DROP POLICY IF EXISTS profiles_update_self_or_admin ON public.profiles;
DROP POLICY IF EXISTS companies_insert_authenticated ON public.companies;

-- ------------------------------------------------------------------------------
-- 2. Hardened Profiles RLS Policies
-- ------------------------------------------------------------------------------

-- Users can only update their own profile fields (e.g. full_name).
-- CRITICAL SECURITY RULE: Users cannot alter their company_id or escalate their role.
CREATE POLICY profiles_update_self ON public.profiles
FOR UPDATE
TO authenticated
USING (
    id = auth.uid()
)
WITH CHECK (
    id = auth.uid()
    AND company_id = public.get_auth_user_company_id()
    AND role = public.get_auth_user_role()
);

-- Company Owners and Admins can manage member departments and roles within their company.
CREATE POLICY profiles_update_admin ON public.profiles
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

-- ------------------------------------------------------------------------------
-- 3. Atomic Company & Owner Onboarding Function (RPC)
-- ------------------------------------------------------------------------------
-- Ensures single-transaction, atomic provisioning of company + owner profile.
-- Enforces:
-- 1. User must be authenticated (auth.uid() IS NOT NULL)
-- 2. User cannot already belong to an active company
-- 3. Company slug must be unique
-- 4. Company record and owner profile are committed together or rolled back atomically

CREATE OR REPLACE FUNCTION public.create_company_with_owner(
    p_name TEXT,
    p_slug TEXT,
    p_full_name TEXT DEFAULT NULL,
    p_settings JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_user_email TEXT;
    v_company_id UUID;
    v_company_row RECORD;
    v_profile_row RECORD;
    v_existing_profile RECORD;
BEGIN
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    -- Check if user already has an active company profile
    SELECT * INTO v_existing_profile FROM public.profiles WHERE id = v_user_id;
    IF v_existing_profile.id IS NOT NULL AND v_existing_profile.company_id IS NOT NULL THEN
        RAISE EXCEPTION 'User is already associated with an existing company workspace' USING ERRCODE = '23505';
    END IF;

    -- Validate input lengths
    IF char_length(p_name) < 2 OR char_length(p_name) > 255 THEN
        RAISE EXCEPTION 'Company name must be between 2 and 255 characters' USING ERRCODE = '22000';
    END IF;

    IF char_length(p_slug) < 2 OR char_length(p_slug) > 100 THEN
        RAISE EXCEPTION 'Company slug must be between 2 and 100 characters' USING ERRCODE = '22000';
    END IF;

    -- Check slug uniqueness
    IF EXISTS (SELECT 1 FROM public.companies WHERE slug = p_slug) THEN
        RAISE EXCEPTION 'Company slug is already taken' USING ERRCODE = '23505';
    END IF;

    -- Get user email from auth.users
    SELECT email INTO v_user_email FROM auth.users WHERE id = v_user_id;

    -- 1. Create company record
    INSERT INTO public.companies (name, slug, subscription_tier, settings)
    VALUES (p_name, p_slug, 'starter', p_settings)
    RETURNING * INTO v_company_row;

    v_company_id := v_company_row.id;

    -- 2. Create owner profile record
    INSERT INTO public.profiles (id, company_id, email, full_name, role, is_active)
    VALUES (
        v_user_id,
        v_company_id,
        COALESCE(v_user_email, 'user@corpusai.internal'),
        COALESCE(p_full_name, p_name || ' Owner'),
        'owner',
        TRUE
    )
    RETURNING * INTO v_profile_row;

    RETURN jsonb_build_object(
        'company', to_jsonb(v_company_row),
        'profile', to_jsonb(v_profile_row)
    );
END;
$$;

-- Grant execution to authenticated users
GRANT EXECUTE ON FUNCTION public.create_company_with_owner(TEXT, TEXT, TEXT, JSONB) TO authenticated;
